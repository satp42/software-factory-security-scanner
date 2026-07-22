"""Derive per-Work-Order dependency attribution from git history.

Real Software Factory Work Orders carry no machine-readable dependency
declarations — the ``dependencies-introduced`` frontmatter field exists only
in this repo's synthetic Knowledge Graph. What real deployments *do* leave
behind is execution state: ``.sw-factory/WO-<n>/context.md`` ties each Work
Order to a delivery branch and/or pull-request URL. From either of those the
Work Order's commit range is recoverable with plain git, and the dependency
delta is computed by running the manifest extractor over the repo tree at
the range's base and head.

``manifest_delta`` is also Lens 4's ``Sd`` sub-signal primitive (F1 over the
dependency manifest delta) — built once, serving both lenses.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .extract import ManifestParseError, extract_dependencies


class DerivationError(Exception):
    """Raised when inputs needed for derivation cannot be read reliably."""


@dataclass(frozen=True)
class WoDelivery:
    """A Work Order's delivery coordinates, as recorded in ``.sw-factory``."""

    wo_id: str
    branch: str | None = None
    pr_url: str | None = None


@dataclass
class DerivationResult:
    """Derived ``eco:pkg`` attributions plus per-WO provenance and warnings."""

    deps_by_wo: dict[str, list[str]] = field(default_factory=dict)
    # wo_id → "base..head" range the delta was computed from
    provenance: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Git plumbing
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip().splitlines()
        tail = stderr[-1] if stderr else f"exit {e.returncode}"
        raise DerivationError(f"git {' '.join(args)}: {tail}") from e
    return proc.stdout.strip()


def _rev_or_none(repo: Path, rev: str) -> str | None:
    try:
        return _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    except DerivationError:
        return None


_PR_NUMBER_RE = re.compile(r"/pull/(\d+)|/merge_requests/(\d+)|#(\d+)$|/(\d+)/?$")


def pr_number_from_url(pr_url: str) -> int | None:
    """Extract a PR number from a pull-request URL (GitHub/GitLab shapes)."""
    match = _PR_NUMBER_RE.search(pr_url.strip())
    if not match:
        return None
    return int(next(g for g in match.groups() if g is not None))


def resolve_wo_commits(
    repo: Path,
    branch: str | None = None,
    pr_url: str | None = None,
) -> tuple[str, str] | None:
    """Resolve a Work Order's delivery to a ``(base_sha, head_sha)`` range.

    Resolution order:

    1. **PR URL** — find the squash/merge commit on the current history whose
       subject references the PR number (``Merge pull request #N`` or the
       squash convention ``(#N)``). Base is its first parent. Works after the
       delivery branch has been deleted, which is the common steady state.
    2. **Branch ref** — if the delivery branch still exists (locally or on
       origin), head is its tip and base is the merge-base with the current
       HEAD history.

    Returns None when neither channel resolves.
    """
    if pr_url:
        number = pr_number_from_url(pr_url)
        if number is not None:
            for pattern in (
                f"Merge pull request #{number} ",
                f"(#{number})",
            ):
                try:
                    sha = _git(
                        repo,
                        "log",
                        f"--grep={pattern}",
                        "--fixed-strings",
                        "--format=%H",
                        "-n",
                        "1",
                        "HEAD",
                    )
                except DerivationError:
                    sha = ""
                if sha:
                    base = _rev_or_none(repo, f"{sha}^")
                    if base is not None:
                        return base, sha

    if branch:
        head = _rev_or_none(repo, branch) or _rev_or_none(repo, f"origin/{branch}")
        if head is not None:
            try:
                base = _git(repo, "merge-base", "HEAD", head)
            except DerivationError:
                base = None
            if base and base != head:
                return base, head

    return None


# ---------------------------------------------------------------------------
# Manifest delta (Lens 4 `Sd` primitive)
# ---------------------------------------------------------------------------


def manifest_delta(repo: Path, base_sha: str, head_sha: str) -> set[tuple[str, str]]:
    """Return the ``(ecosystem, package)`` set introduced between two trees.

    Checks out each SHA into a temporary worktree and reuses the tested
    manifest extractor on both — so every ecosystem and lockfile format that
    Lens 1 scans is covered here for free.
    """
    return _deps_at(repo, head_sha) - _deps_at(repo, base_sha)


def _deps_at(repo: Path, sha: str) -> set[tuple[str, str]]:
    with tempfile.TemporaryDirectory(prefix="sf-scan-wt-") as tmp:
        worktree = Path(tmp) / "tree"
        _git(repo, "worktree", "add", "--detach", str(worktree), sha)
        try:
            try:
                deps = extract_dependencies(worktree)
            except ManifestParseError as e:
                raise DerivationError(
                    f"manifest parse error at {sha[:12]}: {e}"
                ) from e
            return {d.as_key() for d in deps}
        finally:
            try:
                _git(repo, "worktree", "remove", "--force", str(worktree))
            except DerivationError:
                pass  # TemporaryDirectory cleanup removes the tree regardless


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def derive_dependencies(
    repo: Path, deliveries: list[WoDelivery]
) -> DerivationResult:
    """Compute derived ``dependencies-introduced`` for each Work Order.

    Unresolvable Work Orders get no attribution and a warning — their
    findings then surface in the report's Unmapped section rather than being
    silently misattributed.
    """
    result = DerivationResult()
    for delivery in deliveries:
        if not delivery.branch and not delivery.pr_url:
            result.warnings.append(
                f"derivation: {delivery.wo_id} has no delivery branch or PR URL"
            )
            continue
        try:
            resolved = resolve_wo_commits(
                repo, branch=delivery.branch, pr_url=delivery.pr_url
            )
        except DerivationError as e:
            result.warnings.append(f"derivation: {delivery.wo_id}: {e}")
            continue
        if resolved is None:
            result.warnings.append(
                f"derivation: {delivery.wo_id}: could not resolve commits for "
                f"branch={delivery.branch!r} pr={delivery.pr_url!r}"
            )
            continue
        base_sha, head_sha = resolved
        try:
            delta = manifest_delta(repo, base_sha, head_sha)
        except DerivationError as e:
            result.warnings.append(f"derivation: {delivery.wo_id}: {e}")
            continue
        result.deps_by_wo[delivery.wo_id] = sorted(
            f"{eco}:{pkg}" for eco, pkg in delta
        )
        result.provenance[delivery.wo_id] = f"{base_sha[:12]}..{head_sha[:12]}"
    return result
