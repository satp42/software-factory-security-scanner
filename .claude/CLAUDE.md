# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`sf-scan` is Lens 1 of a four-lens "alignment-aware" security engine for 8090's Software Factory. It scans dependency-tree vulnerabilities and maps each finding onto a Software Factory Knowledge Graph (PRD → Feature → Blueprint → Work Order → Code), so a CVE carries business intent: *which PRD requirement it endangers, which Blueprint owns remediation, which Work Order introduced the package.* Findings whose package matches no Work Order land in an "Unmapped" bucket — itself the structural signal that Lens 4 (alignment-debt scoring) is designed to quantify. Lenses 2–4 are sketched only, in `docs/architecture.md`.

## Commands

```bash
# Setup (Python 3.11+ required)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # puts `sf-scan` on PATH

pytest                            # full offline suite (~129 tests, deterministic, no network)
pytest tests/test_kg.py          # one file
pytest tests/test_vuln.py::test_name   # one test
SF_SCAN_NETWORK_TESTS=1 pytest    # also runs the 2 opt-in tests that hit live OSV.dev + clone GitHub

./examples/scan-command.sh        # end-to-end demo scan (sf-plugin + OWASP NodeGoat)
sf-scan scan --repo URL[@SHA] --kg ./kg/software-factory-plugin --out ./reports
```

There is no separate lint step. `pytest` is the gate; CI (`.github/workflows/ci.yml`) runs it on 3.11 and 3.12, then a live e2e scan job.

## Hard invariant: zero runtime dependencies

`dependencies = []` in `pyproject.toml` is deliberate — the scanner runs on nothing but the Python 3.11+ stdlib. This shapes the whole codebase and **must be preserved**:

- OSV.dev is called through `urllib` (`vuln.py`), not `requests`.
- YAML frontmatter is parsed by a hand-rolled restricted-subset parser (`kg.py::parse_simple_yaml`), not `PyYAML`. It only handles top-level `key: value` and `key:\n  - item` lists — do not feed it nested mappings/anchors, and don't reach for a YAML lib to "fix" it.
- TOML uses stdlib `tomllib`; caching uses stdlib `sqlite3`; reports are built by string concatenation, not Jinja2.

`pytest` / `pytest-cov` are the only deps, and they live under `[project.optional-dependencies].dev`.

## Pipeline architecture

`cli.py::run_scan` orchestrates five stages, one module each. Data flows as the models in `models.py` (`Dependency` → `Finding`).

1. **Fetch** (`fetch.py`) — `clone_repo` is a contextmanager cloning each `URL[@SHA]` into a temp dir (shallow when no SHA, depth-50 + checkout when pinned) and cleaning up on exit. `parse_repo_spec` splits `@SHA` but leaves SSH-style `git@host:...` URLs intact.
2. **Extract** (`extract.py`) — walks the tree (skipping `node_modules`, `.venv`, `vendor`, etc.), dispatches per-filename parsers for npm / PyPI / Go / RubyGems, and dedups by `(ecosystem, package, manifest-dir)` with **lockfile entries winning over manifest entries**. Version specifiers are not preserved — only the package name and a pinned version, since OSV is queried by name+version.
3. **Query** (`vuln.py`) — batches deps to OSV.dev's `/v1/querybatch`, then fetches each vuln's full record. `_extract_severity` normalizes across OSV/GHSA/CVSS shapes (note: `MODERATE`→`MEDIUM`); GHSA-prefixed IDs get both `OSV` and `GHSA` source tags.
4. **Resolve** (`kg.py`) — see below.
5. **Render** (`report.py`) — one `render()` emits `report.json` (flat findings + nested `ontology_index` + `unmapped`) and `report.md` (executive summary, risk-ranked top-N action list, findings nested by ontology level with relative links to KG files).

### Testing seam

Network and disk are injected, never hardcoded, so the whole pipeline runs offline and deterministically:

- `run_scan(args, *, osv_client=...)` accepts a stub OSV client. `vuln.query(..., client=..., cache=...)` takes both. `OsvClient` is a `Protocol`; `HttpOsvClient` is the real one, and tests pass fixture-backed stubs (`tests/fixtures/osv-responses/`).
- When adding a stage or option, keep the injectable-client shape. `tests/test_e2e.py` builds a real local git repo + stub OSV client and asserts on report shape — mirror that pattern rather than mocking internals.

## Knowledge Graph model (`kg.py`)

A KG is a directory of Markdown files, each with YAML frontmatter declaring `id`, `type`, and parent references. `README.md` files inside a KG are skipped (disclaimers, not artifacts). The ontology chain and how the frontmatter encodes it:

| `type` frontmatter | internal `artifact_type` | parent field |
|---|---|---|
| `product-overview` | `prd` | (root) |
| `feature-requirements` | `feature` | `product` |
| `blueprint` + `blueprint_type: foundation` | `blueprint-foundation` | `product` |
| `blueprint` + `blueprint_type: feature` | `blueprint-feature` | `feature` |
| `work-order` | `work-order` | `blueprint` |

The **resolver** (`map_dependency`) is the core. Work Orders declare a `dependencies-introduced:` list of `ecosystem:package` strings; `load()` indexes these into `_dep_index`, and a finding's `(ecosystem, package)` walks *up* parent references to a PRD. Two valid path shapes reach a PRD and both count as complete (`KGPath.is_complete`):

- **Feature path**: Work Order → Feature Blueprint → Feature → PRD.
- **Foundation path**: Work Order → Foundation Blueprint → PRD (Feature is legitimately `None` — foundation blueprints are cross-feature concerns like stack choice).

Mapping is by `(ecosystem, package)` only, **not version** — a Work Order records what it introduced, not the currently pinned version. `KnowledgeGraph.validate()` returns non-fatal `ValidationIssue`s (unresolved parent refs = error; same package in multiple Work Orders = warning) that surface in the report's `scan_errors` without aborting the scan.

`kg/software-factory-plugin/` is a **synthetic** demo KG authored to match 8090's public writing guides — not real 8090 data. Preserve that provenance framing (see its README) in any docs you touch.

## Exit codes

`0` OK · `2` usage error (bad/missing args) · `3` input error (KG path missing, or every clone failed). KG parse *warnings/errors* do not change the exit code — they go into the report.
