"""End-to-end tests for the non-directory Knowledge Graph sources.

Covers the two production-shaped modes:

- ``--kg-sw-factory``: the graph comes from the target repo's own
  ``.sw-factory`` execution state, and dependency attribution is derived
  from the git manifest delta of each Work Order's delivery.
- ``--kg-api``: the graph comes from the Software Factory external REST API
  (stub client serving recorded fixtures), with the same git-derived
  attribution joined on the shared Work Order UUID.

No network, fully deterministic.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from sf_scan.cli import _build_parser, run_scan
from tests.test_e2e import StubOsvClient
from tests.test_sf_api import StubSfApiClient


WO_UUID = "3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"
WO_3_UUID = "aaaa1111-0000-4000-8000-000000000000"

WO_12_CONTEXT = f"""\
# Work Order Entity Index: WO-12

**Initialized At (UTC):** 2026-07-01T10:00:00Z
**Current Status:** in_review

## Work Order

- WO-12: Manifest validation pipeline (`{WO_UUID}`)

## Requirements

- Plugin Platform PRD (`req-doc-001`)

## Blueprints

- Validation Architecture (`bp-doc-001`)

## Delivery

- Branch: wo-12-validation
- Pull Request URL: https://github.com/org/repo/pull/7
"""


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


def _make_wo_repo(root: Path) -> Path:
    """A repo where PR #7 (Work Order WO-12) introduced lodash.

    main starts with express only plus committed .sw-factory state; the
    wo-12-validation branch adds lodash and is merged as PR #7.
    """
    root.mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {"name": "demo", "version": "1.0.0", "dependencies": {"express": "^4.17.0"}}
        )
    )
    wo_dir = root / ".sw-factory" / "WO-12"
    wo_dir.mkdir(parents=True)
    (wo_dir / "context.md").write_text(WO_12_CONTEXT)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")

    _git(root, "checkout", "-q", "-b", "wo-12-validation")
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "version": "1.0.0",
                "dependencies": {"express": "^4.17.0", "lodash": "4.17.20"},
            }
        )
    )
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "feat: manifest validation pipeline")
    _git(root, "checkout", "-q", "main")
    _git(
        root,
        "merge",
        "--no-ff",
        "-q",
        "-m",
        "Merge pull request #7 from org/wo-12-validation",
        "wo-12-validation",
    )
    return root


def _make_fallback_wo_repo(
    root: Path,
    *,
    package: str,
    requirement_id: str,
    blueprint_id: str,
) -> Path:
    """A repo whose UUID-less WO-3 introduces one vulnerable package."""
    context = f"""\
# Work Order Entity Index: WO-3

## Work Order

- WO-3: Deliver {package}

## Requirements

- {package} requirements (`{requirement_id}`)

## Blueprints

- {package} blueprint (`{blueprint_id}`)

## Delivery

- Branch: wo-3-delivery
- Pull Request URL: https://github.com/org/repo/pull/3
"""
    root.mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps({"name": "demo", "version": "1.0.0", "dependencies": {}})
    )
    wo_dir = root / ".sw-factory" / "WO-3"
    wo_dir.mkdir(parents=True)
    (wo_dir / "context.md").write_text(context)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")

    _git(root, "checkout", "-q", "-b", "wo-3-delivery")
    version = "4.17.20" if package == "lodash" else "4.17.0"
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "version": "1.0.0",
                "dependencies": {package: version},
            }
        )
    )
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", f"feat: deliver {package}")
    _git(root, "checkout", "-q", "main")
    _git(
        root,
        "merge",
        "--no-ff",
        "-q",
        "-m",
        "Merge pull request #3 from org/wo-3-delivery",
        "wo-3-delivery",
    )
    return root


def _make_ambiguous_api_repo(root: Path) -> Path:
    """A repo where two API-backed Work Orders both introduce lodash."""
    wo_3_context = f"""\
# Work Order Entity Index: WO-3

## Work Order

- WO-3: Quality toolchain (`{WO_3_UUID}`)

## Requirements

- Plugin Platform PRD (`req-doc-overview-001`)

## Blueprints

- Repository Conventions (`bp-doc-custom-001`)

## Delivery

