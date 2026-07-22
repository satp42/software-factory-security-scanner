#!/usr/bin/env node
// CEO Status Update .docx Generator for Dompe Document Authoring Hub
// Usage: NODE_PATH=$(npm root -g) node generate_report.js <config.json> [output.docx]
//
// config.json schema: see references/report-format.md

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, UnderlineType,
  TableLayoutType, VerticalAlign, convertInchesToTwip
} = require("docx");
const fs = require("fs");
const path = require("path");

// ── Load config ────────────────────────────────────────────────
const configPath = process.argv[2];
if (!configPath) {
  console.error("Usage: node generate_report.js <config.json> [output.docx]");
  process.exit(1);
}
const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));
const outPath = process.argv[3] || path.join(path.dirname(configPath),
  `CEO_Status_Update_${cfg.date.replace(/,?\s+/g, "").replace(/\//g, "")}.docx`);

// ── Color palette ──────────────────────────────────────────────
const CLR = {
  navy:      "1F3864",
  white:     "FFFFFF",
  black:     "000000",
  lightGray: "EFEFEF",
  green:     "C6EFCE",
  greenText: "006100",
  yellow:    "FFEB9C",
  yellowTxt: "9C6500",
  red:       "FFC7CE",
  redText:   "9C0006",
  teal:      "2E75B6",
};

// ── Helpers ────────────────────────────────────────────────────
const FONT = "Aptos";
const sz = (pts) => pts * 2;

function txt(text, opts = {}) {
  return new TextRun({
    text,
    font: FONT,
    size: sz(opts.size || 11),
    bold: opts.bold || false,
    italics: opts.italics || false,
    color: opts.color || CLR.black,
    underline: opts.underline ? { type: UnderlineType.SINGLE } : undefined,
  });
}

function bullet(runs, indent = 360) {
  return new Paragraph({
    children: Array.isArray(runs) ? runs : [runs],
    bullet: { level: 0 },
    spacing: { before: 40, after: 40 },
    indent: { left: indent },
  });
}

function sectionHeader(text) {
  return new Paragraph({
    children: [txt(text, { bold: true, size: 13, color: CLR.navy })],
    spacing: { before: 200, after: 80 },
  });
}

function subHeader(text, opts = {}) {
  return new Paragraph({
    children: [txt(text, { bold: true, size: 11, color: opts.color || CLR.teal, italics: opts.italics })],
    spacing: { before: 120, after: 60 },
  });
}

function bodyText(runs, opts = {}) {
  return new Paragraph({
    children: Array.isArray(runs) ? runs : [runs],
    spacing: { before: opts.before || 40, after: opts.after || 40 },
  });
}

const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "AAAAAA" };
const thickBorder = { style: BorderStyle.SINGLE, size: 2, color: CLR.black };

function cell(content, opts = {}) {
  const children = Array.isArray(content) ? content : [
    new Paragraph({
      children: [txt(content, {
        size: opts.fontSize || 10,
        bold: opts.bold || false,
        color: opts.fontColor || CLR.black,
      })],
      alignment: opts.align || AlignmentType.LEFT,
    })
  ];
  return new TableCell({
    children,
    width: opts.width ? { size: opts.width, type: WidthType.DXA } : undefined,
    shading: opts.bg ? { type: ShadingType.CLEAR, fill: opts.bg } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    borders: opts.borders || {
      top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder,
    },
    columnSpan: opts.colSpan,
  });
}

function headerCell(content, opts = {}) {
  return cell(content, {
    bold: true,
    bg: opts.bg || CLR.lightGray,
    fontColor: opts.fontColor || CLR.black,
    fontSize: opts.fontSize || 10,
    width: opts.width,
    borders: {
      top: thickBorder, bottom: thickBorder, left: thinBorder, right: thinBorder,
    },
    ...opts,
  });
}

// ── Color mapping for eval scores ──────────────────────────────
function scoreColor(score, threshold = 80) {
  const num = parseFloat(score);
  if (isNaN(num)) return { bg: CLR.red, fg: CLR.redText };
  if (num >= threshold) return { bg: CLR.green, fg: CLR.greenText };
  if (num >= 50) return { bg: CLR.yellow, fg: CLR.yellowTxt };
  return { bg: CLR.red, fg: CLR.redText };
}

