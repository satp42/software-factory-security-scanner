---
name: miro-sync-and-ship
description: "PackPilot Miro-to-PRD sync and ship workflow. Pulls the Miro board via MCP, diffs bidirectionally against the latest PRD flat file, applies REQ changes as surgical source edits, regenerates the PRD, updates the status email, and copies artifacts to OneDrive, Google Drive, and local deliverables. Use on miro sync, sync miro, miro-to-prd sync, or when Miro has cards the PRD has not absorbed."
---

# Miro Sync and Ship (PackPilot)

End-to-end workflow: pull Miro board, diff against current PRD, apply source edits for Miro-approved drift, regenerate the next PRD version, update the Ryan email, and distribute.

## Success Criteria

A run is successful only if ALL of these are true:

1. **Bidirectional diff completed.** Both Miro→PRD and PRD→Miro directions were checked and each divergence either resolved via source edit or explicitly deferred (stale Miro card awaiting archive, PRD-only REQ pending Miro addition).
2. **Regex covers placeholder IDs.** The REQ ID extractor captures `REQ-XXX-\d+`, `REQ-XXX-\d+[a-z]?`, AND placeholder suffixes (`xxx`, `TBD`, `?+`, `###`). Placeholder IDs are treated as "ID mint needed" state, not missing cards.
3. **Multiple Miro item types queried.** Sticky_note alone is insufficient. List sticky_note, card, app_card, shape, text — OR use `mcp__miro__context_explore` to discover existing types first.
4. **Pipeline pre-flight passes.** Before calling `pipeline.py --version N`, `PRD/vN.0/framing/` contains all expected files (copied from `v{N-1}.0/framing/`). Before step 15 subway, `PRD/process/release-map.json` exists and is fresh.
5. **All artifacts landed in 3 distribution targets** (or explicitly skipped with reason). OneDrive, Google Drive, local deliverables each either receive the new file or the run surfaces a lock/hand-edit warning.

## When to use

Fire on any of:
- "miro sync" / "sync miro" / "miro-to-prd sync"
- "reconcile miro"
- User shares a Miro card image and asks whether it's in PRD
- After a team session that edited Miro cards

Do not fire for:
- Routine PRD edits that don't touch REQ inventory
- Requests for just a diff without shipping changes

## Workflow

### 1. Pull Miro board

```text
mcp__miro__context_get  — board overview (summary + totals by prefix)
mcp__miro__board_list_items — item_type=sticky_note, limit=300 (primary)
mcp__miro__context_explore — if primary returns < expected, use to discover other item types
```

Board URL: `https://miro.com/app/board/uXjVGj2Khqs=/`

### 2. Extract REQ IDs with permissive regex

```python
RE = re.compile(r'REQ-([A-Z]+)-(\d{1,4}[a-z]?|[xX?#]+|TBD)', re.IGNORECASE)
```

For each sticky:
- Strip HTML (`<[^>]+>`), decode `&nbsp;` and `&amp;`, collapse whitespace
- Match the regex
- If suffix is a placeholder (`xxx`, `TBD`, `?`, `###`) → record as `{prefix}-<placeholder>` and flag "ID mint needed"

### 3. Bidirectional diff

Against `PRD/v{N}.0/PackPilot-PRD-v{N}-flat.md` (current cut):

```bash
grep -oE "^### REQ-[A-Z]+-[0-9a-z]+" <flat>
```

Classify each divergence:
- **Miro-only, real ID**: new REQ to add to PRD
- **Miro-only, placeholder ID**: flag for user to rename on Miro before sync
- **Miro-only, known-merged**: stale Miro card (user archives on Miro; no PRD change)
- **PRD-only**: either add to Miro OR remove from PRD (user decides)

Never unilaterally decide between "add to Miro" and "remove from PRD" on PRD-only items. **Always ask.**

### 4. Apply source edits

