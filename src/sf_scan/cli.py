"""Command-line interface for sf-scan.

This module reserves the full CLI surface that downstream implementation
units wire up: U2 plugs in repo fetch + manifest extraction, U3 the
vulnerability query layer, U5 the Knowledge Graph resolver, U6 the report
renderer, and U7 the end-to-end orchestration. U1 ships the parser and a
stub scan handler that prints "not yet implemented" and exits 1, so the
CLI shape is testable before any business logic lands.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


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
            "and the GitHub Advisory Database for known vulnerabilities, and "
            "emit a structured report grouping findings by Software Factory "
            "Knowledge Graph ontology level."
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
    """Return an error message if scan args are invalid, otherwise None."""
    if not args.repo and not args.repo_list:
        return (
            "sf-scan scan: error: at least one of --repo or --repo-list is required"
        )
    if args.repo_list is not None and not args.repo_list.exists():
        return f"sf-scan scan: error: --repo-list path does not exist: {args.repo_list}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    if args.command == "scan":
        error = _validate_scan_args(args)
        if error is not None:
            print(error, file=sys.stderr)
            return 2
        # U7 wires the orchestration here. U1 leaves a clear stub.
        print(
            "sf-scan: scan not yet implemented — implementation arrives with U7.",
            file=sys.stderr,
        )
        return 1

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
