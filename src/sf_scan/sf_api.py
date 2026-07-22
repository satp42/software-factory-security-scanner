"""GraphSource adapter for the Software Factory external REST API.

Software Factory exposes a project-scoped REST surface at
``/v2/external-api/{work_orders,blueprints,requirements,artifacts,...}``,
authenticated with a ``sofa-ext-`` prefixed API key created in Project
Settings (sent as ``Authorization: Bearer <key>``; an organization can be
pinned with the ``X-Sofa-Active-Org-Id`` header). Responses are structured
JSON: lists as ``{"items": [...]}`` envelopes, single resources as
``{"data": {...}}``, with cross-entity edges in ``connected_context``
(``[{"resourceType": ..., "resourceId": ...}]``).

This — not the MCP server — is the scanner's integration surface: MCP
authenticates via short-lived OAuth tokens and returns formatted text
rather than JSON, both wrong for a headless CLI.

Schema mapping into the canonical node shapes:

- requirements document (product overview)  → ``prd``
- requirements document (feature)           → ``feature`` (product = overview doc)
- blueprint document, FEATURE class         → ``blueprint-feature``
- blueprint document, CUSTOM class          → ``blueprint-foundation``
- work order                                → ``work-order`` (blueprint edge
  from ``connected_context``; UUID id; ``work_order_number`` kept for the
  derivation join against ``.sw-factory`` state)

Real Work Orders carry no dependency declarations — attribution comes from
git manifest deltas (``derive.py``), joined on the Work Order UUID that both
this API and ``.sw-factory/*/context.md`` share.

The client follows the ``OsvClient`` pattern in ``vuln.py``: a Protocol so
tests inject a stub, and a urllib implementation so the project stays free
of runtime dependencies.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterator, Protocol

from .kg import KGNode


API_PREFIX = "/v2/external-api"
API_TIMEOUT = 30
PAGE_SIZE = 100
API_KEY_ENV = "SOFA_EXT_API_KEY"
ORG_ID_ENV = "SOFA_ORG_ID"


class SfApiError(Exception):
    """Raised when the external API is unreachable or returns an error."""


class SfApiClient(Protocol):
    """The three-method surface RestApiSource needs. Tests inject stubs."""

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET ``path`` (relative to the API prefix) and return parsed JSON."""
        ...


class HttpSfApiClient:
    """Real client. Uses urllib so we add no runtime dependencies."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        org_id: str | None = None,
        timeout: int = API_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{API_PREFIX}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        if self._org_id:
            headers["X-Sofa-Active-Org-Id"] = self._org_id
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SfApiError(f"GET {url} failed: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise SfApiError(f"GET {url} failed: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise SfApiError(f"GET {url} returned invalid JSON") from e


class RestApiSource:
    """Builds a Knowledge Graph from the Software Factory external API."""

    def __init__(self, client: SfApiClient, *, label: str = "Software Factory external API") -> None:
        self.client = client
        self._label = label

    def describe(self) -> str:
        return self._label

    def iter_nodes(self) -> Iterator[KGNode]:
        overview_id: str | None = None
        feature_docs: list[dict[str, Any]] = []

        # Requirements documents first: the overview doc anchors the chain.
        requirement_items = list(self._pages("/requirements"))
        for item in requirement_items:
            if _is_overview_doc(item) and overview_id is None:
                overview_id = str(item["id"])
                yield self._node(item, "prd")
            else:
                feature_docs.append(item)
        for item in feature_docs:
            metadata = {"product": overview_id} if overview_id else {}
            yield self._node(item, "feature", metadata)

        for item in self._pages("/blueprints"):
            if str(item.get("blueprint_class", "")).upper() == "FEATURE":
                feature_ref = _first_context_id(item, "requirements_document")
                metadata = {"feature": feature_ref} if feature_ref else {}
                yield self._node(item, "blueprint-feature", metadata)
            else:
                metadata = {"product": overview_id} if overview_id else {}
                yield self._node(item, "blueprint-foundation", metadata)

        for item in self._pages("/work_orders"):
            detail = self.client.get(f"/work_orders/{item['id']}")
            data = detail.get("data", detail)
            metadata: dict[str, Any] = {
                "work_order_number": data.get("work_order_number"),
                "work_order_label": f"WO-{data.get('work_order_number')}",
                "status": data.get("status"),
            }
            blueprint_ref = _first_context_id(data, "blueprint")
            if blueprint_ref:
                metadata["blueprint"] = blueprint_ref
            yield self._node(data, "work-order", metadata)

    def _pages(self, path: str) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self.client.get(
                path, params={"page": page, "page_size": PAGE_SIZE}
            )
            items = payload.get("items", [])
            yield from items
            if len(items) < PAGE_SIZE:
                return
            page += 1

    def _node(
        self,
        data: dict[str, Any],
        artifact_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> KGNode:
        resource_id = str(data["id"])
        object_type = str(data.get("object", artifact_type))
        base_url = getattr(self.client, "base_url", "").rstrip("/")
        # The API resource URL — dereferenceable with the same key. The web
        # app's frontend routes aren't part of the external API contract, so
        # we don't guess them.
        url = (
            f"{base_url}{API_PREFIX}/{_collection_for(object_type)}/{resource_id}"
            if base_url
            else None
        )
        return KGNode(
            id=resource_id,
            title=str(data.get("title", resource_id)),
            artifact_type=artifact_type,
            path=None,
            url=url,
            metadata=metadata or {},
        )


def _is_overview_doc(item: dict[str, Any]) -> bool:
    doc_type = str(
        item.get("document_type") or item.get("type") or ""
    ).lower()
    return "overview" in doc_type


def _first_context_id(data: dict[str, Any], resource_type: str) -> str | None:
    for edge in data.get("connected_context") or []:
        if str(edge.get("resourceType", "")).lower() == resource_type:
            resource_id = edge.get("resourceId")
            if resource_id:
                return str(resource_id)
    return None


def _collection_for(object_type: str) -> str:
    return {
        "work_order": "work_orders",
        "blueprint": "blueprints",
        "requirements_document": "requirements",
    }.get(object_type, object_type + "s")
