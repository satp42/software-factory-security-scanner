---
name: docx-build-verify
description: "Build and verify a docx-js generated Word document end-to-end: run the Node generator, convert to PDF via LibreOffice, extract page images with pdftoppm, and report page count with visual confirmation. Use when generating any .docx from a Node script. Never present a PDF without pdftoppm inspection."
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
---

# docx-build-verify

End-to-end build + verify pipeline for docx-js Word documents.

## When to use

Invoke whenever you (or the user) generate a `.docx` file via a Node script. Triggers:
- "generate the doc", "build the report", "create the docx"
- After editing any `generate-*.js` or `*-docx.js` script
- Before presenting any generated PDF to the user

## Success Criteria

A build is successful only if ALL are true:
1. Page count matches the requested target exactly.
2. Every page image extracted by pdftoppm has been read and visually inspected (not just page 1 for multi-page docs).
3. Fonts are at or above the requested minimum readable size.
4. All fixes (sizing, spacing, content) were batched into one rebuild round, not iterated one-per-round.

## Pipeline (run in this order)

```bash
# 1. Build .docx with global node_modules on path
NODE_PATH=$(npm root -g) node <generator-script>.js

# 2. Convert to PDF via LibreOffice headless
soffice --headless --convert-to pdf <output>.docx --outdir <dir>

# 3. Extract page images (150 DPI) for visual inspection
pdftoppm -jpeg -r 150 <output>.pdf <dir>/page

# 4. Count pages and report
ls <dir>/page-*.jpg | wc -l
```

## Critical rules from CLAUDE.md

1. **Font sizes are half-points** — `size: 20` = 10pt, `size: 24` = 12pt, `size: 28` = 14pt
2. **Page measurements use DXA** — 1440 DXA = 1 inch; US Letter = 12240 DXA wide
3. **Table cell shading**: use `ShadingType.CLEAR` (NOT SOLID) for colored backgrounds
4. **Page-fitting strategy**: tighten margins first (top/bottom 504→360→288 DXA, sides 720→576), then reduce fonts 2 half-points at a time
5. **Session/cell descriptions**: 140 chars max — concise plain English, no jargon
6. **Centralized color palette**: define a `CLR = { navy, slate, white, ... }` object
7. **Unicode chars**: `—` em dash, `–` en dash, `·` middle dot, `’` right quote
8. **Use continuous section flow** (no forced page breaks) to eliminate whitespace
9. **Two-paragraph table cells** work well: bold title paragraph + smaller gray description
10. **Full-width break rows**: use `columnSpan` to make a row span all table columns

## Verification gate

**Never** present a generated PDF to the user without first:
1. Running `pdftoppm` to extract images
2. Reading at least the first page image with the Read tool
3. Confirming page count matches the requested target

If page count is wrong: tighten margins → reduce font sizes → re-run pipeline. Batch all fixes in one round (per CLAUDE.md learning: "batch build+verify into one step").

## Helper script

Use `scripts/verify.sh` (in this skill) as a one-shot pipeline:

```bash
bash ~/.claude/skills/docx-build-verify/scripts/verify.sh <generator.js> <output-dir>
```

## Common failure modes

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Cannot find module 'docx'` | Missing NODE_PATH | Prefix command with `NODE_PATH=$(npm root -g)` |
| `soffice: command not found` | LibreOffice not installed | `brew install --cask libreoffice` |
| Page count too high | Margins too wide / fonts too big | Reduce per the page-fitting strategy above |
| Colored cells render white | Used `ShadingType.SOLID` | Switch to `ShadingType.CLEAR` |
| Special chars rendered as `?` | Missing Unicode escape | Use `—` etc. in source strings |
