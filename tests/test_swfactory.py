"""Tests for the ``.sw-factory`` GraphSource adapter."""

from __future__ import annotations

from pathlib import Path

from sf_scan.kg import KnowledgeGraph
from sf_scan.swfactory import SwFactorySource, parse_context_md


WO_12_CONTEXT = """\
# Work Order Entity Index: WO-12

**Initialized At (UTC):** 2026-07-01T10:00:00Z
**Current Status:** in_review

## Work Order

- WO-12: Manifest validation pipeline (`3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c`)

## Requirements

- Plugin Platform PRD (`req-doc-001`)

## Blueprints

- Validation Architecture (`bp-doc-001`)

## Referenced Blueprints

Blueprints reached through `@…` mentions and links while reading linked blueprints.

- Build Pipeline Conventions (`bp-doc-002`)

## Delivery

- Branch: wo-12-validation
- Pull Request URL: https://github.com/org/repo/pull/7
"""

UNFILLED_TEMPLATE = """\
# Work Order Entity Index: {{WORK_ORDER_LABEL}}

**Initialized At (UTC):** {{INITIALIZED_AT}}
**Current Status:**

## Work Order

- {{WORK_ORDER_LABEL}}: {{WORK_ORDER_TITLE}} (`{{WORK_ORDER_ID}}`)

## Requirements

- {{REQUIREMENTS_DOCUMENT_TITLE}} (`{{REQUIREMENTS_DOCUMENT_ID}}`)

## Delivery

- Branch:
- Pull Request URL:
"""

HARNESS_CONTEXT = """\
# Work Order Entity Index: WO-3

## Work Order

- WO-3: Quality toolchain

## Requirements

- Plugin Platform PRD (`req-doc-001`)

## Blueprints

- Toolchain Blueprint (`bp-doc-009`)

## Delivery

- Branch: wo-3-toolchain
- Pull Request URL:
"""


def _write_wo(repo: Path, root: str, label: str, content: str) -> None:
    wo_dir = repo / root / label
    wo_dir.mkdir(parents=True, exist_ok=True)
    (wo_dir / "context.md").write_text(content)


# ---------------------------------------------------------------------------
# context.md parsing
# ---------------------------------------------------------------------------


class TestParseContextMd:
    def test_parses_full_entity_index(self) -> None:
        ctx = parse_context_md(
            WO_12_CONTEXT, source_path=".sw-factory/WO-12/context.md", dir_label="WO-12"
        )
        assert ctx is not None
        assert ctx.label == "WO-12"
        assert ctx.node_id == "3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"
        assert ctx.title == "Manifest validation pipeline"
        assert ctx.requirements == [("Plugin Platform PRD", "req-doc-001")]
        assert ctx.blueprints == [
            ("Validation Architecture", "bp-doc-001"),
            ("Build Pipeline Conventions", "bp-doc-002"),
        ]
        assert ctx.branch == "wo-12-validation"
        assert ctx.pr_url == "https://github.com/org/repo/pull/7"

    def test_unfilled_template_yields_no_entities_or_delivery(self) -> None:
        ctx = parse_context_md(
            UNFILLED_TEMPLATE,
            source_path=".sw-factory/WO-1/context.md",
            dir_label="WO-1",
        )
        assert ctx is not None
        assert ctx.node_id == "WO-1"  # placeholder id falls back to dir label
        assert ctx.requirements == []
        assert ctx.branch is None and ctx.pr_url is None

    def test_wo_line_without_uuid_falls_back_to_label(self) -> None:
        ctx = parse_context_md(
            HARNESS_CONTEXT,
            source_path="scratch/wo-execution/WO-3/context.md",
            dir_label="WO-3",
        )
        assert ctx is not None
        assert ctx.node_id == "WO-3"
        assert ctx.title == "Quality toolchain"
        assert ctx.branch == "wo-3-toolchain"
        assert ctx.pr_url is None

    def test_document_without_wo_section_returns_none(self) -> None:
        assert (
            parse_context_md("# Notes\n\nfree text\n", source_path="x", dir_label="WO-1")
            is None
        )


# ---------------------------------------------------------------------------
# SwFactorySource
# ---------------------------------------------------------------------------