- Branch: wo-3-toolchain
- Pull Request URL:
"""
    root.mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {"name": "demo", "version": "1.0.0", "dependencies": {"express": "4.17.0"}}
        )
    )
    for label, context in (("WO-12", WO_12_CONTEXT), ("WO-3", wo_3_context)):
        wo_dir = root / ".sw-factory" / label
        wo_dir.mkdir(parents=True)
        (wo_dir / "context.md").write_text(context)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")

    for branch in ("wo-12-validation", "wo-3-toolchain"):
        _git(root, "checkout", "-q", "-b", branch)
        (root / "package.json").write_text(
            json.dumps(
                {
                    "name": "demo",
                    "version": "1.0.0",
                    "dependencies": {
                        "express": "4.17.0",
                        "lodash": "4.17.20",
                    },
                }
            )
        )
        _git(root, "add", "package.json")
        _git(root, "commit", "-q", "-m", f"{branch} adds lodash")
        _git(root, "checkout", "-q", "main")
    return root


def _parse(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


class TestSwFactoryMode:
    def test_derived_dep_maps_to_work_order(self, tmp_path: Path) -> None:
        upstream = _make_wo_repo(tmp_path / "upstream")
        out = tmp_path / "reports"
        args = _parse(
            [
                "scan",
                "--repo",
                f"file://{upstream}",
                "--kg-sw-factory",
                "--out",
                str(out),
                "--no-cache",
            ]
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0

        report = json.loads((out / "report.json").read_text())
        assert ".sw-factory" in report["kg_source"]

        by_pkg = {f["package"]: f for f in report["findings"]}
        # lodash was introduced by WO-12's merged PR — derived attribution
        # walks the foundation chain from the Entity Index stubs.
        lodash = by_pkg["lodash"]
        assert lodash["kg_path"]["work_order"]["id"] == WO_UUID
        assert lodash["kg_path"]["blueprint"]["id"] == "bp-doc-001"
        assert lodash["kg_path"]["prd"]["id"] == "req-doc-001"
        # express predates the Work Order — an honest coverage gap.
        assert "kg_path" not in by_pkg["express"]
        assert len(report["unmapped"]) == 1

        md = (out / "report.md").read_text()
        assert "Manifest validation pipeline" in md
        # The WO heading links to the PR that delivered it.
        assert "https://github.com/org/repo/pull/7" in md

    def test_repo_without_state_reports_warning(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        (upstream / "package.json").write_text(
            json.dumps({"name": "d", "dependencies": {"lodash": "4.17.20"}})
        )
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],
            cwd=upstream,
            check=True,
            capture_output=True,
        )
        _git(upstream, "config", "user.email", "t@e.com")
        _git(upstream, "config", "user.name", "T")
        _git(upstream, "add", ".")
        _git(upstream, "commit", "-q", "-m", "init")
        out = tmp_path / "reports"
        args = _parse(
            [
                "scan",
                "--repo",
                f"file://{upstream}",
                "--kg-sw-factory",
                "--out",
                str(out),
                "--no-cache",
            ]
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0
        report = json.loads((out / "report.json").read_text())
        assert any("no Knowledge Graph" in e for e in report["scan_errors"])
        assert all("kg_path" not in f for f in report["findings"])

    def test_fallback_work_order_labels_are_scoped_per_repository(
        self, tmp_path: Path
    ) -> None:
        repo_a = _make_fallback_wo_repo(
            tmp_path / "repo-a",
            package="express",
            requirement_id="req-express",
            blueprint_id="bp-express",
        )
        repo_b = _make_fallback_wo_repo(
            tmp_path / "repo-b",
            package="lodash",
            requirement_id="req-lodash",
            blueprint_id="bp-lodash",
        )
        out = tmp_path / "reports"
        args = _parse(
            [
                "scan",
                "--repo",
                f"file://{repo_a}",
                "--repo",
                f"file://{repo_b}",
                "--kg-sw-factory",
                "--out",
                str(out),
                "--no-cache",
            ]
        )

        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0

        report = json.loads((out / "report.json").read_text())
        by_pkg = {finding["package"]: finding for finding in report["findings"]}
        express_wo = by_pkg["express"]["kg_path"]["work_order"]
        lodash_wo = by_pkg["lodash"]["kg_path"]["work_order"]
        assert express_wo["id"] != lodash_wo["id"]
        assert by_pkg["express"]["kg_path"]["blueprint"]["id"] == "bp-express"
        assert by_pkg["lodash"]["kg_path"]["blueprint"]["id"] == "bp-lodash"


class TestApiMode:
    def test_api_graph_with_derived_attribution(self, tmp_path: Path) -> None:
        upstream = _make_wo_repo(tmp_path / "upstream")
        out = tmp_path / "reports"
        args = _parse(
            [
                "scan",
                "--repo",
                f"file://{upstream}",
                "--kg-api",
                "https://factory.example.com",
                "--out",
                str(out),
                "--no-cache",
            ]
        )
        exit_code = run_scan(
            args, osv_client=StubOsvClient(), sf_api_client=StubSfApiClient()
        )
        assert exit_code == 0

        report = json.loads((out / "report.json").read_text())
        assert "external API" in report["kg_source"]

        by_pkg = {f["package"]: f for f in report["findings"]}
        lodash = by_pkg["lodash"]
        # Derived from git, joined on the WO UUID shared with .sw-factory,
        # resolved through the API-sourced feature chain.
        assert lodash["kg_path"]["work_order"]["id"] == WO_UUID
        assert lodash["kg_path"]["blueprint"]["id"] == "bp-doc-feat-001"
        assert lodash["kg_path"]["feature"]["id"] == "req-doc-feat-001"
        assert lodash["kg_path"]["prd"]["id"] == "req-doc-overview-001"
        # API-sourced nodes link by URL, not file path.
        assert lodash["kg_path"]["work_order"]["path"] is None
        assert lodash["kg_path"]["work_order"]["url"].startswith(
            "https://factory.example.com/v2/external-api/work_orders/"
        )

        md = (out / "report.md").read_text()
        assert "https://factory.example.com/v2/external-api/work_orders/" in md

    def test_enrichment_reports_ambiguous_dependency_ownership(
        self, tmp_path: Path
    ) -> None:
        upstream = _make_ambiguous_api_repo(tmp_path / "upstream")
        out = tmp_path / "reports"
        args = _parse(
            [
                "scan",
                "--repo",
                f"file://{upstream}",
                "--kg-api",
                "https://factory.example.com",
                "--out",
                str(out),
                "--no-cache",
            ]
        )

        exit_code = run_scan(
            args, osv_client=StubOsvClient(), sf_api_client=StubSfApiClient()
        )
        assert exit_code == 0

        report = json.loads((out / "report.json").read_text())
        assert any(
            "npm:lodash declared in multiple work orders" in error
            and WO_UUID in error
            and WO_3_UUID in error
            for error in report["scan_errors"]
        )
