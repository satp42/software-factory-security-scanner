---
name: product-shaping
description: "Product shaping workflow from problem framing through research and spec. Use when scoping a new product investment, writing a spec for a feature, researching competitors, gathering customer evidence, or auditing a codebase for a product decision. Triggers: shape, spec, scope this, research competitors, write a spec."
---

# Product Shaping

Three-phase workflow for turning a product idea into a validated spec with a clear next step.

**Output:** `spec-draft.md` (local) + validation plan (what to build/test next)

## Claude's Role

Act as a thinking partner, not a scribe. Throughout every phase:

- **Push for simplicity.** If a design takes more than 2 sentences to explain, it's too complex. Ask "do we actually need this?"
- **Surface trade-offs.** Don't present options neutrally — have a recommendation and defend it.
- **Question scope.** Every requirement should earn its place. If you can't point to evidence, push back.
- **Keep things tight.** No artifacts "for completeness." Every sentence, section, and file earns its spot.
- **Use clear, declarative writing** in spec content. Lead with the punch. Kill LLM tells.

---

## Phase 1: Frame + Scope Research

*Goal: define the problem statement, decide what research to run.*

### Define the problem

Ask and push on:

1. **Customer job to be done?** Not a feature description — what is the customer trying to accomplish?
2. **Why now?** What changed that makes this worth investing in?
3. **What does success look like?** If we ship this perfectly, what's different in 6 months?
4. **Who's the first customer?** Design partners, segments, deal types.
5. **What's the appetite?** Big bet or small bet? This constrains the shape.
6. **Bottom line business impact?** Revenue, deal velocity, attach rate. How fast? How quickly does this accelerate adoption?
7. **What can we DO with this beyond the feature?** GTM leverage — website, competitive wins, new vertical/segment. Always push: "if we build this, what does it unlock?"

Push hard:
- **"Is this unique product thinking?"** Replicating what exists, or pushing boundaries?
- **"Why are we building this?"** Don't accept at face value. Make the PM defend the problem.

### Scope the research

Once the problem is defined, propose a research plan. Ask the user which streams to run.

**Always available (web only):**
- Competitive research (how do other platforms solve this?)
- External API/docs review (relevant third-party API docs)
- Domain learning (unfamiliar industry/concept — research before designing)

**Available only with internal tool access (MCPs). If not connected, ask PM to paste in context manually:**
- Codebase exploration (what does our product already have?)
- Internal knowledge base (existing docs, wiki, prior specs)
- Customer evidence (call transcripts, CRM notes, support tickets)
- Meeting transcript search (prior decisions from internal/customer calls)

**Also recommend streams Claude thinks are valuable** based on framing. Be specific:
- "This touches payments — I'd recommend reviewing Stripe/Marqeta docs for API patterns"
- "Construction domain — suggest domain learning on lien waiver workflows before designing"
- "There's an existing API — I should audit the codebase to see what's reusable"

### Agree on search keywords

Before launching research, discuss keywords with the PM. The same problem has multiple terms — customers, sales reps, and engineers describe it differently. Build a keyword list and ask the PM to refine. These keywords drive transcript searches, CRM note searches, and codebase exploration.

---

## Phase 2: Research

*Goal: gather evidence across agreed streams.*

See [references/research-streams.md](references/research-streams.md) for detailed execution guide per stream.

### Execution overview

Write each research stream to standalone markdown files under `research/`. Only run streams that are available. If a stream requires internal tool access you don't have, skip it. If the PM pastes in raw context as a substitute, incorporate it into the relevant research file.

| Stream | Output file | Requires |
|--------|-------------|----------|
| Competitors | `research/{platform-name}.md` per platform + `research/best-practices.md` | Web access |
| Call transcripts | `research/call-evidence.md` | Call recording tool |
| CRM notes | `research/crm-evidence.md` | CRM tool |
| Support tickets | `research/support-evidence.md` | Support tool |
| Meeting transcripts | `research/transcript-evidence.md` | Meeting notes tool |
| System audit | `research/system-audit.md` | Codebase access |

### After research completes

Present a synthesis to the PM. Don't dump raw findings — distill into:
1. Key patterns from competitors (what the best platforms do, what to avoid)
2. Customer signal strength (how many deals, what stage, attributed quotes)
3. What we already have (reusable vs. missing)
4. Open questions the research raised

If streams were skipped due to missing tool access, flag what's missing and recommend the PM gather that context before finalizing.

---

## Phase 3: Shape

*Goal: converge on a design through conversation.*
*Output: `spec-draft.md` + validation plan.*

### How shaping works

This is conversational, not template-driven. Claude's job:

1. **Present research synthesis** as a starting point
2. **Ask pointed questions** forcing design decisions: "Should this be a new API or extend the existing one?" "Do you need X or is that scope creep?"
3. **Surface competitor patterns** when relevant: "Stripe does X, Unit does Y — which fits our constraints?"
4. **Track requirements** using R-notation (R0, R1, R2...). Ground each in evidence. Challenge any that can't be grounded.
5. **Mine transcripts for closed questions** — things already decided. Don't re-litigate settled decisions.
6. **Track open questions** — things needing customer input or internal alignment.

### When multiple shapes emerge

Capture 2-3 distinct approaches with a lightweight comparison table: trade-offs, complexity, which segments each serves best.

### Spec format

Write locally to `spec-draft.md`. Keep it tight — 20 lines max for context. Readable in 2 minutes.

```markdown
# [Feature Name]

## Context
[High-level context. ≤20 lines. Problem statement, why now, who it's for.]

## Principles
[Design principles and key requirements that constrain the solution. Non-negotiable truths.]

## Design
[Proposed design. High-level architecture: endpoints, happy path, flow diagram if helpful. "What," not "how."]

## Alternatives
[Other shapes considered, if any. Why rejected.]

## Open Questions
[What we still need to figure out. For each: why it matters.]

## Closed Questions
[Decisions already made, with source (call transcript, internal alignment, etc.)]
```

---

## When to Skip Phases

- **Strong customer evidence + competitive context already exist** → skip to Phase 3
- **Problem understood but need codebase audit** → run only system audit from Phase 2, then shape
- **Small bet or quality-of-life fix** → compress all three phases into a single conversation

## What Comes Next

| Next step | When |
|-----------|------|
| Build a prototype | Validate shape with customers before committing engineering |
| Write a pitch deck | Package for stakeholder buy-in or leadership review |
| Deep domain learning | Unfamiliar industry needing more research before building |
| Start building | Shape validated, open questions resolved, ready to ship |
