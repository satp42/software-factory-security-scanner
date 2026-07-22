---
name: deslop
description: "Apply strict rules of clear, plain, fact-based material writing, to clean up existing text or write new text: strip fluff, weasel words, jargon, em-dashes, partial bullets, and generated-prose slop patterns (hedge stacking, meta-commentary, low-density filler). Use when the user asks to deslop, de-slop, or tighten writing, invokes /deslop, or when finalizing PRDs, specs, or reports that must read plain and declarative. Do not trigger on unrelated writing tasks."
---

# Deslop

Apply the Rules of Material Writing below. This skill works in two modes. Pick the one that matches the request.

**Edit mode** — the user gives you existing text (a message, file, draft, email, spec, user story) and wants it cleaned up. Rewrite it in place to satisfy every rule, preserving the author's meaning and intent. Return the cleaned text, not a critique. Keep commentary minimal: deliver the rewrite, then optionally note any change that altered meaning or any place a fact is missing.

**Generate mode** — the user asks you to write something new "following the deslop rules" or "deslopped". Draft the new content so it satisfies every rule from the start.

**Deliverable finalization mode** — the text being finalized is a structured deliverable (PRD, spec, report, tables, flags, callouts, acceptance criteria) that must read plain, declarative, and high-density. In addition to the rules below, load `references/generated-prose-patterns.md` and apply its numbered pattern rules (concessive openers, antithesis, meta-commentary, hedge stacking, rule-of-three padding, voice and person) and its information-density test on the final text.

In both modes:

1. Do not invent facts. If a rule requires specificity the source lacks (a constraint, a number, a definition), keep or leave the wording open and flag the gap with a short bracketed note like `[author: specify the constraint]`.
2. Match the output format to the medium. Emails and most prose stay all-text. Use Mermaid diagrams only where logic genuinely benefits and the medium expects them.
3. If editing a file, write the deslopped version back as a new file (do not silently overwrite the original unless asked) and present it. If working inline, reply inline.

## Rules of Material Writing

### Clear and Plain Language
- Always use clear and plain English
- Never use fluffy language
- State exactly what happens—clarity matters above everything else
- Stick to the facts
- Use active language

### Structure and Format
- Write in narrative form to encourage connectivity
- Avoid hiding behind partially complete bullet points and corporate jargon
- Maintain consistent format for similar items
- Define all acronyms at least once (like academic papers)
- Unless absolutely necessary (e.g. telling user to run a command) avoid code snippets. Instead use mermaid diagrams and describe the logic. Do not over use diagrams particularly in outputs where expectation is to have all text (e.g. most emails)

### Specificity and Precision
- State all technical or business constraints and non-negotiables
- When writing user stories or feature descriptions be precise and use concise language. Ensure each story or user journey is isolated and clearly stated
- Describe all critical business logic rules or formulas in plain language

### Language Guidelines and Style
- Avoid ambiguous wording and weasel words
- Use adverbs sparingly and only when it contributes to the readability or content meaningfully
- Use adjectives only when necessary and substantiated, ideally by data
- Avoid em-dashes in sentences. Unless it materially changes the meaning, replace them with fluent english sentences that either use commas or break into two sentences. This rule doesn't apply for em-dashes that are used to demarkate bullets or similar.
- the letter after a colon should be capitalized if a complete sentence follows.

## Pre-Delivery Verification

Before returning the rewrite, check the actual final text against each item below. Fix and recheck (up to 3 passes) if any fail:

1. Passive voice removed where active works.
2. No fluff, weasel words, or unexplained jargon.
3. Every acronym defined on first use.
4. Constraints, rules, and formulas stated explicitly in plain language.
5. Adverbs and adjectives trimmed to what earns its place.
6. In-sentence em-dashes replaced with commas or separate sentences.
7. Post-colon capitalization correct.
8. Bullet points are complete thoughts, not fragments; prose is narrative where it should be.

If a check still fails after 3 passes, deliver the rewrite anyway and flag the specific unresolved item rather than silently shipping a failing check.
