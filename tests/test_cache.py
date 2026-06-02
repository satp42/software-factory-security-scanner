"""Tests for the SQLite vulnerability cache."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from sf_scan.cache import TTL_SECONDS, VulnCache
from sf_scan.models import Dependency


@pytest.fixture
def cache(tmp_path: Path) -> VulnCache:
    return VulnCache(tmp_path / "cache.db")


@pytest.fixture
def dep() -> Dependency:
    return Dependency(
        ecosystem="npm",
        package="lodash",
        version="4.17.20",
        manifest_path="package.json",
    )


class TestRoundTrip:
    def test_get_returns_none_when_missing(
        self, cache: VulnCache, dep: Dependency
    ) -> None:
        assert cache.get(dep) is None

    def test_put_then_get_returns_payload(
        self, cache: VulnCache, dep: Dependency
    ) -> None:
        vulns = [{"id": "GHSA-xxxx", "summary": "test"}]
        cache.put(dep, vulns)
        result = cache.get(dep)
        assert result == vulns

    def test_empty_payload_caches_a_negative_result(
        self, cache: VulnCache, dep: Dependency
    ) -> None:
        cache.put(dep, [])
        # The contract is "empty list cached" — get returns [] not None.
        result = cache.get(dep)
        assert result == []

    def test_distinct_versions_are_separate_cache_entries(
        self, cache: VulnCache, dep: Dependency
    ) -> None:
        other = Dependency(
            ecosystem=dep.ecosystem,
            package=dep.package,
            version="4.17.21",
            manifest_path=dep.manifest_path,
        )
        cache.put(dep, [{"id": "A"}])
        cache.put(other, [{"id": "B"}])
        assert cache.get(dep) == [{"id": "A"}]
        assert cache.get(other) == [{"id": "B"}]

    def test_no_version_falls_back_to_star_key(
        self, cache: VulnCache
    ) -> None:
        dep = Dependency(
            ecosystem="PyPI",
            package="pyyaml",
            version=None,
            manifest_path="requirements.txt",
        )
        cache.put(dep, [{"id": "Z"}])
        assert cache.get(dep) == [{"id": "Z"}]


class TestTTL:
    def test_expired_entry_returns_none(
        self, cache: VulnCache, dep: Dependency
    ) -> None:
        # Insert with a fetched_at that's older than the TTL.
        cache.conn.execute(
            (
                "INSERT INTO vuln_lookup "
                "(ecosystem, package, version, source, payload, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (
                dep.ecosystem,
                dep.package,
                dep.version,
                "OSV",
                json.dumps([{"id": "OLD"}]),
                int(time.time()) - TTL_SECONDS - 60,
            ),
        )
        cache.conn.commit()
        assert cache.get(dep) is None


class TestRecoveryFromCorruption:
    def test_corrupted_database_resets_silently(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        # Write garbage where the SQLite file would live.
        path.write_bytes(b"not a sqlite database at all")
        cache = VulnCache(path)
        # Should not raise; the cache should function normally after reset.
        dep = Dependency(
            ecosystem="npm",
            package="x",
            version="1.0",
            manifest_path="package.json",
        )
        cache.put(dep, [])
        assert cache.get(dep) == []


class TestContextManager:
    def test_close_works_as_context_manager(self, tmp_path: Path) -> None:
        with VulnCache(tmp_path / "cm.db") as c:
            dep = Dependency(
                ecosystem="npm",
                package="x",
                version="1.0",
                manifest_path="package.json",
            )
            c.put(dep, [{"id": "X"}])
            assert c.get(dep) == [{"id": "X"}]
        # No assertion on close — just ensure no exception escapes.
