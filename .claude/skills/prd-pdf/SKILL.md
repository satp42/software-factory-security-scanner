---
name: prd-pdf
description: "Render a polished, presentation-quality PDF (and styled .docx) from a markdown PRD using the 8090 house style and the DOCX pipeline (pandoc, python-docx styling, LibreOffice, pdftoppm verify). Use when asked for a polished PDF of a PRD or similar long markdown document, or when a generated PDF looks misaligned or whitespace-heavy. Never use a Chrome/HTML/CSS-to-PDF pipeline for these."
---

# prd-pdf — polished PRD PDF via the 8090 DOCX pipeline

Markdown PRDs render best as a **DOCX**, not as Chrome+HTML+CSS. The flagship example is PackPilot
(`~/projects/packpilot/deliverables/PackPilot-PRD.pdf`, produced by
`~/projects/packpilot/PRD/process/pipeline.py` `format_docx`). This skill distills that into a reusable
styler. Chrome/CSS for these documents produces misaligned tables, clipped cells, and sparse whitespace-heavy
pages; do not use it.

## Success Criteria

A rendered PDF is acceptable only if ALL hold, confirmed by page-image inspection (not assumption):
1. Every ASCII/code block stays monospace and does not wrap (box borders contiguous).
2. Every table fits the text column with cell text wrapped, not clipped (no lost characters at the right edge).
3. No sparse/half-empty pages (natural flow, not break-before-every-heading); running header + page numbers present.
4. Every figure fills the text column and is not clipped or blurry.
5. No content that must stay out of the body (e.g., pricing) appears in the rendered PDF.

## Pipeline

1. **Print copy.** Copy the source markdown to a scratch copy. Inject any bundle figures as Markdown images
   with an **absolute** path at the right heading. Add a cover subtitle line (`Product Requirements Document`)
   and a version line (`Version X | DATE | 8090.inc`) right after the `# Title` so the styler can center them.
2. **pandoc** the print copy to `.docx` (structure only): `pandoc copy.md -o out.docx`. Skip `--toc` unless you
   build a PAGEREF-based TOC (pandoc's SDT TOC renders empty under headless LibreOffice).
3. **Style** with `scripts/style_prd_docx.py out.docx --title ... --subtitle ... --version ... --header ...`.
4. **LibreOffice** to PDF: `soffice --headless --convert-to pdf out.docx --outdir DIR`.
5. **Verify** with `pdftoppm -jpeg -r 100` and inspect page images: cover, a prose page, every ASCII-diagram
   page (must stay monospace and not wrap), the widest table (cell text wrapped, not clipped), figures
   (fill the column), running header + page numbers present, and no sparse/half-empty pages.

Preflight first: `pandoc`, `python3 -c "import docx"`, `soffice`, `pdftoppm`, IBM Plex Mono font, and any
figure PNG must exist.

## House style (from PackPilot `format_docx`, encoded in `scripts/style_prd_docx.py`)

- One typeface everywhere: **IBM Plex Mono**, locked at rFonts ascii/hAnsi/cs (a final pass over every run, not
  just styles, because pandoc emits direct run fonts).
- Colors: navy `#003366` (H1/H2, table-header fill, running header); `#333`/`#555`/`#666` grays.
- Body 10.5pt, line-spacing 1.08; H1 20 / H2 16 / H3 12 / H4 11 pt; heading space-before H1 36, H2 24.
- Letter, 1-inch margins. Running header (project + version, 8pt navy left); footer page-number (right tab).
- Cover: the single `#` H1 is the title (24pt navy bold centered); the subtitle and version lines centered gray.

## The two highest-leverage rules (these fix "misaligned / too much whitespace")

1. **Selective page breaks, not break-before-every-heading.** Default to **natural flow** with
   `keep_with_next` on heading styles; for short docs add only one break that separates the cover/front matter
   from the body. Forcing a page break before every section is what creates sparse, whitespace-heavy pages.
2. **Normalize every image and table to the fixed text column.** Images scale to the 6.5-inch column (down if
   oversized, cap 8 inches tall). Tables use `tblLayout=fixed` with **content-proportional column widths**
   (wide columns for long-text cells), a navy header row (`w:shd val=clear fill=003366`, white bold), 8pt body
   for many-column tables, `cantSplit` rows and a repeating `tblHeader`. LibreOffice then wraps cell text
   within the fixed widths so nothing clips. Do NOT rotate wide tables to landscape via python-docx (brittle:
   the orientation leaks to surrounding text).

The other regression to watch: pandoc styles fenced code blocks as `Source Code` / `Verbatim Char`, separate
from body. Force those to **8pt mono on the style and every run** or 70-column ASCII diagrams wrap and break.

## Reference

- Canonical implementation: `~/projects/packpilot/PRD/process/pipeline.py` (`format_docx`, the proven XML for
  rFonts, table shading, image-EMU normalization, PAGEREF TOC, header/footer PAGE field).
- The reusable styler here: `scripts/style_prd_docx.py`.

## Pre-Delivery Verification

Before presenting the PDF, page-image inspect it (`pdftoppm -jpeg -r 100`) and confirm every Success Criterion
above against the real pages: the cover, a prose page, EVERY ASCII-diagram page, the widest table, and each
figure. Also `pdftotext | grep` for any content that must stay out of the body. If any criterion fails, fix the
styler and re-render; iterate up to 3 times. Never claim "verified" from a partial check.
