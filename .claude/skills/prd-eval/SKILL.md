---
name: prd-eval
description: "Evaluate a PRD against the 12-criterion EvalPRD rubric using in-session reasoning (no external API, no network). Produces a binary PASS/FAIL scorecard with evidence quotes, a GO/REVISE/HOLD readiness gate, a P0/P1/P2 fix plan, and an executable agent task DAG. Fire ONLY on explicit rubric mentions: EvalPRD, C1-C12, 12 criteria, readiness gate, GO/REVISE/HOLD, prd-eval, score or grade my PRD. Reviewing or red-teaming a PRD belongs to prd-judge; writing a PRD belongs to prd-writer."
---

# PRD Eval

Evaluate a PRD against the 12-criterion EvalPRD rubric. Evaluation runs inside this Claude session — no network calls, no API, no script.

## When to use

Fire only when the user explicitly names the rubric or its outputs:

- "run EvalPRD on this PRD", "score my PRD against C1–C12", "give me the readiness gate"
- "generate a fix plan against the 12-criterion rubric"
- "generate agent tasks using EvalPRD / EvalGPT"
- files clearly tagged as EvalPRD outputs (BinaryScoreOutput / FixPlanOutput / AgentTasksOutput)

**Do not fire** for:
- "review this PRD" / "audit my PRD" / stakeholder-perspective critiques → use `prd-review`
- "draft a PRD" / "write a PRD" / PRD templates → use `prd-writer`
- generic product or design reviews without the rubric

If the user says "review" without naming the rubric, ask one clarifying question before deciding between `prd-eval` and `prd-review`.

## Prerequisites

- PRD text accessible as plain text. `.md` / `.txt` work directly. For `.pdf` or `.docx`, the user is responsible for providing extracted text — if a CLI extractor (`pdftotext`, `pandoc`, `python-docx`) is not already installed, ask the user to paste the extracted text rather than trying to install tools.
- No network access or API key needed. Evaluation is done by the current Claude session reasoning over the PRD text using the bundled system prompt.

## Workflow

1. **Locate the PRD**. Ask if not provided. Accept a file path, pasted text, or URL to a local file. If extraction fails, ask for plain text.
2. **Confirm which outputs to produce** and collect tuning knobs (see below). Ask the user:
   - Which outputs: (a) scorecard only, (b) scorecard + fix plan, (c) scorecard + agent tasks, (d) all three. Default: all three.
   - Scorecard: `evidence_per_criterion` (0–3, default 1), `fail_on_missing` (default true), optional `peer_reviews` for agreement stats, `rubric_version` (default "v1.0").
   - Fix plan: `limit` (default 10), `include_acceptance_tests` (default true), `time_horizon_days` (default 10, advisory).
   - Agent tasks: `task_hours_min`/`task_hours_max` (default 2/4), optional `feature_filter` array, `emit_mermaid` (default false).
3. **Ground in the rubric**. Read `references/system-prompt.md` — this is the verbatim EvalGPT system prompt with all 12 criterion definitions (pass/fail indicators + examples), failure mode taxonomy, GxP overlay, and scoring gates. Treat it as the system prompt for the evaluation.
4. **Evaluate each output mode independently from the PRD text**. Do not condition the fix plan on the scorecard, or the agent tasks on the fix plan — each mode must re-read the PRD. This matches how the hosted service calls the model three separate times. If the user wants cross-mode consistency (e.g., fix plan references specific scorecard failures), state that explicitly and note it is a deviation from hosted behavior.
5. **Emit JSON matching the schemas in `references/output-schemas.md` exactly**. Before returning, walk each schema's `required` array field-by-field and confirm every property is present with the correct type. The hosted validator rejects missing fields and extra fields. Note: the Mode 3 appender calls some fields "optional" but the JSON Schema requires them — always emit the full field set (see the conformance callout in the schemas file).
6. **Summarize**. Lead with the readiness gate + pass count (e.g., "HOLD — 2/12 pass"), list failed gating criteria, top 3 P0 fixes, and total task hours. Under 15 lines. Offer: "Want the full JSON, a Markdown report, or to drill into a specific criterion?"

## Evaluation principles

- **Strict on gating criteria**. C3, C5, C10, C11, C12. A single ambiguous integration reference fails C5. A feature whose "done" state is subjective fails C10. A PRD with no falsifiable bet or no kill/scale/graduate thresholds fails C12.
- **Evidence is mandatory**. Every criterion verdict — pass or fail — needs at least one direct quote from the PRD with a `{section, page}` locator. If no quote supports a PASS, the criterion fails. Use `"N/A"` for page when the PRD has no page numbers.
- **No "quick wins"**. The EvalGPT persona forbids the phrase.
- **Plain English, active voice, audit-ready**. No corporate fluff. State exact system behaviors with explicit acceptance criteria.
- **GxP overlay when relevant**. If the PRD implies regulated workflows (pharma, clinical, medical device, financial), check for audit trails, RBAC, ALCOA+, 21 CFR Part 11 eSignatures, validation plan, HIPAA/PHI handling, Veeva/Vault or LIMS/EMR integration. Missing = FAIL on C5/C10 and log compliance gaps.

