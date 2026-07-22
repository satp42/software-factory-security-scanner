---
name: evidence-gated-exhibit
description: "Build or revise a numeric HTML exhibit deliverable (pricing pages, cost scenarios, business-case exhibits) with a verification model and a no-mistakes ship gate. Use when creating or editing any deliverable where dollar figures, percentages, or derived metrics appear on a page leadership will read. Triggers: cost scenarios, pricing page, business case exhibit, update the numbers on the page."
---

# Evidence-Gated Exhibit

A numeric deliverable ships only when every figure on it is reproduced by a script and a blocking gate passes. Pattern extracted from the Dompé BC1 cost-scenarios work (June 2026), where it survived six full rebuilds without a stale or unsourced number reaching the reader.

## Success Criteria

1. Every dollar figure, percentage, and derived metric on the page is printed by the verification model script; no number exists only in HTML.
2. Every input carries a provenance tag: [REPO] (documented in source files, cited), [MEETING] (stated, not derived), [RESEARCH] (adversarially verified, dated), [POLICY] (modeling choice, stated and contestable), [DERIVED] (computed from tagged inputs).
3. The ship gate exits 0 before the deliverable is presented; a blocked gate is fixed, never bypassed.
4. Superseded figures are either removed or marked with explicit supersession language; the gate blocks them elsewhere.
5. Value anchors are cross-checked against every documented basis in the repo; conflicts are presented dual-anchor, never silently resolved.

## The three artifacts

1. **The model script** (`scratch/<name>_model.py`): all inputs as tagged constants, all derivations as code, prints every figure that will appear on the page. Date/random calls forbidden (reproducibility).
2. **The page** (HTML): displays only script-reproduced figures; provenance tags inline; working-papers content fenced from presented content.
3. **The gate** (`scratch/deck_gate.py`): blocking checks grouped by gate — render integrity (tag balance), figure reproduction (page needle must appear in model output), stale-content blocks, structure checks (required sections present), provenance discipline, compliance markings, doctrine checks specific to the artifact.

## Workflow

1. Compute first: add or change figures in the model script, run it, read the output.
2. Edit the page using only printed figures.
3. Update gate needles in the same change (new figures added, old figures moved to stale checks with supersession-context allowances).
4. Run the gate; fix blocks; re-run to exit 0.
5. Open in browser for the visual pass.

## Gate-needle rules (learned the hard way)

- Write needles context-aware at creation: a superseded figure may legitimately appear in a disclosure sentence ("revised down from X"); use negative-lookahead or context checks, not bare substring blocks.
- Skip code identifiers and CSS class names when scanning prose for banned terms.
- When a checked phrase is reworded for style, update the needle in the same commit; never let the gate and page drift.

## Pre-Delivery Verification

Before presenting: (1) model script runs clean and prints every page figure; (2) gate exits 0; (3) tag balance passes; (4) any anchor conflict is shown dual-anchor on the page; (5) the page opened in a browser at least once since the last edit. If any fails, fix and re-run; iterate up to 3 times, then surface the gap rather than ship.
