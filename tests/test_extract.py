"""Tests for manifest extraction."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sf_scan.extract import (
    ManifestParseError,
    extract_dependencies,
    parse_gemfile_lock,
    parse_go_mod,
    parse_package_json,
    parse_package_lock,
    parse_pyproject_toml,
    parse_requirements_txt,
)
from sf_scan.models import Dependency


FIXTURES = Path(__file__).parent / "fixtures" / "manifests"


# ---------------------------------------------------------------------------
# Per-parser tests
# ---------------------------------------------------------------------------


class TestPackageJson:
    def test_returns_runtime_and_dev_deps(self) -> None:
        deps = parse_package_json(FIXTURES / "npm" / "package.json", "npm/package.json")
        names = {(d.package, d.kind) for d in deps}
        assert ("express", "runtime") in names
        assert ("lodash", "runtime") in names
        assert ("axios", "runtime") in names
        assert ("jest", "dev") in names
        assert ("typescript", "dev") in names
        assert all(d.ecosystem == "npm" for d in deps)

    def test_handles_no_dev_deps(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text(json.dumps({"name": "x", "dependencies": {"a": "^1.0.0"}}))
        deps = parse_package_json(p, "package.json")
        assert len(deps) == 1
        assert deps[0].package == "a"

    def test_handles_empty_manifest(self, tmp_path: Path) -> None:
        p = tmp_path / "package.json"
        p.write_text(json.dumps({"name": "x"}))
        deps = parse_package_json(p, "package.json")
        assert deps == []

    def test_malformed_json_raises_typed_error(self) -> None:
        with pytest.raises(ManifestParseError) as exc_info:
            parse_package_json(
                FIXTURES / "malformed" / "package.json", "malformed/package.json"
            )
        assert "malformed/package.json" in str(exc_info.value)


class TestPackageLock:
    def test_v3_packages_block(self) -> None:
        deps = parse_package_lock(
            FIXTURES / "npm" / "package-lock.json", "npm/package-lock.json"
        )
        by_name = {d.package: d for d in deps}
        # Lockfile yields resolved versions, not specifiers.
        assert by_name["express"].version == "4.18.2"
        assert by_name["lodash"].version == "4.17.21"
        assert by_name["axios"].version == "1.4.0"
        # Dev marker propagated.
        assert by_name["jest"].kind == "dev"
        assert by_name["typescript"].kind == "dev"
        # Runtime deps default to runtime.
        assert by_name["express"].kind == "runtime"


class TestRequirementsTxt:
    def test_strips_comments_and_pip_flags(self) -> None:
        deps = parse_requirements_txt(
            FIXTURES / "pypi" / "requirements.txt", "pypi/requirements.txt"
        )
        names = {d.package for d in deps}
        assert "requests" in names
        assert "flask" in names
        assert "django" in names
        assert "pyyaml" in names
        assert "sqlalchemy" in names

    def test_skips_urls_and_editable_installs(self) -> None:
        deps = parse_requirements_txt(
            FIXTURES / "pypi" / "requirements.txt", "pypi/requirements.txt"
        )
        # url/editable lines must not appear as deps
        for d in deps:
            assert not d.package.startswith(("git+", "http"))
            assert not d.package.startswith(("-r", "-e"))

    def test_pinned_versions_captured(self) -> None:
        deps = parse_requirements_txt(
            FIXTURES / "pypi" / "requirements.txt", "pypi/requirements.txt"
        )
        by_name = {d.package: d for d in deps}
        assert by_name["requests"].version == "2.28.1"
        # ~= specifier should also capture the version
        assert by_name["django"].version == "4.1.0"

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "requirements.txt"
        p.write_text("")
        assert parse_requirements_txt(p, "requirements.txt") == []


class TestPyprojectToml:
    def test_pep621_runtime_dependencies(self) -> None:
        deps = parse_pyproject_toml(
            FIXTURES / "pypi" / "pyproject.toml", "pypi/pyproject.toml"
        )
        runtime = [d for d in deps if d.kind == "runtime"]
        names = {d.package for d in runtime}
        assert "requests" in names
        assert "pyyaml" in names
        assert "click" in names

    def test_pep621_optional_dependencies_marked_dev(self) -> None:
        deps = parse_pyproject_toml(
            FIXTURES / "pypi" / "pyproject.toml", "pypi/pyproject.toml"
        )
        dev = [d for d in deps if d.kind == "dev"]
        names = {d.package for d in dev}
        assert "pytest" in names
        assert "mypy" in names
        assert "sphinx" in names

    def test_malformed_toml_raises_typed_error(self, tmp_path: Path) -> None:
        p = tmp_path / "pyproject.toml"
        p.write_text("[[[not valid toml")
        with pytest.raises(ManifestParseError):
            parse_pyproject_toml(p, "pyproject.toml")


class TestGoMod:
    def test_parses_require_block(self) -> None:
        deps = parse_go_mod(FIXTURES / "go" / "go.mod", "go/go.mod")
        names = {d.package: d for d in deps}
        assert "github.com/gin-gonic/gin" in names
        assert names["github.com/gin-gonic/gin"].version == "v1.9.1"
        assert "github.com/spf13/cobra" in names
        assert names["github.com/spf13/cobra"].version == "v1.7.0"

    def test_parses_single_line_require(self) -> None:
        deps = parse_go_mod(FIXTURES / "go" / "go.mod", "go/go.mod")
        names = {d.package: d for d in deps}
        assert "github.com/google/uuid" in names
        assert names["github.com/google/uuid"].version == "v1.3.0"

    def test_all_marked_as_go_ecosystem(self) -> None:
        deps = parse_go_mod(FIXTURES / "go" / "go.mod", "go/go.mod")
        assert all(d.ecosystem == "Go" for d in deps)


class TestGemfileLock:
    def test_parses_top_level_gems_only(self) -> None:
        deps = parse_gemfile_lock(
            FIXTURES / "ruby" / "Gemfile.lock", "ruby/Gemfile.lock"
        )
        names = {d.package: d for d in deps}
        # Top-level gems
        assert "rails" in names
        assert "rack" in names
        assert "nokogiri" in names
        assert "pg" in names
        # Transitive deps (6-space indented under rails / nokogiri) excluded
        assert "actioncable" not in names
        assert "racc" not in names

    def test_versions_extracted(self) -> None:
        deps = parse_gemfile_lock(
            FIXTURES / "ruby" / "Gemfile.lock", "ruby/Gemfile.lock"
        )
        by_name = {d.package: d for d in deps}
        assert by_name["rails"].version == "7.0.4"
        assert by_name["nokogiri"].version == "1.14.3"


# ---------------------------------------------------------------------------
# extract_dependencies (walker + dedup) tests
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Assemble a small repo with one of every supported manifest."""
    repo = tmp_path / "repo"
    repo.mkdir()
    # Layout a few ecosystems side by side.
    shutil.copytree(FIXTURES / "npm", repo / "frontend")
    shutil.copytree(FIXTURES / "pypi", repo / "backend")
    shutil.copytree(FIXTURES / "go", repo / "service")
    shutil.copytree(FIXTURES / "ruby", repo / "ops")
    return repo


