"""SQLite cache for vulnerability lookups.

Cache key: ``(ecosystem, package, version, source)``. TTL: 24 hours. Empty
responses (no findings) are cached too — they're often a majority of lookups
in a typical scan, and re-querying them on every run is wasted work.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .models import Dependency

DEFAULT_CACHE_PATH = Path.home() / ".cache" / "sf-scan" / "vuln-cache.db"
TTL_SECONDS = 86400  # 24 hours


class VulnCache:
    """Lightweight SQLite-backed cache for OSV/GHSA lookup results."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_CACHE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(str(self.path))
            self._init_schema()
        except sqlite3.DatabaseError:
            # Corrupted cache — wipe and restart rather than failing the scan.
            self.path.unlink(missing_ok=True)
            self.conn = sqlite3.connect(str(self.path))
            self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vuln_lookup (
                ecosystem TEXT NOT NULL,
                package TEXT NOT NULL,
                version TEXT NOT NULL,
                source TEXT NOT NULL,
                payload TEXT NOT NULL,
                fetched_at INTEGER NOT NULL,
                PRIMARY KEY (ecosystem, package, version, source)
            )
            """
        )
        self.conn.commit()

    def get(self, dep: Dependency, source: str = "OSV") -> list[dict[str, Any]] | None:
        """Return cached vulns for ``dep`` from ``source``, or None if absent/expired."""
        version = dep.version or "*"
        row = self.conn.execute(
            (
                "SELECT payload, fetched_at FROM vuln_lookup "
                "WHERE ecosystem=? AND package=? AND version=? AND source=?"
            ),
            (dep.ecosystem, dep.package, version, source),
        ).fetchone()
        if row is None:
            return None
        payload, fetched_at = row
        if int(time.time()) - int(fetched_at) > TTL_SECONDS:
            return None
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, list) else None

    def put(
        self,
        dep: Dependency,
        vulns: list[dict[str, Any]],
        source: str = "OSV",
    ) -> None:
        """Persist ``vulns`` for ``dep`` from ``source``. Empty lists are cached too."""
        version = dep.version or "*"
        self.conn.execute(
            (
                "INSERT OR REPLACE INTO vuln_lookup "
                "(ecosystem, package, version, source, payload, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            ),
            (
                dep.ecosystem,
                dep.package,
                version,
                source,
                json.dumps(vulns),
                int(time.time()),
            ),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except sqlite3.Error:
            pass

    def __enter__(self) -> "VulnCache":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
