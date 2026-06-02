"""Command-line interface for sf-scan.

This module reserves the full CLI surface and orchestrates the scan
pipeline end-to-end:

  1. Parse args, validate inputs (KG path exists, at least one target).
  2. Load the Knowledge Graph and surface any structural issues.
  3. For each target repo: clone (honoring URL@SHA pinning), extract its
     dependency tree, collect into the aggregate dep list.
  4. Query OSV.dev for vulnerabilities across the aggregate list, with
     SQLite caching.
  5. Render report.json and report.md, grouping findings by ontology
     level and surfacing any unmapped findings as a KG coverage gap.

The ``run_scan`` function takes the heavy lifting and accepts an
injectable ``osv_client`` so tests can run end-to-end without network.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from . import __version__
from .extract import ManifestParseError, extract_dependencies
from .fetch import RepoFetchError, clone_repo, parse_repo_spec
from .kg import KGParseError, KnowledgeGraph
from .models import Dependency, Finding
from .report import render
from .vuln import OsvClient, query as vuln_query


# Exit codes
EXIT_OK = 0
EXIT_PARTIAL = 1  # findings present (kept as 0 for now; reserved)
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
    scan_parser.add_argument(
        "--kg",
        type=Path,
        required=True,
        metavar="PATH",
        help="Path to a Software Factory Knowledge Graph directory.",
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
# Scan pipeline
# ---------------------------------------------------------------------------


def run_scan(
    args: argparse.Namespace,
    *,
    osv_client: OsvClient | None = None,
    stderr=None,
) -> int:
    """Execute a scan. Returns the process exit code.

    ``stderr`` defaults to the live ``sys.stderr`` resolved at call time so
    tests redirecting via ``contextlib.redirect_stderr`` see the output.
    """
    if stderr is None:
        stderr = sys.stderr
    # Validate KG path before any expensive work.
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

    # Load the KG. Capture structural issues; errors don't abort the scan
    # (the report's scan_errors section surfaces them), but warnings do go
    # through.
    scan_errors: list[str] = []
    try:
        kg = KnowledgeGraph.load(args.kg)
    except KGParseError as e:
        print(f"sf-scan scan: error: KG could not be parsed: {e}", file=stderr)
        return EXIT_INPUT

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

    # Clone each target, extract deps, accumulate.
    all_deps: list[Dependency] = []
    target_labels: list[str] = []
    successful_clones = 0
    for target in targets:
        url, sha = parse_repo_spec(target)
        label = f"{url}{'@' + sha if sha else ''}"
        print(f"sf-scan: scanning {label}", file=stderr)
        try:
            with clone_repo(url, sha=sha) as repo_path:
                deps = extract_dependencies(repo_path)
        except RepoFetchError as e:
            scan_errors.append(f"fetch failure: {e}")
            continue
        except ManifestParseError as e:
            scan_errors.append(f"manifest parse error: {e}")
            continue
        successful_clones += 1
        all_deps.extend(deps)
        target_labels.append(label)

    if successful_clones == 0:
        print(
            "sf-scan: all target clones failed. See scan errors above.",
            file=stderr,
        )
        return EXIT_INPUT

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
