"""Report rendering for sf-scan.

Two formats are produced from a single render call:
- ``report.json``: machine-readable, with a flat ``findings`` list, an
  ``ontology_index`` nested by PRD → Feature → Blueprint → Work Order, and an
  ``unmapped`` section.
- ``report.md``: human-readable, opening with an executive summary then
  walking the same ontology nesting with Markdown headings. Each ontology
  heading is a clickable link to the corresponding KG artifact file.

Rendering is pure Python — no Jinja2 dependency. The Markdown structure is
simple enough that string concatenation reads more clearly than a template.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .kg import KGNode, KGPath, KnowledgeGraph
from .models import Finding


_SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")
_ACTION_LIST_TOP_N = 10


@dataclass(frozen=True)
class ReportPaths:
    json_path: Path
    md_path: Path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def render(
    findings: list[Finding],
    kg: KnowledgeGraph,
    out_dir: Path,
    *,
    repo_label: str = "<unspecified>",
    sha: str | None = None,
    scan_errors: list[str] | None = None,
) -> ReportPaths:
    """Write ``report.json`` and ``report.md`` to ``out_dir`` and return paths."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map each finding to its KG path. Findings with no resolution end up in
    # the unmapped bucket.
    mapped: list[tuple[Finding, KGPath]] = []
    unmapped: list[Finding] = []
    for f in findings:
        path = kg.map_dependency(f.ecosystem, f.package)
        if path is not None and path.work_order is not None and path.prd is not None:
            mapped.append((f, path))
        else:
            unmapped.append(f)

    summary = _build_summary(mapped, unmapped)
    ontology_index = _build_ontology_index(mapped, out_dir)

    json_path = out_dir / "report.json"
    json_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "repo": {"label": repo_label, "sha": sha},
                "kg_source": kg.source_label,
                "findings": [_finding_to_dict(f, p, out_dir) for f, p in mapped]
                + [_finding_to_dict(f, None, out_dir) for f in unmapped],
                "ontology_index": ontology_index,
                "unmapped": [_finding_to_dict(f, None, out_dir) for f in unmapped],
                "scan_errors": list(scan_errors or []),
            },
            indent=2,
            sort_keys=False,
        )
    )

    md_path = out_dir / "report.md"
    md_path.write_text(
        _render_markdown(
            mapped=mapped,
            unmapped=unmapped,
            summary=summary,
            repo_label=repo_label,
            sha=sha,
            out_dir=out_dir,
            scan_errors=scan_errors or [],
            kg_source=kg.source_label,
        )
    )

    return ReportPaths(json_path=json_path, md_path=md_path)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


def _build_summary(
    mapped: list[tuple[Finding, KGPath]],
    unmapped: list[Finding],
) -> dict[str, Any]:
    all_findings = [f for f, _ in mapped] + unmapped
    by_severity = {sev: 0 for sev in _SEVERITY_ORDER}
    for f in all_findings:
        by_severity[f.severity if f.severity in by_severity else "UNKNOWN"] += 1

    prds_at_risk: set[str] = set()
    features_at_risk: set[str] = set()
    blueprints_at_risk: set[str] = set()
    work_orders_at_risk: set[str] = set()
    for _f, p in mapped:
        if p.prd is not None:
            prds_at_risk.add(p.prd.id)
        if p.feature is not None:
            features_at_risk.add(p.feature.id)
        if p.blueprint is not None:
            blueprints_at_risk.add(p.blueprint.id)
        if p.work_order is not None:
            work_orders_at_risk.add(p.work_order.id)

    # Action list: highest-severity findings first, capped at top N.
    ranked = sorted(
        mapped,
        key=lambda pair: (-pair[0].severity_rank, pair[0].package),
    )
    action_list = []
    for finding, path in ranked[:_ACTION_LIST_TOP_N]:
        action_list.append(
            {
                "cve_id": finding.cve_id,
                "package": finding.package,
                "version": finding.version,
                "severity": finding.severity,
                "fix_version": finding.fix_version,
                "prd": path.prd.id if path.prd else None,
                "work_order": path.work_order.id if path.work_order else None,
            }
        )

    return {
        "total_findings": len(all_findings),
        "mapped_count": len(mapped),
        "unmapped_count": len(unmapped),
        "by_severity": by_severity,
        "ontology_levels_at_risk": {
            "prds": sorted(prds_at_risk),
            "features": sorted(features_at_risk),
            "blueprints": sorted(blueprints_at_risk),
            "work_orders": sorted(work_orders_at_risk),
        },
        "action_list": action_list,
    }


