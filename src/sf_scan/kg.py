"""Software Factory Knowledge Graph ontology resolver and its source seam.

The resolver (:class:`KnowledgeGraph`) is source-agnostic: it indexes
normalized :class:`KGNode` values produced by a :class:`GraphSource` adapter
(local Markdown directory here; ``.sw-factory`` reader in ``swfactory.py``;
Software Factory external REST API in ``sf_api.py``).

The local-directory source reads a directory tree of Markdown files. Each
file carries a YAML frontmatter block declaring its identifier and parent
references:

- Product Overview (``type: product-overview``) — top of the chain.
- Feature Requirements (``type: feature-requirements``) — point at a PRD via ``product``.
- Blueprints (``type: blueprint``) — Feature blueprints point at a Feature via ``feature``.
- Work Orders (``type: work-order``) — point at a Blueprint via ``blueprint`` AND list
  the dependencies they introduced via ``dependencies-introduced``.

The resolver answers "which PRD requirement is at risk when CVE-X affects
package P?" by indexing each Work Order's ``dependencies-introduced`` field,
then walking parent references upward.

We roll a minimal frontmatter parser here (rather than adding ``PyYAML`` or
``python-frontmatter`` as a runtime dependency) because the YAML we consume is
a restricted subset: top-level string keys, scalar or list-of-scalar values,
no nested mappings or anchors. ~50 lines covers it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Protocol


# ---------------------------------------------------------------------------
# Frontmatter parsing (restricted YAML subset)
# ---------------------------------------------------------------------------


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse top-level ``key: value`` and ``key:\\n  - item`` shapes.

    Supports string scalars and lists of string scalars. Comments (lines
    starting with ``#``) and blank lines are ignored. Nested mappings, flow
    style, anchors, and multi-line scalars are not supported — and are not
    used anywhere in the KG frontmatter.
    """
    result: dict[str, Any] = {}
    current_list_key: str | None = None
    current_list: list[str] | None = None

    def finalize_list() -> None:
        nonlocal current_list_key, current_list
        if current_list_key is not None and current_list is not None:
            result[current_list_key] = current_list
        current_list_key = None
        current_list = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # List item line: starts with `- ` (possibly indented).
        if stripped.startswith("- "):
            if current_list is None:
                continue
            value = _strip_quotes(stripped[2:].strip())
            current_list.append(value)
            continue

        # Top-level key line.
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            finalize_list()

            if value == "":
                # Key opens a list (or empty mapping; we only handle lists).
                current_list_key = key
                current_list = []
            else:
                result[key] = _strip_quotes(value)

    finalize_list()
    return result


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown document into ``(frontmatter, body)``."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    yaml_block = match.group(1)
    body = text[match.end():]
    return parse_simple_yaml(yaml_block), body


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


class KGParseError(Exception):
    """Raised when an artifact's frontmatter is malformed beyond repair."""


@dataclass(frozen=True)
class KGNode:
    """One artifact in the Knowledge Graph (PRD / Feature / Blueprint / WO)."""

    id: str
    title: str
    artifact_type: str  # "prd" | "feature" | "blueprint-foundation" | "blueprint-feature" | "work-order"
    path: str | None  # repo-relative POSIX path to the source Markdown file, when file-backed
    url: str | None = None  # web link to the artifact, when API-backed
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def parent_id(self) -> str | None:
        """The id of this node's parent in the ontology chain, when applicable.

        Foundation Blueprints (cross-feature concerns like stack choice or
        common patterns) attach directly to a PRD via the ``product`` field —
        they have no Feature parent because they apply across every Feature.
        """
        if self.artifact_type == "work-order":
            return self.metadata.get("blueprint")
        if self.artifact_type == "blueprint-feature":
            return self.metadata.get("feature")
        if self.artifact_type == "blueprint-foundation":
            return self.metadata.get("product")
        if self.artifact_type == "feature":
            return self.metadata.get("product")
        return None


@dataclass(frozen=True)
class KGPath:
    """Upward path from a dependency through the Knowledge Graph chain.

    Two valid shapes:
    - **Feature path**: Work Order → Feature Blueprint → Feature → PRD (all four set).
    - **Foundation path**: Work Order → Foundation Blueprint → PRD (Feature stays None
      because foundation blueprints describe cross-feature concerns).

    Both shapes reach a PRD; both are considered "complete" for reporting.
    """

    work_order: KGNode | None = None
    blueprint: KGNode | None = None
    feature: KGNode | None = None
    prd: KGNode | None = None

    @property
    def is_complete(self) -> bool:
        # A path is complete when it can attribute the finding to a PRD via a
        # Work Order and a Blueprint. The Feature level is mandatory only for
        # feature-blueprint paths; foundation-blueprint paths legitimately
        # have feature=None.
        if not (self.work_order and self.blueprint and self.prd):
            return False
        if self.blueprint.artifact_type == "blueprint-foundation":
            return True
        return self.feature is not None

    @property
    def levels(self) -> list[tuple[str, KGNode | None]]:
        """Return ``[(level_name, node)]`` pairs in PRD→WorkOrder order."""
        return [
            ("prd", self.prd),
            ("feature", self.feature),
            ("blueprint", self.blueprint),
            ("work_order", self.work_order),
        ]


