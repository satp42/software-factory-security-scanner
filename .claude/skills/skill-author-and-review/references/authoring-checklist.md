# Authoring and review checklist

Run this whether authoring a new skill or auditing an existing one. Each line is pass or fail.

## Frontmatter

- [ ] `name` is present, lowercase letters, numbers, and hyphens only. No underscores or spaces.
- [ ] `name` equals the parent directory name exactly.
- [ ] `description` is present and written in the third person.
- [ ] `description` states what the skill does AND when to fire it, with concrete trigger words.
- [ ] `description` disambiguates from any sibling skill with overlapping scope (name the sibling and the boundary).
- [ ] `description` stays within about 1024 characters.
- [ ] Optional fields (`metadata`, `license`, `allowed-tools`, `compatibility`) are present only when they earn their place.

## Body

- [ ] Has a clear "when to use" and "when not to use."
- [ ] Reads as plain instructions, not marketing prose.
- [ ] Is lean. Bulky templates, checklists, and long reference docs live in `references/`, scripts in `scripts/`, assets in `assets/`.
- [ ] Internal references use relative paths that resolve.
- [ ] For a workflow skill (not a pure reference or style skill): includes success criteria and a pre-delivery verification step.

## Content safety and fidelity

- [ ] No secrets, credentials, tokens, or API keys.
- [ ] No proprietary or client data (customer folders, recordings, transcripts, internal PDFs). Point to the source repo for examples instead.
- [ ] When built from a source file, the body is faithful to the source. Diff it to confirm.
- [ ] The source author's words and tone are preserved. Only frontmatter and structure were added, unless the user asked for a rewrite.

## Discovery

- [ ] The skill appears in the available-skills list (or is invocable as `/<name>`) in a session that can see it.

## Commit and share (when asked)

- [ ] Target repo and branch confirmed. For `8090-inc/8090-claude-skills`, `main` is protected and expects PRs; branch and open a PR, or ask first.
- [ ] Author is Rohit Kelapure. No Co-Authored-By lines and no AI attribution.
- [ ] Only the skill's own files are staged. No unrelated working-tree changes are swept in.
