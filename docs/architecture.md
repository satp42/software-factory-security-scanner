# Architecture — Alignment-Aware Security Assessment Engine

This document positions `sf-scan` Lens 1 (the dependency-vulnerability scanner shipped in this repository) as the first of four lenses in a broader **alignment-aware security assessment engine** for 8090's Software Factory. It names the next three lenses, sketches their inputs and outputs, and surfaces the deeper bet: that the same lens architecture, extended into Lens 4 (trace completeness), produces a tractable, formally-grounded scalar **alignment-debt score** for every edge in a Software Factory Knowledge Graph.

---

## Why this exists

Software Factory's distinctive bet is that the **Knowledge Graph** — connecting Product Requirements Documents (PRDs) → Feature nodes → Blueprints → Work Orders → Code — is the right substrate for AI-native enterprise software development. Each edge in the graph encodes a translation step: intent into decision, decision into specification, specification into implementation. The thesis is that holding this chain coherent over time is what separates AI-native software from AI-assisted prototyping.

But the chain has no security lens yet. Dependency vulnerabilities — the single most common class of production security risk in a real codebase — surface as flat CVE lists divorced from the Knowledge Graph context that gives them meaning. A typical scan report tells you "package P at version V has CVE-X." It does not tell you which Requirement is at risk, which Blueprint owns the remediation, or which Work Order brought the dependency in. The Knowledge Graph holds the answers; the security tooling does not consume the graph.

This product is the simplest possible lens that closes that gap, plus the architectural commitment that it is **one of four lenses** — three additional lenses are sketched here for context. Together they constitute the assessment engine.

---

## The four lenses

![Lens overview](diagrams/lens-overview.mmd)

> *The mermaid source for the diagram above lives at [diagrams/lens-overview.mmd](diagrams/lens-overview.mmd). On a GitHub-rendered Markdown view, the image link won't auto-render the mermaid — view the .mmd file or paste it into the mermaid live editor for the picture. The prose below carries the same information.*

All four lenses share a contract: each consumes part of the Knowledge Graph plus part of the shipped code, and produces a structured report attributing every finding to specific nodes in the graph. They differ in **what they measure** and **what input they read**.

### Lens 1 — Dependency CVE → Ontology mapping  **(shipped)**

**What it measures.** Each dependency in the project's manifest files is checked against OSV.dev (which aggregates the GitHub Advisory Database, RustSec, PyPI Safety DB, and others). Findings are mapped to the Knowledge Graph by matching the package name against each Work Order's `dependencies-introduced` field, then walking parent references upward.

**Input from KG.** Work Order frontmatter (specifically the `dependencies-introduced` and `blueprint` fields), plus the chain of parent references on Blueprints (`feature` or `product`), Features (`product`), and PRDs.

**Input from code.** The repo's dependency manifests (`package.json`, `package-lock.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Gemfile.lock`).

**Output.** `report.md` and `report.json`. Each finding lists the affected package, severity, fix version, and the upward path through Work Order → Blueprint → Feature → PRD. Findings whose package is not declared in any Work Order land in the **Unmapped Findings** section — themselves a Lens 4 precursor (KG coverage gap that an alignment-debt score would quantify).

**Status.** Shipped. This repository.

---

### Lens 2 — Requirements-to-Test Coverage  **(sketched)**

**What it measures.** For each Acceptance Example declared in a PRD's Feature Requirements documents, does at least one test in the codebase exercise it? An Acceptance Example is treated as a measurable claim: "given X input, the system should do Y." Coverage is binary per Acceptance Example; the report aggregates coverage at the Feature and PRD level.