**For new REQs from Miro:**
- Pull full card text via `mcp__miro__context_get` on widget URL to get user story
- Draft REQ in matching style of existing feature file (REQ heading, user story, narrative paragraph with source cite, AC block)
- Insert into correct source file in `PRD/sections/feature-X-*.md`
- Update `PRD/process/generate-traceability-matrix.py` RELEASE_MAP with release assignment

**For PRD removals (user-approved):**
- Replace REQ block with HTML-comment tombstone noting reason + restoration path
- Remove RELEASE_MAP entry with matching comment
- Remove from deployment matrix in `PRD/v{N}.0/framing/phases.md` (requires new version)

### 5. Regenerate new PRD version

```bash
N_NEW=$((N_CURRENT + 1))
mkdir -p PRD/v${N_NEW}.0/framing PRD/v${N_NEW}.0/reviews
cp PRD/v${N_CURRENT}.0/framing/*.md PRD/v${N_NEW}.0/framing/
python3 PRD/process/pipeline.py --version ${N_NEW} --step all
```

Verify:
- Flat file exists at `PRD/v${N_NEW}.0/PackPilot-PRD-v${N_NEW}-flat.md`
- REQ totals match Miro: grep `^### REQ-` | count
- Subway map regenerated (check `release-map.json` mtime is fresh)

### 6. Update Ryan status email

Edit `deliverables/ryan-response.js`:
- Bump version label (v{N_CURRENT} → v{N_NEW})
- Update feature breakdown table (REQ counts per feature)
- Add / update "What changed since v{N_PRIOR}" paragraph with Miro sync summary
- Update totals row
- Update "N-REQ decomposition" sentence

Regenerate: `NODE_PATH=$(npm root -g) node deliverables/ryan-response.js`

### 7. Distribute artifacts

Three canonical destinations:

```text
~/Library/CloudStorage/OneDrive-SharedLibraries-Bausch&Lomb,Inc/Field Force Management Systems - Project Documents/PRD
~/Library/CloudStorage/GoogleDrive-rohit@8090.inc/Shared drives/8090 CSE Practice/Customers/Bausch+Lomb/PRD
projects/packpilot/deliverables
```

Files to distribute:
- PRD DOCX + PDF + traceability XLSX (the pipeline's `step_deliver` does this automatically)
- `ryan-response.docx` (copy manually — not in pipeline's step_deliver)
- `release-subway-map.pptx` (copy to `subway-maps/` subdirectory on OneDrive, and versioned name on Google Drive)

**Before any `cp` to a shared drive**, lock/hand-edit heuristic:
- If target mtime < 5 min ago → likely OneDrive syncing; retry once, then skip with warning
- If target size ≥ 3× source size → likely hand-edited; skip, recommend manual replace
- If target permissions include `rwx------` on a data file → likely locked; skip

## Pre-Delivery Verification

Before returning "done" to the user, verify each Success Criterion:

1. Was the diff truly bidirectional (both Miro→PRD and PRD→Miro checked)?
2. Did the regex match placeholder suffixes like `xxx` and `TBD`?
3. Were multiple Miro item types queried (or `context_explore` used first)?
4. Did `pipeline.py` succeed without the framing-missing fatal? Did subway step pre-flight the JSON?
5. Did the new DOCX + PDF + Ryan email reach all 3 destinations (or were lock/hand-edit skips explicitly reported)?

If any check fails, revise and re-verify. Iterate up to 3 times. If the third attempt still fails, surface the unresolved gap to the user rather than delivering silently.

## Variance and known edge cases

- **Placeholder Miro card IDs** (`REQ-SNM-xxx`): treat as "ID mint needed" and match the card to PRD by title similarity if the numeric ID isn't yet assigned.
- **Stale Miro cards** (merged into another REQ but not archived): flag for user archival; do not delete the PRD counterpart without explicit approval.
- **Hand-edited "Latest Version" files on OneDrive**: size and mtime patterns give them away. Do not overwrite — recommend manual replace.
- **Subway stops derived vs hardcoded**: the generator reads from `release-map.json` exported by the traceability script. If that file is stale, subway stops drift. Pipeline step 15 pre-flights the JSON freshness.
