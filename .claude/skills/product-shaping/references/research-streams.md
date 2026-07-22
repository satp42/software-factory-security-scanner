# Research Stream Execution Guide

Detailed instructions for executing each research stream in Phase 2.

## Table of Contents
- [Competitors](#competitors)
- [Customer Evidence](#customer-evidence)
- [Meeting Transcripts](#meeting-transcripts)
- [System Audit](#system-audit)

---

## Competitors

*How do others solve this job to be done?*

### Execution

- Launch one agent per platform in parallel (6-10 agents) using background agents
- Each agent: 3-5 web searches + 2-4 page fetches
- Give each agent the framing from Phase 1 so they search with the right lens
- Each agent writes `research/{platform-name}.md`

### Synthesis

After all agents complete, synthesize into `research/best-practices.md`:
- Common patterns across platforms
- Anti-patterns to avoid
- How competitors handle open questions from Phase 1
- Gaps no one solves well (potential differentiation)

### Gotcha

Review sites (G2, GetApp, Capterra) often block automated fetching. Use search result summaries as fallback.

---

## Customer Evidence

*What are customers actually saying?*

### Call transcripts (`research/call-evidence.md`)

Search call recordings using agreed keywords from Phase 1. For each piece of evidence:
- Who said it (role, company size)
- What deal stage
- How large the account
- Direct quote with attribution

Quantity matters: "12 enterprise prospects asked for this in Q4" beats "customers want this."

### CRM notes (`research/crm-evidence.md`)

Search CRM for deal notes, lost-deal reasons, feature requests. Structure:
- Deal sizes and stage breakdown
- Attributed notes with deal context
- Patterns across segments

### Support tickets (`research/support-evidence.md`)

Search support system for related complaints and workarounds. Structure:
- Ticket themes and volumes
- Customer pain patterns
- Current workarounds customers use

### When tools aren't connected

Ask the PM to paste in relevant customer quotes, support ticket summaries, or sales notes. Organize whatever is provided into the relevant research file with the same structure.

---

## Meeting Transcripts

*What's already been decided?*

### Execution (`research/transcript-evidence.md`)

Search internal meeting recordings and notes for prior decisions on this topic. Structure:
- Decisions already made (with source meeting and date)
- Context behind each decision
- Any constraints or requirements surfaced

Flag anything already decided so you don't re-litigate settled questions.

### When tools aren't connected

Ask the PM: "Are there any prior decisions or context from past meetings I should know about? I want to avoid re-opening things that are already settled."

---

## System Audit

*What does the product already have?*

### Execution (`research/system-audit.md`)

Investigate in parallel (split into multiple agents by area):

| Area | What to look for |
|------|-----------------|
| User flows | Existing flows this feature touches |
| Data models | Schemas, relationships, constraints |
| API surfaces | Endpoints, contracts, versioning |
| Integration points | ERPs, partner systems, webhooks |
| Reusability | What can be extended vs. what's net new |
| Prior art | Internal docs, prior specs on this domain |

### When codebase access isn't available

Ask the PM to describe:
- Current system architecture
- Existing APIs relevant to this feature
- What they think is reusable

Document their answers in `research/system-audit.md`.