**Input from KG.** Acceptance Examples from Feature Requirements documents (the `AE-...` IDs structured in 8090's published Requirements Writing Guide).

**Input from code.** The repo's test files. The matching mechanism is intentionally explicit rather than fuzzy — tests opt into Acceptance Example coverage by carrying a marker (a comment, decorator, or test-id convention) that names the AE-ID. Untagged tests don't count, and the report's interesting output is the set of Acceptance Examples with **zero** matching tests.

**Output.** A coverage report per Feature, showing which AEs have tests, which don't, and which tests are marked but reference non-existent AEs.

**Why this lens.** Sina explicitly named this as Pillar 2 in our conversation: "generate tests from requirements to validate functionality." The lens makes coverage measurable as a precondition to that generation — you can't generate what's missing until you know what's missing.

---

### Lens 3 — Blueprint-to-Code Drift Detection  **(sketched)**

**What it measures.** For each architectural decision declared in a Blueprint (technology choice, pattern, data-flow constraint), does the shipped code reflect it? Drift is the fraction of stated decisions the code violates.

**Input from KG.** Blueprint frontmatter and structured "decision" sections. A decision is a tuple `(scope, claim)` — for example `(repository, "uses pnpm workspaces")` or `(src/validate.ts, "validates manifests against zod schemas at load time")`.

**Input from code.** The repo at HEAD. Each claim has a corresponding **verifier function** — a small piece of code that returns true/false against the live source tree. For repository-scope claims, the verifier inspects manifests and config. For file-scope claims, the verifier parses the file with the appropriate AST tool and looks for the claim's invariant.

**Output.** A drift report listing every violated claim, the file or repository surface that failed it, and the Blueprint that declared the claim.

**Why this lens.** Sina explicitly named this as Pillar 1: "projects accumulate debt when not actively maintained" — the "confident upgrade path without manual QA" problem. A drift score is the leading indicator: a project drifts before it breaks, and a Blueprint-anchored drift score lets the team intervene before the drift becomes incident.

---

### Lens 4 — Work-Order-to-Code Trace Completeness  **(sketched, bridges to research)**

**What it measures.** For each Work Order, how completely does the resulting code reflect the Work Order's stated intent? Output is a scalar **trace-completeness score** per Work Order, plus an aggregate per edge in the Knowledge Graph (Work Order → Blueprint, Blueprint → Feature, Feature → PRD).

**Input from KG.** Work Order frontmatter (`files-affected`, `dependencies-introduced`) and the Work Order's prose intent.

**Input from code.** The code diff (or current state) of every file listed in `files-affected`.

**Output.** A per-Work-Order score plus a per-edge alignment-debt score for the KG as a whole.

**This is the bridge to alignment research.** It is also the most ambitious lens. The next two sections explain it.

---

## Lens 4 — directional worked example

A concrete (but not-yet-computed) sketch of how Lens 4 would score one Work Order in the synthetic Knowledge Graph for `8090-inc/software-factory-plugin`.

### The target Work Order

[`kg/software-factory-plugin/work-orders/wo-002-validation-pipeline.md`](../kg/software-factory-plugin/work-orders/wo-002-validation-pipeline.md) — *"Manifest validation pipeline."*

Its declared intent: "Implement the per-plugin manifest validator described in BP-001. Establishes the canonical `plugins/<name>/plugin.yaml` schema and the validation entry point that downstream build stages depend on."

Its declared `files-affected`: `src/validate.ts`, `src/schema.ts`, `plugins/`.

Its declared `dependencies-introduced`: `npm:zod`, `npm:yaml`, `npm:ajv`, `npm:json-schema`, `npm:semver`.

### The scoring formula (directional)

A trace-completeness score for WO-002 is computed from three sub-signals, each in [0, 1]. The composite score is the harmonic mean — using the harmonic mean rather than arithmetic punishes any single sub-signal that drops to zero, which matches the intuition that a Work Order whose intent is not reflected at all in one of these dimensions has a deeper problem than one with mild gaps across all three.

**1. Files-touched precision/recall** (`Sₜ`). The validator runs the actual git history for this Work Order's branch (or, when no branch attribution exists, the most recent N commits whose messages reference WO-002). It computes the set of files actually modified, intersects with `files-affected`, and produces an F1 score over precision and recall. A WO that declares it touches `src/validate.ts` but the implementation also rewrites `src/build-hooks.ts` (unannounced scope creep) takes a hit on precision; a WO that declares `src/schema.ts` but no commit ever touched it takes a hit on recall.

**2. Dependencies-introduced precision/recall** (`Sᵈ`). Same shape but over the dependency manifest delta. The validator parses `package.json` before and after the Work Order's commits and compares the new entries against `dependencies-introduced`. The lens correctly identifies WOs that brought in packages they didn't declare (a "silent dependency" — a small alignment debt) and WOs that declared dependencies they never actually used.

**3. Intent-implementation semantic similarity** (`Sᵢ`). The hardest signal. The Work Order's prose intent — *"Implement the per-plugin manifest validator described in BP-001"* — is compared against the actual code change. We propose two candidate implementations for the v1 prototype, both at low cost:

- **(a)** Embedding similarity between the WO's intent text and the docstring/comments of the new code in `files-affected`. Cheap, no external model required beyond an embedding API.
- **(b)** LLM-as-judge: a structured prompt that gives the LLM the WO's intent and the diff, and asks whether the code can plausibly be characterized by the intent. Returns a [0, 1] confidence.

Either signal alone is noisy. Combined with `Sₜ` and `Sᵈ`, even a noisy `Sᵢ` is a useful third axis because the harmonic mean punishes any axis that drops to near-zero, and intent-implementation mismatch is the most common alignment failure.

The composite is `S(WO) = 3 / (1/Sₜ + 1/Sᵈ + 1/Sᵢ)`, clamped to [0, 1].

### Worked example values (illustrative)

For a hypothetical WO-002 implementation:

| Sub-signal | Value | Why |
|---|---|---|
| `Sₜ` (files touched) | 0.86 | Implementation touched `src/validate.ts`, `src/schema.ts`, AND `src/build-validate-helpers.ts` (declared 2, touched 3 — precision 2/3, recall 1.0 → F1 0.80) |
| `Sᵈ` (deps introduced) | 1.00 | All five declared deps appear in the diff; no silent additions |
| `Sᵢ` (intent vs code) | 0.72 | Embedding similarity between WO intent text and the validator's docstrings is moderate; LLM-as-judge confirms with a similar score |
| **Composite `S`** | **0.84** | Harmonic mean |

A score below ~0.5 on any single sub-signal should trigger a human review of that Work Order. A composite drift across many Work Orders is the project-level alignment-debt indicator.

**This is directional, not yet computed.** No actual score for the synthetic KG appears in `sf-scan` v1. Lens 4 is the next-week implementation target once IP access opens; the formula above is the v1 architectural commitment.

---

## Why this matters — the federated-learning bridge

There is a deeper structural reason Lens 4 deserves the term *alignment debt* rather than the more conventional *drift* or *technical debt*.

In a federated learning system, multiple clients train local models against shared global weights. The typical attack surface is: an adversarial client subtly corrupts its local update before contributing, the central aggregator merges the update into global weights, and a model backdoor propagates to all downstream consumers — silently, without raising any single anomaly large enough to trip detection. Defenses work by measuring **per-client update divergence** from a robust baseline (double-momentum trackers, Krum-style outlier filtering, gradient inversion) — and crucially, by tracking that divergence **at every aggregation step**, not just at training end.

The Software Factory's Knowledge Graph is structurally a federated computation: each Work Order is a local "client" that translates an upstream intent (the Blueprint) into a downstream artifact (the code diff). Each translation step accumulates small alignment errors — a function got renamed, a constraint got dropped, a default got changed. Individually each error is too small to surface as a bug; aggregated across hundreds of Work Orders the codebase quietly stops reflecting the PRD. By the time the misalignment is large enough to break user-facing behavior, the chain is too long and noisy to walk backwards.

This is exactly the federated backdoor problem in a different domain. The same detection technology — per-edge divergence scoring with a robust baseline, accumulated over a long horizon — should apply. **Lens 4 is the channel where that technology enters the Software Factory.**

My prior research (federated-learning backdoor detection paper, *LawLoop* applied in 20+ law firms with knowledge-graph-anchored compliance constraints) lives in this technical lineage. The natural follow-on is to apply double-momentum divergence trackers, normally used for adversarial client detection, to per-edge translation-loss scoring in the Knowledge Graph. The scoring formula in the worked example above is the entry point.

This section is the technical foundation, not the implementation. A full essay on the federated-learning ↔ alignment-debt mapping is held for a follow-on writeup once Lens 4 is implementable against the real Software Factory Knowledge Graph.

---

## What's next

Sequenced after Lens 1, in priority order:

1. **Lens 2 (Requirements-to-Test Coverage)**: highest immediate utility per Sina's stated Pillar 2. Requires KG read access via the Software Factory API; estimated ~2 weeks to working v1 once API access opens.
2. **Lens 4 (Trace Completeness, v1)**: the alignment-debt entry point. The score formula above is the v1; the federated-learning-style double-momentum tracker is a stretch v2. ~3 weeks to a measurable per-WO score.
3. **Lens 3 (Blueprint-to-Code Drift)**: most architecturally ambitious because each Blueprint claim needs a verifier function. Highest leverage once landed because it directly addresses the "projects accumulate debt" framing. ~4 weeks for a useful baseline.

The IP-protection gate is upstream of all three lenses — none of them can run against real customer data until the contract surface is in place. They can all be prototyped against the synthetic Knowledge Graph in this repo, which is a defensible iteration path.

---

## Open questions

- **Q-A1.** Should Lens 2's Acceptance Example coverage matcher be purely declarative (test-side tag → AE-ID), or should it also support inferred matching (LLM-based check)? Inferred matching is higher recall but introduces a noise floor.
- **Q-A2.** Should Lens 4's intent-implementation similarity use embedding-only, LLM-as-judge, or both? Embedding-only is cheaper and deterministic; LLM is more discriminating but introduces variance.
- **Q-A3.** Should the per-edge alignment-debt score be a single scalar (as proposed above) or a vector (per-axis breakdown — files / deps / intent)? Scalar is cleaner for dashboards; vector is more diagnostic.

These resolve during Lens 4 implementation, not now.
