# Status Report Examples v2.0.0

**Purpose**: Sample reports following the MANDATORY template format exactly.

---

## Example 1: Development Phase (Complete Data)

**Filename**: `HealthCorp_PatientPortal_20251219.md`

```markdown
# **HealthCorp - PatientPortal - Weekly Status Report**

---

**Client:** HealthCorp **Project:** PatientPortal **Client POC:** John Smith **Current Phase:** DEVELOPMENT

**PRD Acceptance Deadline:** November 15, 2025, **Cumulative Delay:** 0 Days
*When are we sending the notice for acceptance?*

**Feature Complete Deadline:** January 31, 2026, **Cumulative Delay:** 5 Days
*When are we sending the notice for acceptance?*

**Software Acceptance Deadline:** March 15, 2026, **Cumulative Delay:** 0 Days
*When are we officially in maintenance mode?*

**Date of Next Exec Demo:** December 20, 2025
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Minor Demo:** N/A
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Code Release:** January 2026
*Only Applicable during active development or potentially during maintenance.*

**Date of Last Code Release:** N/A
*Only Applicable during active development or during maintenance.*

---

## **Blockers or Potential Blockers:**

* SystemX API credentials pending - scheduled validation call Monday 12/16 at 1:30 PM EST with Jane Doe. Risk: blocks patient data integration.

## **Notes:**

* FYI #1: Question generation approach finalized - limiting to top 3 recommendations per visit.
* FYI #2: Pilot scheduled for January 2026 with 5 experienced nurses.

---

| Engineer | Refinery | Foundry | Planner | Validator |
| :---- | :---- | :---- | :---- | :---- |
| Alex Johnson | 4 hrs / 3/5 | 8 hrs / 4/5 | 2 hrs / 4/5 | N/A |
| Sam Patel | N/A | 12 hrs / 4/5 | 4 hrs / 3/5 | 2 hrs / 4/5 |

*Track from last Thursday to upcoming Thursday*
```

---

## Example 2: Requirements Phase (Partial Data)

**Filename**: `FinTech_Compliance_20251219.md`

Note: Feature Complete and Software Acceptance deadlines are left **BLANK** because they have not yet been established in the requirements phase. This is correct behavior - never fabricate.

```markdown
# **FinTech - Compliance - Weekly Status Report**

---

**Client:** FinTech **Project:** Compliance **Client POC:** Emily Johnson **Current Phase:** REQUIREMENTS

**PRD Acceptance Deadline:** December 31, 2025, **Cumulative Delay:** 0 Days
*When are we sending the notice for acceptance?*

**Feature Complete Deadline:** , **Cumulative Delay:**
*When are we sending the notice for acceptance?*

**Software Acceptance Deadline:** , **Cumulative Delay:**
*When are we officially in maintenance mode?*

**Date of Next Exec Demo:** January 10, 2026
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Minor Demo:** December 23, 2025
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Code Release:** N/A
*Only Applicable during active development or potentially during maintenance.*

**Date of Last Code Release:** N/A
*Only Applicable during active development or during maintenance.*

---

## **Blockers or Potential Blockers:**

* Compliance framework documentation access pending from client - follow-up scheduled December 20.

## **Notes:**

* FYI #1: Completed 8 stakeholder interviews this week.
* FYI #2: Initial wireframes received positive feedback.

---

| Engineer | Refinery | Foundry | Planner | Validator |
| :---- | :---- | :---- | :---- | :---- |
| Sarah Chen | 20 hrs / 5/5 | N/A | 6 hrs / 4/5 | N/A |

*Track from last Thursday to upcoming Thursday*
```

---

## Example 3: Maintenance Phase (Minimal Activity)

**Filename**: `ShopHub_Platform_20251219.md`

```markdown
# **ShopHub - Platform - Weekly Status Report**

---

**Client:** ShopHub **Project:** Platform **Client POC:** Michael Chen **Current Phase:** MAINTENANCE

**PRD Acceptance Deadline:** August 1, 2025, **Cumulative Delay:** 0 Days
*When are we sending the notice for acceptance?*

**Feature Complete Deadline:** August 31, 2025, **Cumulative Delay:** 0 Days
*When are we sending the notice for acceptance?*

**Software Acceptance Deadline:** September 15, 2025, **Cumulative Delay:** 0 Days
*When are we officially in maintenance mode?*

**Date of Next Exec Demo:** N/A
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Minor Demo:** N/A
*Only Applicable during active development or potentially during maintenance.*

**Date of Next Code Release:** January 5, 2026
*Only Applicable during active development or potentially during maintenance.*

**Date of Last Code Release:** December 8, 2025
*Only Applicable during active development or during maintenance.*

---

## **Blockers or Potential Blockers:**

* None identified this week.

## **Notes:**

* FYI #1: System uptime 99.8% this week.
* FYI #2: 12 support tickets resolved, avg resolution 2.1 hours.

---

| Engineer | Refinery | Foundry | Planner | Validator |
| :---- | :---- | :---- | :---- | :---- |
| Alex Kim | N/A | 6 hrs / 5/5 | 1 hr / 4/5 | 4 hrs / 5/5 |

*Track from last Thursday to upcoming Thursday*
```

---

## Key Differences from v1.0.0 Format

| Aspect | v1.0.0 | v2.0.0 (MANDATORY) |
|--------|--------|-------------------|
| Deadline names | Project-specific flexible | Fixed: PRD/Feature/Software Acceptance |
| Phase options | Descriptive narratives | ONLY: REQUIREMENTS/DEVELOPMENT/MAINTENANCE |
| Work sections | "Work This Week", "Next Steps" | NOT in template - omit |
| Blocker format | Detailed with Risk Level tags | Bullet list without explicit Risk Level header |
| Notes format | Descriptive labels | FYI #1, FYI #2 format |
| Category prefix | HEALTH_, FINANCE_, etc. | None - just Client_Project |
| Unknown data | "TBD" or estimates | Leave BLANK |

---

## Common Mistakes to Avoid

### Wrong: Using TBD or Unknown

```markdown
**Feature Complete Deadline:** TBD, **Cumulative Delay:** Unknown
```

### Correct: Leave Blank

```markdown
**Feature Complete Deadline:** , **Cumulative Delay:**
```

### Wrong: Fabricating Dates

```markdown
**Date of Next Code Release:** Probably mid-January
```

### Correct: Use N/A or Leave Blank

```markdown
**Date of Next Code Release:** N/A
```
(if not applicable to current phase)

```markdown
**Date of Next Code Release:**
```
(if applicable but unknown)
