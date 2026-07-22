"""Tests for the Software Factory external-API GraphSource adapter.

The stub client serves recorded JSON fixtures shaped exactly like the
external API's response schemas (``{"items": [...]}`` list envelopes,
``{"data": {...}}`` single-resource envelopes, ``connected_context`` edges).
No network involved.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from sf_scan.kg import KnowledgeGraph
from sf_scan.sf_api import PAGE_SIZE, HttpSfApiClient, RestApiSource, SfApiError


FIXTURES = Path(__file__).parent / "fixtures" / "sf-api"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


class StubSfApiClient:
    """Routes API paths to recorded fixtures, tracking calls."""

    base_url = "https://factory.example.com"

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._routes = {
            "/requirements": _fixture("requirements.json"),
            "/blueprints": _fixture("blueprints.json"),
            "/work_orders": _fixture("work_orders.json"),
            "/work_orders/3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c": _fixture(
                "work_order_3f1c2a9e.json"
            ),
            "/work_orders/aaaa1111-0000-4000-8000-000000000000": _fixture(
                "work_order_aaaa1111.json"
            ),
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(path)
        if path not in self._routes:
            raise SfApiError(f"GET {path} failed: HTTP 404")
        return self._routes[path]


class TestRestApiSource:
    def test_normalizes_full_graph(self) -> None:
        kg = KnowledgeGraph.from_source(RestApiSource(StubSfApiClient()))

        assert kg.nodes["req-doc-overview-001"].artifact_type == "prd"
        feature = kg.nodes["req-doc-feat-001"]
        assert feature.artifact_type == "feature"
        assert feature.metadata["product"] == "req-doc-overview-001"

        feat_bp = kg.nodes["bp-doc-feat-001"]
        assert feat_bp.artifact_type == "blueprint-feature"
        assert feat_bp.metadata["feature"] == "req-doc-feat-001"
        custom_bp = kg.nodes["bp-doc-custom-001"]
        assert custom_bp.artifact_type == "blueprint-foundation"
        assert custom_bp.metadata["product"] == "req-doc-overview-001"

        wo = kg.nodes["3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"]
        assert wo.artifact_type == "work-order"
        assert wo.metadata["blueprint"] == "bp-doc-feat-001"
        assert wo.metadata["work_order_label"] == "WO-12"
        assert wo.path is None
        assert (
            wo.url
            == "https://factory.example.com/v2/external-api/work_orders/"
            "3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c"
        )

    def test_graph_validates_clean(self) -> None:
        kg = KnowledgeGraph.from_source(RestApiSource(StubSfApiClient()))
        assert [i for i in kg.validate() if i.severity == "error"] == []

    def test_enriched_dep_resolves_through_feature_chain(self) -> None:
        kg = KnowledgeGraph.from_source(RestApiSource(StubSfApiClient()))
        kg.add_dependencies("3f1c2a9e-6a51-4c1e-9b1a-0d5e8f7a2b4c", ["npm:zod"])
        path = kg.map_dependency("npm", "zod")
        assert path is not None and path.is_complete
        assert path.feature.id == "req-doc-feat-001"
        assert path.prd.id == "req-doc-overview-001"

    def test_foundation_chain_skips_feature_level(self) -> None:
        kg = KnowledgeGraph.from_source(RestApiSource(StubSfApiClient()))
        kg.add_dependencies("aaaa1111-0000-4000-8000-000000000000", ["npm:eslint"])
        path = kg.map_dependency("npm", "eslint")
        assert path is not None and path.is_complete
        assert path.feature is None
        assert path.blueprint.id == "bp-doc-custom-001"

    def test_first_page_error_propagates(self) -> None:
        client = StubSfApiClient()
        client._routes.pop("/requirements")
        with pytest.raises(SfApiError):
            list(RestApiSource(client).iter_nodes())

    def test_later_page_error_propagates(self) -> None:
        class LaterPageErrorClient:
            def get(
                self, path: str, params: dict[str, Any] | None = None
            ) -> dict[str, Any]:
                page = (params or {}).get("page", 1)
                if path == "/requirements" and page == 1:
                    return {
                        "items": [
                            {
                                "id": f"feature-{index}",
                                "document_type": "feature_requirements",
                            }
                            for index in range(PAGE_SIZE)
                        ]
                    }
                if path == "/requirements":
                    raise SfApiError("requirements page 2 failed")
                return {"items": []}

        with pytest.raises(SfApiError, match="page 2"):
            list(RestApiSource(LaterPageErrorClient()).iter_nodes())


# ---------------------------------------------------------------------------
# HTTP client (urllib) against a local stub server
# ---------------------------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        auth = self.headers.get("Authorization", "")
        if auth != "Bearer sofa-ext-test-key":
            self.send_response(401)
            self.end_headers()
            return
        if self.path.startswith("/v2/external-api/requirements"):
            body = json.dumps(_fixture("requirements.json")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def stub_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


class TestHttpSfApiClient:
    def test_sends_bearer_key_and_parses_json(self, stub_server: str) -> None:
        client = HttpSfApiClient(stub_server, "sofa-ext-test-key")
        payload = client.get("/requirements", params={"page": 1})
        assert payload["items"][0]["id"] == "req-doc-overview-001"

    def test_bad_key_raises_sf_api_error(self, stub_server: str) -> None:
        client = HttpSfApiClient(stub_server, "sofa-ext-wrong")
        with pytest.raises(SfApiError, match="HTTP 401"):
            client.get("/requirements")

    def test_unknown_path_raises(self, stub_server: str) -> None:
        client = HttpSfApiClient(stub_server, "sofa-ext-test-key")
        with pytest.raises(SfApiError, match="HTTP 404"):
            client.get("/nope")
