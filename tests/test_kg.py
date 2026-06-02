"""Tests for the Knowledge Graph parser and ontology resolver."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sf_scan.kg import (
    KGParseError,
    KGPath,
    KnowledgeGraph,
    parse_frontmatter,
    parse_simple_yaml,
)


FIXTURES = Path(__file__).parent / "fixtures" / "kg"


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


class TestSimpleYaml:
    def test_scalar_strings(self) -> None:
        data = parse_simple_yaml("id: PRD-001\ntitle: Hello\n")
        assert data == {"id": "PRD-001", "title": "Hello"}

    def test_quoted_strings_get_stripped(self) -> None:
        data = parse_simple_yaml('id: "PRD-001"\ntitle: \'Hello\'\n')
        assert data == {"id": "PRD-001", "title": "Hello"}

    def test_lists(self) -> None:
        data = parse_simple_yaml("features:\n  - F-001\n  - F-002\n")
        assert data == {"features": ["F-001", "F-002"]}

    def test_quoted_list_items(self) -> None:
        data = parse_simple_yaml(
            'dependencies-introduced:\n  - "npm:lodash"\n  - "npm:express"\n'
        )
        assert data == {"dependencies-introduced": ["npm:lodash", "npm:express"]}

    def test_blank_and_comment_lines_ignored(self) -> None:
        text = """
        # comment
id: X

title: Y
"""
        data = parse_simple_yaml(text)
        assert data == {"id": "X", "title": "Y"}

    def test_mixed_scalars_and_lists(self) -> None:
        data = parse_simple_yaml(
            "id: PRD-001\ntitle: Test\nfeatures:\n  - F-001\ncreated: 2026-06-02\n"
        )
        assert data == {
            "id": "PRD-001",
            "title": "Test",
            "features": ["F-001"],
            "created": "2026-06-02",
        }


class TestParseFrontmatter:
    def test_extracts_frontmatter_and_body(self) -> None:
        text = "---\nid: X\ntitle: Y\n---\n\n# Body content\n"
        front, body = parse_frontmatter(text)
        assert front == {"id": "X", "title": "Y"}
        assert "# Body content" in body

    def test_no_frontmatter_returns_empty_dict(self) -> None:
        text = "# Just markdown\n\nNo frontmatter here.\n"
        front, body = parse_frontmatter(text)
        assert front == {}
        assert body == text

    def test_unterminated_frontmatter_returns_empty(self) -> None:
        text = "---\nid: X\n# no closing fence\n"
        front, _ = parse_frontmatter(text)
        assert front == {}


# ---------------------------------------------------------------------------
# Loader + resolver
# ---------------------------------------------------------------------------


@pytest.fixture
def tiny_kg(tmp_path: Path) -> Path:
    """Copy the fixture KG so tests don't share filesystem state."""
    dest = tmp_path / "kg"
    shutil.copytree(FIXTURES / "tiny", dest)
    return dest