class TestSwFactorySource:
    def test_builds_resolvable_graph(self, tmp_path: Path) -> None:
        _write_wo(tmp_path, ".sw-factory", "WO-12", WO_12_CONTEXT)
        source = SwFactorySource(tmp_path)
        kg = KnowledgeGraph.from_source(source)

        wo = kg.nodes["3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"]
        assert wo.artifact_type == "work-order"
        assert wo.url == "https://github.com/org/repo/pull/7"
        assert kg.nodes["bp-doc-001"].artifact_type == "blueprint-foundation"
        assert kg.nodes["req-doc-001"].artifact_type == "prd"

        # Enrich with a derived dep and confirm the chain resolves end-to-end
        # as a foundation path (WO → Blueprint → Requirements doc).
        kg.add_dependencies(wo.id, ["npm:lodash"])
        path = kg.map_dependency("npm", "lodash")
        assert path is not None and path.is_complete
        assert path.blueprint.id == "bp-doc-001"
        assert path.prd.id == "req-doc-001"
        assert path.feature is None

    def test_deliveries_expose_branch_and_pr(self, tmp_path: Path) -> None:
        _write_wo(tmp_path, ".sw-factory", "WO-12", WO_12_CONTEXT)
        deliveries = SwFactorySource(tmp_path).deliveries()
        assert len(deliveries) == 1
        assert deliveries[0].wo_id == "3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"
        assert deliveries[0].branch == "wo-12-validation"
        assert deliveries[0].pr_url == "https://github.com/org/repo/pull/7"

    def test_harness_scratch_root_is_fallback(self, tmp_path: Path) -> None:
        _write_wo(tmp_path, "scratch/wo-execution", "WO-3", HARNESS_CONTEXT)
        kg = KnowledgeGraph.from_source(SwFactorySource(tmp_path))
        assert kg.nodes["WO-3"].artifact_type == "work-order"

    def test_fallback_work_order_ids_are_isolated_by_repository(
        self, tmp_path: Path
    ) -> None:
        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        _write_wo(repo_a, "scratch/wo-execution", "WO-3", HARNESS_CONTEXT)
        _write_wo(
            repo_b,
            "scratch/wo-execution",
            "WO-3",
            HARNESS_CONTEXT.replace("req-doc-001", "req-doc-002")
            .replace("bp-doc-009", "bp-doc-010")
            .replace("wo-3-toolchain", "wo-3-runtime"),
        )

        source_a = SwFactorySource(repo_a, source_id="org/repo-a")
        source_b = SwFactorySource(repo_b, source_id="org/repo-b")
        delivery_a = source_a.deliveries()[0]
        delivery_b = source_b.deliveries()[0]

        assert delivery_a.wo_id != delivery_b.wo_id

        kg = KnowledgeGraph.from_source(source_a)
        kg.extend_from_source(source_b)
        kg.add_dependencies(delivery_a.wo_id, ["npm:left-pad"])
        kg.add_dependencies(delivery_b.wo_id, ["npm:right-pad"])

        left_path = kg.map_dependency("npm", "left-pad")
        right_path = kg.map_dependency("npm", "right-pad")
        assert left_path is not None and left_path.blueprint.id == "bp-doc-009"
        assert right_path is not None and right_path.blueprint.id == "bp-doc-010"

    def test_repo_without_state_yields_nothing(self, tmp_path: Path) -> None:
        source = SwFactorySource(tmp_path)
        assert list(source.iter_nodes()) == []
        assert source.deliveries() == []

    def test_shared_entities_deduplicated_across_wos(self, tmp_path: Path) -> None:
        _write_wo(tmp_path, ".sw-factory", "WO-12", WO_12_CONTEXT)
        second = WO_12_CONTEXT.replace("WO-12", "WO-13").replace(
            "3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c",
            "aaaa1111-0000-4000-8000-000000000000",
        )
        _write_wo(tmp_path, ".sw-factory", "WO-13", second)
        nodes = list(SwFactorySource(tmp_path).iter_nodes())
        assert len([n for n in nodes if n.id == "req-doc-001"]) == 1
        assert len([n for n in nodes if n.artifact_type == "work-order"]) == 2
