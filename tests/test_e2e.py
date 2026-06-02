"""End-to-end CLI integration tests.

These exercise the full pipeline — repo fetch, manifest extraction,
vulnerability query, KG resolution, report rendering — against a local
fixture git repo and a stub OSV client. No network, fully deterministic.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from sf_scan.cli import _build_parser, run_scan
from sf_scan.vuln import VulnQueryError


FIXTURES = Path(__file__).parent / "fixtures"
TINY_KG = FIXTURES / "kg" / "tiny"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_local_git_repo(root: Path, manifests: dict[str, str]) -> Path:
    """Create a local git repo at ``root`` with the given manifest files."""
    root.mkdir(parents=True, exist_ok=True)
    for rel_path, content in manifests.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "add", "."], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", "init"],
        check=True,
        capture_output=True,
    )
    return root


class StubOsvClient:
    """A stub OSV client that returns fixture data for a fixed set of CVEs."""

    BATCH_RESPONSE = {
        "results": [
            {"vulns": [{"id": "GHSA-fake-express"}]},
            {"vulns": [{"id": "GHSA-fake-lodash"}]},
        ]
    }

    VULNS = {
        "GHSA-fake-express": {
            "id": "GHSA-fake-express",
            "summary": "Test express CVE",
            "affected": [
                {
                    "package": {"ecosystem": "npm", "name": "express"},
                    "ranges": [
                        {
                            "type": "ECOSYSTEM",
                            "events": [{"introduced": "0"}, {"fixed": "4.18.2"}],
                        }
                    ],
                    "database_specific": {"severity": "HIGH"},
                }
            ],
            "database_specific": {"severity": "HIGH"},
            "references": [
                {"type": "ADVISORY", "url": "https://example.com/express-cve"}
            ],
        },
        "GHSA-fake-lodash": {
            "id": "GHSA-fake-lodash",
            "summary": "Test lodash CVE",
            "affected": [
                {
                    "package": {"ecosystem": "npm", "name": "lodash"},
                    "ranges": [
                        {
                            "type": "ECOSYSTEM",
                            "events": [{"introduced": "0"}, {"fixed": "4.17.21"}],
                        }
                    ],
                    "database_specific": {"severity": "CRITICAL"},
                }
            ],
            "database_specific": {"severity": "CRITICAL"},
            "references": [
                {"type": "ADVISORY", "url": "https://example.com/lodash-cve"}
            ],
        },
    }

    def __init__(self, *, fail_batch: bool = False) -> None:
        self.fail_batch = fail_batch
        self.batch_calls = 0

    def query_batch(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        self.batch_calls += 1
        if self.fail_batch:
            raise VulnQueryError("stub batch failed")
        # Build a response matching the order of input queries. The test
        # expects express to be queried first, then lodash. Always return
        # those two; any extra queries get empty results.
        results: list[dict[str, Any]] = []
        for q in queries:
            name = q.get("package", {}).get("name", "")
            if name == "express":
                results.append({"vulns": [{"id": "GHSA-fake-express"}]})
            elif name == "lodash":
                results.append({"vulns": [{"id": "GHSA-fake-lodash"}]})
            else:
                results.append({})
        return {"results": results}

    def get_vuln(self, vuln_id: str) -> dict[str, Any]:
        return self.VULNS[vuln_id]


# ---------------------------------------------------------------------------
# Argparse helper
# ---------------------------------------------------------------------------


def _scan_args(
    *,
    repo: list[str],
    kg: Path,
    out: Path,
    repo_list: Path | None = None,
    no_cache: bool = True,
) -> argparse.Namespace:
    parser = _build_parser()
    argv = ["scan"]
    for r in repo:
        argv.extend(["--repo", r])
    if repo_list is not None:
        argv.extend(["--repo-list", str(repo_list)])
    argv.extend(["--kg", str(kg)])
    argv.extend(["--out", str(out)])
    if no_cache:
        argv.append("--no-cache")
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSingleTarget:
    def test_full_e2e_produces_both_reports(self, tmp_path: Path) -> None:
        upstream = _make_local_git_repo(
            tmp_path / "upstream",
            {
                "package.json": json.dumps(
                    {
                        "name": "demo",
                        "version": "1.0.0",
                        "dependencies": {
                            "express": "^4.17.0",
                            "lodash": "4.17.20",
                        },
                    }
                ),
            },
        )
        out = tmp_path / "reports"
        args = _scan_args(
            repo=[f"file://{upstream}"],
            kg=TINY_KG,
            out=out,
        )
        stub = StubOsvClient()
        exit_code = run_scan(args, osv_client=stub)
        assert exit_code == 0
        assert (out / "report.json").exists()
        assert (out / "report.md").exists()

    def test_report_contains_mapped_finding(self, tmp_path: Path) -> None:
        upstream = _make_local_git_repo(
            tmp_path / "upstream",
            {
                "package.json": json.dumps(
                    {
                        "name": "demo",
                        "version": "1.0.0",
                        "dependencies": {
                            "express": "^4.17.0",
                            "lodash": "4.17.20",
                        },
                    }
                ),
            },
        )
        out = tmp_path / "reports"
        args = _scan_args(
            repo=[f"file://{upstream}"], kg=TINY_KG, out=out
        )
        run_scan(args, osv_client=StubOsvClient())
        md = (out / "report.md").read_text()
        # Both findings should be mapped through the tiny KG (which declares
        # both packages in its WO frontmatter).
        assert "express" in md
        assert "lodash" in md
        assert "PRD-T-001" in md

    def test_critical_finding_in_action_list(self, tmp_path: Path) -> None:
        upstream = _make_local_git_repo(
            tmp_path / "upstream",
            {
                "package.json": json.dumps(
                    {"name": "demo", "dependencies": {"lodash": "4.17.20"}}
                ),
            },
        )
        out = tmp_path / "reports"
        args = _scan_args(repo=[f"file://{upstream}"], kg=TINY_KG, out=out)
        run_scan(args, osv_client=StubOsvClient())
        data = json.loads((out / "report.json").read_text())
        assert data["summary"]["by_severity"]["CRITICAL"] == 1
        assert any(
            item["severity"] == "CRITICAL"
            for item in data["summary"]["action_list"]
        )


class TestMultipleTargets:
    def test_repo_list_expanded(self, tmp_path: Path) -> None:
        a = _make_local_git_repo(
            tmp_path / "a",
            {"package.json": json.dumps({"name": "a", "dependencies": {"express": "^4.0.0"}})},
        )
        b = _make_local_git_repo(
            tmp_path / "b",
            {"package.json": json.dumps({"name": "b", "dependencies": {"lodash": "4.17.0"}})},
        )
        repo_list = tmp_path / "targets.txt"
        repo_list.write_text(f"file://{a}\nfile://{b}\n# a comment\n\n")
        out = tmp_path / "reports"
        args = _scan_args(
            repo=[],
            repo_list=repo_list,
            kg=TINY_KG,
            out=out,
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0
        data = json.loads((out / "report.json").read_text())
        assert data["summary"]["total_findings"] == 2

    def test_repo_and_repo_list_combined_and_deduped(self, tmp_path: Path) -> None:
        a = _make_local_git_repo(
            tmp_path / "a",
            {"package.json": json.dumps({"name": "a", "dependencies": {"express": "^4.0.0"}})},
        )
        repo_list = tmp_path / "targets.txt"
        repo_list.write_text(f"file://{a}\n")
        out = tmp_path / "reports"
        args = _scan_args(
            repo=[f"file://{a}"],
            repo_list=repo_list,
            kg=TINY_KG,
            out=out,
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0
        # Dedup: only one finding for express, not two.
        data = json.loads((out / "report.json").read_text())
        express_findings = [
            f for f in data["findings"] if f["package"] == "express"
        ]
        assert len(express_findings) == 1


class TestUrlAtShaSyntax:
    def test_sha_pinned_clone(self, tmp_path: Path) -> None:
        upstream = _make_local_git_repo(
            tmp_path / "upstream",
            {"package.json": json.dumps({"name": "demo", "dependencies": {"express": "^4.0.0"}})},
        )
        # Capture current SHA
        sha = subprocess.check_output(
            ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
        ).strip()
        # Add a second commit so HEAD differs from the pinned SHA
        (upstream / "extra.txt").write_text("more")
        subprocess.run(
            ["git", "-C", str(upstream), "add", "extra.txt"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "commit", "-q", "-m", "extra"],
            check=True,
            capture_output=True,
        )
        out = tmp_path / "reports"
        args = _scan_args(
            repo=[f"file://{upstream}@{sha}"],
            kg=TINY_KG,
            out=out,
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0


class TestKgValidation:
    def test_missing_kg_path_returns_input_error(self, tmp_path: Path) -> None:
        args = _scan_args(
            repo=["https://example.com/x"],
            kg=tmp_path / "does-not-exist",
            out=tmp_path / "out",
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 3

    def test_kg_path_is_file_not_dir(self, tmp_path: Path) -> None:
        bad_kg = tmp_path / "kg.md"
        bad_kg.write_text("not a directory")
        args = _scan_args(
            repo=["https://example.com/x"],
            kg=bad_kg,
            out=tmp_path / "out",
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 3

    def test_kg_with_errors_still_runs_scan(self, tmp_path: Path) -> None:
        # Build a KG with a broken reference; the scan should still complete
        # and surface the issue in scan_errors.
        broken_kg = tmp_path / "broken-kg"
        shutil.copytree(TINY_KG, broken_kg)
        wo_path = broken_kg / "work-orders" / "wo-001.md"
        wo_path.write_text(
            wo_path.read_text().replace("blueprint: BP-T-001", "blueprint: BP-NOPE")
        )
        upstream = _make_local_git_repo(
            tmp_path / "upstream",
            {"package.json": json.dumps({"name": "demo", "dependencies": {"express": "^4.0.0"}})},
        )
        out = tmp_path / "reports"
        args = _scan_args(repo=[f"file://{upstream}"], kg=broken_kg, out=out)
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 0  # scan succeeded
        data = json.loads((out / "report.json").read_text())
        assert any("BP-NOPE" in e for e in data["scan_errors"])


class TestAllClonesFail:
    def test_all_clones_failing_returns_input_error(self, tmp_path: Path) -> None:
        args = _scan_args(
            repo=[f"file://{tmp_path}/no-such-repo"],
            kg=TINY_KG,
            out=tmp_path / "reports",
        )
        exit_code = run_scan(args, osv_client=StubOsvClient())
        assert exit_code == 3
