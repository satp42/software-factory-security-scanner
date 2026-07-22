---
name: skill-author-and-review
description: "Author a new agent skill from a source file or repo, or review an existing skill against the authoring standard. Scaffolds a conforming SKILL.md (frontmatter as a routing rule, bulky material under references/), runs the authoring and review checklist (name matches directory, description disambiguates from sibling skills, source fidelity, no proprietary data, progressive disclosure, size), and verifies the skill is discoverable. Use when the user says create, author, install, scaffold, package, or review a skill, or hands over a markdown file or GitHub repo to turn into one. For discovering or installing existing published skills use find-skills; for settings, hooks, and permissions use update-config."
metadata:
  version: 1.0.0
---

# Skill author and review

Turn source material into a conforming agent skill, or audit an existing skill against the standard. This skill follows the format it teaches: the procedure lives here, the reusable template and the full checklist live under `references/`.

## When to use

- Author a new skill from a markdown file, a GitHub repo, or a described behavior.
- Scaffold a skill from scratch.
- Review or audit an existing `SKILL.md` before committing or sharing it.

## When not to use

- Discovering or installing existing published skills: use `find-skills`.
- Settings, hooks, permissions, or env vars: use `update-config`.

## Inputs

Confirm these before scaffolding:

- The source material: a file path, a repo URL, or a description of the behavior.
- The scope: global (`~/.claude/skills/<name>/`) or a project (`<project>/.claude/skills/<name>/`). Default to global for personal or cross-project skills, project for team skills committed with a repo.
- Whether the user wants it committed afterward.

## The standard

- The directory name equals the `name`, and both use lowercase letters, numbers, and hyphens only. No underscores, no spaces.
- `SKILL.md` opens with YAML frontmatter. Required: `name` and `description`. Optional: `metadata`, `license`, `allowed-tools`, `compatibility`.
- The `description` is a routing rule, not a title. Write it in the third person, state what the skill does and when to fire it, include concrete trigger words, and disambiguate from any sibling skill with overlapping scope. The harness routes mostly on this field.
- The body is plain instructions. A reliable structure: what it does, when to use and when not, inputs, step-by-step procedure, validation, common failure modes.
- Progressive disclosure: keep `SKILL.md` lean. Push bulky templates, checklists, and long reference docs to `references/`, scripts to `scripts/`, and static assets to `assets/`. Point to them by relative path.

Copy `references/skill-template.md` as the starting skeleton. Run `references/authoring-checklist.md` as the gate.

## Authoring procedure

1. Read the source material in full. If it is a repo, clone it to the scratchpad and inventory every file before deciding what to bundle.
2. Choose the name: hyphen-case, names a real behavior, and checked against existing skills for collisions.
3. Choose scope and location.
4. Scaffold the directory. Copy bulky source material into `references/` verbatim. Exclude proprietary or client data by default (customer folders, recordings, transcripts, internal PDFs) and state the exclusion. Bundle only template and reference files; point to the source repo for examples.
5. Write `SKILL.md` from the template. Write the `description` as a routing rule and disambiguate it from siblings.
6. Preserve the source author's words. Add frontmatter and structure only; do not rewrite the user's content unless asked. When built from a file, the body should stay faithful to the source.
7. Run the review checklist.
8. Verify the skill is discoverable.

## Review gate

Run `references/authoring-checklist.md` whether authoring a new skill or auditing an existing one. The short form:

- `name` equals the directory name; lowercase and hyphens only.
- `description` is third person, states what and when, has trigger words, disambiguates from siblings, and stays within about 1024 characters.
- The body has a clear "when to use," is not bloated, and keeps bulky content in `references/`.
- No secrets, credentials, or proprietary client data are bundled.
- Internal reference paths resolve.
- If built from a source file, diff the body against the source to confirm fidelity.
- For a workflow skill (not a pure reference or style skill), it has success criteria and a verification step.

## Commit and share

- Skills under `~/.claude/skills` are the `8090-inc/8090-claude-skills` repo, whose `main` is protected and expects PR-based changes. Branch and open a PR, or ask first, rather than pushing to `main` directly.
- Author is Rohit Kelapure. Do not add Co-Authored-By lines or any AI attribution.
- Stage only the skill's own files. Do not sweep unrelated working-tree changes into the commit.

## Success Criteria

1. `name` matches the directory and the frontmatter parses.
2. The `description` routes correctly and disambiguates from sibling skills.
3. The `SKILL.md` body is faithful to the source (when there is one) and lean; bulky material sits in `references/`.
4. No proprietary or client data is bundled.
5. The skill is discoverable and invocable.

## Pre-Delivery Verification

Before reporting done, verify each success criterion: read the frontmatter, confirm `name` equals the directory, diff the body against any source, list the `references/` files, and confirm the skill appears in the available-skills list. Iterate up to three times. If a criterion still fails on the third pass, surface the gap to the user rather than reporting success.

## Common failure modes

- Underscores or spaces in the name. The format rejects them.
- A `description` written as a title with no trigger words, so the skill never routes.
- Everything inlined into `SKILL.md`, producing a bloated file. Move bulky content to `references/`.
- Bundling client data into a global skill.
- Committing to a protected `main`, or sweeping unrelated working-tree changes into the commit.
- Prose that miscounts its own references, for example "read both" above a list of three files.
