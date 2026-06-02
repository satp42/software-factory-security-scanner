"""Vulnerability database query client.

Primary source: OSV.dev's batch query API. OSV aggregates the GitHub Security
Advisory Database, RustSec, PyPI Safety DB, and several others, so a single
OSV query covers most of what a multi-source cross-check would. The
:class:`HttpOsvClient` is injectable so tests can substitute a fixture-backed
client without network access.

GitHub Advisory DB direct cross-check is deferred to a future iteration — OSV
already includes GHSA findings, so the cross-check would be confidence-only,
not coverage-additional.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Iterable, Iterator, Protocol

from .cache import VulnCache
from .models import Dependency, Finding


OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{vuln_id}"
OSV_TIMEOUT = 30

# sf-scan's ecosystem names → OSV.dev ecosystem strings. They mostly match but
# this indirection lets us extend coverage without touching the rest of the
# code.
ECOSYSTEM_TO_OSV = {
    "npm": "npm",
    "PyPI": "PyPI",
    "Go": "Go",
    "RubyGems": "RubyGems",
}

# Max items in a single OSV /v1/querybatch request. OSV's documented limit is
# 1000; we batch smaller for kinder failure modes on flaky networks.
OSV_BATCH_SIZE = 500


class VulnQueryError(Exception):
    """Raised when a vulnerability database lookup fails irrecoverably."""


# ---------------------------------------------------------------------------
# Client abstraction
# ---------------------------------------------------------------------------


class OsvClient(Protocol):
    """Minimal client interface for OSV.dev — swapped out in tests."""

    def query_batch(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        ...

    def get_vuln(self, vuln_id: str) -> dict[str, Any]:
        ...


class HttpOsvClient:
    """Real OSV.dev client. Uses urllib so we add no runtime dependencies."""

    def query_batch(self, queries: list[dict[str, Any]]) -> dict[str, Any]:
        body = json.dumps({"queries": queries}).encode("utf-8")
        req = urllib.request.Request(
            OSV_BATCH_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=OSV_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise VulnQueryError(f"OSV batch HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise VulnQueryError(f"OSV batch unreachable: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise VulnQueryError(f"OSV batch returned non-JSON: {e}") from e

    def get_vuln(self, vuln_id: str) -> dict[str, Any]:
        url = OSV_VULN_URL.format(vuln_id=vuln_id)
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=OSV_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise VulnQueryError(f"OSV vuln HTTP {e.code} for {vuln_id}") from e
        except urllib.error.URLError as e:
            raise VulnQueryError(f"OSV vuln unreachable: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise VulnQueryError(f"OSV vuln returned non-JSON: {e}") from e


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def query(
    deps: Iterable[Dependency],
    *,
    use_cache: bool = True,
    cache: VulnCache | None = None,
    client: OsvClient | None = None,
) -> list[Finding]:
    """Look up vulnerabilities for ``deps`` and return merged findings.

    Cache and client are injectable so tests run without network or shared
    state. Cache lifecycle is managed here when callers don't pass one in.
    """
    dep_list = list(deps)
    if not dep_list:
        return []

    if client is None:
        client = HttpOsvClient()

    cache_owned = False
    if use_cache and cache is None:
        cache = VulnCache()
        cache_owned = True

    findings: list[Finding] = []
    try:
        for batch in _batched(dep_list, OSV_BATCH_SIZE):
            uncached: list[Dependency] = []
            for dep in batch:
                if cache is not None:
                    cached_vulns = cache.get(dep)
                    if cached_vulns is not None:
                        findings.extend(_vulns_to_findings(cached_vulns, dep))
                        continue
                uncached.append(dep)

            if not uncached:
                continue

            try:
                osv_results = _query_osv_batch(uncached, client)
            except VulnQueryError:
                # The whole batch failed. Log via stderr indirection later;
                # for now, leave these deps unresolved so the scan continues.
                continue

            for dep in uncached:
                vulns = osv_results.get(_dep_key(dep), [])
                if cache is not None:
                    cache.put(dep, vulns)
                findings.extend(_vulns_to_findings(vulns, dep))

        return findings
    finally:
        if cache_owned and cache is not None:
            cache.close()


# ---------------------------------------------------------------------------
# OSV batch query implementation
# ---------------------------------------------------------------------------


def _query_osv_batch(
    deps: list[Dependency], client: OsvClient
) -> dict[str, list[dict[str, Any]]]:
    """Submit a batch query and resolve each finding's full vuln record."""
    queries: list[dict[str, Any]] = []
    queryable_deps: list[Dependency] = []
    for dep in deps:
        osv_ecosystem = ECOSYSTEM_TO_OSV.get(dep.ecosystem)
        if osv_ecosystem is None:
            # Unsupported ecosystem — record an empty result for this dep so
            # the caller knows we considered it.
            continue
        q: dict[str, Any] = {
            "package": {"name": dep.package, "ecosystem": osv_ecosystem}
        }
        if dep.version:
            q["version"] = dep.version
        queries.append(q)
        queryable_deps.append(dep)

    if not queries:
        return {_dep_key(d): [] for d in deps}

    response = client.query_batch(queries)
    results = response.get("results", [])

    out: dict[str, list[dict[str, Any]]] = {_dep_key(d): [] for d in deps}

    for dep, result in zip(queryable_deps, results):
        key = _dep_key(dep)
        result = result if isinstance(result, dict) else {}
        vuln_ids = [
            v["id"]
            for v in (result.get("vulns") or [])
            if isinstance(v, dict) and "id" in v
        ]
        if not vuln_ids:
            out[key] = []
            continue

        full_vulns: list[dict[str, Any]] = []
        for vid in vuln_ids:
            try:
                full = client.get_vuln(vid)
                full_vulns.append(full)
            except VulnQueryError:
                # Skip a single bad vuln; don't fail the batch.
                continue
        out[key] = full_vulns

    return out


