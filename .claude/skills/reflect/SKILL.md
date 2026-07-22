---
name: reflect
description: "Session retrospective that reviews the current chat for mistakes, friction, and unclear outputs, then proposes concrete improvements and optionally audits any skills used. Trigger on reflect, review the session, or a retrospective request; suggest it proactively when the user has had to correct you or rephrase the same request twice."
---

# Reflect

A lightweight session retrospective. Goal: surface what went well, what didn't, and what to carry forward so future sessions start smarter.

## Success Criteria

A reflect pass is successful only if ALL of these are true:

1. **Grouped by class, not exhaustive.** Issues are grouped by the underlying pattern (e.g., "over-trimmed mandatory sections"), not listed per instance.
2. **Each improvement is executable.** Every proposed improvement is specific enough that a future session can act on it without interpretation — no generic advice like "be more careful."
3. **Skill audits read the source.** If a skill was invoked, the audit reads the actual `SKILL.md` file (not memory) before proposing edits.
4. **User confirmation gates every write.** No edit to `CLAUDE.md` or any skill file happens without explicit user approval. EXCEPTION: if the user invokes `/reflect` with args containing `integrate`, `apply`, `save`, or `remember all`, treat those args as pre-authorization — skip the Step 5 ask but still announce each pending write before executing it.
5. **Dates are concrete.** Every `CLAUDE.md` entry starts with `[YYYY-MM-DD]` using today's actual date.

## When to run

Run when the user types "reflect" or asks for a session review.

**Proactive nudge** — suggest "reflect" when you notice any of: an error the user had to fix; the same intent clarified twice+; frustration tone ("no, I meant...", "again"); output required significant rework. Frame naturally: *"I notice I needed corrections there. Want to type `reflect` so we can capture what to do differently?"*

## Execution steps

### 1. Review the session

Scan the full conversation. Categorize each exchange:
- **What worked:** tasks completed cleanly first attempt; outputs accepted without edits.
- **What didn't:** mistakes, misunderstandings, reworks, questions the context already answered.
- **Friction points:** moments the user had to repeat themselves, correct you, or supply inferrable info.

### 2. Present findings

```
## Session Retrospective

**What went well**
- [1-3 bullets, specific and concrete]

**Mistakes & friction**
- [Each issue: what happened, why, what should have been done instead]

**Proposed improvements**
- [Numbered list of actionable changes for future sessions]
```

Each bullet must be specific enough to act on. If the session was clean, say so in one sentence and skip the improvements list.

### 3. Audit skills used in this session

For each skill invoked during the conversation:

**a)** Read the `SKILL.md` source file at the skill's location.

**b) Check for self-check.** If the skill lacks success criteria and a verification loop, draft additions:
- `## Success Criteria` near the top: 3-5 measurable criteria for a successful output.
- `## Pre-Delivery Verification` at the bottom: verify all criteria are met before presenting output; iterate up to 3 times on failure.

**c) Check for conciseness.** Flag redundant instructions or verbose sections that compress without losing clarity. Token efficiency matters across millions of invocations.

**d) Check for behavioral issues** based on session performance: wrong defaults, missing edge cases, unclear instructions.

**e) Present proposed changes** as a numbered list. Do not apply until the user confirms. For read-only skill directories, note the user will need to reinstall.

### 4. Detect repeated patterns

Two flavors:

**a) Repeated user requests** — if the user asked for the same (or variations of the same) workflow more than once, suggest extracting it to a skill:

*"I noticed you asked me to [pattern] multiple times. Want me to create a skill for this?"*

Wait for confirmation before creating.

**b) Repeated friction** — if the user verified the same completion class 2+ times ("did you do X", "did you also do Y", "did you cover Z"), surface it as a system-improvement candidate, not a skill candidate. Propose a concrete change to memory, pipeline, or `CLAUDE.md` that would have prevented the friction. Example: "You asked 3 times whether shared-drive copies were updated. Suggests a completeness-checklist memory entry or a pipeline post-deliver assertion."

### 5. Ask what to remember (or skip if pre-authorized)

**If `/reflect` args contain `integrate`, `apply`, `save`, or `remember all`:** skip the ask. Report each pending write (file path + summary of change) before executing it, then apply all proposed improvements without further prompting.

**Otherwise:** present the proposed improvements as a numbered checklist. Ask:

*"Which should I remember for future chats? Give me the numbers, or say 'all' / 'none'."*

On confirmation, append selected items to the project's `CLAUDE.md` under `## Session Learnings` (create the section if missing). Use today's actual date — run `date +%Y-%m-%d` to fetch it if uncertain:

```markdown
## Session Learnings

- [YYYY-MM-DD] [The improvement, stated as an instruction]
```

If the user says "none", skip the write. Never write without confirmation (unless pre-authorized via args, see above).

## Pre-Delivery Verification

Before presenting the retrospective output, verify each Success Criterion:

1. Are issues grouped by class rather than exhaustively listed?
2. Is every proposed improvement executable without interpretation?
3. If skills were audited, was the actual `SKILL.md` read (not recalled)?
4. Are all `CLAUDE.md` and skill-file writes explicitly gated on user confirmation in the output?
5. Does every `CLAUDE.md` draft entry use today's concrete date?

If any check fails, revise and re-verify. Iterate up to 3 times. If the third attempt still fails, surface the unresolved gap to the user rather than delivering silently degraded output.
