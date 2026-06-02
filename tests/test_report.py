"""Tests for report generation (U6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sf_scan.kg import KnowledgeGraph
from sf_scan.models import Dependency, Finding
from sf_scan.report import render


FIXTURES = Path(__file__).parent / "fixtures" / "kg" / "tiny"


@pytest.fixture
def kg() -> KnowledgeGraph:
    return KnowledgeGraph.load(FIXTURES)


@pytest.fixture
def express_finding() -> Finding:
    return Finding(
        cve_id="GHSA-test-express",
        package="express",
        ecosystem="npm",
        version="4.17.0",
        severity="HIGH",
        summary="Express vulnerable to open redirect.",
        fix_version="4.19.0",
        sources=("OSV", "GHSA"),
        dependency_ref=Dependency(
            ecosystem="npm",
            package="express",
            version="4.17.0",
            manifest_path="package.json",
        ),
        references=("https://github.com/advisories/express-redirect",),
    )


@pytest.fixture
def lodash_finding() -> Finding:
    return Finding(
        cve_id="GHSA-test-lodash",
        package="lodash",
        ecosystem="npm",
        version="4.17.20",
        severity="CRITICAL",
        summary="Prototype Pollution.",
        fix_version="4.17.21",
        sources=("OSV", "GHSA"),
        dependency_ref=Dependency(
            ecosystem="npm",
            package="lodash",
            version="4.17.20",
            manifest_path="package.json",
        ),
        references=("https://github.com/advisories/lodash-pp",),
    )


@pytest.fixture
def unmapped_finding() -> Finding:
    return Finding(
        cve_id="GHSA-test-axios",
        package="axios",
        ecosystem="npm",
        version="0.21.0",
        severity="MEDIUM",
        summary="SSRF via redirect.",
        fix_version="0.21.1",
        sources=("OSV",),
        dependency_ref=Dependency(
            ecosystem="npm",
            package="axios",
            version="0.21.0",
            manifest_path="package.json",
        ),
        references=(),
    )


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------


class TestJsonShape:
    def test_files_written_to_out_dir(
        self, tmp_path: Path, kg: KnowledgeGraph, lodash_finding: Finding
    ) -> None:
        paths = render([lodash_finding], kg, tmp_path)
        assert paths.json_path.exists()
        assert paths.md_path.exists()
        assert paths.json_path.name == "report.json"
        assert paths.md_path.name == "report.md"

    def test_json_summary_counts(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
        express_finding: Finding,
    ) -> None:
        render([lodash_finding, express_finding], kg, tmp_path)
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["summary"]["total_findings"] == 2
        assert data["summary"]["mapped_count"] == 2
        assert data["summary"]["unmapped_count"] == 0
        assert data["summary"]["by_severity"]["CRITICAL"] == 1
        assert data["summary"]["by_severity"]["HIGH"] == 1

    def test_json_action_list_sorted_by_severity(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
        express_finding: Finding,
    ) -> None:
        render([express_finding, lodash_finding], kg, tmp_path)
        data = json.loads((tmp_path / "report.json").read_text())
        action_list = data["summary"]["action_list"]
        # CRITICAL must come before HIGH
        assert action_list[0]["severity"] == "CRITICAL"
        assert action_list[1]["severity"] == "HIGH"

    def test_json_unmapped_section(
        self, tmp_path: Path, kg: KnowledgeGraph, unmapped_finding: Finding
    ) -> None:
        render([unmapped_finding], kg, tmp_path)
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["summary"]["unmapped_count"] == 1
        assert len(data["unmapped"]) == 1
        assert data["unmapped"][0]["package"] == "axios"

    def test_json_ontology_index_nested(
        self, tmp_path: Path, kg: KnowledgeGraph, lodash_finding: Finding
    ) -> None:
        render([lodash_finding], kg, tmp_path)
        data = json.loads((tmp_path / "report.json").read_text())
        index = data["ontology_index"]
        assert "PRD-T-001" in index
        # The feature path leads through F-T-001 → BP-T-001 → WO-T-001
        feature_entry = index["PRD-T-001"]["features"]["F-T-001"]
        bp_entry = feature_entry["blueprints"]["BP-T-001"]
        wo_entry = bp_entry["work_orders"]["WO-T-001"]
        assert lodash_finding.cve_id in wo_entry["findings"]

    def test_json_handles_zero_findings(
        self, tmp_path: Path, kg: KnowledgeGraph
    ) -> None:
        render([], kg, tmp_path)
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["summary"]["total_findings"] == 0
        assert data["findings"] == []
        assert data["ontology_index"] == {}

    def test_json_scan_errors_preserved(
        self, tmp_path: Path, kg: KnowledgeGraph
    ) -> None:
        render([], kg, tmp_path, scan_errors=["OSV batch failed for npm"])
        data = json.loads((tmp_path / "report.json").read_text())
        assert data["scan_errors"] == ["OSV batch failed for npm"]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


class TestMarkdownShape:
    def test_has_executive_summary(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
        express_finding: Finding,
    ) -> None:
        render([lodash_finding, express_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "## Executive Summary" in md
        assert "CRITICAL" in md
        assert "HIGH" in md

    def test_has_findings_by_prd_section(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
    ) -> None:
        render([lodash_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "## Findings by PRD Requirement" in md
        assert "PRD-T-001" in md
        assert "F-T-001" in md
        assert "BP-T-001" in md
        assert "WO-T-001" in md

    def test_unmapped_section_renders_when_present(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        unmapped_finding: Finding,
    ) -> None:
        render([unmapped_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "## Unmapped Findings" in md
        assert "axios" in md
        assert "alignment-debt" in md.lower() or "lens 4" in md.lower()

    def test_unmapped_section_omitted_when_all_mapped(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
    ) -> None:
        render([lodash_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "## Unmapped Findings" not in md

    def test_no_findings_renders_clean_summary(
        self, tmp_path: Path, kg: KnowledgeGraph
    ) -> None:
        render([], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "No vulnerabilities found" in md

    def test_link_to_kg_artifact(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
    ) -> None:
        # out_dir is tmp_path; kg fixture lives under tests/fixtures/kg/tiny/.
        # The rendered link should at least include the KG artifact's
        # repo-relative path tail.
        render([lodash_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "product-overview.md" in md
        assert "feature-001.md" in md

    def test_action_list_top_critical_named_first(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
        express_finding: Finding,
    ) -> None:
        render([express_finding, lodash_finding], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        # The action list's first numbered entry should be the CRITICAL
        # finding (lodash), not the HIGH (express).
        action_section_start = md.find("Risk-prioritized action list")
        assert action_section_start != -1
        first_line = md[action_section_start:].splitlines()[2]  # 1. **[...
        assert "lodash" in first_line

    def test_repo_label_and_sha_in_header(
        self,
        tmp_path: Path,
        kg: KnowledgeGraph,
        lodash_finding: Finding,
    ) -> None:
        render(
            [lodash_finding],
            kg,
            tmp_path,
            repo_label="8090-inc/software-factory-plugin",
            sha="a1b2c3d4e5f6",
        )
        md = (tmp_path / "report.md").read_text()
        assert "8090-inc/software-factory-plugin" in md
        assert "a1b2c3d4e5f6" in md

    def test_severity_emoji_or_no_findings_marker(
        self, tmp_path: Path, kg: KnowledgeGraph
    ) -> None:
        # We only assert the "clean scan" state has a clear marker — the
        # exact glyph (✅ or text) is a UI detail not pinned here.
        render([], kg, tmp_path)
        md = (tmp_path / "report.md").read_text()
        assert "No vulnerabilities found" in md
