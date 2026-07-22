# Patent Drawing Conventions and Spec Schema

Reference material for producing patent-application-style block diagrams.
Loaded as needed; the renderer (`scripts/render_patent_diagram.py`) already
enforces the visual rules, so this file mainly governs *content* decisions and
documents the JSON spec.

## Visual rules (USPTO / informal-drawing practice)

These are baked into the renderer. Do not override them with inline color or
fills.

- **Monochrome line art.** Black strokes on a white background. No fill colors,
  no gray shading, no gradients, no drop shadows. Color and grayscale photos
  are accepted only by exception; line drawings are the default and the safe
  choice.
- **Uniform stroke weight.** Every box and line uses the same thin weight.
- **Plain rectangles** with square corners for components. Lines (straight,
  orthogonal) connect them.
- **Arrowheads** indicate direction of flow or signal. Use a plain undirected
  line (`"arrow": false`) for a purely structural association.
- **Sans-serif label text** (Helvetica/Arial), kept short.
- **One figure per logical view.** If a drawing gets crowded, split it into
  `FIG. 1`, `FIG. 2`, ... rather than cramming everything in.

## Reference numerals

- Every distinct element shown in a figure carries a reference numeral. The
  same element keeps the same numeral across all figures.
- Numerals are conventionally assigned in **even increments** so odd numbers
  remain free to insert later: 100, 102, 104, 106, ... A two-digit scheme
  (10, 12, 14, ...) is also common. Pick a hundreds band per figure or per
  subsystem if helpful (figure 1 -> 1xx, figure 2 -> 2xx).
- The renderer auto-assigns numerals to any box or group that lacks an explicit
  `ref`, starting from `numbering.start` (default 100) in steps of
  `numbering.step` (default 2), in document order. Provide an explicit `ref`
  on a box to pin it (e.g. to keep a component's numeral stable across figures).
- A subsystem (group) gets its own numeral, distinct from its members.

## Reference-numeral legend

The renderer always draws a numeral-to-element legend below the diagram, in
the same monochrome line-art style: a thin rectangular border, two columns
(numeral on the left, element name on the right), entries sorted numerically.
Group/subsystem rows are tagged `(subsystem)` so they read distinctly from
component rows.

This is non-standard for a strict USPTO filing (in a filing the numeral list
lives in the written specification, not on the drawing). It is on by design
for the practical case this skill is used for: pasting the PNG/SVG into a PRD,
design doc, or slide where the mapping needs to travel with the image. If you
ever need a filing-pure version, strip the legend out of the SVG by hand or
re-render after deleting it from the generated DOT.

The legend is built automatically from the boxes and groups in the spec; there
is no field to configure. To omit an element from the legend, omit it from the
spec.

## Content rules

- Box text is a terse noun phrase naming the element ("CLAIMS DATA STORE",
  "SCORING MODULE"). Verbs, metrics, and explanation belong in the written
  patent specification, not inside the box.
- When converting an existing diagram, use the real component names and the
  real connections. Do not invent elements. If a connection or a name is
  unclear in the source, mark it TBD and ask rather than guessing.
- ALL-CAPS labels read as conventional patent style but are optional.

## JSON spec schema

```json
{
  "fig_number": "1",
  "title": "OPTIONAL SMALL LINE UNDER THE FIG CAPTION",
  "rankdir": "TB",
  "numbering": { "start": 100, "step": 2 },
  "numeral_style": "inside",
  "boxes": [
    { "id": "a", "label": "FIRST COMPONENT", "ref": "102" },
    { "id": "b", "label": "SECOND\nCOMPONENT" }
  ],
  "groups": [
    { "id": "sub", "label": "SUBSYSTEM", "ref": "120", "members": ["a", "b"] }
  ],
  "edges": [
    { "from": "a", "to": "b" },
    { "from": "b", "to": "c", "arrow": false },
    { "from": "c", "to": "d", "label": "result", "style": "dashed" }
  ]
}
```

### Fields

| Field | Where | Meaning |
|-------|-------|---------|
| `fig_number` | top | Renders as the centered `FIG. N` caption. Omit for no caption. |
| `title` | top | Optional small line under the caption. Keep it short. |
| `rankdir` | top | `TB` (top-to-bottom, default) or `LR` (left-to-right). |
| `numbering.start` / `.step` | top | Base and increment for auto-assigned numerals. |
| `numeral_style` | top | `inside` (numeral on its own line inside the box, default) or `outside` (numeral floated beside the box as an xlabel). |
| `boxes[].id` | box | Unique node id, referenced by edges and group members. |
| `boxes[].label` | box | Display text; `\n` becomes a line break. |
| `boxes[].ref` | box | Explicit reference numeral; omit to auto-assign. |
| `groups[].members` | group | Box ids enclosed in the dashed subsystem. |
| `edges[].from` / `.to` | edge | Box ids to connect. |
| `edges[].arrow` | edge | `true` (arrowhead, default) or `false` (plain line). |
| `edges[].label` | edge | Optional text on the line. |
| `edges[].style` | edge | Optional `dashed` / `dotted` for the line. |

### Notes on `numeral_style`

- `inside` is the most legible for software/system block diagrams and is the
  default.
- `outside` mimics the classic patent look of a numeral floating next to the
  element. Graphviz places the xlabel automatically and does **not** draw a
  lead line to the element; lead lines are not auto-generated. If true lead
  lines are required, that is a manual SVG edit after rendering.

## Rendering

```bash
python3 scripts/render_patent_diagram.py SPEC.json --out-dir OUT --name FIGURE
# options: --format svg,png   --dpi 220   --print-dot
```

After rendering, open the PNG and check for overlaps, illegible numerals, and
lines routed through boxes. Fix by changing `rankdir`, regrouping, shortening
labels, or splitting into multiple figures.
