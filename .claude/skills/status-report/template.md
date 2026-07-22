# Status Report Template v2.0.0

**MANDATORY**: This template structure is NON-NEGOTIABLE. Follow EXACTLY as shown.

---

## Template

```markdown
# **[CLIENT] - [PROJECT] - Weekly Status Report**

---

**Client:** [CLIENT] **Project:** [PROJECT] **Client POC:** [First-name Last-name] **Current Phase:** [REQUIREMENTS / DEVELOPMENT / MAINTENANCE]

**PRD Acceptance Deadline:** [Date or BLANK], **Cumulative Delay:** [X Days or 0]
*When are we sending the notice for acceptance?*

**Feature Complete Deadline:** [Date or BLANK], **Cumulative Delay:** [X Days or 0]
*When are we sending the notice for acceptance?*

**Software Acceptance Deadline:** [Date or BLANK], **Cumulative Delay:** [X Days or 0]
*When are we officially in maintenance mode?*

**Date of Next Exec Demo:** [Date / N/A]
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Minor Demo:** [Date / N/A]
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Code Release:** [Date / N/A]
*Only Applicable during active development or potentially during maintenance.*

**Date of Last Code Release:** [Date / N/A]
*Only Applicable during active development or during maintenance.*

---

## **Blockers or Potential Blockers:**

* [MOST IMPORTANT - prioritize by impact]

## **Notes:**

* FYI #1
* FYI #2
* Etc.

---

| Engineer | Refinery | Foundry | Planner | Validator |
| :---- | :---- | :---- | :---- | :---- |
| [Name] | [Time Spent] / [Quality Score (X/5)] | [Time Spent] / [Quality Score (X/5)] | [Time Spent] / [Quality Score (X/5)] | [Time Spent] / [Quality Score (X/5)] |
| [Name] |  |  |  |  |
| Etc. |  |  |  |  |

*Track from last Thursday to upcoming Thursday*
```

---

## Field Definitions

### Header Section

| Field | Format | Rules |
|-------|--------|-------|
| CLIENT | Text | Client company name (use same casing as in previous reports) |
| PROJECT | Text | Project name (use same casing as in previous reports) |
| Client POC | First-name Last-name | Full name of point of contact |
| Current Phase | REQUIREMENTS / DEVELOPMENT / MAINTENANCE | **ONLY these three values allowed** |

### Deadline Section

| Field | Format | Rules |
|-------|--------|-------|
| Deadline Date | Month DD, YYYY | Leave **BLANK** if unknown - NEVER fabricate |
| Cumulative Delay | X Days | 0 if on time, X if delayed from original baseline |
| Acceptance Question | Italicized | Standard question - do not modify |

**Cumulative Delay Calculation:**
- Track delay from the ORIGINAL baseline deadline
- Do not reset delays when deadlines are renegotiated
- Example: If original deadline was Jan 15 but now Feb 1, delay = 17 Days

### Demo/Release Section

| Field | Format | Rules |
|-------|--------|-------|
| Demo/Release Date | Month DD, YYYY | Use exact date if known |
| N/A | Literal "N/A" | Use if not applicable to current phase |
| BLANK | Empty | Use if unknown but applicable |

### Blockers Section

**Header**: `## **Blockers or Potential Blockers:**`

**Format**: Bullet list, prioritized by impact

**Content Guidelines**:
- Be specific and actionable
- Include who/what is blocking
- Include any scheduled resolution dates
- If no blockers: "* None identified this week."

**Example Blockers**:
```markdown
* SystemX API credentials pending - scheduled validation call Monday 12/16 at 1:30 PM EST with Jane Doe. Risk: blocks patient data integration.
* Client feedback on wireframes delayed - expected by end of week. Risk: may delay design sign-off.
```

### Notes Section

**Header**: `## **Notes:**`

**Format**: Bullet list with FYI labels

**Content Guidelines**:
- Important updates for stakeholders
- Decisions made this week
- Context that may affect next week
- If no notes: "* No additional notes this week."

**Example Notes**:
```markdown
* FYI #1: Question generation approach finalized - limiting to top 3 recommendations per visit.
* FYI #2: Pilot scheduled for January 2026 with 5 experienced nurses.
```

### Engineer Metrics Table

| Column | Description | Format |
|--------|-------------|--------|
| Engineer | Engineer full name | Text |
| Refinery | Requirements/analysis work | Time / X/5 |
| Foundry | Development/implementation | Time / X/5 |
| Planner | Planning/coordination | Time / X/5 |
| Validator | Testing/QA | Time / X/5 |

**Time Format**: `X hrs` or `N/A`
**Quality Score Format**: `X/5` (1-5 scale) or `N/A`
**Combined Format**: `8 hrs / 4/5` or `N/A`

**Date Range**: Last Thursday to upcoming Thursday

---

## Blank Field Policy

**CRITICAL**: When information is not found, follow these rules:

| Missing Data | Action |
|--------------|--------|
| Deadline date | Leave field BLANK after the colon |
| Cumulative delay | Leave field BLANK after the colon |
| Demo/release date | Leave field BLANK (not N/A unless explicitly not applicable) |
| Engineer time | Use `N/A` |
| Quality score | Use `N/A` |
| Client POC | **Ask user** - do not guess |
| Current Phase | **Ask user** - do not guess |

**What NOT to use**:
- "TBD"
- "Unknown"
- "To be determined"
- Estimated dates
- Fabricated values

---

## Filename Convention

**Format**: `Client_Project_YYYYMMDD.md`

**Rules**:
- Use underscores between Client, Project, and date
- Client and Project names should match header (no spaces in filename)
- Date is the Thursday that ends the tracking week
- Example: `HealthCorp_PatientPortal_20251219.md`

---

## Word Count Guidelines

**Maximum**: 1000 words

**Priority for trimming** (if over limit):
1. Keep all deadlines and dates (factual)
2. Keep all blockers (critical)
3. Trim notes to essential FYIs
4. Keep engineer table compact

**What counts toward word limit**:
- All text content in the report
- Excluding markdown formatting characters
- Excluding table structure
