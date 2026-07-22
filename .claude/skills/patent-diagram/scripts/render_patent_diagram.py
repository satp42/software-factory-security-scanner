#!/usr/bin/env python3
"""Render a USPTO-style patent figure (boxes-and-lines block diagram) from a
JSON spec using Graphviz `dot`.

Patent drawing conventions enforced here:
  - Monochrome line art: black strokes on a white background, no fills, no
    color, no shadows, no gradients.
  - Plain rectangular boxes (square corners), uniform thin stroke weight.
  - Every element carries a reference numeral. Numerals are auto-assigned in
    even increments (100, 102, 104, ...) unless given explicitly per box.
  - Subsystems are drawn as dashed enclosures with their own numeral.
  - A centered "FIG. N" caption sits below the drawing.

Spec schema (JSON):
{
  "fig_number": "1",                      # caption -> "FIG. 1"
  "title": "MEDICAID FRAUD DETECTION",    # optional small line under FIG. N
  "rankdir": "TB",                        # TB | LR  (default TB)
  "numbering": {"start": 100, "step": 2}, # auto-numeral base (optional)
  "numeral_style": "inside",              # inside | outside (default inside)
  "boxes": [
     {"id": "csv", "label": "CLAIMS DATA STORE", "ref": "102"},
     {"id": "duck", "label": "ANALYTICAL\nDATA HUB"}        # ref auto-assigned
  ],
  "groups": [                             # optional dashed subsystem enclosures
     {"id": "det", "label": "PARALLEL DETECTION ENGINE",
      "ref": "120", "members": ["stat", "temp"]}
  ],
  "edges": [
     {"from": "csv", "to": "duck"},                  # arrowed line (default)
     {"from": "a", "to": "b", "arrow": false},       # plain undirected line
     {"from": "x", "to": "y", "label": "scored"}     # labeled line
  ]
}

Usage:
  render_patent_diagram.py spec.json [--out-dir DIR] [--name NAME]
                           [--format svg,png] [--dpi 220]

Requires: graphviz `dot` on PATH.
"""

import argparse
import json
import os
import subprocess
import sys

# --- patent stylesheet ------------------------------------------------------
INK = "black"
PAPER = "white"
FONT = "Helvetica"          # modern e-filed patents use Arial/Helvetica
STROKE = "1.4"              # uniform line weight
NUM_SIZE = "11"             # reference-numeral point size
LABEL_SIZE = "13"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def br(label):
    """Convert newlines in a label to centered HTML line breaks."""
    parts = [esc(p) for p in str(label).split("\n")]
    return '<BR/>'.join(parts)


def _ref_sort_key(ref):
    """Sort numeric reference numerals as ints; fall back to string order."""
    s = str(ref)
    return (0, int(s)) if s.isdigit() else (1, s)


def legend_table_html(boxes, groups, refs):
    """Build the inner HTML <TABLE> for the reference-numeral legend.

    Always rendered (PRD/internal-doc use). Returns "" if there are no
    numerals. The result is meant to be embedded inside the figure's bottom
    label so it travels with the PNG/SVG and sits right above the caption
    instead of in its own ranked subgraph (which creates a huge gap).
    """
    entries = []
    for b in boxes:
        ref = refs.get(b["id"])
        if ref is not None:
            label = str(b.get("label", "")).replace("\n", " ")
            entries.append((ref, label, "element"))
    for g in groups:
        ref = refs.get(g["id"])
        if ref is not None:
            label = str(g.get("label", "")).replace("\n", " ")
            entries.append((ref, label, "subsystem"))
    if not entries:
        return ""
    entries.sort(key=lambda e: _ref_sort_key(e[0]))

    rows = [
        '<TR>'
        f'<TD COLSPAN="2" ALIGN="CENTER" CELLPADDING="6">'
        f'<FONT FACE="{FONT}" POINT-SIZE="11"><B>REFERENCE NUMERALS</B></FONT>'
        '</TD></TR>'
    ]
    for ref, label, kind in entries:
        tag = " (subsystem)" if kind == "subsystem" else ""
        rows.append(
            '<TR>'
            f'<TD ALIGN="RIGHT" VALIGN="TOP"><FONT FACE="{FONT}" POINT-SIZE="10">{esc(ref)}</FONT></TD>'
            f'<TD ALIGN="LEFT" VALIGN="TOP"><FONT FACE="{FONT}" POINT-SIZE="10">{esc(label)}{esc(tag)}</FONT></TD>'
            '</TR>'
        )
    return (
        '<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3">'
        + "".join(rows)
        + '</TABLE>'
    )


