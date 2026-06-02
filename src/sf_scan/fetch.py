"""Repo fetch helper. Clones a target GitHub repository into a temp directory.

The clone is shallow when no SHA is pinned (depth 1). When a SHA is provided,
clone with a larger depth and check it out — depth 1 alone wouldn't fetch the
commit unless it happens to be HEAD.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class RepoFetchError(Exception):
    """Raised when ``git clone`` or ``git checkout`` fails."""


def parse_repo_spec(spec: str) -> tuple[str, str | None]:
    """Split an ``URL[@SHA]`` spec into ``(url, sha)``.

    HTTPS URLs are split on the last ``@``. SSH-style URLs (``git@host:org/repo``)
    are returned as-is because their ``@`` is part of the host portion.
    """
    if spec.startswith(("http://", "https://")) and "@" in spec:
        url, sha = spec.rsplit("@", 1)
        return url, sha
    return spec, None


@contextmanager
def clone_repo(url: str, sha: str | None = None) -> Iterator[Path]:
    """Clone ``url`` (optionally at ``sha``) into a temp directory.

    Yields the absolute path to the cloned tree. Cleans up the temp directory
    when the context exits, even if an exception is raised inside.
    """
    tempdir = Path(tempfile.mkdtemp(prefix="sf-scan-"))
    target = tempdir / "repo"
    try:
        depth = ["--depth", "1"] if sha is None else ["--depth", "50"]
        try:
            subprocess.run(
                ["git", "clone", *depth, url, str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip().splitlines()
            tail = stderr[-1] if stderr else f"exit {e.returncode}"
            raise RepoFetchError(f"git clone failed for {url}: {tail}") from e

        if sha is not None:
            try:
                subprocess.run(
                    ["git", "-C", str(target), "checkout", sha],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                stderr = (e.stderr or "").strip().splitlines()
                tail = stderr[-1] if stderr else f"exit {e.returncode}"
                raise RepoFetchError(
                    f"git checkout {sha} failed for {url}: {tail}"
                ) from e

        yield target
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
