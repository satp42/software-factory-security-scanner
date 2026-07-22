# CEO Status Update Report Format

## Config JSON Schema

The generator script (`scripts/generate_report.js`) accepts a JSON config file with these fields:

```json
{
  "date": "February 14, 2026",
  "weekNumber": 10,
  "totalWeeks": 16,
  "rampSubtitle": "16-week transition plan (Dec 18, 2025 — Apr 6, 2026) | Week 10 of 16",

  "summary": [
    "Schedule on track: Week 10 of 16 in ramp plan",
    "**RESOLVED:** Veeva upload blocker fixed in v1.0.19",
    "Quality gap: scores at X%–Y% vs. 80% target"
  ],

  "rampPlan": [
    { "weeks": "1–2",   "milestone": "Training",       "status": "done",    "notes": "Done" },
    { "weeks": "3–6",   "milestone": "Bug-Fix Sprint",  "status": "done",    "notes": "Done" },
    { "weeks": "7–8",   "milestone": "Re-validate",     "status": "done",    "notes": "Done" },
    { "weeks": "10",    "milestone": "Ramp Achieved",    "status": "risk",    "notes": "At Risk", "current": true },
    { "weeks": "10–16", "milestone": "Scale to Prod",    "status": "pending", "notes": "Pending" }
  ],

  "evalScores": [
    { "label": "Eval 1 (Feb 2)",  "score": "65.4%",  "issue": "Passed" },
    { "label": "Eval 2 (Feb 5)",  "score": "23.1%",  "issue": "Import bug" },
    { "label": "Target (Prod)",   "score": "80%+",   "issue": "Not met" }
  ],

  "evalFootnote": "Optional footnote text about eval caveats.",

  "timePerDoc": {
    "ai": "10–20 min",
    "manual": "45–55 min",
    "total": "45–90 min"
  },

  "blockers": [
    {
      "title": "Veeva Upload",
      "resolved": true,
      "risk": null,
      "description": "Fixed in v1.0.19 (Feb 9)."
    },
    {
      "title": "Eval Environment Setup",
      "resolved": false,
      "risk": "Medium",
      "description": "Process gap, not a tool bug."
    }
  ],

  "decisionPoint": {
    "date": "February 17, 2026",
    "options": [
      "If X → Continue ramp",
      "If Y → Investigate"
    ]
  },

  "releases": [
    {
      "version": "v1.0.19",
      "date": "Feb 9",
      "description": "Veeva upload fix, search improvements"
    },
    {
      "version": "v1.1.0",
      "date": "Feb 12",
      "description": "No Data SRD, tabbed workspace"
    }
  ]
}
```

## Field Details

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | string | yes | Display date (e.g., "February 14, 2026") |
| `weekNumber` | number | yes | Current RAMP week number |
| `totalWeeks` | number | yes | Total RAMP weeks (currently 16) |
| `rampSubtitle` | string | yes | Italic subtitle under RAMP header |
| `summary` | string[] | yes | Executive summary bullets. Wrap text in `**bold**` for emphasis. |
| `rampPlan` | object[] | yes | RAMP table rows. `status`: "done", "risk", or "pending". Set `current: true` on the active week row. |
| `evalScores` | object[] | yes | Quality table rows. Auto-colored: green >=80%, yellow >=50%, red <50%. Always include Target row last. |
| `evalFootnote` | string | no | Italicized footnote below eval table |
| `timePerDoc` | object | yes | Keys: `ai`, `manual`, `total` (string ranges) |
| `blockers` | object[] | yes | Each: `title`, `resolved` (bool), `risk` (string or null), `description` |
| `decisionPoint` | object | yes | Keys: `date` (string), `options` (string[]) |
| `releases` | object[] | yes | Each: `version`, `date`, `description` |

## Report Sections (in order)

1. **Title** — "Document Authoring Hub" (navy, underlined, centered) + italic subtitle
2. **Executive Summary** — 4–6 bullet points, executive-focused
3. **RAMP Plan Progress** — Color-coded milestone table
4. **Quality & Time Metrics** — Eval score table + time breakdown
5. **Critical Blockers** — Resolved (green) and active (red/black) blockers
6. **Decision Point** — Date + if/then options
7. **Recent Releases** — Version + date + brief description

## Styling Reference

- **Font**: Aptos, 11pt body, 13pt section headers, 18pt title
- **Colors**: Navy (#1F3864) headers, teal (#2E75B6) sub-headers
- **Table status colors**: Green (#C6EFCE) done, Yellow (#FFEB9C) risk, Red (#FFC7CE) fail
- **Margins**: 0.6" top, 0.4" bottom, 0.8" sides
- **Target**: Single-page layout

## Stakeholders

**To:** Nathalie Dompe (CEO)
**CC:** Neal Patel, Ivy Chang, Janice Lin, Andrew Sheldon, Beth Scott, Jonathan Yu, Alexander Downey, Sina Sojoodi

## Source Data Location

Weekly update files are in: `~/projects/dompe-crd-srd-auth/nat-update/<week-folder>/`

Each week folder typically contains:
- `<version>.md` — Release notes for each version shipped that week
- `Eval-scores.md` — Evaluation scores table with clinical questions, scores, times
- Optional: `drafts/`, `emails/`, `screenshots/` subdirectories