class TestExtractDependencies:
    def test_walks_repo_and_parses_each_format(self, sample_repo: Path) -> None:
        deps = extract_dependencies(sample_repo)
        ecosystems = {d.ecosystem for d in deps}
        assert {"npm", "PyPI", "Go", "RubyGems"} <= ecosystems

    def test_skips_node_modules(self, sample_repo: Path) -> None:
        # Plant a fake nested manifest inside node_modules; it must not appear.
        nm = sample_repo / "frontend" / "node_modules" / "react"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text('{"name": "react", "version": "18.2.0"}')
        deps = extract_dependencies(sample_repo)
        manifest_paths = {d.manifest_path for d in deps}
        for mp in manifest_paths:
            assert "node_modules" not in mp

    def test_lockfile_takes_precedence_over_manifest(
        self, sample_repo: Path
    ) -> None:
        deps = extract_dependencies(sample_repo)
        # Same package express appears in package.json (^4.18.0) and
        # package-lock.json (4.18.2). After dedup, only one record remains and
        # it carries the lockfile's resolved version.
        express = [
            d
            for d in deps
            if d.ecosystem == "npm" and d.package == "express"
        ]
        assert len(express) == 1
        assert express[0].version == "4.18.2"
        assert express[0].manifest_path.endswith("package-lock.json")

    def test_monorepo_subdir_manifests_kept_separate(self, tmp_path: Path) -> None:
        """Same package in two subdirs of a monorepo must appear twice."""
        repo = tmp_path / "monorepo"
        (repo / "pkg-a").mkdir(parents=True)
        (repo / "pkg-b").mkdir(parents=True)
        (repo / "pkg-a" / "package.json").write_text(
            json.dumps({"name": "a", "dependencies": {"lodash": "^4.17.0"}})
        )
        (repo / "pkg-b" / "package.json").write_text(
            json.dumps({"name": "b", "dependencies": {"lodash": "^4.17.0"}})
        )
        deps = extract_dependencies(repo)
        lodash_records = [d for d in deps if d.package == "lodash"]
        assert len(lodash_records) == 2

    def test_empty_repo_returns_empty_list(self, tmp_path: Path) -> None:
        repo = tmp_path / "empty"
        repo.mkdir()
        assert extract_dependencies(repo) == []

    def test_malformed_manifest_propagates_parse_error(
        self, sample_repo: Path
    ) -> None:
        (sample_repo / "bad").mkdir()
        (sample_repo / "bad" / "package.json").write_text("{this is not json")
        with pytest.raises(ManifestParseError):
            extract_dependencies(sample_repo)
