"""Command-line interface for sf-scan.

The scan pipeline runs in five stages:

  1. Parse args, validate inputs (exactly one KG source, at least one target).
  2. Load the Knowledge Graph from the selected source — a local Markdown
     directory (``--kg``), the Software Factory external REST API
     (``--kg-api``), or the targets' own ``.sw-factory`` execution state
     (``--kg-sw-factory``) — and surface any structural issues.
  3. For each target repo: clone (honoring URL@SHA pinning), extract its
     dependency tree, collect into the aggregate dep list. In the API and
     ``.sw-factory`` modes, also derive per-Work-Order dependency
     attribution from the repo's git manifest deltas.
  4. Query OSV.dev for vulnerabilities across the aggregate list, with
     SQLite caching.
  5. Render report.json and report.md, grouping findings by ontology
     level and surfacing any unmapped findings as a KG coverage gap.

``run_scan`` is the orchestration entry point and accepts injectable
``osv_client`` and ``sf_api_client`` so tests can run end-to-end without
network.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

from . import __version__
from .derive import derive_dependencies
from .extract import ManifestParseError, extract_dependencies
from .fetch import RepoFetchError, clone_repo, parse_repo_spec
from .kg import KGParseError, KnowledgeGraph
from .models import Dependency, Finding
from .report import render
from .sf_api import (
    API_KEY_ENV,
    ORG_ID_ENV,
    HttpSfApiClient,
    RestApiSource,
    SfApiClient,
    SfApiError,
)
from .swfactory import SwFactorySource
from .vuln import OsvClient, query as vuln_query


# Exit codes
EXIT_OK = 0
EXIT_USAGE = 2  # bad args, missing flags
EXIT_INPUT = 3  # input not found or invalid (KG path, all clones failed)


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sf-scan",
        description=(
            "Software Factory Security Scanner — Lens 1. "
            "Dependency vulnerability scanner with Knowledge Graph ontology mapping."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sf-scan {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        metavar="<command>",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan one or more GitHub repos for vulnerabilities mapped to a Knowledge Graph",
        description=(
            "Clone each target repo, extract its dependency tree, query OSV.dev "
            "for known vulnerabilities, and emit a structured report grouping "
            "findings by Software Factory Knowledge Graph ontology level."
        ),
    )
    scan_parser.add_argument(
        "--repo",
        action="append",
        default=[],
        metavar="URL[@SHA]",
        help=(
            "Target repo URL. Repeatable for multi-target scans. "
            "Supports URL@SHA pinning to a specific commit."
        ),
    )
    scan_parser.add_argument(
        "--repo-list",
        type=Path,
        metavar="PATH",
        help="Path to a file containing target repo URLs, one per line.",
    )
    kg_source = scan_parser.add_mutually_exclusive_group()
    kg_source.add_argument(
        "--kg",
        type=Path,
        metavar="PATH",
        help="Path to a local Knowledge Graph directory of Markdown artifacts.",
    )
    kg_source.add_argument(
        "--kg-api",
        metavar="BASE_URL",
        help=(
            "Base URL of a Software Factory instance; the Knowledge Graph is "
            "read from its external REST API (/v2/external-api). Requires a "
            f"project-scoped API key in ${API_KEY_ENV} "
            f"(optional org id in ${ORG_ID_ENV})."
        ),
    )
    kg_source.add_argument(
        "--kg-sw-factory",
        action="store_true",
        help=(
            "Build the Knowledge Graph from the target repos' own .sw-factory "
            "execution state (work orders, blueprint/requirement links, and "
            "delivery branches for git-derived dependency attribution)."
        ),
    )
    scan_parser.add_argument(
        "--out",
        type=Path,
        default=Path("./reports"),
        metavar="PATH",
        help="Output directory for report.json and report.md (default: ./reports).",
    )
    scan_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the local vulnerability lookup cache.",
    )

    return parser


def _validate_scan_args(args: argparse.Namespace) -> str | None:
    if not args.repo and not args.repo_list:
        return (
            "sf-scan scan: error: at least one of --repo or --repo-list is required"
        )
    if args.repo_list is not None and not args.repo_list.exists():
        return f"sf-scan scan: error: --repo-list path does not exist: {args.repo_list}"
    if args.kg is None and args.kg_api is None and not args.kg_sw_factory:
        return (
            "sf-scan scan: error: one of --kg, --kg-api, or --kg-sw-factory "
            "is required"
        )
    return None


# ---------------------------------------------------------------------------
# Target list expansion
# ---------------------------------------------------------------------------


def _collect_targets(args: argparse.Namespace) -> list[str]:
    """Build the deduplicated target list from --repo and --repo-list."""
    targets: list[str] = list(args.repo)
    if args.repo_list is not None:
        for raw in args.repo_list.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            targets.append(line)

    # Preserve order, drop duplicates.
    seen: set[str] = set()
    deduped: list[str] = []
    for t in targets:
        if t in seen:
            continue
        seen.add(t)
        deduped.append(t)
    return deduped


# ---------------------------------------------------------------------------
# Derivation enrichment
# ---------------------------------------------------------------------------


def _derive_and_enrich(
    kg: KnowledgeGraph,
    repo_path: Path,
    *,
    source: SwFactorySource | None = None,
) -> list[str]:
    """Attribute git-derived manifest deltas to the graph's Work Orders.

    Returns warnings for the report's scan_errors section. Work Orders are
    joined on the UUID shared between the platform and ``.sw-factory``
    state, falling back to the ``WO-<n>`` label for harness-variant repos.
    """
    deliveries = (source or SwFactorySource(repo_path)).deliveries()
    if not deliveries:
        return [
            f"derivation: no .sw-factory execution state in {repo_path.name}; "
            "work orders have no dependency attribution"
        ]
    result = derive_dependencies(repo_path, deliveries)
    warnings = list(result.warnings)
    label_to_id = {
        node.metadata.get("work_order_label"): node.id
        for node in kg.nodes.values()
        if node.artifact_type == "work-order"
    }
    for wo_id, deps in result.deps_by_wo.items():
        node_id = wo_id if wo_id in kg.nodes else label_to_id.get(wo_id)
        if node_id is None:
            warnings.append(
                f"derivation: work order {wo_id} not present in the Knowledge "
                f"Graph; {len(deps)} derived dependency(ies) unattributed"
            )
            continue
        if deps:
            kg.add_dependencies(node_id, deps)
    return warnings


# ---------------------------------------------------------------------------
# Scan pipeline
# ---------------------------------------------------------------------------


def run_scan(
    args: argparse.Namespace,
    *,
    osv_client: OsvClient | None = None,
    sf_api_client: SfApiClient | None = None,
    stderr=None,
) -> int:
    """Execute a scan. Returns the process exit code.

    ``stderr`` defaults to the live ``sys.stderr`` resolved at call time so
    tests redirecting via ``contextlib.redirect_stderr`` see the output.
    """
    if stderr is None:
        stderr = sys.stderr

    # The API and .sw-factory modes derive per-Work-Order dependency
    # attribution from each target's git history, which needs full clones.
    derive_mode = bool(args.kg_api or args.kg_sw_factory)

    # Load the KG. Capture structural issues; errors don't abort the scan
    # (the report's scan_errors section surfaces them), but warnings do go
    # through. In .sw-factory mode the graph is built from the target
    # checkouts inside the clone loop instead.
    scan_errors: list[str] = []
    kg: KnowledgeGraph | None = None
    if args.kg is not None:
        if not args.kg.exists():
            print(
                f"sf-scan scan: error: --kg path does not exist: {args.kg}",
                file=stderr,
            )
            return EXIT_INPUT
        if not args.kg.is_dir():
            print(
                f"sf-scan scan: error: --kg path is not a directory: {args.kg}",
                file=stderr,
            )
            return EXIT_INPUT
        try:
            kg = KnowledgeGraph.load(args.kg)
        except KGParseError as e:
            print(f"sf-scan scan: error: KG could not be parsed: {e}", file=stderr)
            return EXIT_INPUT
    elif args.kg_api is not None:
        client = sf_api_client
        if client is None:
            api_key = os.environ.get(API_KEY_ENV)
            if not api_key:
                print(
                    f"sf-scan scan: error: --kg-api requires a project-scoped "
                    f"API key in ${API_KEY_ENV}",
                    file=stderr,
                )
                return EXIT_USAGE
            client = HttpSfApiClient(
                args.kg_api, api_key, org_id=os.environ.get(ORG_ID_ENV)
            )
        source = RestApiSource(
            client, label=f"Software Factory external API at {args.kg_api}"
        )
        try:
            kg = KnowledgeGraph.from_source(source)
        except SfApiError as e:
            print(
                f"sf-scan scan: error: Knowledge Graph could not be read: {e}",
                file=stderr,
            )
            return EXIT_INPUT

    if kg is not None:
        for issue in kg.validate():
            prefix = "KG error" if issue.severity == "error" else "KG warning"
            scan_errors.append(f"{prefix}: {issue.message}")

    targets = _collect_targets(args)
    if not targets:
        print(
            "sf-scan scan: error: no targets specified after expanding --repo-list",
            file=stderr,
        )
        return EXIT_USAGE

    # Clone each target, extract deps, accumulate. In derive mode, also
    # build/extend the graph from .sw-factory state and attribute
    # dependencies from git manifest deltas while the checkout exists.
    all_deps: list[Dependency] = []
    target_labels: list[str] = []
    successful_clones = 0
    for target in targets:
        url, sha = parse_repo_spec(target)
        label = f"{url}{'@' + sha if sha else ''}"
        print(f"sf-scan: scanning {label}", file=stderr)
        try:
            with clone_repo(url, sha=sha, full_history=derive_mode) as repo_path:
                deps = extract_dependencies(repo_path)
                sw_source: SwFactorySource | None = None
                if args.kg_sw_factory:
                    sw_source = SwFactorySource(repo_path, source_id=label)
                    if kg is None:
                        kg = KnowledgeGraph.from_source(sw_source)
                    else:
                        kg.extend_from_source(sw_source)
                if derive_mode and kg is not None:
                    scan_errors.extend(
                        _derive_and_enrich(kg, repo_path, source=sw_source)
                    )
        except RepoFetchError as e:
            scan_errors.append(f"fetch failure: {e}")
            continue
        except ManifestParseError as e:
            scan_errors.append(f"manifest parse error: {e}")
            continue
        successful_clones += 1
        all_deps.extend(deps)
        target_labels.append(label)

    if successful_clones == 0 or kg is None:
        print(
            "sf-scan: all target clones failed. See scan errors above.",
            file=stderr,
        )
        return EXIT_INPUT

    if derive_mode:
        for issue in kg.validate():
            prefix = "KG error" if issue.severity == "error" else "KG warning"
            message = f"{prefix}: {issue.message}"
            if message not in scan_errors:
                scan_errors.append(message)

    # Query vulnerabilities. Pass osv_client so tests can inject a stub.
    findings: list[Finding] = vuln_query(
        all_deps,
        use_cache=not args.no_cache,
        client=osv_client,
    )

    # Render reports.
    repo_label = " + ".join(target_labels) if target_labels else "<no targets>"
    sha_for_label: str | None = None
    if len(targets) == 1:
        _, sha_for_label = parse_repo_spec(targets[0])

    paths = render(
        findings,
        kg,
        args.out,
        repo_label=repo_label,
        sha=sha_for_label,
        scan_errors=scan_errors,
    )

    # Final summary.
    sev_counts = Counter(f.severity for f in findings)
    print(
        f"sf-scan: scanned {successful_clones} repo(s), "
        f"{len(all_deps)} dep(s); {len(findings)} finding(s) "
        f"({sev_counts.get('CRITICAL', 0)} critical, "
        f"{sev_counts.get('HIGH', 0)} high).",
        file=stderr,
    )
    print(f"sf-scan: report at {paths.md_path.resolve()}", file=stderr)

    return EXIT_OK


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    if args.command == "scan":
        error = _validate_scan_args(args)
        if error is not None:
            print(error, file=sys.stderr)
            return EXIT_USAGE
        return run_scan(args)

    parser.print_help(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
