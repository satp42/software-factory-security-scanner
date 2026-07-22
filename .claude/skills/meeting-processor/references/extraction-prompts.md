# Extraction Prompts Reference

This document contains all specialized prompts used by the meeting processor for multi-stage knowledge extraction.

## Philosophy

The meeting processor acts as a **knowledge architect** that exhaustively mines meeting content. Key principles:

- **Missing content is unacceptable** - every valuable insight must be captured
- **Hunt for implicit content** - ideas embedded in problems, decisions made by NOT deciding
- **Depth over brevity** - a 1-page summary for an hour+ meeting indicates incomplete processing
- **Capture everything** - a casual mention today might be tomorrow's priority

---

## 1. Transcript Prompt

**Purpose:** Create a complete verbatim transcript with timestamps and speaker identification.

```
You are a professional transcriptionist. Create a COMPLETE verbatim transcript of this meeting video.

Requirements:
1. Include ALL spoken content - do not skip or summarize
2. Add timestamps in [HH:MM:SS] format at regular intervals (every 30-60 seconds of speaking)
3. Identify speakers where possible (Speaker 1, Speaker 2, or names if mentioned)
4. Include verbal fillers, false starts, and corrections to preserve authenticity
5. Note any non-verbal audio cues in brackets [laughs], [pause], [crosstalk]
6. If audio is unclear, mark as [inaudible] or [unclear]

Format:
[00:00:00] Speaker: Text of what they said...

This must be the FULL transcript, not a summary. Every word matters.
```

---

## 2. Summary Prompt

**Purpose:** Create a comprehensive meeting summary (2-4 pages for hour+ meetings).

```
You are the knowledge architect for this meeting. Create a comprehensive meeting summary.

Based on the video, provide:

# Meeting Summary

## Overview
- Date/Time context
- Participants (names/roles if identifiable)
- Meeting purpose/context

## Key Discussion Points
For each major topic discussed:
- What was discussed
- Key points raised
- Outcomes/conclusions

## Critical Insights
- Most important takeaways
- Strategic observations
- Notable quotes or statements

## Open Questions
- Unresolved items
- Topics needing follow-up

This summary should be substantial - for an hour+ meeting, expect 2-4 pages of content.
Be thorough. Missing content is unacceptable.
```

---

## 3. Decisions Prompt

**Purpose:** Extract all decisions - explicit, implicit, and deferred.

```
You are mining this meeting for ALL decisions - both explicit and implicit.

Extract every decision into these categories:

# Decisions Made

## Explicit Decisions
Decisions that were clearly stated:
- "[Timestamp] Decision: [what was decided]"
- Include context and rationale if discussed

## Implicit Decisions
Decisions made by NOT deciding or by assumption:
- Things deprioritized ("let's not wait for...")
- Defaults accepted without discussion
- Directions taken by omission

## Deferred Decisions
Items explicitly pushed to later:
- What was deferred
- Why it was deferred
- When it might be revisited

## Decision Rationale
For major decisions, capture the reasoning discussed.

Look for phrases like:
- "Let's go with..."
- "We've decided..."
- "The plan is to..."
- "We're not going to..."
- "For now, let's..."
```

---

## 4. Ideas Prompt

**Purpose:** Capture all ideas, even casual mentions and embedded ideas.

```
You are hunting for ALL ideas mentioned in this meeting - even casual ones.

Extract into these categories:

# Ideas & Project Sparks

## Feature Ideas
Ideas for features in existing projects:
- [Timestamp] "Description of the idea"
- Context: where/why it came up
- Related project if mentioned

Look for:
- "Wouldn't it be cool if..."
- "We could also..."
- "What if we..."
- "It would be nice to..."

## Project Sparks
New tool concepts, standalone initiatives:
- Completely new projects mentioned
- Tools that could be built
- Services or systems proposed

## Embedded Ideas
Ideas hidden in problem discussions:
- "The issue is we don't have X" → X is an idea
- "It's hard because Y" → solving Y is an idea
- Complaints often contain feature requests

## Raw Ideas
Even half-formed thoughts worth capturing:
- Quick asides
- "Random idea but..."
- Ideas dismissed or tabled

Don't filter - capture everything. A casual mention today might be tomorrow's priority.
```

---

## 5. Action Items Prompt

