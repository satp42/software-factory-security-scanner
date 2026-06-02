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

    def test_scan_with_valid_args_reaches_stub(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://github.com/example/repo",
            ]
        )
        # U1 stub: scan path validates inputs then exits 1 with "not yet
        # implemented" until U7 wires the orchestration.
        assert code == 1
        assert "not yet implemented" in stderr.lower()

    def test_scan_accepts_url_at_sha_syntax_without_error_in_u1(
        self, tmp_path: Path
    ) -> None:
        # U1 doesn't parse the @SHA — that's U7. We just confirm argparse
        # accepts the string and U1's stub fires.
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://github.com/example/repo@a1b2c3d",
            ]
        )
        assert code == 1
        assert "not yet implemented" in stderr.lower()


class TestRepeatableRepoFlag:
    def test_multiple_repos_accepted(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, stderr = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://github.com/example/one",
                "--repo",
                "https://github.com/example/two",
            ]
        )
        # Both URLs accepted by argparse, validation passes, stub fires.
        assert code == 1
        assert "not yet implemented" in stderr.lower()
