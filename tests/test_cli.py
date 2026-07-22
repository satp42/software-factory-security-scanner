"""Tests for the sf-scan CLI surface."""

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

    def test_scan_without_kg_source_rejected(self) -> None:
        # One of --kg / --kg-api / --kg-sw-factory is required.
        code, _, stderr = _capture(["scan", "--repo", "https://example.com/r"])
        assert code == 2
        assert "--kg" in stderr

    def test_kg_source_flags_mutually_exclusive(self) -> None:
        code, _, stderr = _capture(
            [
                "scan",
                "--repo",
                "https://example.com/r",
                "--kg",
                "some/dir",
                "--kg-sw-factory",
            ]
        )
        assert code == 2
        assert "not allowed with" in stderr

    def test_kg_api_without_key_env_rejected(self, monkeypatch) -> None:
        monkeypatch.delenv("SOFA_EXT_API_KEY", raising=False)
        code, _, stderr = _capture(
            [
                "scan",
                "--repo",
                "https://example.com/r",
                "--kg-api",
                "https://factory.example.com",
            ]
        )
        assert code == 2
        assert "SOFA_EXT_API_KEY" in stderr

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

    def test_scan_with_unreachable_repo_returns_input_error(
        self, tmp_path: Path
    ) -> None:
        # Every target clone fails ⇒ exit 3 (input error). The scan reached
        # the fetch stage; it didn't fail at arg validation.
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        code, _, _ = _capture(
            [
                "scan",
                "--kg",
                str(kg_dir),
                "--repo",
                "https://example.invalid/no-such-repo",
            ]
        )
        assert code == 3

    def test_scan_accepts_url_at_sha_syntax(self, tmp_path: Path) -> None:
        # URL@SHA is a parseable spec; argparse passes it through to fetch.
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
    def test_repeatable_repo_flag_scans_each_target(self, tmp_path: Path) -> None:
        # --repo is repeatable; every value reaches the per-target fetch
        # stage and shows up in the scanning log, even when all clones fail.
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
        assert "example.invalid/one" in stderr
        assert "example.invalid/two" in stderr