# ---------------------------------------------------------------------------
# Ontology index (nested JSON shape)
# ---------------------------------------------------------------------------


def _build_ontology_index(
    mapped: list[tuple[Finding, KGPath]],
    out_dir: Path,
) -> dict[str, Any]:
    """Build the ``ontology_index`` JSON: PRD → Feature → Blueprint → WO → findings."""
    index: dict[str, Any] = {}
    for finding, path in mapped:
        prd = path.prd
        feature = path.feature
        bp = path.blueprint
        wo = path.work_order
        if prd is None or bp is None or wo is None:
            continue
        prd_entry = index.setdefault(
            prd.id,
            {
                "title": prd.title,
                "path": _node_link(out_dir, prd),
                "features": {},
                "foundation_blueprints": {},
            },
        )
        # Foundation paths skip the Feature level; nest them differently.
        if feature is None:
            fnd_entry = prd_entry["foundation_blueprints"].setdefault(
                bp.id,
                {
                    "title": bp.title,
                    "path": _node_link(out_dir, bp),
                    "work_orders": {},
                },
            )
            wo_entry = fnd_entry["work_orders"].setdefault(
                wo.id,
                {
                    "title": wo.title,
                    "path": _node_link(out_dir, wo),
                    "findings": [],
                },
            )
        else:
            feature_entry = prd_entry["features"].setdefault(
                feature.id,
                {
                    "title": feature.title,
                    "path": _node_link(out_dir, feature),
                    "blueprints": {},
                },
            )
            bp_entry = feature_entry["blueprints"].setdefault(
                bp.id,
                {
                    "title": bp.title,
                    "path": _node_link(out_dir, bp),
                    "work_orders": {},
                },
            )
            wo_entry = bp_entry["work_orders"].setdefault(
                wo.id,
                {
                    "title": wo.title,
                    "path": _node_link(out_dir, wo),
                    "findings": [],
                },
            )
        wo_entry["findings"].append(finding.cve_id)
    return index


# ---------------------------------------------------------------------------
# Finding serialization
# ---------------------------------------------------------------------------


def _finding_to_dict(
    finding: Finding, path: KGPath | None, out_dir: Path
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "cve_id": finding.cve_id,
        "package": finding.package,
        "ecosystem": finding.ecosystem,
        "version": finding.version,
        "severity": finding.severity,
        "summary": finding.summary,
        "fix_version": finding.fix_version,
        "sources": list(finding.sources),
        "references": list(finding.references),
    }
    if finding.dependency_ref is not None:
        base["manifest_path"] = finding.dependency_ref.manifest_path
        base["kind"] = finding.dependency_ref.kind
    if path is not None:
        base["kg_path"] = {
            "work_order": _node_summary(path.work_order, out_dir),
            "blueprint": _node_summary(path.blueprint, out_dir),
            "feature": _node_summary(path.feature, out_dir),
            "prd": _node_summary(path.prd, out_dir),
        }
    return base


