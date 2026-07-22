# EvalPRD Rubric — Quick Reference

Names and gating flags below are generated from `RUBRIC_CRITERIA` in `api-gateway/src/lib/rubric.ts` (the authoritative source used by the hosted service and the frontend). The longer definition labels in `references/system-prompt.md` (e.g., "Business Problem Clarity and Justification" for C1) come from `rubric-definitions.ts`; both are in use and mean the same criterion.

**C12 (Falsifiable Bet & Decision Thresholds) is a skill-local extension added by hand.** It is not yet in the authoritative `rubric.ts`, so this skill runs 12 criteria while the hosted service runs 11. Reconcile by porting C12 into `rubric.ts` + `rubric-definitions.ts` if the product should match.

## Criteria

| ID | Name (rubric.ts) | Short | Gating |
|----|------------------|-------|--------|
| C1 | Business Problem Clarity | Problem Clarity | — |
| C2 | Current Process Documentation | Current Process | — |
| C3 | Solution–Problem Alignment | Solution Alignment | ✅ |
| C4 | Narrative Clarity & Plain Language | Clarity | — |
| C5 | Technical Requirements Completeness | Tech Requirements | ✅ |
| C6 | Feature Specificity & Implementation Clarity | Feature Specificity | — |
| C7 | Measurability & Success Criteria | Measurability | — |
| C8 | Consistent Formatting & Structure | Formatting | — |
| C9 | Scope Discipline (Anti-Explosion) | Scope Discipline | — |
| C10 | AI Agent Readiness & Implementability | Eng Readiness | ✅ |
| C11 | AI Agent Task Decomposability | Agent Decomposability | ✅ |
| C12 | Falsifiable Bet & Decision Thresholds | Bet & Thresholds | ✅ |

Gating criteria: **C3, C5, C10, C11, C12**. All five must PASS for a GO readiness gate.

## Readiness gate thresholds

From `READINESS_THRESHOLDS` in `rubric.ts`:

- `GO_MIN_PASS = 10` — GO requires ≥10/12 pass AND all gating pass AND <3 compliance gaps
- `REVISE_MIN_PASS = 8` — 8–9/12 pass = REVISE (also REVISE if any gating fails but total ≥10, per system prompt)
- `HOLD_MAX_PASS = 7` — ≤7/12 pass = HOLD
- `HOLD_COMPLIANCE_GAPS = 3` — ≥3 compliance gaps = HOLD

## One-line smell tests (fast triage)

- **C1**: Does the problem statement quantify impact ($, time, error rate)? If no — FAIL.
- **C2**: Can you reconstruct the current workflow from the PRD alone? If no — FAIL.
- **C3**: Does every feature trace to a stated pain point? Any orphaned feature — FAIL.
- **C4**: Is "leverage", "robust", "seamless", "holistic" load-bearing? — FAIL.
- **C5**: Are integrations named with auth method, endpoints, and failure behavior? If not — FAIL.
- **C6**: Can you tell what "done" looks like for each feature without asking questions? If not — FAIL.
- **C7**: Are success metrics measurable in-system (not survey-based)? If not — FAIL.
- **C8**: Template order (Problem → Current → Description → Features → Tech → Measurement → Appendix)? If not — FAIL.
- **C9**: Any "future versions might…" or "could also…" phrases? — FAIL.
- **C10**: Could an engineer build this from the PRD alone (with standard external API docs)? If not — FAIL.
- **C11**: Can an AI agent decompose each feature into 2–4h tasks without human judgment? If not — FAIL.
- **C12**: Is the investment a falsifiable bet (if/then/by-when/metric) with explicit kill, scale, and graduate thresholds? If not — FAIL.

For full criterion definitions with pass/fail indicators and worked examples, see `system-prompt.md`.
