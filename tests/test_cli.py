"""Tests for the sf-scan CLI surface (U1)."""

from __future__ import annotations

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from sf_scan import __version__
from sf_scan.cli import main


def _capture(argv: list[str]) -> tuple[int, str, str]:
    """Run ``main(argv)`` and capture exit code, stdout, and stderr.

    argparse paths (``--version``, ``--help``, parse errors) raise
    ``SystemExit``; this helper normalizes them into a plain return value
    so test assertions stay readable.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        try:
            exit_code = main(argv)
        except SystemExit as e:
            exit_code = int(e.code) if e.code is not None else 0
    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


class TestVersion:
    def test_prints_version_and_exits_zero(self) -> None:
        code, stdout, stderr = _capture(["--version"])
        combined = stdout + stderr
        assert code == 0
        assert __version__ in combined


class TestHelp:
    def test_top_level_help_exits_zero(self) -> None:
        code, stdout, _ = _capture(["--help"])
        assert code == 0
        assert "sf-scan" in stdout
        assert "scan" in stdout  # subcommand listed in help output

    def test_scan_help_lists_all_flags(self) -> None:
        code, stdout, _ = _capture(["scan", "--help"])
        assert code == 0
        for flag in ("--repo", "--repo-list", "--kg", "--out", "--no-cache"):
            assert flag in stdout, f"scan --help should mention {flag}"


class TestScanInvocation:
    def test_no_command_returns_usage_error(self) -> None:
        code, _, stderr = _capture([])
        assert code == 2
        assert "usage" in stderr.lower() or "sf-scan" in stderr.lower()

    def test_scan_without_kg_argparse_rejects(self) -> None:
        # argparse fires its own error on missing --kg before our validation runs.
        code, _, stderr = _capture(["scan"])
        assert code == 2
        assert "--kg" in stderr

    def test_scan_with_kg_but_no_repo_targets_fails(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(["scan", "--kg", str(kg_dir)])
        assert code == 2
        assert "--repo" in stderr
        assert "--repo-list" in stderr

    def test_scan_with_nonexistent_repo_list_fails_cleanly(
        self, tmp_path: Path
    ) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        missing = tmp_path / "does-not-exist.txt"
        code, _, stderr = _capture(
            ["scan", "--kg", str(kg_dir), "--repo-list", str(missing)]
        )
        assert code == 2
        assert "--repo-list" in stderr
        assert "does not exist" in stderr.lower() or str(missing) in stderr

    def test_scan_with_valid_args_invokes_real_orchestration(
        self, tmp_path: Path
    ) -> None:
        # With U7 wired, the scan path reaches real orchestration. A bogus
        # remote URL ends up at the all-clones-failed exit code (3), not the
        # original U1 "not yet implemented" stub.
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://example.invalid/no-such-repo",
            ]
        )
        # Exit 3 = input error (all clones failed). Stub message no longer
        # appears.
        assert code == 3
        assert "not yet implemented" not in stderr.lower()

    def test_scan_accepts_url_at_sha_syntax(self, tmp_path: Path) -> None:
        # U7 parses the @SHA. Bogus URL still fails to clone (exit 3) but
        # argparse no longer rejects the URL@SHA shape itself.
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, _ = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://example.invalid/repo@a1b2c3d",
            ]
        )
        assert code == 3


class TestRepeatableRepoFlag:
    def test_multiple_repos_accepted_by_argparse(self, tmp_path: Path) -> None:
        # Both URLs accepted by argparse; orchestration tries to clone each
        # and fails (bogus URLs), exiting 3. We only assert argparse didn't
        # itself reject the repeatable flag.
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://example.invalid/one",
                "--repo",
                "https://example.invalid/two",
            ]
        )
        assert code == 3
        # Both URLs surfaced in the per-target scanning log
        assert "example.invalid/one" in stderr
        assert "example.invalid/two" in stderr