## Fidelity limits vs. the hosted service

Call these out to the user when relevant; do not pretend the skill reproduces production behavior exactly.

- **No temperature control**. The hosted service uses temperature 0.2 for the scorecard and 0.3 for fix plan / tasks. This skill runs at whatever temperature the current session uses. Expect more variance than the production service; rerun if consistency matters.
- **No JSON Schema enforcement at runtime**. The hosted service validates outputs with Ajv against `schemas.ts` and retries on failure. This skill has no validator — the self-check in step 5 is the only guard. Do a pass over every `required` field before returning.
- **No structured-outputs beta**. The hosted service uses the Anthropic structured-outputs beta with an explicit JSON Schema attached to the request. Here, Claude emits JSON from the prompt only.
- **Model may differ**. The hosted service pins `claude-sonnet-4-5-20250929`. This session may be a different model. Say so if the user asks for strict parity.

## PRD-Lite vs. PRD-Heavy yardstick

The 12-criterion rubric is calibrated for engineering-ready PRDs. A PRD-Lite (pre-sales executive funding artifact, target ~6 pages) will structurally fail C5 (exact endpoints/payloads), C7 (exact SLO thresholds), C10 (AI Agent Readiness), and C11 (Task Decomposability) by design. C12 (Falsifiable Bet and Decision Thresholds) is NOT a structural deferral — a funding artifact is exactly where the bet and its kill/scale/graduate thresholds belong, so hold a PRD-Lite to C12. Those criteria demand implementation detail a PRD-Lite is not supposed to carry.

**When the input PRD is labeled as a PRD-Lite, or when an Appendix subsection explicitly defers technical-completeness or task-decomposability to a Release 1 PRD-Heavy:**

- Run the rubric as written; do not adjust the scoring.
- In the summary, present the structural fails (C5, C10, C11) as expected scope deferrals, not as defects. Surface them as "structural per PRD-Lite format" rather than as actionable failures.
- Filter the fix plan into PRD-Lite-actionable items (workflow gaps, missing baselines, scope hygiene, audit-event naming) versus PRD-Heavy demands (exact endpoints, RBAC matrices, per-feature 2-4h decomposition). Lead the user with the filtered list, not the raw rubric verdicts.
- If the PRD has no scope-deferral framing in its Appendix, suggest adding one so future reviewers do not relitigate the structural fails.

This guidance does not apply when the input PRD is positioned as engineering-ready (a Release 1 PRD-Heavy, an internal build spec, or a vendor SOW). In that case, structural fails are real defects and the rubric should be applied strictly.

## Readiness gate

- **GO**: ≥10/12 pass AND all of {C3, C5, C10, C11, C12} pass AND <3 compliance gaps
- **REVISE**: 8–9/12 pass (or any gating criterion fails but total ≥10 per the system prompt)
- **HOLD**: ≤7/12 pass OR ≥3 compliance gaps

Always emit the gate as `GO` / `REVISE` / `HOLD` (uppercase).

## References

- `references/system-prompt.md` — **read this first**. Verbatim EvalGPT system prompt with all 12 criterion definitions, pass/fail indicators, examples (including C8–C12), evaluation examples (WestREC / Spring Health / Apex Health), failure mode taxonomy, GxP overlay, scoring gates, and output mode appenders. Generated from `prompts.ts` (C12 added as a skill-local extension).
- `references/rubric.md` — quick-reference table of criteria using the `RUBRIC_CRITERIA` names from `rubric.ts` (which the frontend and API also use), plus readiness thresholds and one-line smell tests.
- `references/output-schemas.md` — verbatim JSON schemas for `BinaryScoreInput/Output`, `FixPlanInput/Output`, `AgentTasksInput/Output` dumped from `schemas.ts`. Includes conformance notes and the Mode 3 "optional vs. required" resolution.

## Presenting results

Keep summaries tight. Do not paste raw JSON unless asked.

- **Scorecard summary**: readiness gate, pass/fail count, failed gating criteria (one-line rationale each), top compliance gaps.
- **Fix plan summary**: P0 items fully (title + owner + effort), P1/P2 one-liners grouped by priority.
- **Agent tasks summary**: feature breakdown (task count + hours per feature), then total hours and task count.

Close with: "Want the full JSON, a Markdown report, or to drill into a specific criterion/fix/task?"