// ── RAMP Plan Table ────────────────────────────────────────────
function rampTable() {
  const statusMap = {
    done:    { text: "[DONE]", bg: CLR.green, fg: CLR.greenText },
    risk:    { text: "[!]",    bg: CLR.yellow, fg: CLR.yellowTxt },
    pending: { text: "->",     bg: undefined,  fg: CLR.black },
  };

  const rows = [
    new TableRow({
      children: [
        headerCell("Wks",       { width: 1000, bg: CLR.navy, fontColor: CLR.white }),
        headerCell("Milestone", { width: 2400, bg: CLR.navy, fontColor: CLR.white }),
        headerCell("Status",    { width: 1200, bg: CLR.navy, fontColor: CLR.white }),
        headerCell("Notes",     { width: 2400, bg: CLR.navy, fontColor: CLR.white }),
      ],
    }),
    ...cfg.rampPlan.map(r => {
      const s = statusMap[r.status] || statusMap.pending;
      const isCurrent = r.current === true;
      return new TableRow({
        children: [
          cell(r.weeks,     { width: 1000, bold: isCurrent }),
          cell(r.milestone, { width: 2400, bold: isCurrent }),
          cell(s.text,      { width: 1200, bg: s.bg, fontColor: s.fg, bold: true }),
          cell(r.notes,     { width: 2400, bold: isCurrent }),
        ],
      });
    }),
  ];

  return new Table({
    rows,
    width: { size: 7000, type: WidthType.DXA },
    layout: TableLayoutType.FIXED,
  });
}

// ── Quality Metrics Table ──────────────────────────────────────
function qualityTable() {
  const rows = [
    new TableRow({
      children: [
        headerCell("Evaluation", { width: 2200, bg: CLR.navy, fontColor: CLR.white }),
        headerCell("Score",      { width: 1200, bg: CLR.navy, fontColor: CLR.white }),
        headerCell("Issue",      { width: 3600, bg: CLR.navy, fontColor: CLR.white }),
      ],
    }),
    ...cfg.evalScores.map(e => {
      const sc = scoreColor(e.score);
      return new TableRow({
        children: [
          cell(e.label, { width: 2200 }),
          cell(e.score, { width: 1200, bg: sc.bg, fontColor: sc.fg, bold: true }),
          cell(e.issue, { width: 3600 }),
        ],
      });
    }),
  ];

  return new Table({
    rows,
    width: { size: 7000, type: WidthType.DXA },
    layout: TableLayoutType.FIXED,
  });
}

// ── Build document children ────────────────────────────────────
const children = [];

// Title
children.push(
  new Paragraph({
    children: [txt("Document Authoring Hub", { bold: true, size: 18, color: CLR.navy, underline: true })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
  }),
  new Paragraph({
    children: [txt(`CEO Status Update \u2014 ${cfg.date}`, { italics: true, size: 11, color: CLR.navy })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 160 },
  }),
);

// Executive Summary
children.push(sectionHeader("Executive Summary"));
cfg.summary.forEach(line => {
  // Support bold prefixes via **text** markdown syntax
  const parts = line.split(/(\*\*[^*]+\*\*)/);
  const runs = parts.map(p => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return txt(p.slice(2, -2), { bold: true });
    }
    return txt(p);
  });
  children.push(bullet(runs));
});

// RAMP Plan Progress
children.push(sectionHeader("RAMP Plan Progress"));
children.push(new Paragraph({
  children: [txt(cfg.rampSubtitle, { italics: true, size: 10, color: "666666" })],
  spacing: { after: 80 },
}));
children.push(rampTable());

// Quality & Time Metrics
children.push(sectionHeader("Quality & Time Metrics"));
children.push(qualityTable());
if (cfg.evalFootnote) {
  children.push(new Paragraph({
    children: [txt(cfg.evalFootnote, { italics: true, size: 9, color: "666666" })],
    spacing: { before: 40, after: 80 },
  }));
}

// Time per Document
children.push(subHeader("Time per Document"));
children.push(bullet([
  txt(`AI stages: ${cfg.timePerDoc.ai}  |  `),
  txt(`Manual editing: ${cfg.timePerDoc.manual}`, { bold: true }),
  txt(`  |  Total: ${cfg.timePerDoc.total}`),
]));

// Critical Blockers
children.push(sectionHeader("Critical Blockers"));
cfg.blockers.forEach(b => {
  const color = b.resolved ? CLR.greenText : (b.risk === "High" ? CLR.redText : CLR.black);
  const labelSuffix = b.resolved ? " (RESOLVED): " : ` (Risk: ${b.risk}): `;
  children.push(bodyText([
    txt(b.title + labelSuffix, { bold: true, color }),
    txt(b.description),
  ]));
});

// Decision Point
children.push(subHeader(`Decision Point: ${cfg.decisionPoint.date}`));
cfg.decisionPoint.options.forEach(opt => {
  children.push(bullet([txt(opt)]));
});

// Recent Releases
children.push(sectionHeader("Recent Releases"));
cfg.releases.forEach(r => {
  children.push(bodyText([
    txt(`${r.version} (${r.date}): `, { bold: true }),
    txt(r.description),
  ]));
});

// ── Create and write document ──────────────────────────────────
const doc = new Document({
  sections: [{
    properties: {
      page: {
        margin: {
          top: convertInchesToTwip(0.6),
          bottom: convertInchesToTwip(0.4),
          left: convertInchesToTwip(0.8),
          right: convertInchesToTwip(0.8),
        },
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log("Generated:", outPath);
});
