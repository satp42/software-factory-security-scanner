# Data Sources for Status Reports

**Purpose**: Guide for gathering data in both Claude Desktop (MCP) and Claude Code CLI (manual) environments.

---

## Dual-Use Data Access Pattern

This skill works in two environments with different data access capabilities:

### Claude Desktop Mode (MCP Available)

When running in Claude Desktop with MCP servers configured:

```
Step 1: Check MCP server availability
  ├── Slack MCP → Query project channel
  ├── Google Drive MCP → Search project folders
  └── Email MCP → Search recent correspondence

Step 2: Supplement with local files
  └── ~/projects/<client_project>/ → Search for context

Step 3: Request manual input for gaps
  └── Ask user for specific missing information

Step 4: Generate report with all available data
```

### Claude Code CLI Mode (No MCP)

When running in Claude Code CLI without MCP servers:

```
Step 1: Search local project files
  └── ~/projects/<client_project>/ → All project context

Step 2: Find previous status reports
  └── ~/projects/<client_project>/reports/ → Historical data

Step 3: Request all additional context from user
  ├── Blockers?
  ├── Engineer hours this week?
  ├── Any deadline changes?
  └── Notable updates or decisions?

Step 4: Generate report with provided data
```

---

## MCP Integration Details (Claude Desktop)

### 1. Slack MCP (8090inc.slack.com)

**Target**: `#<client_project>` channel (e.g., `#healthcorp-patientportal`)

**What to Extract**:
- Blocker discussions and escalations
- Demo/release date mentions or changes
- Team updates and progress reports
- Decision points and approvals
- Time tracking mentions

**Search Query Patterns**:
- `deadline` or `due date` in channel
- `blocker` or `blocked` in channel
- `completed` or `done` or `finished` in channel
- `demo` or `release` in channel
- Date range filter: last Thursday to today

### 2. Google Drive MCP

**Target**: Project folders in Google Drive

**What to Extract**:
- Meeting notes from past week
- Updated project documents
- Deadline spreadsheets or trackers
- Demo recordings or presentation notes
- Decision documents

**Search Locations**:
- Folder: `<Client> <Project>` or `<client>-<project>`
- Recent documents modified in date range
- Files containing "status", "deadline", "milestone", "blocker"

### 3. Email MCP (Gmail/Outlook)

**Target**: Project-related correspondence

**What to Extract**:
- Deadline confirmations or changes
- Blocker escalations
- Client communications and feedback
- Team status updates
- Meeting scheduling and outcomes

**Search Filters**:
- Subject or body contains client name
- Subject or body contains project name
- Date range: last Thursday to today
- From/To project stakeholders

---

## Local File Search (Both Environments)

### Project Directory Structure

**Path**: `~/projects/<client_project>/`

**Common Locations to Search**:
```
~/projects/<client_project>/
├── reports/           # Previous status reports
│   └── *_YYYYMMDD.md
├── docs/              # Project documentation
├── notes/             # Meeting notes
├── logs/              # Development logs
└── README.md          # Project overview
```

### Previous Status Reports

**Priority**: Always check previous reports first for:
- Baseline deadlines (for cumulative delay calculation)
- Previous blockers (check if resolved)
- Team composition
- Established formatting conventions

**Search Pattern**: `~/projects/<client_project>/reports/*_YYYYMMDD.md`

---

## Data Extraction Rules

### CRITICAL: Never Fabricate

If a data source does not contain specific information:

| Missing Data Type | Action |
|-------------------|--------|
| Dates/Deadlines | Leave field **BLANK** |
| Metrics/Numbers | Use **N/A** |
| Names | **Ask user** for clarification |
| Cumulative delays | **Calculate** from previous report baseline |

---

## Date Range Enforcement

**Tracking Period**: Last Thursday to upcoming Thursday

### Calculating the Date Range

**Example** (if today is Wednesday December 18, 2025):
- Last Thursday: December 12, 2025
- Upcoming Thursday: December 19, 2025
- Report covers: Dec 12 - Dec 19, 2025
- Filename date: `20251219` (ending Thursday)

---

## Asking Clarifying Questions

### Question Template

```markdown
Before generating the status report, I need the following information:

**Required (cannot proceed without)**:
1. [Question about critical missing data]

**Optional (will leave blank if not provided)**:
2. [Question about nice-to-have data]

Please provide the information or indicate which fields should remain blank.
```

### Example Questions (Claude Code CLI)

```markdown
Before generating the [Client] - [Project] status report for [Date Range]:

**Required**:
1. What are the current blockers or potential blockers this week?
2. Are there any deadline changes from last week?

**Optional (will leave blank if not provided)**:
3. Engineer hours breakdown by tool (Refinery/Foundry/Planner/Validator)?
4. Quality scores for each engineer this week?
5. Any FYI notes for stakeholders?

Please provide what you have, and I'll generate the report with available data.
```