# ---------------------------------------------------------------------------
# Severity + fix-version extraction
# ---------------------------------------------------------------------------


_SEVERITY_SYNONYMS = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "MODERATE": "MEDIUM",  # GitHub uses MODERATE; we normalize to MEDIUM
    "LOW": "LOW",
}


def _extract_severity(vuln: dict[str, Any]) -> str:
    """Best-effort severity extraction across OSV / GHSA / CVSS shapes."""
    # 1. GitHub-style top-level database_specific.severity
    db_specific = vuln.get("database_specific")
    if isinstance(db_specific, dict):
        sev = db_specific.get("severity")
        if isinstance(sev, str) and sev.upper() in _SEVERITY_SYNONYMS:
            return _SEVERITY_SYNONYMS[sev.upper()]

    # 2. severity[].score with a numeric CVSS score
    severity_array = vuln.get("severity")
    if isinstance(severity_array, list):
        for item in severity_array:
            if not isinstance(item, dict):
                continue
            numeric = _parse_cvss_numeric(item.get("score"))
            if numeric is not None:
                return _score_to_severity(numeric)

    # 3. Per-affected database_specific.severity
    affected = vuln.get("affected")
    if isinstance(affected, list):
        for a in affected:
            if not isinstance(a, dict):
                continue
            ad = a.get("database_specific")
            if isinstance(ad, dict):
                sev = ad.get("severity")
                if isinstance(sev, str) and sev.upper() in _SEVERITY_SYNONYMS:
                    return _SEVERITY_SYNONYMS[sev.upper()]

    return "UNKNOWN"


def _parse_cvss_numeric(score: Any) -> float | None:
    """Try to extract a numeric CVSS score from a string field.

    OSV stores CVSS as a vector string like ``CVSS:3.1/AV:N/...`` — those
    don't carry a numeric base score directly. We accept (and convert) pure
    numeric strings here; vector parsing is out of scope for v1.
    """
    if score is None or isinstance(score, bool):
        return None
    if isinstance(score, (int, float)):
        return float(score)
    if isinstance(score, str):
        try:
            return float(score)
        except ValueError:
            return None
    return None


def _score_to_severity(score: float) -> str:
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "UNKNOWN"


def _extract_fix_version(vuln: dict[str, Any], dep: Dependency) -> str | None:
    """Return the first ``fixed`` version listed for ``dep.package``, if any."""
    affected = vuln.get("affected")
    if not isinstance(affected, list):
        return None
    for a in affected:
        if not isinstance(a, dict):
            continue
        pkg = a.get("package") or {}
        if pkg.get("name") != dep.package:
            continue
        ranges = a.get("ranges") or []
        for r in ranges:
            if not isinstance(r, dict):
                continue
            for event in r.get("events") or []:
                if isinstance(event, dict) and "fixed" in event:
                    return str(event["fixed"])
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vulns_to_findings(
    vulns: list[dict[str, Any]], dep: Dependency
) -> list[Finding]:
    out: list[Finding] = []
    for v in vulns:
        if not isinstance(v, dict):
            continue
        cve_id = v.get("id") or "UNKNOWN"
        summary = v.get("summary") or v.get("details") or ""
        if isinstance(summary, str) and len(summary) > 280:
            summary = summary[:277] + "..."
        severity = _extract_severity(v)
        fix_version = _extract_fix_version(v, dep)
        references = tuple(
            ref["url"]
            for ref in (v.get("references") or [])
            if isinstance(ref, dict) and "url" in ref
        )
        # GHSA-prefixed IDs come via OSV but originate at GitHub Advisory DB.
        sources = ("OSV", "GHSA") if str(cve_id).startswith("GHSA") else ("OSV",)
        out.append(
            Finding(
                cve_id=str(cve_id),
                package=dep.package,
                ecosystem=dep.ecosystem,
                version=dep.version,
                severity=severity,
                summary=str(summary),
                fix_version=fix_version,
                sources=sources,
                dependency_ref=dep,
                references=references,
            )
        )
    return out


def _dep_key(dep: Dependency) -> str:
    return f"{dep.ecosystem}::{dep.package}::{dep.version or '*'}"


def _batched(items: list[Dependency], n: int) -> Iterator[list[Dependency]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]