def box_label(label, ref, numeral_style):
    """HTML-like node label: component name, with the reference numeral on its
    own line below (inside style). For outside style the numeral is emitted via
    an xlabel instead, so only the name goes here."""
    name = (f'<FONT FACE="{FONT}" POINT-SIZE="{LABEL_SIZE}">{br(label)}</FONT>')
    if numeral_style == "outside" or ref is None:
        return f'<{name}>'
    num = (f'<FONT FACE="{FONT}" POINT-SIZE="{NUM_SIZE}">{esc(ref)}</FONT>')
    return ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
            f'<TR><TD>{name}</TD></TR>'
            f'<TR><TD>{num}</TD></TR></TABLE>>')


def build_dot(spec):
    rankdir = spec.get("rankdir", "TB")
    numeral_style = spec.get("numeral_style", "inside")
    numbering = spec.get("numbering", {})
    nxt = int(numbering.get("start", 100))
    step = int(numbering.get("step", 2))

    boxes = spec.get("boxes", [])
    groups = spec.get("groups", [])
    edges = spec.get("edges", [])

    # Assign reference numerals to any box/group missing one, in document order.
    refs = {}
    for b in boxes:
        if b.get("ref") is not None:
            refs[b["id"]] = str(b["ref"])
    for g in groups:
        if g.get("ref") is not None:
            refs[g["id"]] = str(g["ref"])
    for b in boxes:
        if b["id"] not in refs:
            refs[b["id"]] = str(nxt)
            nxt += step
    for g in groups:
        if g["id"] not in refs:
            refs[g["id"]] = str(nxt)
            nxt += step

    member_of = {}
    for g in groups:
        for m in g.get("members", []):
            member_of[m] = g["id"]

    # Bottom block: reference-numeral legend, then "FIG. N", then optional
    # title. All packed into the single graph-level label so they render as one
    # group below the diagram (avoids the rank-gap whitespace that a separate
    # sink-ranked node introduces).
    bottom_rows = []
    legend_html = legend_table_html(boxes, groups, refs)
    if legend_html:
        bottom_rows.append(f'<TR><TD>{legend_html}</TD></TR>')
        bottom_rows.append('<TR><TD HEIGHT="14"></TD></TR>')  # spacer
    fig = spec.get("fig_number")
    if fig is not None:
        bottom_rows.append(
            f'<TR><TD><FONT FACE="{FONT}" POINT-SIZE="20"><B>FIG.&nbsp;{esc(fig)}</B></FONT></TD></TR>'
        )
    if spec.get("title"):
        bottom_rows.append(
            f'<TR><TD><FONT FACE="{FONT}" POINT-SIZE="11">{br(spec["title"])}</FONT></TD></TR>'
        )
    caption = ""
    if bottom_rows:
        caption = (
            '  label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
            + "".join(bottom_rows)
            + '</TABLE>>;\n'
            '  labelloc=b; labeljust=c; fontname="' + FONT + '";\n'
        )

    out = []
    out.append("digraph patent {")
    out.append(f'  bgcolor="{PAPER}";')
    out.append(f'  rankdir={rankdir}; splines=ortho; compound=true; forcelabels=true;')
    out.append("  nodesep=0.45; ranksep=0.6; pad=0.4;")
    out.append(caption.rstrip("\n") if caption else "")
    out.append(f'  node [shape=box, style="", color="{INK}", fontcolor="{INK}", '
               f'penwidth={STROKE}, fontname="{FONT}", margin="0.24,0.15"];')
    out.append(f'  edge [color="{INK}", penwidth={STROKE}, arrowsize=0.8, '
               f'fontname="{FONT}", fontsize=10, fontcolor="{INK}"];')

    def emit_node(b, indent="  "):
        nid = b["id"]
        ref = refs.get(nid)
        attrs = [f'label={box_label(b["label"], ref, numeral_style)}']
        if numeral_style == "outside" and ref is not None:
            attrs.append(f'xlabel=<<FONT FACE="{FONT}" POINT-SIZE="{NUM_SIZE}">{esc(ref)}</FONT>>')
        out.append(f'{indent}{nid} [{", ".join(attrs)}];')

    # grouped nodes -> dashed cluster enclosures with their own numeral
    for g in groups:
        gid = g["id"]
        gref = refs.get(gid)
        glabel = esc(g.get("label", ""))
        if gref is not None:
            glabel = f'{glabel}  {esc(gref)}'
        out.append(f'  subgraph cluster_{gid} {{')
        out.append(f'    style=dashed; color="{INK}"; penwidth={STROKE};')
        out.append(f'    label=<<FONT FACE="{FONT}" POINT-SIZE="11"><B>{glabel}</B></FONT>>;')
        out.append(f'    labelloc=t; labeljust=l; margin=14; fontname="{FONT}";')
        for b in boxes:
            if member_of.get(b["id"]) == gid:
                emit_node(b, indent="    ")
        out.append("  }")

    # ungrouped nodes
    for b in boxes:
        if b["id"] not in member_of:
            emit_node(b)

    # edges
    for e in edges:
        attrs = []
        if e.get("arrow", True) is False:
            attrs.append("dir=none")
        else:
            attrs.append("arrowhead=vee")
        if e.get("label"):
            # xlabel (not label) so labels survive orthogonal edge routing
            attrs.append(f'xlabel=" {esc(e["label"])} "')
        if e.get("style"):
            attrs.append(f'style={e["style"]}')
        suffix = f' [{", ".join(attrs)}]' if attrs else ""
        out.append(f'  {e["from"]} -> {e["to"]}{suffix};')

    out.append("}")
    return "\n".join(l for l in out if l != "") + "\n"


