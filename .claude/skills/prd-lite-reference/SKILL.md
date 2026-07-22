---
name: prd-lite-reference
description: "Canonical 8090 PRD-Lite template and writing rules. Load BEFORE authoring, generating, or reviewing any 8090 customer PRD-Lite so the document follows the required section structure, narrative style, and scope discipline. Use when the user mentions PRD-Lite, PRD template, Refinery, or an 8090 customer proposal. The prd-writer skill runs the workflow; this skill supplies the reference materials it must obey."
metadata:
  source: https://github.com/8090-inc/customer-prd-lite-reference-materials
  version: 1.0.0
---

# 8090 PRD-Lite reference

This skill carries the standard 8090 reference materials for writing a customer PRD-Lite. Read both reference files before you generate or review a PRD-Lite. They define the section structure and the writing style every 8090 PRD-Lite must follow.

## Reference files (read the two core files first)

- `references/8090-PRD-Lite-Template.md` — the required section structure and the content each section must contain, plus the authoring guidelines.
- `references/rules-of-material-writing.md` — the writing rules: plain English, narrative form, explicit acceptance criteria, no fluff.

Read both core files in full before drafting. Do not work from memory of the section names alone. `references/repo-README.md` is the upstream repository overview and is supplementary context only.

## The seven sections, in order

Work top to bottom. Drafting in order keeps the document aligned to the stated business problem, the current process, and the product description.

1. Business Problem
2. Current Process
3. Product Description
4. Product Features
5. Technical Requirements
6. Measurement
7. Appendix

## How to make a high signal PRD-Lite

These tips matter more than the section list. Apply them every time.

**Spend 30 to 40 percent of your effort on the Business Problem section.** It is the biggest gotcha. This section states why the customer needs the custom app and the specific outcomes they want. Include both the software goals and the process changes the customer owns. Get this right and the rest of the document stays bounded.

**Keep the Business Problem distinct from the Measurement metrics.** The Business Problem describes customer outcomes, including process changes the customer is responsible for. The Measurement section is different: it states 1 to 4 clear goals for the 8090 improvement engineering team, focused on the non-deterministic parts of the software. Do not mix customer-owned outcomes into the software success metrics.

**Hold the scope down.** Generative tools tend to explode requirements and add complexity the customer did not ask for. Solve only the problems stated in the Business Problem section, replace existing process steps, or address requirements stated explicitly in the meeting recordings. Do not invent features.

**Work sequentially from top to bottom.** Each section builds on the one above it. Drafting out of order produces a document that drifts from the business problem.

**Treat it as a pre-sales artifact first.** Content and format can change after the contract is signed. Make it detailed enough for well-understood scope, and concise enough to read in 20 to 30 minutes.

## Writing style (from the rules file)

- Clear and plain English. State exactly what the software does. Stick to the facts. Use active voice.
- Narrative form, not bullet points. Full sentences that connect.
- Define every acronym at least once.
- State all technical and business constraints and non-negotiables.
- Add explicit acceptance criteria for every feature or user story, covering the definition of done and the edge cases.
- Avoid weasel words. Use adverbs sparingly. Use adjectives only when data backs them.
- A PRD-Lite is frozen once approved. Changes produce a new version; add to the document rather than rewriting approved content.

## Customer examples

The upstream repository also holds example PRD-Lites under per-customer folders (Abbott, BridgeBio, Clover Health, DT, NSD, P&G). Those contain proprietary client recordings, transcripts, and PDFs, so they are not bundled into this skill. Pull them from the source repository when a worked example helps:

`gh repo clone 8090-inc/customer-prd-lite-reference-materials`
