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

---

## How 8090 Software Factory works (from the official docs)

Source: <https://www.8090.ai/docs/general/introduction> (and the `modules/` + `raw-materials/` pages). This is the real platform `sf-scan` targets; the synthetic `kg/software-factory-plugin/` only imitates it. Where the two diverge, the synthetic-KG caveats below the meeting-context section apply.

Software Factory is an AI-native SDLC orchestration platform. Its premise: writing code was never the bottleneck — deciding *what* to build and keeping intent, architecture, and code aligned is. It replaces tool sprawl with one workspace where humans and specialized agents work from a single source of truth, the **Knowledge Graph**, which connects requirements → architecture → implementation so they evolve together. When requirements change or code drifts, the system detects the divergence and drives a human-in-the-loop resolution.

### Raw materials (inputs to the graph)

- **Artifacts** — external files (legacy PRDs, meeting notes, mockups, interviews, diagrams, audio) uploaded and indexed so agents draw on real context instead of assumptions. Can be linked into documents for traceability.
- **Codebase connection** — repositories connected through the **8090 Software Factory GitHub App** (read-only). Indexing runs automatically (~5–10 min); a webhook reindexes on every push to the tracked branch.

### The pipeline — four modules

1. **Requirements** — define *what* and *why*, implementation-agnostic. Two document kinds: **Product Overview Documents** (strategic context) and **Feature Requirements Documents (FRDs)**, one per feature. The Requirements Agent reverse-engineers requirements from artifacts/code or drafts them via structured Q&A, and flags ambiguity, gaps, conflicts, and duplication.
2. **Blueprints** — human-readable technical specs, the source of truth for *how* the system is built. Three layers:
   - **Container Blueprint** — one C4 container (deployable/runnable unit: web app, API server, DB, worker, pipeline). Infrastructure-focused, feature-agnostic.
   - **Component Blueprint** — a reusable system capability spanning multiple C4 components, often cross-container. Feature-agnostic.
   - **Feature Blueprint** — composes Component Blueprints (plus feature-specific glue) to satisfy one FRD; it is the technical counterpart of that FRD.
3. **Work Orders** — structured, traceable tasks toward the target state. Each carries: core metadata (ID, title, status, assignees, phase), a rich description (**Purpose, Acceptance Criteria, Out of Scope**), **Knowledge Graph connections** (links up to requirements/blueprints), an optional file-level **implementation plan**, and activity/comments. Extracted from Blueprints by the agent (configurable extraction strategy) or created manually, then organized into **phases** and sequenced.
4. **Feedback** *(formerly "Validator" — the intro page still says Validator; the module is now Feedback)* — collects end-user reports (`FB-N` items) and groups them into **Themes** with quote evidence, which link back to Work Orders. This closes the loop from real-world usage into planning.

### Drift detection

Background agents continuously compare requirements, blueprints, work orders, and code. Alerts fire when code changes may invalidate a blueprint, a PRD update is not reflected downstream, foundation/shared changes conflict with features, or work orders fall out of date with their blueprints. Each alert opens a guided workflow to re-align — this internal-consistency drift check is exactly what has no notion of an *external* reference like a CVE, which is why `sf-scan` exists.

### Integration surfaces

- **MCP** — coding agents connect to Work Orders from the local dev environment (list assigned/Ready work orders, read full details + implementation plans, update status, search requirements/blueprints/artifacts). Set up from the Work Orders table view.
- **Feedback Integration REST API** — `POST /v2/reporting-api/feedback` with an `X-API-Key: sf-rpt-...` key submits feedback (`end_user_email` + `content` required). The old `POST /v1/integration/validator/feedback` (`sf-int-...`) endpoint is deprecated and retires 2026-08-01.

---

## Project context (from 8090 collaboration meetings)

Background framing for why this project exists and how the real Software Factory differs from the synthetic demo KG. This is orientation for anyone working on the code, not build instructions.

### Why this project exists

- Across 37 documented Software Factory releases there is not one security, CVE, or SBOM feature. Every code-analysis feature 8090 ships compares code only against documents the project's own team authored.
- "Drift" is therefore an internal consistency check: a vulnerable dependency is invisible to it by construction, because no blueprint ever asserted a version was safe.
- `sf-scan` is not adding security *to* the graph — it brings the first external reference (OSV/CVE data) into a system that has only ever compared intent to itself.

### The Software Factory Knowledge Graph in practice

- Ontology: PRD → Feature → Blueprint → Work Order → Code. Blueprints map to Work Orders (specific components); Work Orders connect to code.
- Real-world limitation: traces between components are incomplete. Coding-agent traces are missing, and traces are not unified across the separate requirements / blueprint / work-order agents, so cross-correlation is hard.

### Synthetic-KG caveat (critical for Lens 1)

- Lens 1 maps CVEs to Work Orders by matching packages against a `dependencies-introduced` list. **This will not survive contact with a real Knowledge Graph.**
- A real 8090 Work Order has exactly six sections: Summary, In Scope, Out of Scope, Requirements, Blueprints, E2E Acceptance Tests. Neither `dependencies-introduced` nor `files-affected` appears in any published 8090 guide — the synthetic `kg/software-factory-plugin/` invented both, so against a real repo the mapping rate would go to 0%.
- To harden Lens 1, map through what real Work Orders actually carry: REQ/AC IDs, blueprint names, or git history.

### Real 8090 artifact conventions (for Lens 2 onward)

- Requirements use `REQ-[PREFIX]-NNN`; acceptance criteria use `AC-[PREFIX]-NNN.N`, each phrased "When [condition], the system shall [behavior]."
- Real Work Orders copy those IDs verbatim. The Work Order guide specifies `COV_` coverage IDs, `@COV_` test tags, and exact spec paths.
- There is no "AE-" / "Acceptance Examples" convention — that was invented and should not be cited.

### Direction of the four-lens engine

- Lens 2: map how a single vulnerability propagates through the graph and dispatch Work Orders to fix impacted components.
- Lens 4 (alignment debt): a scalar drift score for every Knowledge Graph edge, measuring translation loss across Refinery → Foundry → Work Orders → Code.
- Long-term goal: an autonomous end-to-end security pipeline — plug into a source like Wiz or Dependabot, then detect, remediate, test, and resolve.
