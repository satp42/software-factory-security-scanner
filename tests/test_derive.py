"""Tests for git-history-based dependency derivation (derive.py).

Each test builds a real local git repo with manifest history — no network,
fully deterministic.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sf_scan.derive import (
    WoDelivery,
    derive_dependencies,
    manifest_delta,
    pr_number_from_url,
    resolve_wo_commits,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _pkg_json(deps: dict[str, str]) -> str:
    return json.dumps({"name": "target", "version": "1.0.0", "dependencies": deps})


def _init_repo(root: Path, deps: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(_pkg_json(deps))
    subprocess.run(
        ["git", "init", "-q", "-b", "main"], cwd=root, check=True, capture_output=True
    )
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _commit_deps_on_branch(
    repo: Path, branch: str, deps: dict[str, str], message: str = "add deps"
) -> None:
    _git(repo, "checkout", "-q", "-b", branch)
    (repo / "package.json").write_text(_pkg_json(deps))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", message)
    _git(repo, "checkout", "-q", "main")


@pytest.fixture
def repo_with_wo_branch(tmp_path: Path) -> Path:
    """main has express; branch wo-1-validation adds lodash (unmerged)."""
    repo = _init_repo(tmp_path / "repo", {"express": "4.17.1"})
    _commit_deps_on_branch(
        repo, "wo-1-validation", {"express": "4.17.1", "lodash": "4.17.20"}
    )
    return repo


# ---------------------------------------------------------------------------
# PR number extraction
# ---------------------------------------------------------------------------


class TestPrNumberFromUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://github.com/org/repo/pull/42", 42),
            ("https://github.com/org/repo/pull/42/files", 42),
            ("https://gitlab.com/org/repo/-/merge_requests/7", 7),
            ("org/repo#13", 13),
            ("https://example.com/pr/99/", 99),
        ],
    )
    def test_extracts_number(self, url: str, expected: int) -> None:
        assert pr_number_from_url(url) == expected

    def test_no_number_returns_none(self) -> None:
        assert pr_number_from_url("https://github.com/org/repo") is None


# ---------------------------------------------------------------------------
# Commit resolution
# ---------------------------------------------------------------------------


class TestResolveWoCommits:
    def test_resolves_merge_commit_by_pr_number(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        _git(
            repo,
            "merge",
            "--no-ff",
            "-m",
            "Merge pull request #7 from org/wo-1-validation",
            "wo-1-validation",
        )
        resolved = resolve_wo_commits(
            repo, pr_url="https://github.com/org/repo/pull/7"
        )
        assert resolved is not None
        base, head = resolved
        assert head == _git(repo, "rev-parse", "HEAD")
        assert base == _git(repo, "rev-parse", "HEAD^")

    def test_resolves_squash_commit_by_pr_number(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        _git(repo, "merge", "--squash", "-q", "wo-1-validation")
        _git(repo, "commit", "-q", "-m", "feat: manifest validation (#7)")
        resolved = resolve_wo_commits(
            repo, pr_url="https://github.com/org/repo/pull/7"
        )
        assert resolved is not None
        base, head = resolved
        assert head == _git(repo, "rev-parse", "HEAD")

    def test_resolves_live_branch_via_merge_base(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        resolved = resolve_wo_commits(repo, branch="wo-1-validation")
        assert resolved is not None
        base, head = resolved
        assert head == _git(repo, "rev-parse", "wo-1-validation")
        assert base == _git(repo, "rev-parse", "main")

    def test_unknown_pr_and_branch_returns_none(self, repo_with_wo_branch: Path) -> None:
        resolved = resolve_wo_commits(
            repo_with_wo_branch,
            branch="no-such-branch",
            pr_url="https://github.com/org/repo/pull/999",
        )
        assert resolved is None


# ---------------------------------------------------------------------------
# Manifest delta
# ---------------------------------------------------------------------------


class TestManifestDelta:
    def test_delta_contains_only_new_packages(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        base = _git(repo, "rev-parse", "main")
        head = _git(repo, "rev-parse", "wo-1-validation")
        assert manifest_delta(repo, base, head) == {("npm", "lodash")}

    def test_removed_packages_do_not_appear(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo", {"express": "4.17.1", "lodash": "4.17.20"})
        _commit_deps_on_branch(repo, "wo-2-cleanup", {"express": "4.17.1"})
        base = _git(repo, "rev-parse", "main")
        head = _git(repo, "rev-parse", "wo-2-cleanup")
        assert manifest_delta(repo, base, head) == set()

    def test_worktrees_are_cleaned_up(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        base = _git(repo, "rev-parse", "main")
        head = _git(repo, "rev-parse", "wo-1-validation")
        manifest_delta(repo, base, head)
        worktrees = _git(repo, "worktree", "list")
        assert len(worktrees.splitlines()) == 1  # only the main checkout


# ---------------------------------------------------------------------------
# derive_dependencies
# ---------------------------------------------------------------------------


class TestDeriveDependencies:
    def test_derives_deps_for_merged_pr(self, repo_with_wo_branch: Path) -> None:
        repo = repo_with_wo_branch
        _git(
            repo,
            "merge",
            "--no-ff",
            "-m",
            "Merge pull request #7 from org/wo-1-validation",
            "wo-1-validation",
        )
        result = derive_dependencies(
            repo,
            [WoDelivery(wo_id="WO-1", pr_url="https://github.com/org/repo/pull/7")],
        )
        assert result.deps_by_wo == {"WO-1": ["npm:lodash"]}
        assert "WO-1" in result.provenance
        assert result.warnings == []

    def test_derives_deps_for_live_branch(self, repo_with_wo_branch: Path) -> None:
        result = derive_dependencies(
            repo_with_wo_branch,
            [WoDelivery(wo_id="WO-1", branch="wo-1-validation")],
        )
        assert result.deps_by_wo == {"WO-1": ["npm:lodash"]}

    def test_unresolvable_wo_warns_and_skips(self, repo_with_wo_branch: Path) -> None:
        result = derive_dependencies(
            repo_with_wo_branch,
            [WoDelivery(wo_id="WO-9", branch="deleted-branch")],
        )
        assert result.deps_by_wo == {}
        assert any("WO-9" in w for w in result.warnings)

    def test_wo_without_delivery_warns(self, repo_with_wo_branch: Path) -> None:
        result = derive_dependencies(repo_with_wo_branch, [WoDelivery(wo_id="WO-3")])
        assert result.deps_by_wo == {}
        assert any("WO-3" in w and "no delivery" in w for w in result.warnings)

    def test_malformed_base_manifest_warns_without_fabricating_additions(
        self, tmp_path: Path
    ) -> None:
        repo = _init_repo(tmp_path / "repo", {})
        (repo / "package.json").write_text("{")
        _git(repo, "add", "package.json")
        _git(repo, "commit", "--amend", "-q", "-m", "malformed base")
        _commit_deps_on_branch(repo, "wo-4-repair", {"lodash": "4.17.20"})

        result = derive_dependencies(
            repo,
            [WoDelivery(wo_id="WO-4", branch="wo-4-repair")],
        )

        assert result.deps_by_wo == {}
        assert any(
            "WO-4" in warning and "manifest parse error" in warning
            for warning in result.warnings
        )

    def test_malformed_head_manifest_warns_without_recording_a_delta(
        self, tmp_path: Path
    ) -> None:
        repo = _init_repo(tmp_path / "repo", {"express": "4.17.1"})
        _git(repo, "checkout", "-q", "-b", "wo-5-broken")
        (repo / "package.json").write_text("{")
        _git(repo, "add", "package.json")
        _git(repo, "commit", "-q", "-m", "break manifest")
        _git(repo, "checkout", "-q", "main")

        result = derive_dependencies(
            repo,
            [WoDelivery(wo_id="WO-5", branch="wo-5-broken")],
        )

        assert result.deps_by_wo == {}
        assert any(
            "WO-5" in warning and "manifest parse error" in warning
            for warning in result.warnings
        )
        assert len(_git(repo, "worktree", "list").splitlines()) == 1
