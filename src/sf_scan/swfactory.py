"""GraphSource adapter for the ``.sw-factory`` execution-state directory.

Software Factory's coding-agent plugin writes per-Work-Order execution state
into the customer repo at ``.sw-factory/WO-<n>/`` (committed alongside the
code when git is the system of record). The file that matters here is
``context.md`` — an "Entity Index" tying the Work Order to its linked
Requirements and Blueprint documents, and (in the ``## Delivery`` section)
to the branch and pull-request URL that shipped it.

The harness variant of the plugin writes the same files under
``scratch/wo-execution/`` instead, without a stable Work Order UUID; that
root is supported as a fallback (node ids fall back to the ``WO-<n>`` label).

What this source yields:

- one ``work-order`` node per ``WO-*`` directory,
- stub ``blueprint-foundation`` nodes for each linked/referenced Blueprint,
- stub ``prd`` nodes for each linked Requirements document.

Chains resolve as foundation paths (Work Order → Blueprint → Requirements
doc); the synthetic four-level ontology's Feature layer has no counterpart
in the Entity Index. ``dependencies-introduced`` is never present here —
attribution comes from git manifest deltas (``derive.py``) via the
deliveries this source exposes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .derive import WoDelivery
from .kg import KGNode


SWFACTORY_ROOTS = (".sw-factory", "scratch/wo-execution")

# `- WO-12: Title (`id`)`  — the id-carrying Work Order line.
_WO_LINE_RE = re.compile(r"^- (WO-\d+):\s*(.*?)(?:\s*\(`([^`]+)`\))?\s*$")
# `- Title (`id`)` — Requirements / Blueprints entity lines.
_ENTITY_LINE_RE = re.compile(r"^- (.+?)\s*\(`([^`]+)`\)\s*$")
_HEADING_RE = re.compile(r"^##\s+(.*)$")


@dataclass(frozen=True)
class WoContext:
    """Parsed ``context.md`` for one Work Order directory."""

    label: str  # "WO-12"
    node_id: str  # stable UUID when present, else the label
    title: str
    requirements: list[tuple[str, str]]  # (title, id)
    blueprints: list[tuple[str, str]]  # (title, id) — linked + referenced
    branch: str | None
    pr_url: str | None
    source_path: str  # repo-relative path to context.md


def parse_context_md(text: str, *, source_path: str, dir_label: str) -> WoContext | None:
    """Parse one Entity Index document. Returns None when no WO line parses."""
    sections = _split_sections(text)
    if "Work Order" not in sections:
        return None

    # Fall back to the directory name when the WO line is an unfilled
    # template or a harness-variant line without the stable UUID.
    label = dir_label
    node_id = dir_label
    title = ""
    for line in sections["Work Order"]:
        match = _WO_LINE_RE.match(line)
        if not match:
            continue
        label = match.group(1)
        title = match.group(2).strip()
        raw_id = (match.group(3) or "").strip()
        if raw_id and not _is_template_token(raw_id):
            node_id = raw_id
        else:
            node_id = label
        break

    requirements = _entity_lines(sections.get("Requirements", []))
    blueprints = _entity_lines(sections.get("Blueprints", [])) + _entity_lines(
        sections.get("Referenced Blueprints", [])
    )

    branch = _delivery_value(sections.get("Delivery", []), "Branch")
    pr_url = _delivery_value(sections.get("Delivery", []), "Pull Request URL")

    return WoContext(
        label=label,
        node_id=node_id,
        title=title or label,
        requirements=requirements,
        blueprints=blueprints,
        branch=branch,
        pr_url=pr_url,
        source_path=source_path,
    )


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = _HEADING_RE.match(line)
        if heading:
            current = sections.setdefault(heading.group(1).strip(), [])
            continue
        if current is not None and line:
            current.append(line)
    return sections


def _entity_lines(lines: list[str]) -> list[tuple[str, str]]:
    entities: list[tuple[str, str]] = []
    for line in lines:
        match = _ENTITY_LINE_RE.match(line)
        if not match:
            continue
        title, entity_id = match.group(1).strip(), match.group(2).strip()
        if _is_template_token(title) or _is_template_token(entity_id):
            continue  # unfilled template placeholder, not a real link
        entities.append((title, entity_id))
    return entities


def _delivery_value(lines: list[str], key: str) -> str | None:
    prefix = f"- {key}:"
    for line in lines:
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            if value and not _is_template_token(value):
                return value
    return None


def _is_template_token(value: str) -> bool:
    return value.startswith("{{") and value.endswith("}}")


class SwFactorySource:
    """Builds a Knowledge Graph from a repo checkout's ``.sw-factory`` state."""

    def __init__(self, repo_path: Path, *, source_id: str | None = None) -> None:
        self.repo_path = repo_path
        self.source_id = source_id
        self._contexts: list[WoContext] | None = None

    def describe(self) -> str:
        return f".sw-factory execution state in {self.repo_path}"

    # -- parsing ------------------------------------------------------------

    def contexts(self) -> list[WoContext]:
        if self._contexts is None:
            self._contexts = list(self._parse_all())
        return self._contexts

    def _parse_all(self) -> Iterator[WoContext]:
        for root_name in SWFACTORY_ROOTS:
            root = self.repo_path / root_name
            if not root.is_dir():
                continue
            for wo_dir in sorted(root.glob("WO-*")):
                context_md = wo_dir / "context.md"
                if not context_md.is_file():
                    continue
                ctx = parse_context_md(
                    context_md.read_text(encoding="utf-8"),
                    source_path=context_md.relative_to(self.repo_path).as_posix(),
                    dir_label=wo_dir.name,
                )
                if ctx is not None:
                    yield ctx
            break  # the first root that exists wins; the two never coexist

    # -- GraphSource --------------------------------------------------------

    def _work_order_id(self, ctx: WoContext) -> str:
        if self.source_id is not None and ctx.node_id == ctx.label:
            return f"{self.source_id}#{ctx.node_id}"
        return ctx.node_id

    def iter_nodes(self) -> Iterator[KGNode]:
        seen: set[str] = set()
        for ctx in self.contexts():
            prd_id = ctx.requirements[0][1] if ctx.requirements else None

            for title, req_id in ctx.requirements:
                if req_id not in seen:
                    seen.add(req_id)
                    yield KGNode(
                        id=req_id, title=title, artifact_type="prd", path=None
                    )

            for title, bp_id in ctx.blueprints:
                if bp_id not in seen:
                    seen.add(bp_id)
                    metadata = {"product": prd_id} if prd_id else {}
                    yield KGNode(
                        id=bp_id,
                        title=title,
                        artifact_type="blueprint-foundation",
                        path=None,
                        metadata=metadata,
                    )

            metadata: dict[str, object] = {
                "work_order_label": ctx.label,
                "source_path": ctx.source_path,
            }
            if ctx.blueprints:
                metadata["blueprint"] = ctx.blueprints[0][1]
            if ctx.branch:
                metadata["branch"] = ctx.branch
            if ctx.pr_url:
                metadata["pr_url"] = ctx.pr_url
            yield KGNode(
                id=self._work_order_id(ctx),
                title=ctx.title,
                artifact_type="work-order",
                path=None,
                # Link report readers to the PR that delivered the WO — the
                # closest thing to a canonical artifact URL available here.
                url=ctx.pr_url,
                metadata=metadata,
            )

    # -- derivation input ---------------------------------------------------

    def deliveries(self) -> list[WoDelivery]:
        return [
            WoDelivery(
                wo_id=self._work_order_id(ctx),
                branch=ctx.branch,
                pr_url=ctx.pr_url,
            )
            for ctx in self.contexts()
        ]