@dataclass(frozen=True)
class ValidationIssue:
    """A structural concern surfaced by :meth:`KnowledgeGraph.validate`."""

    severity: str  # "error" | "warning"
    path: str
    message: str


# ---------------------------------------------------------------------------
# GraphSource seam
# ---------------------------------------------------------------------------


class GraphSource(Protocol):
    """Anything that can produce Knowledge Graph nodes.

    The resolver (:class:`KnowledgeGraph`) is source-agnostic: it consumes
    normalized :class:`KGNode` values and never touches disk or network
    itself. Each source adapter is responsible for mapping its native schema
    into the canonical node shape — in particular, populating
    ``metadata["dependencies-introduced"]`` (or leaving it absent, in which
    case dependency attribution comes from post-construction enrichment via
    :meth:`KnowledgeGraph.add_dependencies`).
    """

    def iter_nodes(self) -> Iterable[KGNode]:
        """Yield every node in the graph."""
        ...

    def describe(self) -> str:
        """One-line provenance label for reports and error messages."""
        ...


class LocalDirectorySource:
    """Reads a KG from a directory tree of frontmattered Markdown files.

    This is the synthetic-KG loader used for demos and test fixtures.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def describe(self) -> str:
        return f"local directory {self.root}"

    def iter_nodes(self) -> Iterator[KGNode]:
        for md_path in self._iter_markdown(self.root):
            node = self._load_node(self.root, md_path)
            if node is not None:
                yield node

    @staticmethod
    def _iter_markdown(root: Path) -> Iterator[Path]:
        for p in sorted(root.rglob("*.md")):
            # README files inside the KG are conventional disclaimers, not
            # KG artifacts — skip them. KG artifacts always have frontmatter.
            if p.name.lower() == "readme.md":
                continue
            yield p

    @staticmethod
    def _load_node(root: Path, path: Path) -> KGNode | None:
        text = path.read_text(encoding="utf-8")
        front, _body = parse_frontmatter(text)
        if not front:
            return None  # not a KG artifact
        node_id = front.get("id")
        title = front.get("title", "")
        type_field = front.get("type")
        if not node_id or not type_field:
            raise KGParseError(
                f"{path.relative_to(root)}: missing required 'id' or 'type' frontmatter field"
            )

        artifact_type = type_field
        if type_field == "blueprint":
            blueprint_kind = front.get("blueprint_type")
            if blueprint_kind == "foundation":
                artifact_type = "blueprint-foundation"
            elif blueprint_kind == "feature":
                artifact_type = "blueprint-feature"
            else:
                raise KGParseError(
                    f"{path.relative_to(root)}: blueprint must declare blueprint_type (foundation|feature)"
                )
        elif type_field == "product-overview":
            artifact_type = "prd"
        elif type_field == "feature-requirements":
            artifact_type = "feature"
        elif type_field == "work-order":
            artifact_type = "work-order"
        else:
            # Unknown type — keep verbatim, validator will flag it.
            pass

        rel = path.relative_to(root).as_posix()
        return KGNode(
            id=node_id,
            title=title,
            artifact_type=artifact_type,
            path=rel,
            metadata=front,
        )

# ---------------------------------------------------------------------------
# KnowledgeGraph resolver
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """In-memory index of a Software Factory Knowledge Graph."""

    def __init__(self, source_label: str) -> None:
        self.source_label = source_label
        self.nodes: dict[str, KGNode] = {}
        # (ecosystem, package) → list of Work Order ids that declared it
        self._dep_index: dict[tuple[str, str], list[str]] = {}

    @classmethod
    def from_source(cls, source: GraphSource) -> "KnowledgeGraph":
        kg = cls(source.describe())
        kg.extend_from_source(source)
        return kg

    def extend_from_source(self, source: GraphSource) -> None:
        """Merge another source's nodes in (first declaration wins).

        Used by multi-target ``.sw-factory`` scans, where each cloned repo
        contributes its own execution state to one aggregate graph.
        """
        for node in source.iter_nodes():
            if node.id in self.nodes:
                continue
            self.nodes[node.id] = node
            if node.artifact_type == "work-order":
                self._index_dependencies(node)

    @classmethod
    def load(cls, root: Path) -> "KnowledgeGraph":
        """Back-compat convenience for the local-directory source."""
        return cls.from_source(LocalDirectorySource(root))

    def _index_dependencies(self, wo: KGNode) -> None:
        deps = wo.metadata.get("dependencies-introduced") or []
        if not isinstance(deps, list):
            return
        for entry in deps:
            if ":" not in entry:
                continue
            ecosystem, _, package = entry.partition(":")
            ecosystem = ecosystem.strip()
            package = package.strip()
            if not ecosystem or not package:
                continue
            self._dep_index.setdefault((ecosystem, package), []).append(wo.id)

    def add_dependencies(self, wo_id: str, deps: Iterable[str]) -> None:
        """Attribute ``eco:pkg`` entries to a Work Order after construction.

        Used by derivation-based enrichment (git manifest deltas) for sources
        whose native schema carries no dependency declarations.
        """
        for entry in deps:
            if ":" not in entry:
                continue
            ecosystem, _, package = entry.partition(":")
            ecosystem = ecosystem.strip()
            package = package.strip()
            if not ecosystem or not package:
                continue
            wo_ids = self._dep_index.setdefault((ecosystem, package), [])
            if wo_id not in wo_ids:
                wo_ids.append(wo_id)

    # -----------------------------------------------------------------------
    # Resolver
    # -----------------------------------------------------------------------

    def map_dependency(self, ecosystem: str, package: str) -> KGPath | None:
        """Return the ontology path for ``(ecosystem, package)``, or None."""
        wo_ids = self._dep_index.get((ecosystem, package))
        if not wo_ids:
            return None

        # If multiple Work Orders declare the same dependency we pick the
        # first by declaration order — the validator surfaces this as an
        # ambiguity warning so the KG author can resolve it.
        wo_id = wo_ids[0]
        wo = self.nodes.get(wo_id)
        if wo is None:
            return None

        blueprint = self._lookup_parent(wo)
        # Foundation blueprints attach directly to a PRD; feature blueprints
        # go through a Feature first.
        if blueprint is not None and blueprint.artifact_type == "blueprint-foundation":
            feature = None
            prd = self._lookup_parent(blueprint)
        else:
            feature = self._lookup_parent(blueprint) if blueprint else None
            prd = self._lookup_parent(feature) if feature else None

        return KGPath(work_order=wo, blueprint=blueprint, feature=feature, prd=prd)

    def _lookup_parent(self, node: KGNode | None) -> KGNode | None:
        if node is None:
            return None
        parent_id = node.parent_id
        if parent_id is None:
            return None
        return self.nodes.get(parent_id)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self) -> list[ValidationIssue]:
        """Return a list of structural issues. Empty list ⇒ clean."""
        issues: list[ValidationIssue] = []

        if not self.nodes:
            issues.append(
                ValidationIssue(
                    severity="error",
                    path=self.source_label,
                    message="no Knowledge Graph artifacts found",
                )
            )
            return issues

        for node in self.nodes.values():
            # Required parent refs must resolve.
            if node.artifact_type == "work-order":
                bp = node.metadata.get("blueprint")
                if not bp:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"work order {node.id} missing 'blueprint' reference",
                        )
                    )
                elif bp not in self.nodes:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"work order {node.id} references unknown blueprint {bp!r}",
                        )
                    )
            elif node.artifact_type == "blueprint-feature":
                f = node.metadata.get("feature")
                if not f:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"feature blueprint {node.id} missing 'feature' reference",
                        )
                    )
                elif f not in self.nodes:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"feature blueprint {node.id} references unknown feature {f!r}",
                        )
                    )
            elif node.artifact_type == "blueprint-foundation":
                p = node.metadata.get("product")
                if not p:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=(
                                f"foundation blueprint {node.id} missing 'product' reference"
                            ),
                        )
                    )
                elif p not in self.nodes:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=(
                                f"foundation blueprint {node.id} references unknown product {p!r}"
                            ),
                        )
                    )
            elif node.artifact_type == "feature":
                p = node.metadata.get("product")
                if not p:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"feature {node.id} missing 'product' reference",
                        )
                    )
                elif p not in self.nodes:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            path=node.path or node.id,
                            message=f"feature {node.id} references unknown product {p!r}",
                        )
                    )

        # Ambiguous dependency declarations (same package in multiple WOs).
        for (ecosystem, package), wo_ids in self._dep_index.items():
            if len(wo_ids) > 1:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        path=", ".join(
                            self.nodes[w].path or w for w in wo_ids if w in self.nodes
                        ),
                        message=(
                            f"{ecosystem}:{package} declared in multiple work orders: "
                            f"{', '.join(wo_ids)}"
                        ),
                    )
                )

        return issues

    # -----------------------------------------------------------------------
    # Introspection
    # -----------------------------------------------------------------------

    def declared_dependencies(self) -> list[tuple[str, str]]:
        """Return every (ecosystem, package) declared somewhere in the KG."""
        return sorted(self._dep_index.keys())
