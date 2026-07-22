---
name: status-report
description: "Expert guidance for creating weekly status reports for 8090 project management teams. Use when generating status reports, weekly updates, project progress reports, or team updates. Follows MANDATORY template format with strict 1000-word limit. Supports dual-use: Claude Desktop (MCP access to Google Drive, Slack, Email) and Claude Code CLI (local files + manual context). CRITICAL: Never fabricate dates or deadlines - leave fields BLANK if information not found. Triggered by requests like 'create status report', 'generate weekly update', 'prepare project status', or 'create this week's status report'."
---

# Status Report Generator v2.0.0

**Version**: 2.0.0
**Last Updated**: 2025-12-18
**Author**: Rohit Kelapure
**Template Source**: `Client_Project_YYYYMMDD.md` (MANDATORY - NO EXCEPTIONS)

---

## Changelog

- **v2.0.0** (2025-12-18): Complete redesign with MANDATORY template, dual-use support (Claude Desktop + Claude Code CLI), 1000-word limit, blank-field policy
- **v1.0.0** (2025-11-17): Initial release

---

## When to Use This Skill

**Trigger Phrases**:
- "create status report"
- "generate weekly update"
- "prepare project status"
- "create this week's status report"
- "weekly status for [client] [project]"

**Target Users**: Project Managers at 8090 managing client projects

**Output Location**: `~/projects/<client_project>/reports/Client_Project_YYYYMMDD.md`

---

## Critical Rules (MUST Hierarchy)

| Priority | Rule | Description |
|----------|------|-------------|
| **MUST** | Template Adherence | Follow template structure EXACTLY - NO EXCEPTIONS |
| **MUST** | Filename Format | `Client_Project_YYYYMMDD.md` |
| **MUST** | Save Location | `~/projects/<client_project>/reports/` |
| **MUST** | Word Limit | Maximum 1000 words total |
| **MUST** | No Fabrication | NEVER make up dates or deadlines |
| **MUST** | Blank Fields | Leave items BLANK if information not found |
| **MUST** | Date Range | Track "from last Thursday to upcoming Thursday" |
| **SHOULD** | Ask PM | Request clarifying questions if PM input needed |

---

## How to Use This Skill (v2.0.0)

### ALWAYS Follow This 5-Step Sequence:

### Step 1: Identify Project Context

- Determine client name and project name
- Confirm project directory: `~/projects/<client_project>/`
- Establish date range: last Thursday to upcoming Thursday
- **IF unclear, ASK the user before proceeding**

### Step 2: Gather Data from Available Sources

**Load `data-sources.md` for detailed MCP integration guidance.**

**Dual-Use Data Access Pattern:**

| Environment | Data Sources (Priority Order) |
|-------------|------------------------------|
| **Claude Desktop** | 1. Slack MCP 2. Google Drive MCP 3. Email MCP 4. Local files 5. Manual context |
| **Claude Code CLI** | 1. Local files 2. Previous reports 3. Manual context from user |

**For each data source, extract:**
- Deadlines and milestone dates (ONLY if explicitly stated)
- Blockers and issues
- Completed work
- Team time allocations
- Quality feedback

### Step 3: Find Previous Status Report

- Search: `~/projects/<client_project>/reports/*_YYYYMMDD.md`
- Read most recent report for:
  - Existing deadlines and delays
  - Previous blockers and their resolution status
  - Team composition
  - Cumulative delay calculations

### Step 4: Generate Status Report

- **Load `template.md`** (MANDATORY format - NO EXCEPTIONS)
- Fill in ALL sections per template
- Apply validation rules (see Quality Control)
- Save to: `~/projects/<client_project>/reports/Client_Project_YYYYMMDD.md`

### Step 5: Quality Control

- Run validation checklist (see below)
- Verify word count <= 1000
- Confirm no fabricated data
- Ensure blank fields for unknown information

---

## Response Format

When this skill is invoked, ALWAYS follow this structure:

```
Using Status Report Skill v2.0.0 - MANDATORY Template
Date Range: [Last Thursday] to [Upcoming Thursday]
Project: [Client] - [Project]

**Step 1**: Identifying project context...
[Report project details and date range]

**Step 2**: Gathering data from sources...
- Slack (8090inc.slack.com): [Available/Not Available]
- Google Drive: [Available/Not Available]
- Email: [Available/Not Available]
- Local Files: [Found X files / None found]
- Manual Context: [Provided/None]

[Summarize what data was found from each source]

**Step 3**: Finding previous report...
[Report what was found or note if first report]

**Step 4**: Generating report...

---

[GENERATED STATUS REPORT CONTENT FOLLOWING EXACT TEMPLATE]

---

**Status Report Created**: `Client_Project_YYYYMMDD.md`
**Location**: `~/projects/<client_project>/reports/`
**Word Count**: [X]/1000

**Clarifications Needed** (if any):
- [List questions for PM if data was missing]

Would you like me to:
- Save this report?
- Make any adjustments?
- Add additional context?
```

---

## Quality Control Checklist (MANDATORY)

Before finalizing, verify ALL items:

### Template Compliance
- [ ] Title: `# **CLIENT - PROJECT - Weekly Status Report**`
- [ ] Horizontal rule after title
- [ ] Header block with Client/Project/POC/Phase on single line
- [ ] Three deadline sections with format: `**Name Deadline:** Date, **Cumulative Delay:** X Days`
- [ ] Four demo/release date fields
- [ ] Horizontal rule separator
- [ ] Blockers section with header `## **Blockers or Potential Blockers:**`
- [ ] Notes section with header `## **Notes:**`
- [ ] Horizontal rule separator
- [ ] Engineer metrics table with exact column headers

### Data Integrity
- [ ] NO fabricated dates or deadlines
- [ ] Unknown fields left BLANK (not "TBD" or "Unknown")
- [ ] Cumulative delays calculated from original baseline
- [ ] Date range: last Thursday to upcoming Thursday

### Format Rules
- [ ] Word count <= 1000 words
- [ ] Filename: `Client_Project_YYYYMMDD.md`
- [ ] Current Phase: REQUIREMENTS / DEVELOPMENT / MAINTENANCE
- [ ] Quality scores: X/5 format

### Content Quality
- [ ] Blockers prioritized by impact
- [ ] Notes provide actionable context
- [ ] Engineer table reflects actual time spent

---

## File Structure

```
.claude/skills/status-report/
├── SKILL.md           # This file - main workflow and rules
├── template.md        # MANDATORY template format
├── data-sources.md    # MCP integration & data gathering guidance
└── examples.md        # Sample reports demonstrating correct format
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Missing deadline dates | Leave field BLANK - never fabricate |
| No previous reports | Start fresh, ask PM for baseline dates |
| MCP not available | Fall back to local files + manual context |
| Engineer hours unknown | Use N/A for that cell |
| Word count exceeded | Prioritize blockers, trim notes |

### When to Ask for Clarification

**Always ask before proceeding if:**
- Client name or project name is unclear
- Current phase is ambiguous
- Critical deadlines are missing and needed for context
- Blockers require PM escalation decisions

**Use this format:**

```
Before generating the status report, I need the following information:

**Required (cannot proceed without)**:
1. [Question about critical missing data]

**Optional (will leave blank if not provided)**:
2. [Question about nice-to-have data]

Please provide the information or indicate which fields should remain blank.
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-18 | Complete redesign: MANDATORY template, dual-use support, 1000-word limit, blank-field policy |
| 1.0.0 | 2025-11-17 | Initial release |
