"""Dependency manifest extraction.

Walks a cloned repo's tree and parses every supported manifest file into a
normalized list of :class:`Dependency` records. Lockfile entries (specific
resolved versions) take precedence over manifest entries (version specifiers)
when both exist in the same directory.

Supported formats:
- npm: ``package.json``, ``package-lock.json`` (lockfile v1 and v2/v3)
- PyPI: ``requirements.txt``, ``pyproject.toml`` (PEP 621 + Poetry), ``Pipfile.lock``
- Go modules: ``go.mod``
- RubyGems: ``Gemfile.lock``
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .models import Dependency


class ManifestParseError(Exception):
    """Raised when a manifest file is malformed."""


# Directories skipped during the walk to avoid scanning installed dependency
# trees themselves (which would inflate the dependency list with transitive
# manifests rather than the target project's declared deps).
_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "ENV",
        "__pycache__",
        ".tox",
        ".nox",
        "dist",
        "build",
        ".pytest_cache",
        "vendor",  # Go and Ruby use vendor/ for bundled deps
    }
)

_LOCKFILE_NAMES = frozenset(
    {"package-lock.json", "Pipfile.lock", "Gemfile.lock", "poetry.lock"}
)

# Best-effort name + (optional pinned) version extractor for PEP 508
# requirement strings and ``requirements.txt`` lines. We intentionally don't
# preserve full version specifiers — the scanner queries OSV.dev against the
# package name and uses the pinned version when present.
_REQ_LINE_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_.\-]+)"
    r"(?:\[[^\]]*\])?"  # optional extras like requests[socks]
    r"(?:\s*(?:==|>=|<=|~=|!=|<|>)\s*(?P<version>[^;,\s]+))?",
)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def extract_dependencies(repo_root: Path) -> list[Dependency]:
    """Walk ``repo_root`` and return all declared dependencies, deduplicated."""
    deps: list[Dependency] = []
    for path in _walk_manifests(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        deps.extend(_dispatch_parser(path, rel))
    return _dedup(deps)


def _walk_manifests(repo_root: Path):
    """Yield manifest file paths under ``repo_root``, skipping vendor dirs."""
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if path.name in _MANIFEST_PARSERS:
            yield path


def _dispatch_parser(path: Path, rel_path: str) -> list[Dependency]:
    parser = _MANIFEST_PARSERS.get(path.name)
    if parser is None:
        return []
    return parser(path, rel_path)


# ---------------------------------------------------------------------------
# Per-format parsers
# ---------------------------------------------------------------------------


def parse_package_json(path: Path, rel_path: str) -> list[Dependency]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestParseError(f"Malformed JSON in {rel_path}: {e}") from e
    if not isinstance(data, dict):
        return []
    out: list[Dependency] = []
    for kind, key in (("runtime", "dependencies"), ("dev", "devDependencies")):
        section = data.get(key) or {}
        if not isinstance(section, dict):
            continue
        for name, version in section.items():
            out.append(
                Dependency(
                    ecosystem="npm",
                    package=name,
                    version=str(version) if version is not None else None,
                    manifest_path=rel_path,
                    kind=kind,
                )
            )
    return out


def parse_package_lock(path: Path, rel_path: str) -> list[Dependency]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestParseError(f"Malformed JSON in {rel_path}: {e}") from e
    if not isinstance(data, dict):
        return []

    out: list[Dependency] = []
    seen: set[tuple[str, str]] = set()

    # Lockfile v2/v3 uses a top-level "packages" object keyed by install path.
    packages = data.get("packages")
    if isinstance(packages, dict):
        for pkg_path, info in packages.items():
            if not pkg_path or not isinstance(info, dict):
                continue  # "" is the root package itself
            # The package name lives after the last "node_modules/" segment.
            if "node_modules/" in pkg_path:
                name = pkg_path.rsplit("node_modules/", 1)[-1]
            else:
                name = info.get("name") or pkg_path
            version = info.get("version")
            if not version:
                continue
            kind = "dev" if info.get("dev") else "runtime"
            if (name, version) in seen:
                continue
            seen.add((name, version))
            out.append(
                Dependency(
                    ecosystem="npm",
                    package=name,
                    version=str(version),
                    manifest_path=rel_path,
                    kind=kind,
                )
            )
        return out

    # Lockfile v1 fallback uses a recursive "dependencies" tree.
    deps_tree = data.get("dependencies")
    if isinstance(deps_tree, dict):

        def walk(tree: dict, is_dev: bool) -> None:
            for name, info in tree.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version")
                if version and (name, version) not in seen:
                    seen.add((name, version))
                    out.append(
                        Dependency(
                            ecosystem="npm",
                            package=name,
                            version=str(version),
                            manifest_path=rel_path,
                            kind="dev" if (is_dev or info.get("dev")) else "runtime",
                        )
                    )
                nested = info.get("dependencies")
                if isinstance(nested, dict):
                    walk(nested, is_dev or bool(info.get("dev")))

        walk(deps_tree, is_dev=False)

    return out


def parse_requirements_txt(path: Path, rel_path: str) -> list[Dependency]:
    out: list[Dependency] = []
    text = path.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        # Skip pip flags (-r, -e, --extra-index-url, etc.) and url/file installs.
        if line.startswith("-") or line.startswith(
            ("git+", "http://", "https://", "file://")
        ):
            continue
        m = _REQ_LINE_RE.match(line)
        if not m:
            continue
        out.append(
            Dependency(
                ecosystem="PyPI",
                package=m.group("name"),
                version=m.group("version"),
                manifest_path=rel_path,
                kind="runtime",
            )
        )
    return out


def parse_pyproject_toml(path: Path, rel_path: str) -> list[Dependency]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ManifestParseError(f"Malformed TOML in {rel_path}: {e}") from e

    out: list[Dependency] = []
    project = data.get("project") or {}

    # PEP 621 runtime
    for spec in project.get("dependencies") or []:
        name, version = _parse_pep508(spec)
        if name:
            out.append(
                Dependency(
                    ecosystem="PyPI",
                    package=name,
                    version=version,
                    manifest_path=rel_path,
                    kind="runtime",
                )
            )

    # PEP 621 optional-dependencies (treated as dev)
    optional = project.get("optional-dependencies") or {}
    if isinstance(optional, dict):
        for specs in optional.values():
            for spec in specs:
                name, version = _parse_pep508(spec)
                if name:
                    out.append(
                        Dependency(
                            ecosystem="PyPI",
                            package=name,
                            version=version,
                            manifest_path=rel_path,
                            kind="dev",
                        )
                    )

    # Poetry [tool.poetry.dependencies]
    poetry = (data.get("tool") or {}).get("poetry") or {}
    for name, spec in (poetry.get("dependencies") or {}).items():
        if name.lower() == "python":
            continue
        version: str | None
        if isinstance(spec, str):
            version = spec
        elif isinstance(spec, dict):
            version = spec.get("version")
        else:
            version = None
        out.append(
            Dependency(
                ecosystem="PyPI",
                package=name,
                version=version,
                manifest_path=rel_path,
                kind="runtime",
            )
        )

    return out


def parse_go_mod(path: Path, rel_path: str) -> list[Dependency]:
    out: list[Dependency] = []
    text = path.read_text(encoding="utf-8")

    # Block form: require ( ... )
    for block in re.finditer(r"require\s*\(([^)]*)\)", text, flags=re.DOTALL):
        for line in block.group(1).splitlines():
            line = line.split("//", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                out.append(
                    Dependency(
                        ecosystem="Go",
                        package=parts[0],
                        version=parts[1],
                        manifest_path=rel_path,
                        kind="runtime",
                    )
                )

    # Single-line form: require module version
    for match in re.finditer(
        r"^require\s+(?P<mod>\S+)\s+(?P<ver>\S+)\s*(?://.*)?$",
        text,
        flags=re.MULTILINE,
    ):
        out.append(
            Dependency(
                ecosystem="Go",
                package=match.group("mod"),
                version=match.group("ver"),
                manifest_path=rel_path,
                kind="runtime",
            )
        )

    return out


def parse_gemfile_lock(path: Path, rel_path: str) -> list[Dependency]:
    """Parse top-level gems from a Gemfile.lock's ``GEM > specs:`` section.

    Top-level gems are indented exactly 4 spaces under ``specs:``; transitive
    deps are indented 6+. We capture only the top level — they're the direct
    declarations a Work Order would have introduced.
    """
    out: list[Dependency] = []
    in_gem_section = False
    in_specs = False

    spec_re = re.compile(r"^([A-Za-z0-9_\-]+)\s+\(([^)]+)\)\s*$")

    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "GEM":
            in_gem_section = True
            in_specs = False
            continue
        if in_gem_section and not line.startswith(" ") and line != "":
            # Left a GEM block (e.g., entered PLATFORMS or DEPENDENCIES section)
            in_gem_section = False
            in_specs = False
            continue
        if in_gem_section and line.strip() == "specs:":
            in_specs = True
            continue
        if in_specs and line.startswith("    ") and not line.startswith("      "):
            m = spec_re.match(line.strip())
            if m:
                out.append(
                    Dependency(
                        ecosystem="RubyGems",
                        package=m.group(1),
                        version=m.group(2),
                        manifest_path=rel_path,
                        kind="runtime",
                    )
                )

    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_pep508(spec: str) -> tuple[str | None, str | None]:
    """Best-effort PEP 508 extract: returns (name, optional pinned version)."""
    # Drop environment markers (text after ``;``) — they don't affect the name.
    head = spec.split(";", 1)[0].strip()
    m = _REQ_LINE_RE.match(head)
    if not m:
        return None, None
    return m.group("name"), m.group("version")


def _manifest_dir(rel_path: str) -> str:
    return rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""


def _is_lockfile(rel_path: str) -> bool:
    return rel_path.rsplit("/", 1)[-1] in _LOCKFILE_NAMES


def _dedup(deps: list[Dependency]) -> list[Dependency]:
    """Deduplicate by (ecosystem, package, manifest-dir). Lockfile wins."""
    by_key: dict[tuple[str, str, str], Dependency] = {}
    for d in deps:
        key = (d.ecosystem, d.package, _manifest_dir(d.manifest_path))
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = d
            continue
        # Lockfile entries (specific resolved versions) win over manifest entries.
        if _is_lockfile(d.manifest_path) and not _is_lockfile(existing.manifest_path):
            by_key[key] = d
    return sorted(
        by_key.values(),
        key=lambda d: (d.ecosystem, d.package, d.manifest_path),
    )


_MANIFEST_PARSERS: dict[str, callable] = {
    "package.json": parse_package_json,
    "package-lock.json": parse_package_lock,
    "requirements.txt": parse_requirements_txt,
    "pyproject.toml": parse_pyproject_toml,
    "go.mod": parse_go_mod,
    "Gemfile.lock": parse_gemfile_lock,
}
