---
name: patent-diagram
description: Generate USPTO patent-application-style boxes-and-lines block diagrams - monochrome line art on white, plain rectangular boxes, reference numerals on every element, dashed subsystem enclosures, a centered "FIG. N" caption, and an always-on reference-numeral legend embedded under the figure so the numeral->element mapping travels with the image when pasted into a PRD or design doc. Use this skill when asked to create a patent diagram, patent figure, invention figure, patent-style or reference-numeral diagram, or to redraw an existing architecture, pipeline, or flow diagram in patent-submission format. Outputs SVG and PNG via Graphviz.
---

# Patent Diagram

## Overview

This skill renders technical figures in the visual language of a patent
application: black line art on a white page, plain rectangular boxes joined by
thin lines, a reference numeral on every element, and a centered `FIG. N`
caption. A reference-numeral legend is always rendered as a thin-bordered
panel directly below the diagram, listing every numeral and its element name
(boxes and subsystem groups) so the mapping travels with the PNG/SVG when the
figure is pasted into a PRD, design doc, or slide. It takes a small JSON spec
describing the boxes and the lines between them and produces `.svg` and `.png`
files with `scripts/render_patent_diagram.py`.

Use it to author a patent figure from scratch, or to convert an existing
diagram (architecture, data pipeline, flowchart, system block diagram) into
patent-submission style.

## When to use

Trigger on requests such as "make a patent diagram", "patent figure", "draw
this in patent style", "boxes-and-lines diagram with reference numerals",
"invention figure", or "redraw this architecture as a patent drawing".

## Workflow

1. **Get the content.** Either the user describes the elements, or read the
   source diagram/code/doc that defines the components and how they connect.
   When converting an existing diagram, extract the real component names and
   the real connections - do not invent boxes or flows. Mark anything
   uncertain as TBD rather than fabricating it.

2. **Write a spec JSON.** Model each component as a box and each connection as
   an edge. Group related boxes into a dashed subsystem with `groups`. Let
   reference numerals auto-assign (100, 102, 104, ...) unless the user wants
   specific numbers. See `assets/example_spec.json` for a complete example and
   `references/patent_conventions.md` for the full schema and the drawing rules.

3. **Render.** Run the script:

   ```bash
   python3 scripts/render_patent_diagram.py SPEC.json --out-dir OUT --name FIGURE
   ```

   This writes `OUT/FIGURE.svg`, `OUT/FIGURE.png`, and the intermediate
   `OUT/FIGURE.dot`. Use `--format svg` or `--format png` to emit just one,
   `--dpi` to change PNG resolution, and `--print-dot` to inspect the generated
   DOT without rendering.

4. **Verify visually.** Read the rendered PNG back to confirm the layout reads
   cleanly: no overlapping boxes, numerals legible, lines not crossing through
   boxes, caption present. Adjust `rankdir` (TB vs LR), regroup boxes, or split
   into multiple figures if it is crowded, then re-render.

## Requirements

- Graphviz `dot` on PATH (`brew install graphviz`). Confirm with `dot -V`.
- The script shells out to `dot`; no Python packages are required.

## Key conventions (enforced by the renderer)

- Monochrome only: black strokes on white. Never add fill colors, gradients, or
  shadows - that breaks patent-drawing rules.
- Plain rectangles, uniform thin stroke weight, Helvetica labels.
- Reference numerals on every element; subsystems get a dashed enclosure with
  its own numeral.
- A reference-numeral legend is always rendered directly under the diagram
  (above the `FIG. N` caption), so the numeral->element mapping ships with the
  PNG/SVG when the figure is pasted into a PRD or design doc. Subsystem
  entries are tagged `(subsystem)`.
- Keep box text terse (a noun phrase). Detail belongs in the patent
  specification text, not inside the box.

Full rules, the numbering scheme, and the complete spec schema are in
`references/patent_conventions.md`.