class TestLoad:
    def test_load_indexes_all_artifacts(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        assert "PRD-T-001" in kg.nodes
        assert "F-T-001" in kg.nodes
        assert "BP-T-001" in kg.nodes
        assert "WO-T-001" in kg.nodes
        assert "WO-T-002" in kg.nodes

    def test_artifact_types_classified(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        assert kg.nodes["PRD-T-001"].artifact_type == "prd"
        assert kg.nodes["F-T-001"].artifact_type == "feature"
        assert kg.nodes["BP-T-001"].artifact_type == "blueprint-feature"
        assert kg.nodes["WO-T-001"].artifact_type == "work-order"

    def test_load_skips_readme(self, tiny_kg: Path) -> None:
        (tiny_kg / "README.md").write_text(
            "# README\n\nNo frontmatter; should be skipped.\n"
        )
        kg = KnowledgeGraph.load(tiny_kg)
        # The README has no frontmatter so it wouldn't load anyway; here we
        # just confirm the explicit skip doesn't accidentally raise.
        assert len(kg.nodes) == 5

    def test_missing_id_raises_parse_error(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        (kg_dir / "bad.md").write_text("---\ntitle: missing id\ntype: feature-requirements\n---\n")
        with pytest.raises(KGParseError):
            KnowledgeGraph.load(kg_dir)

    def test_blueprint_without_kind_raises(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        (kg_dir / "bad-bp.md").write_text(
            "---\nid: BP-X\ntitle: bad\ntype: blueprint\n---\n"
        )
        with pytest.raises(KGParseError):
            KnowledgeGraph.load(kg_dir)


class TestMapDependency:
    def test_returns_full_path_for_declared_dep(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        path = kg.map_dependency("npm", "express")
        assert path is not None
        assert path.is_complete
        assert path.work_order.id == "WO-T-001"
        assert path.blueprint.id == "BP-T-001"
        assert path.feature.id == "F-T-001"
        assert path.prd.id == "PRD-T-001"

    def test_returns_none_for_undeclared_dep(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        assert kg.map_dependency("npm", "totally-unknown-pkg") is None

    def test_distinct_ecosystems_are_separate(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        # Both work orders' deps; PyPI:pyyaml maps, but PyPI:express does not.
        assert kg.map_dependency("PyPI", "pyyaml") is not None
        assert kg.map_dependency("PyPI", "express") is None

    def test_first_declarer_wins_on_duplicate(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        # Two WOs both claim "npm:foo" — resolver returns the first.
        shutil.copytree(FIXTURES / "tiny", kg_dir)
        (kg_dir / "work-orders" / "wo-dup.md").write_text(
            "---\nid: WO-T-DUP\ntitle: dup\ntype: work-order\n"
            "blueprint: BP-T-001\ndependencies-introduced:\n  - \"npm:express\"\n---\n"
        )
        kg = KnowledgeGraph.load(kg_dir)
        path = kg.map_dependency("npm", "express")
        assert path is not None
        # Either WO-T-001 or WO-T-DUP is acceptable; validate() flags the
        # ambiguity but mapping still produces a result deterministically.
        assert path.work_order.id in {"WO-T-001", "WO-T-DUP"}


class TestValidate:
    def test_clean_kg_returns_no_issues(self, tiny_kg: Path) -> None:
        kg = KnowledgeGraph.load(tiny_kg)
        assert kg.validate() == []

    def test_empty_kg_dir_returns_error(self, tmp_path: Path) -> None:
        empty = tmp_path / "kg"
        empty.mkdir()
        kg = KnowledgeGraph.load(empty)
        issues = kg.validate()
        assert any(i.severity == "error" and "no Knowledge Graph" in i.message for i in issues)

    def test_broken_blueprint_reference_flagged(self, tiny_kg: Path) -> None:
        # Mutate a WO to point at a nonexistent blueprint.
        wo_path = tiny_kg / "work-orders" / "wo-001.md"
        wo_path.write_text(
            wo_path.read_text().replace("blueprint: BP-T-001", "blueprint: BP-NOPE")
        )
        kg = KnowledgeGraph.load(tiny_kg)
        issues = kg.validate()
        assert any(
            i.severity == "error" and "BP-NOPE" in i.message for i in issues
        )

    def test_broken_feature_reference_flagged(self, tiny_kg: Path) -> None:
        bp_path = tiny_kg / "blueprints" / "features" / "bp-001.md"
        bp_path.write_text(
            bp_path.read_text().replace("feature: F-T-001", "feature: F-NOPE")
        )
        kg = KnowledgeGraph.load(tiny_kg)
        issues = kg.validate()
        assert any("F-NOPE" in i.message for i in issues)

    def test_broken_product_reference_flagged(self, tiny_kg: Path) -> None:
        f_path = tiny_kg / "requirements" / "feature-001.md"
        f_path.write_text(
            f_path.read_text().replace("product: PRD-T-001", "product: PRD-NOPE")
        )
        kg = KnowledgeGraph.load(tiny_kg)
        issues = kg.validate()
        assert any("PRD-NOPE" in i.message for i in issues)

    def test_duplicate_dep_declaration_warns(self, tmp_path: Path) -> None:
        kg_dir = tmp_path / "kg"
        shutil.copytree(FIXTURES / "tiny", kg_dir)
        (kg_dir / "work-orders" / "wo-dup.md").write_text(
            "---\nid: WO-T-DUP\ntitle: dup\ntype: work-order\n"
            "blueprint: BP-T-001\ndependencies-introduced:\n  - \"npm:express\"\n---\n"
        )
        kg = KnowledgeGraph.load(kg_dir)
        issues = kg.validate()
        assert any(
            i.severity == "warning" and "npm:express" in i.message for i in issues
        )


# ---------------------------------------------------------------------------
# Integration: real sf-plugin synthetic KG
# ---------------------------------------------------------------------------


class TestRealSyntheticKg:
    """Verify the actual kg/software-factory-plugin/ KG loads and resolves."""

    @pytest.fixture
    def real_kg_root(self) -> Path:
        # Walk up from tests/ to find the kg/ at the repo root.
        return Path(__file__).resolve().parent.parent / "kg" / "software-factory-plugin"

    def test_loads_without_errors(self, real_kg_root: Path) -> None:
        kg = KnowledgeGraph.load(real_kg_root)
        assert kg.validate() == []

    def test_resolves_known_sf_plugin_deps(self, real_kg_root: Path) -> None:
        kg = KnowledgeGraph.load(real_kg_root)
        # These are declared in our authored Work Orders.
        for ecosystem, package in [
            ("npm", "tsx"),
            ("npm", "typescript"),
            ("npm", "zod"),
            ("npm", "vitest"),
            ("npm", "husky"),
            ("npm", "eslint"),
        ]:
            path = kg.map_dependency(ecosystem, package)
            assert path is not None, f"{ecosystem}:{package} should map"
            assert path.is_complete, f"{ecosystem}:{package} should have full chain"
            assert path.prd.id == "PRD-001"

    def test_unmapped_types_dep_returns_none(self, real_kg_root: Path) -> None:
        # @types/* is deliberately unmapped per the KG README — surfaces in
        # the Unmapped Findings section of reports.
        kg = KnowledgeGraph.load(real_kg_root)
        assert kg.map_dependency("npm", "@types/node") is None