**Purpose:** Extract all tasks, next steps, and follow-ups.

```
Extract ALL action items, tasks, and next steps from this meeting.

# Action Items

## Assigned Tasks
Tasks with clear ownership:
- [Timestamp] Task: [description]
- Owner: [who is responsible]
- Deadline: [if mentioned]
- Context: [why this task matters]

## Unassigned Tasks
Things that need to happen but no owner yet:
- Task description
- Why it was raised

## Next Steps
General direction/momentum items:
- What happens after this meeting
- Follow-up activities discussed

## Follow-ups
Items needing future attention:
- Questions to research
- People to contact
- Things to verify

Look for phrases like:
- "I'll..." / "You'll..." / "We need to..."
- "Can you..." / "Let's make sure..."
- "Action item:"
- "Next step is..."
- "By [date]..."
```

---

## 6. Frameworks Prompt

**Purpose:** Extract mental models, principles, and philosophies.

```
Extract all mental models, frameworks, principles, and philosophies from this meeting.

# Frameworks & Philosophies

## Mental Models
Ways of thinking about problems:
- [Timestamp] Framework: [description]
- How it was applied in discussion

## Principles
Guiding rules mentioned:
- "We always..."
- "The rule is..."
- "Our approach is..."

## Philosophies
Team beliefs and working principles:
- Values expressed
- Cultural statements
- How the team thinks about their work

## Ways of Thinking
Interesting perspectives shared:
- Novel approaches to problems
- Reframes of situations
- Strategic lenses applied

Look for:
- Explanatory analogies
- "The way I think about it..."
- "Our philosophy is..."
- Repeated principles/values
- Asides that reveal beliefs
```

---

## 7. Status Updates Prompt

**Purpose:** Extract all project status changes and timeline updates.

```
Extract ALL status updates and state changes from this meeting.

# Status Updates

## Projects Now Live/Complete
Things that shipped or finished:
- [Timestamp] "[Project/Feature] is now live/done"
- What changed
- Impact discussed

## Projects In Progress
Active work updates:
- Current state
- Progress made
- Expected completion

## Projects Blocked/On Hold
Things that are stuck:
- What is blocked
- Why it's blocked
- What would unblock it

## Changes in Priority
Shifts in importance:
- Things moving up
- Things moving down
- Reasons for changes

## Timeline Updates
Schedule changes:
- Delays announced
- Accelerations
- New deadlines set

Look for:
- "X is now..."
- "We shipped..."
- "That's done..."
- "We're waiting on..."
- "The new timeline is..."
```

---

## 8. Blockers Prompt

**Purpose:** Identify all blockers, obstacles, and risks.

```
Identify ALL blockers, obstacles, and impediments mentioned in this meeting.

# Blockers & Obstacles

## Technical Blockers
Technical issues preventing progress:
- [Timestamp] Blocker: [description]
- Impact: what can't proceed
- Proposed solution (if discussed)

## Dependencies
Waiting on external factors:
- People to respond
- Decisions from others
- Resources needed

## Resource Constraints
Limitations mentioned:
- Time constraints
- Budget limitations
- Capacity issues

## Knowledge Gaps
Information needed:
- Things we don't know yet
- Research needed
- Expertise required

## Process Blockers
Organizational friction:
- Approval processes
- Coordination challenges
- Communication issues

## Risks Identified
Potential future blockers:
- Concerns raised
- Things that could go wrong
- Uncertainties flagged

Look for:
- "We can't until..."
- "We're blocked on..."
- "The issue is..."
- "We need to figure out..."
- "The risk is..."
```

---

## Implicit Content Detection

When processing, actively hunt for:

| Surface Pattern | Hidden Content |
|-----------------|----------------|
| "The issue is we don't have X" | X is an idea |
| "It's hard because Y" | Solving Y is an idea |
| "We always say..." | Philosophy |
| "Let's not wait for..." | Decision (implicit) |
| Complaints | Feature requests |
| Problems discussed | Opportunities |

---

## Red Flags (Incomplete Processing)

If you see these patterns, processing is incomplete:

- Meeting summary shorter than 1 page for hour+ meeting
- Only 1-2 ideas extracted from brainstorming discussion
- No status changes identified in status-heavy meeting
- Missing implicit decisions
- No embedded ideas found in problem discussions
