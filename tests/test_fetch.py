"""Tests for repo fetch helper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from sf_scan.fetch import RepoFetchError, clone_repo, parse_repo_spec


class TestParseRepoSpec:
    def test_https_url_without_sha(self) -> None:
        url, sha = parse_repo_spec("https://github.com/example/repo")
        assert url == "https://github.com/example/repo"
        assert sha is None

    def test_https_url_with_sha(self) -> None:
        url, sha = parse_repo_spec("https://github.com/example/repo@a1b2c3d")
        assert url == "https://github.com/example/repo"
        assert sha == "a1b2c3d"

    def test_https_url_with_long_sha(self) -> None:
        url, sha = parse_repo_spec(
            "https://github.com/example/repo@1234567890abcdef1234567890abcdef12345678"
        )
        assert url == "https://github.com/example/repo"
        assert sha == "1234567890abcdef1234567890abcdef12345678"

    def test_ssh_url_at_not_split(self) -> None:
        # SSH URLs of the form git@host:org/repo must not be split — the @ is
        # part of the host portion.
        url, sha = parse_repo_spec("git@github.com:example/repo")
        assert url == "git@github.com:example/repo"
        assert sha is None


class TestCloneRepo:
    def test_clone_local_bare_repo_succeeds(self, tmp_path: Path) -> None:
        # Build a tiny local bare repo, then clone it via the helper. Avoids
        # network and exercises the real git subprocess path.
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],
            cwd=upstream,
            check=True,
            capture_output=True,
        )
        (upstream / "README.md").write_text("hello")
        subprocess.run(
            ["git", "-C", str(upstream), "config", "user.email", "test@example.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "commit", "-q", "-m", "init"],
            check=True,
            capture_output=True,
        )

        with clone_repo(f"file://{upstream}") as cloned:
            assert cloned.exists()
            assert (cloned / "README.md").read_text() == "hello"

        # Temp directory cleaned up after context exit.
        assert not cloned.exists()

    def test_clone_nonexistent_url_raises(self, tmp_path: Path) -> None:
        with pytest.raises(RepoFetchError) as exc_info:
            with clone_repo(f"file://{tmp_path}/no-such-repo"):
                pass
        assert "git clone failed" in str(exc_info.value)

    def test_clone_with_bad_sha_raises(self, tmp_path: Path) -> None:
        # Local fixture repo for the SHA check.
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        subprocess.run(
            ["git", "init", "-q", "-b", "main"],
            cwd=upstream,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "config", "user.email", "test@example.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
        (upstream / "README.md").write_text("hello")
        subprocess.run(
            ["git", "-C", str(upstream), "add", "."],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(upstream), "commit", "-q", "-m", "init"],
            check=True,
            capture_output=True,
        )

        with pytest.raises(RepoFetchError) as exc_info:
            with clone_repo(f"file://{upstream}", sha="deadbeef0000"):
                pass
        assert "checkout" in str(exc_info.value).lower()


@pytest.mark.skipif(
    os.environ.get("SF_SCAN_NETWORK_TESTS") != "1",
    reason="Network test; opt-in via SF_SCAN_NETWORK_TESTS=1",
)
class TestCloneRepoNetwork:
    def test_clone_sf_harness(self) -> None:
        with clone_repo("https://github.com/8090-inc/software-factory-harness") as p:
            # Bare minimum: the cloned tree exists and has a README.
            assert any(p.iterdir())
