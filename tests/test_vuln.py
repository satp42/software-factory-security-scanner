"""Tests for the vulnerability query client (U3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from sf_scan.cache import VulnCache
from sf_scan.models import Dependency, Finding
from sf_scan.vuln import (
    HttpOsvClient,
    VulnQueryError,
    _extract_fix_version,
    _extract_severity,
    _score_to_severity,
    _vulns_to_findings,
    query,
)


FIXTURES = Path(__file__).parent / "fixtures" / "osv-responses"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


class StubOsvClient:
    """Test double that serves committed fixture responses."""

    def __init__(
        self,
        batch_response: dict[str, Any],
        vulns: dict[str, dict[str, Any]],
        *,
        fail_on_vuln: set[str] | None = None,
        fail_batch: bool = False,
    ) -> None:
        self.batch_response = batch_response
        self.vulns = vulns
        self.batch_calls = 0
        self.vuln_calls: list[str] = []
        self.fail_on_vuln = fail_on_vuln or set()
        self.fail_batch = fail_batch

    def query_batch(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        self.batch_calls += 1
        if self.fail_batch:
            raise VulnQueryError("batch failed (stub)")
        return self.batch_response

    def get_vuln(self, vuln_id: str) -> dict[str, Any]:
        self.vuln_calls.append(vuln_id)
        if vuln_id in self.fail_on_vuln:
            raise VulnQueryError(f"vuln {vuln_id} failed (stub)")
        return self.vulns[vuln_id]


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def deps() -> list[Dependency]:
    return [
        Dependency(
            ecosystem="npm",
            package="lodash",
            version="4.17.20",
            manifest_path="package.json",
        ),
        Dependency(
            ecosystem="PyPI",
            package="pyyaml",
            version="5.3",
            manifest_path="requirements.txt",
        ),
        Dependency(
            ecosystem="npm",
            package="clean-pkg",
            version="1.0.0",
            manifest_path="package.json",
        ),
        Dependency(
            ecosystem="npm",
            package="express",
            version="4.18.0",
            manifest_path="package.json",
        ),
    ]


@pytest.fixture
def stub(deps: list[Dependency]) -> StubOsvClient:
    return StubOsvClient(
        batch_response=_load_fixture("batch-known-cves.json"),
        vulns={
            "GHSA-jf85-cpcp-j695": _load_fixture("vuln-lodash.json"),
            "GHSA-29mw-wpgm-hmr9": _load_fixture("vuln-pyyaml.json"),
            "GHSA-rrqm-p222-3p2q": _load_fixture("vuln-express.json"),
        },
    )


@pytest.fixture
def cache(tmp_path: Path) -> VulnCache:
    return VulnCache(tmp_path / "cache.db")


# ---------------------------------------------------------------------------
# Query orchestration
# ---------------------------------------------------------------------------


class TestQuery:
    def test_returns_findings_for_known_cves(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        findings = query(deps, client=stub, cache=cache)
        cve_ids = {f.cve_id for f in findings}
        assert "GHSA-jf85-cpcp-j695" in cve_ids  # lodash
        assert "GHSA-29mw-wpgm-hmr9" in cve_ids  # pyyaml
        assert "GHSA-rrqm-p222-3p2q" in cve_ids  # express

    def test_clean_package_yields_no_finding(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        findings = query(deps, client=stub, cache=cache)
        for f in findings:
            assert f.package != "clean-pkg"

    def test_empty_dependency_list_returns_empty(
        self, stub: StubOsvClient, cache: VulnCache
    ) -> None:
        assert query([], client=stub, cache=cache) == []
        assert stub.batch_calls == 0

    def test_cache_hit_skips_http(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        # Prime: first call hits the stub.
        query(deps, client=stub, cache=cache)
        first = stub.batch_calls
        # Second call should be served entirely from cache.
        query(deps, client=stub, cache=cache)
        assert stub.batch_calls == first  # no new batch calls

    def test_negative_results_are_cached(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        query(deps, client=stub, cache=cache)
        clean = next(d for d in deps if d.package == "clean-pkg")
        # The empty list is cached, not None — second call hits cache.
        assert cache.get(clean) == []

    def test_batch_failure_does_not_crash_scan(
        self, deps: list[Dependency], cache: VulnCache
    ) -> None:
        failing_stub = StubOsvClient(
            batch_response={},
            vulns={},
            fail_batch=True,
        )
        findings = query(deps, client=failing_stub, cache=cache)
        # No findings, no crash — scan continues.
        assert findings == []

    def test_per_vuln_failure_is_isolated(
        self,
        deps: list[Dependency],
        cache: VulnCache,
    ) -> None:
        partial_stub = StubOsvClient(
            batch_response=_load_fixture("batch-known-cves.json"),
            vulns={
                "GHSA-jf85-cpcp-j695": _load_fixture("vuln-lodash.json"),
                "GHSA-29mw-wpgm-hmr9": _load_fixture("vuln-pyyaml.json"),
                "GHSA-rrqm-p222-3p2q": _load_fixture("vuln-express.json"),
            },
            fail_on_vuln={"GHSA-29mw-wpgm-hmr9"},
        )
        findings = query(deps, client=partial_stub, cache=cache)
        cves = {f.cve_id for f in findings}
        # pyyaml's CVE was skipped; the others still made it through.
        assert "GHSA-29mw-wpgm-hmr9" not in cves
        assert "GHSA-jf85-cpcp-j695" in cves
        assert "GHSA-rrqm-p222-3p2q" in cves

    def test_findings_carry_dependency_ref(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        findings = query(deps, client=stub, cache=cache)
        for f in findings:
            assert f.dependency_ref is not None
            assert f.dependency_ref.package == f.package

    def test_findings_include_advisory_url(
        self, deps: list[Dependency], stub: StubOsvClient, cache: VulnCache
    ) -> None:
        findings = query(deps, client=stub, cache=cache)
        lodash_finding = next(
            f for f in findings if f.cve_id == "GHSA-jf85-cpcp-j695"
        )
        assert any("advisories" in ref for ref in lodash_finding.references)


# ---------------------------------------------------------------------------
# Severity normalization
# ---------------------------------------------------------------------------


class TestSeverityExtraction:
    def test_database_specific_severity_wins(self) -> None:
        vuln = {"database_specific": {"severity": "CRITICAL"}}
        assert _extract_severity(vuln) == "CRITICAL"

    def test_moderate_normalizes_to_medium(self) -> None:
        vuln = {"database_specific": {"severity": "MODERATE"}}
        assert _extract_severity(vuln) == "MEDIUM"

    def test_per_affected_severity_used_when_top_level_absent(self) -> None:
        vuln = {
            "affected": [
                {"database_specific": {"severity": "HIGH"}}
            ]
        }
        assert _extract_severity(vuln) == "HIGH"

    def test_unknown_severity_returns_unknown(self) -> None:
        assert _extract_severity({}) == "UNKNOWN"

    def test_numeric_score_used_when_present(self) -> None:
        vuln = {"severity": [{"type": "CVSS_V3", "score": "9.5"}]}
        assert _extract_severity(vuln) == "CRITICAL"

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (9.5, "CRITICAL"),
            (9.0, "CRITICAL"),
            (8.0, "HIGH"),
            (7.0, "HIGH"),
            (5.0, "MEDIUM"),
            (4.0, "MEDIUM"),
            (3.0, "LOW"),
            (0.5, "LOW"),
            (0.0, "UNKNOWN"),
        ],
    )
    def test_score_to_severity_buckets(
        self, score: float, expected: str
    ) -> None:
        assert _score_to_severity(score) == expected


class TestFixVersion:
    def test_extracts_fixed_event(self) -> None:
        vuln = _load_fixture("vuln-lodash.json")
        dep = Dependency(
            ecosystem="npm",
            package="lodash",
            version="4.17.20",
            manifest_path="package.json",
        )
        assert _extract_fix_version(vuln, dep) == "4.17.12"

    def test_returns_none_when_no_fixed_event(self) -> None:
        vuln = {
            "affected": [
                {
                    "package": {"ecosystem": "npm", "name": "x"},
                    "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}],
                }
            ]
        }
        dep = Dependency(
            ecosystem="npm",
            package="x",
            version="1.0",
            manifest_path="package.json",
        )
        assert _extract_fix_version(vuln, dep) is None

    def test_returns_none_when_package_does_not_match(self) -> None:
        vuln = _load_fixture("vuln-lodash.json")
        dep = Dependency(
            ecosystem="npm",
            package="not-lodash",
            version="1.0",
            manifest_path="package.json",
        )
        assert _extract_fix_version(vuln, dep) is None


class TestVulnsToFindings:
    def test_sources_marked_ghsa_when_id_prefixed(self) -> None:
        dep = Dependency(
            ecosystem="npm",
            package="lodash",
            version="4.17.20",
            manifest_path="package.json",
        )
        findings = _vulns_to_findings([_load_fixture("vuln-lodash.json")], dep)
        assert findings[0].sources == ("OSV", "GHSA")

    def test_truncates_long_summary(self) -> None:
        dep = Dependency(
            ecosystem="npm",
            package="x",
            version="1.0",
            manifest_path="package.json",
        )
        vuln = {"id": "X", "summary": "y" * 500}
        findings = _vulns_to_findings([vuln], dep)
        assert len(findings[0].summary) <= 280


# ---------------------------------------------------------------------------
# Live test — opt-in
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("SF_SCAN_NETWORK_TESTS") != "1",
    reason="Network test; opt-in via SF_SCAN_NETWORK_TESTS=1",
)
class TestLiveOsv:
    def test_lodash_has_findings(self, cache: VulnCache) -> None:
        dep = Dependency(
            ecosystem="npm",
            package="lodash",
            version="4.17.20",
            manifest_path="package.json",
        )
        findings = query([dep], client=HttpOsvClient(), cache=cache)
        assert findings, "lodash@4.17.20 should have at least one CVE"
