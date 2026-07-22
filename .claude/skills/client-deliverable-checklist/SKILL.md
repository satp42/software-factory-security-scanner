---
name: client-deliverable-checklist
description: "Pre-send checklist for any client-facing deliverable (docx, pdf, pptx, email, status report). Picks the right verify pipeline for the output format and runs the audience-appropriate language check. Use BEFORE sending any artifact to a client."
allowed-tools:
  - Bash
  - Read
  - Edit
  - Glob
  - Agent
---

# client-deliverable-checklist

One-shot pre-send gate for client-facing artifacts. Combines the docx/pdf verify rules from CLAUDE.md with audience-appropriate language checks.

## When to use

Before sending ANY of:
- Status reports (dompe-status, cse-status-update, status-report skills)
- PRDs (prd-writer, prd-eval skills)
- Demo prep docs (r2d2-demo)
- One-pagers, briefs, or emails to clients
- Workshop materials, agendas, or session plans

## Phase 1: Format-specific verification

### `.docx`
1. Run `~/.claude/skills/docx-build-verify/scripts/verify.sh <generator.js>`
2. Inspect at least page-1.jpg
3. Confirm page count matches target

### `.pdf` (direct, not from docx)
```bash
pdftoppm -jpeg -r 150 <file>.pdf <dir>/page
ls <dir>/page-*.jpg | wc -l
```
Read at least page-1.jpg. CLAUDE.md: "Never present a PDF without first running pdftoppm and inspecting".

### `.pptx`
- Convert to images via `soffice --headless --convert-to png` per slide
- Or open in browser and screenshot via Playwright
- Verify all charts rendered (esp. proportionally-sized bar charts)

### Email/Markdown
- Run through `humanizer` skill if AI-generated tone risk
- Check for "we"/"our" if you're an external consultant

## Phase 2: Audience language check

CLAUDE.md learning: *"Ask about audience before choosing language. If shared externally, no 'bugs', 'regressions', 'our mistakes.'"*

Run a grep for forbidden terms in client-facing artifacts:
```bash
grep -in -E '\b(bug|bugs|regression|regressions|our mistake|our fault|broken|failed|broke|hack|workaround|todo|fixme|wtf)\b' <file>
```

If hits found:
- "bug" → "issue", "behavior"
- "regression" → "change in behavior"
- "our mistake" → "the previous version" or omit
- "broken" → "non-functional" or "needs adjustment"
- "TODO/FIXME" → remove entirely (these don't belong in client docs)

## Phase 3: Date/data integrity

- All dates absolute, not relative ("Q2 2026" not "next quarter")
- All metrics double-checked against a longer historical window (CLAUDE.md: "verify against a longer historical window before presenting" — anomalous baselines inflate dramatic changes)
- Charts proportionally sized to data (CLAUDE.md: "bar chart height = base + N×per-bar height")

## Phase 4: Final visual review

Use the `client-deliverable-reviewer` subagent for a fresh-eyes pass on:
- Visual consistency
- Hierarchy
- AI-slop patterns (per `humanizer` skill)

## Phase 5: Confirmation

NEVER auto-send. Always show the user:
1. Final artifact path
2. Audience (who's this going to)
3. Format
4. Page/slide count
5. One-line summary

User explicitly confirms before send.
