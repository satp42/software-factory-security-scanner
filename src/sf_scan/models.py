"""Core data models used across the scanner pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Dependency:
    """A package dependency discovered in a project's manifest file."""

    ecosystem: str  # "npm" | "PyPI" | "Go" | "RubyGems"
    package: str
    version: str | None  # None when the manifest doesn't pin a version
    manifest_path: str  # repo-relative POSIX path to the manifest that declared it
    kind: str = "runtime"  # "runtime" | "dev"

    def as_key(self) -> tuple[str, str]:
        """Return the ``(ecosystem, package)`` key used for KG resolver lookups."""
        # KG mapping is by ecosystem + package, not version — Work Orders declare
        # what they introduced, not which version is currently pinned.
        return (self.ecosystem, self.package)


@dataclass(frozen=True)
class Finding:
    """A vulnerability finding for a single dependency."""

    cve_id: str
    package: str
    ecosystem: str
    version: str | None
    severity: str  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
    summary: str
    fix_version: str | None
    sources: tuple[str, ...] = field(default_factory=tuple)  # ("OSV", "GHSA")
    dependency_ref: Dependency | None = None
    references: tuple[str, ...] = field(default_factory=tuple)  # advisory URLs

    @property
    def severity_rank(self) -> int:
        """Numeric rank for sorting; higher is worse."""
        return {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "UNKNOWN": 0,
        }.get(self.severity, 0)