def render(dot_src, out_dir, name, formats, dpi):
    os.makedirs(out_dir, exist_ok=True)
    dot_path = os.path.join(out_dir, name + ".dot")
    with open(dot_path, "w") as f:
        f.write(dot_src)
    written = [dot_path]
    for fmt in formats:
        out_path = os.path.join(out_dir, f"{name}.{fmt}")
        cmd = ["dot", f"-T{fmt}", dot_path, "-o", out_path]
        if fmt == "png":
            cmd.insert(1, f"-Gdpi={dpi}")
        subprocess.run(cmd, check=True)
        written.append(out_path)
    return written


def main():
    ap = argparse.ArgumentParser(description="Render a patent-style boxes-and-lines figure.")
    ap.add_argument("spec", help="path to JSON spec")
    ap.add_argument("--out-dir", default=".", help="output directory (default: cwd)")
    ap.add_argument("--name", default=None, help="output basename (default: spec filename)")
    ap.add_argument("--format", default="svg,png", help="comma list: svg,png (default both)")
    ap.add_argument("--dpi", type=int, default=220, help="PNG resolution (default 220)")
    ap.add_argument("--print-dot", action="store_true", help="print generated DOT and exit")
    args = ap.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    dot_src = build_dot(spec)
    if args.print_dot:
        sys.stdout.write(dot_src)
        return

    name = args.name or os.path.splitext(os.path.basename(args.spec))[0]
    formats = [x.strip() for x in args.format.split(",") if x.strip()]
    written = render(dot_src, args.out_dir, name, formats, args.dpi)
    for p in written:
        print("wrote", p)


if __name__ == "__main__":
    main()