def _node_summary(node: KGNode | None, out_dir: Path) -> dict[str, Any] | None:
    if node is None:
        return None
    return {
        "id": node.id,
        "title": node.title,
        "path": _link_to(out_dir, node.path) if node.path else None,
        "url": node.url,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_markdown(
    *,
    mapped: list[tuple[Finding, KGPath]],
    unmapped: list[Finding],
    summary: dict[str, Any],
    repo_label: str,
    sha: str | None,
    out_dir: Path,
    scan_errors: list[str],
    kg_source: str,
) -> str:
    lines: list[str] = []

    # Header
    header = f"# Security Scan: {repo_label}"
    if sha:
        header += f" @ `{sha[:12]}`"
    lines.append(header)
    lines.append("")
    lines.append(
        "*Generated by [sf-scan](../..) — dependency vulnerabilities mapped "
        "to the Software Factory Knowledge Graph ontology.*"
    )
    lines.append("")
    lines.append(f"*Knowledge Graph source: {kg_source}.*")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Total findings:** {summary['total_findings']}")
    lines.append(f"  - Mapped to Knowledge Graph: {summary['mapped_count']}")
    lines.append(f"  - Unmapped (KG coverage gap): {summary['unmapped_count']}")
    lines.append("")
    lines.append("**Findings by severity:**")
    lines.append("")
    for sev in _SEVERITY_ORDER:
        count = summary["by_severity"][sev]
        if count > 0:
            lines.append(f"- **{sev}:** {count}")
    if all(summary["by_severity"][s] == 0 for s in _SEVERITY_ORDER):
        lines.append("- No vulnerabilities found. ✅")
    lines.append("")

    levels = summary["ontology_levels_at_risk"]
    lines.append("**Ontology levels at risk:**")
    lines.append("")
    lines.append(
        f"- **PRDs:** {len(levels['prds'])} "
        + (f"({', '.join(levels['prds'])})" if levels["prds"] else "")
    )
    lines.append(
        f"- **Features:** {len(levels['features'])} "
        + (f"({', '.join(levels['features'])})" if levels["features"] else "")
    )
    lines.append(
        f"- **Blueprints:** {len(levels['blueprints'])} "
        + (f"({', '.join(levels['blueprints'])})" if levels["blueprints"] else "")
    )
    lines.append(
        f"- **Work Orders:** {len(levels['work_orders'])} "
        + (
            f"({', '.join(levels['work_orders'])})"
            if levels["work_orders"]
            else ""
        )
    )
    lines.append("")

    if summary["action_list"]:
        lines.append("**Risk-prioritized action list (top critical/high):**")
        lines.append("")
        for i, item in enumerate(summary["action_list"], 1):
            pkg = item["package"]
            ver = item["version"] or "*"
            sev = item["severity"]
            fix = item["fix_version"] or "no fix available"
            prd = item["prd"] or "—"
            wo = item["work_order"] or "—"
            lines.append(
                f"{i}. **[{item['cve_id']}]** `{pkg}@{ver}` — **{sev}** → "
                f"upgrade to `{fix}`. Affects {prd} / {wo}."
            )
        lines.append("")

    if scan_errors:
        lines.append("**Scan warnings:**")
        lines.append("")
        for e in scan_errors:
            lines.append(f"- {e}")
        lines.append("")

    # Findings by ontology
    lines.append("---")
    lines.append("")
    lines.append("## Findings by PRD Requirement")
    lines.append("")

    if not mapped:
        lines.append("*No findings mapped to a PRD.*")
        lines.append("")
    else:
        lines.extend(_render_mapped_findings(mapped, out_dir))

    # Unmapped
    if unmapped:
        lines.append("---")
        lines.append("")
        lines.append("## Unmapped Findings")
        lines.append("")
        lines.append(
            "These findings affect packages not declared in any Work Order's "
            "`dependencies-introduced` field. The Knowledge Graph has a coverage "
            "gap here — itself a Lens 4 (alignment-debt) precursor: an explicit "
            "translation-loss score would quantify how much of the implemented "
            "code surface the KG fails to describe."
        )
        lines.append("")
        for f in sorted(unmapped, key=lambda x: (-x.severity_rank, x.package)):
            lines.append(_format_finding_bullet(f))
        lines.append("")

    return "\n".join(lines) + "\n"


def _render_mapped_findings(
    mapped: list[tuple[Finding, KGPath]],
    out_dir: Path,
) -> list[str]:
    # Group by PRD → Feature (or "<foundation>") → Blueprint → WO.
    grouped: dict[str, Any] = {}
    for f, p in mapped:
        prd = p.prd
        feature = p.feature
        bp = p.blueprint
        wo = p.work_order
        assert prd is not None and bp is not None and wo is not None
        prd_entry = grouped.setdefault(
            prd.id, {"node": prd, "features": {}, "foundations": {}}
        )
        if feature is None:
            f_entry = prd_entry["foundations"].setdefault(
                bp.id, {"node": bp, "work_orders": {}}
            )
            wo_entry = f_entry["work_orders"].setdefault(
                wo.id, {"node": wo, "findings": []}
            )
        else:
            feat_entry = prd_entry["features"].setdefault(
                feature.id, {"node": feature, "blueprints": {}}
            )
            bp_entry = feat_entry["blueprints"].setdefault(
                bp.id, {"node": bp, "work_orders": {}}
            )
            wo_entry = bp_entry["work_orders"].setdefault(
                wo.id, {"node": wo, "findings": []}
            )
        wo_entry["findings"].append(f)

    out: list[str] = []
    for prd_id in sorted(grouped.keys()):
        prd_data = grouped[prd_id]
        prd_node = prd_data["node"]
        out.append(f"### {_md_ref(out_dir, prd_node)}")
        out.append("")

        # Foundation blueprints (skip Feature level)
        for bp_id in sorted(prd_data["foundations"]):
            f_data = prd_data["foundations"][bp_id]
            bp_node = f_data["node"]
            out.append(f"#### Foundation: {_md_ref(out_dir, bp_node)}")
            out.append("")
            for wo_id in sorted(f_data["work_orders"]):
                wo_data = f_data["work_orders"][wo_id]
                wo_node = wo_data["node"]
                out.append(f"##### {_md_ref(out_dir, wo_node)}")
                out.append("")
                for f in sorted(
                    wo_data["findings"], key=lambda x: (-x.severity_rank, x.cve_id)
                ):
                    out.append(_format_finding_bullet(f))
                out.append("")

        # Feature-blueprint paths
        for feature_id in sorted(prd_data["features"]):
            feat_data = prd_data["features"][feature_id]
            feat_node = feat_data["node"]
            out.append(f"#### Feature: {_md_ref(out_dir, feat_node)}")
            out.append("")
            for bp_id in sorted(feat_data["blueprints"]):
                bp_data = feat_data["blueprints"][bp_id]
                bp_node = bp_data["node"]
                out.append(f"##### Blueprint: {_md_ref(out_dir, bp_node)}")
                out.append("")
                for wo_id in sorted(bp_data["work_orders"]):
                    wo_data = bp_data["work_orders"][wo_id]
                    wo_node = wo_data["node"]
                    out.append(f"###### Work Order: {_md_ref(out_dir, wo_node)}")
                    out.append("")
                    for f in sorted(
                        wo_data["findings"], key=lambda x: (-x.severity_rank, x.cve_id)
                    ):
                        out.append(_format_finding_bullet(f))
                    out.append("")
    return out


def _format_finding_bullet(f: Finding) -> str:
    pkg_label = f"`{f.package}@{f.version or '*'}`"
    fix_label = (
        f"upgrade to `{f.fix_version}`" if f.fix_version else "no fix available"
    )
    advisory_link = ""
    if f.references:
        advisory_link = f" · [advisory]({f.references[0]})"
    manifest_label = ""
    if f.dependency_ref is not None:
        manifest_label = f" · *manifest: `{f.dependency_ref.manifest_path}`*"
    sources = "/".join(f.sources) if f.sources else "OSV"
    bullet = (
        f"- **[{f.cve_id}]** {pkg_label} — **{f.severity}** · {fix_label} "
        f"· source: {sources}{advisory_link}{manifest_label}"
    )
    if f.summary:
        bullet += f"\n  - {f.summary}"
    return bullet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node_link(out_dir: Path, node: KGNode) -> str | None:
    """Best available link for a node: relative file path, else web URL.

    File-backed nodes (local-directory source) link to the artifact Markdown
    relative to the report; API-backed nodes carry an absolute URL; stub
    nodes (``.sw-factory`` entity references) may have neither.
    """
    if node.path:
        return _link_to(out_dir, node.path)
    return node.url


def _md_ref(out_dir: Path, node: KGNode) -> str:
    """Markdown reference for a node: linked when possible, plain otherwise."""
    label = f"{node.id}: {node.title}" if node.title else node.id
    link = _node_link(out_dir, node)
    return f"[{label}]({link})" if link else label


def _link_to(out_dir: Path, repo_relative_path: str) -> str:
    """Return a POSIX-style relative path from ``out_dir`` to a repo file.

    The KG file paths are repo-relative (e.g.,
    ``kg/software-factory-plugin/requirements/product-overview.md``) and the
    report files live at ``out_dir``. The Markdown link must navigate from
    the report's location to the target.
    """
    repo_root = _find_repo_root(out_dir)
    if repo_root is None:
        # Fall back to a placeholder rather than producing a broken link.
        return repo_relative_path
    target_abs = (repo_root / repo_relative_path).resolve()
    try:
        rel = os.path.relpath(target_abs, start=out_dir.resolve())
    except ValueError:
        return repo_relative_path
    # Normalize to POSIX so Markdown links work cross-platform.
    return Path(rel).as_posix()


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from ``start`` looking for a ``.git`` marker or pyproject."""
    current = start.resolve()
    for _ in range(20):
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None
