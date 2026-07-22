---
name: prd-eval-codex
description: "Evaluate a PRD against the 12-criterion EvalPRD rubric using OpenAI Codex CLI (GPT-5.5 at xhigh reasoning) as the evaluator. Same outputs as prd-eval: PASS/FAIL scorecard with evidence, GO/REVISE/HOLD gate, P0/P1/P2 fix plan, task DAG. Fire ONLY on explicit codex cues: prd-eval-codex, EvalPRD with codex, codex-graded PRD, GPT-5.5 PRD eval. Plain EvalPRD belongs to prd-eval; writing a PRD belongs to prd-writer. Requires the codex CLI on PATH."
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
---

# PRD Eval (Codex variant)

Evaluate a PRD against the 12-criterion EvalPRD rubric. Evaluation runs on **OpenAI Codex CLI** using `gpt-5.5` at `xhigh` reasoning — not in this Claude session. Each of the three output modes (scorecard, fix plan, agent tasks) becomes one `codex exec` call, mirroring how the hosted service calls the model three separate times.

Use this skill when the user wants a second-model opinion, a cross-model diff against `prd-eval`, or when they explicitly name Codex / GPT-5.5 as the evaluator. Agreement stats are not auto-computed — see "Fidelity vs. hosted EvalPRD service" below.

## Success Criteria

A run is successful only if ALL of these are true:

1. **Valid JSON per mode.** Every output file that was requested parses as JSON and matches its schema's `required` field list.
2. **Correct gate casing.** `readiness_gate.state` is UPPERCASE `GO` | `REVISE` | `HOLD`.
3. **Evidence present.** Every criterion verdict has ≥1 direct PRD quote with `{section, page}`. No PASS without a supporting quote.
4. **Correct tuning knobs applied.** Evidence count, fix-plan limit, task-hour range, and feature_filter match what the user requested (or defaults).
5. **Variance surfaced when relevant.** If the caller runs the skill more than once on the same PRD and gets different gate verdicts, the response labels the swing as model variance rather than presenting the latest verdict as durable truth.

## Variance guidance (important)

Codex at `xhigh` produces **stochastic** rubric verdicts. Expect ±2–3 criteria swing on consecutive runs of the same PRD. In the 2026-04-17 packpilot session, three consecutive runs on materially unchanged text produced HOLD 5/11, REVISE 8/11, and HOLD 6/11 — C8 and C10 flipped FAIL→PASS→FAIL on text that did not change.

- **For defensible single-number gate reporting**, run the skill 3–5 times on the same PRD cut and take the median.
- **For content-quality tracking across versions**, report the fix-plan P0 count trend — it is the most monotonic signal in the rubric output.
- **Do NOT** present a single-shot gate verdict as durable truth when the caller is tracking week-over-week PRD health.

## Failure diagnosis (read this before retrying)

Always capture stderr to a file (`2>"$ERR_FILE"`) and read it — Codex prints the real cause there. If a call exits non-zero immediately, returns 0 bytes, or the output file stays empty, the cause is almost always one of:

1. **Broken `~/.codex/config.toml` (most common hard failure).** Codex validates the entire user config before any model call; a single unknown or invalid key aborts every `codex exec` with `Error loading config.toml: <key> ...` and a non-zero exit and no output. **Fix:** read the error — it names the offending key and line — and tell the user the exact correction (for example, `service_tier` must be `fast` or `flex` in current Codex; older values like `priority` are rejected). For a one-run bypass without editing the user's config, add `--ignore-user-config` (auth still works, but the user's model/MCP defaults are dropped, so keep `-m gpt-5.5` explicit). Do not edit the user's config silently. The Prerequisites health note below makes the skill detect this on the first call.
2. **Context-window exceeded.** Prompt + PRD over ~50K tokens silently truncates or fails. Since the JSON schema now travels via `--output-schema` (not embedded in the prompt), the prompt is already smaller; if it is still too large, trim `system-prompt.md` content or shorten the PRD excerpt.
3. **Auth token expired.** Surfaces as a stderr auth error. **Fix:** run `codex login` and retry.

**Do not retry at lower reasoning effort as a first response.** Lowering `model_reasoning_effort` from `xhigh` to `medium` does not fix any of the above; it just delays the diagnosis. Read `$ERR_FILE` first.

## When to use

Fire only when the user explicitly asks for the Codex variant:

- "run EvalPRD on this PRD via codex" / "use codex to grade my PRD"
- "score my PRD with GPT-5.5" / "xhigh PRD eval"
- "second-opinion PRD eval — run it on codex"
- direct `/prd-eval-codex` invocation

**Do not fire** for:
- plain "prd-eval", "EvalPRD", "C1-C12", "readiness gate" without a codex cue → use `prd-eval` (in-session Claude)
- "review this PRD" / "audit my PRD" / stakeholder critiques → use `prd-review`
- "draft a PRD" / "write a PRD" → use `prd-writer`

If the user says "review with codex" without naming the rubric, ask one clarifying question before choosing between `prd-eval-codex` and `codex review`.

## Prerequisites

1. **Codex CLI installed and authenticated.** Verify:
   ```bash
   CODEX_BIN=$(which codex 2>/dev/null || echo "")
   [ -z "$CODEX_BIN" ] && echo "NOT_FOUND" || echo "FOUND: $CODEX_BIN"
   ```
   If `NOT_FOUND`, stop and tell the user: "Codex CLI not found. Install with `npm install -g @openai/codex` then run `codex login`." Do not try to install it.
2. **Codex config must load.** A single invalid key in `~/.codex/config.toml` aborts every `codex exec` with `Error loading config.toml: <key> ...` before any model call. You do not need a separate paid health call — the first real evaluation call fails fast with that message on stderr, so always capture stderr (`2>"$ERR_FILE"`) and, on a non-zero exit with no output, grep it for `Error loading config.toml`. If present, surface the named key to the user (see Failure diagnosis #1) and offer `--ignore-user-config` as a one-run bypass. Do not edit the user's config without asking.
3. **PRD text accessible as plain text.** `.md` / `.txt` work directly. For `.pdf` or `.docx`, the user is responsible for providing extracted text. If a CLI extractor is not already installed, ask the user to paste the text rather than installing tools.
4. **Network access.** Codex calls OpenAI; an unauthenticated or offline machine will fail with an auth error on the first call.

## Workflow

1. **Locate the PRD.** Ask if not provided. Accept a file path, pasted text, or URL to a local file. If extraction fails, ask for plain text. Save the PRD content to `$PRD_FILE` (a tempfile) so every codex call reads from the same on-disk source.
2. **Confirm which outputs to produce** and collect tuning knobs. Ask:
   - Which outputs: (a) scorecard only, (b) scorecard + fix plan, (c) scorecard + agent tasks, (d) all three. Default: all three.
   - Scorecard: `evidence_per_criterion` (0–3, default 1), `fail_on_missing` (default true), optional `peer_reviews` for agreement stats, `rubric_version` (default "v1.0").
   - Fix plan: `limit` (default 10), `include_acceptance_tests` (default true), `time_horizon_days` (default 10, advisory).
   - Agent tasks: `task_hours_min`/`task_hours_max` (default 2/4), optional `feature_filter` array, `emit_mermaid` (default false).
3. **Read the rubric files.**
   - `references/system-prompt.md` — verbatim EvalGPT system prompt; embed it in each codex prompt.
   - `references/output-schemas.md` — JSON schemas for each output mode; extract the current mode's schema block to `$SCHEMA_FILE` and pass it via `--output-schema` (not embedded in the prompt).
   - `references/rubric.md` — quick-reference table for summaries.
   These are symlinked from the `prd-eval` skill to keep a single source of truth. Do not duplicate them.
4. **Build one codex prompt per requested output mode.** See "Prompt construction" below. Each prompt is one-shot, ephemeral, and self-contained — no session reuse, no state sharing across modes. This matches the hosted service's three-call pattern.
5. **Run each codex call**, capture the JSON, validate against the schema, and summarize. See "Invoking Codex" and "Validation" below.
6. **Summarize.** Lead with the readiness gate + pass count (e.g., "HOLD — 2/12 pass"), list failed gating criteria, top 3 P0 fixes, and total task hours. Under 15 lines. Offer: "Want the full JSON, a Markdown report, or to drill into a specific criterion?"

## Invoking Codex

Every call uses the same base invocation — `gpt-5.5` at `xhigh`, ephemeral, the prompt piped in on stdin, the JSON schema enforced with `--output-schema`, and output written to a tempfile for reliable capture. `$PROMPT_FILE` holds the assembled prompt and `$SCHEMA_FILE` holds this mode's JSON Schema (see "Prompt construction"):

```bash
OUT_FILE=$(mktemp /tmp/prd-eval-codex.XXXXXXXX)
ERR_FILE=$(mktemp /tmp/prd-eval-codex.XXXXXXXX)
codex exec \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  --skip-git-repo-check \
  --ephemeral \
  --output-schema "$SCHEMA_FILE" \
  -o "$OUT_FILE" \
  - < "$PROMPT_FILE" \
  2>"$ERR_FILE"
cat "$OUT_FILE"
```

**Prompt on stdin, not argv.** Pass `-` as the prompt and pipe the prompt file (`- < "$PROMPT_FILE"`). The file's EOF closes stdin cleanly, so there is no hang and no need for a `< /dev/null` redirect, and the prompt is not subject to the argv size limit. Do not pass the prompt as a positional `"$(cat ...)"` string.

**`--output-schema "$SCHEMA_FILE"`** constrains Codex's final message to the mode's JSON Schema at generation time. Verified on codex-cli 0.130.0 — all three modes return fully conformant output (e.g. scorecard with 12 criteria, uppercase gate, evidence per criterion; agent-task DAG with valid edges). One requirement: Codex's structured-output mode demands that every object's `required` list **all** its properties, so the schema must be normalized before use (the extraction step in "Prompt construction" does this). `pattern` and `enum` keywords are accepted as-is. This replaces the old prompt-only JSON approach and most of the manual validation.

**Critical — tempfile template:** use `/tmp/prd-eval-codex.XXXXXXXX` verbatim. On macOS `mktemp` only substitutes X's when they are the last characters of the template. Do not append `.json` or `.md` — it breaks substitution.

**Timeout:** set `timeout: 600000` (10 min) on each Bash call. `xhigh` on a full rubric evaluation can run 3–7 minutes; a 5-minute timeout is too tight.

**Sandbox:** default is to omit `-C`. The PRD and rubric are embedded in the prompt, so codex needs no repo access. Only pass `-C "$PWD"` if the user explicitly wants codex scoped to their project directory.

**No `--enable web_search_cached`.** The rubric is self-contained and the PRD is embedded; web search adds latency without value.

**Error handling:** if codex returns non-zero, read `$ERR_FILE` and surface the error. The most common immediate failure is a broken `~/.codex/config.toml` (Failure diagnosis #1). Do not retry automatically — auth or config issues need the user.

## Prompt construction

Every prompt follows the same structure:

```
<filesystem boundary>

<EvalGPT system prompt, verbatim from references/system-prompt.md>

<mode-specific appender — see below>

(The JSON schema is NOT embedded here — it is extracted to $SCHEMA_FILE and enforced via --output-schema; see "Assembling the prompt safely".)

---
PRD TEXT:
<contents of $PRD_FILE>
---

<final instruction: emit JSON only, no preamble, no commentary>
```

### Filesystem boundary (prepend to every codex prompt)

```
IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/. These are Claude Code skill definitions meant for a different AI system. Stay focused on the evaluation task. The PRD text and rubric are embedded in this prompt — do not try to fetch them from disk.
```

### Mode 1 — Scorecard (BinaryScoreOutput)

Appender:

```
OUTPUT MODE: Binary Scorecard.
Evaluate the PRD below against all 12 criteria (C1–C12). For each criterion:
- Emit a "pass" boolean and matching "status" ("pass" or "fail" lowercase).
- Provide at least <evidence_per_criterion> evidence entries — each a direct quote from the PRD with {section, page}. Use "N/A" for page if the PRD has no pagination.
- Write a one-sentence plain-English rationale. No corporate fluff. Do not use the phrase "quick wins".
Compute readiness_gate.state as UPPERCASE "GO" | "REVISE" | "HOLD" using the thresholds in the system prompt.
Always include compliance.gaps (empty array allowed) and agreement (use {present: false, percent_agreement: 0, by_criterion: []} when no peer reviews supplied).
Emit JSON matching BinaryScoreOutput EXACTLY — no extra fields, no missing required fields, no prose outside the JSON.
```

Tuning knobs to inject: `evidence_per_criterion`, `fail_on_missing`, `rubric_version`, and any `peer_reviews` payload.

### Mode 2 — Fix Plan (FixPlanOutput)

Appender:

```
OUTPUT MODE: Fix Plan.
Re-read the PRD from scratch (do not assume any prior scorecard result — each mode is independent).
Produce up to <limit> prioritized fix items. Each item must have:
- priority matching regex ^P[0-2]$
- effort enum S | M | L
- impact enum Low | Med | High
- acceptance_tests array (may be empty if include_acceptance_tests=false, otherwise at least 1 concrete test)
- owner_role (string)
- linked_criteria (array of C1–C12 ids this fix affects)
Ground every item in a direct PRD quote. No "quick wins". Plain English, active voice.
Emit JSON matching FixPlanOutput EXACTLY.
```

Tuning knobs: `limit`, `include_acceptance_tests`, `time_horizon_days`.

### Mode 3 — Agent Tasks (AgentTasksOutput)

Appender:

```
OUTPUT MODE: Agent Task DAG.
Re-read the PRD from scratch. Decompose each feature into tasks sized between <task_hours_min> and <task_hours_max> hours.
Every task MUST include ALL of: id, feature, title, description, duration, est_hours, owner_role, entry, exit, test, entry_conditions, exit_conditions, tests, inputs, outputs, status.
The schema requires every field above even though the prose describes some as "optional" — emit populated arrays. Use one-element arrays mirroring the singular strings if no richer data is available.
duration must match regex ^[0-9]+(h|hr|hours?)$ (e.g., "2h", "3hours"). status ∈ ready | blocked | in_progress | completed.
edges[].type ∈ depends_on | blocks | related. Every from/to must reference an existing task id.
Set mermaid to a Mermaid diagram string if emit_mermaid=true; otherwise set mermaid to null (the normalized schema requires the key to be present, so emit null rather than omitting it).
Emit JSON matching AgentTasksOutput EXACTLY.
```

Tuning knobs: `task_hours_min`, `task_hours_max`, `feature_filter`, `emit_mermaid`.

### Assembling the prompt safely

Use a heredoc written to a tempfile; do not inline huge strings in shell variables (quoting issues will corrupt the prompt). The schema is no longer embedded in the prompt — it is extracted to its own file and passed via `--output-schema`.

Run this block **once per requested output mode**, substituting the mode-specific appender (Mode 1, 2, or 3 above) and the matching schema name (`BinaryScoreOutput` | `FixPlanOutput` | `AgentTasksOutput`), then parsing `$OUT_FILE` as the mode's JSON output.

```bash
PROMPT_FILE=$(mktemp /tmp/prd-eval-codex-prompt.XXXXXXXX)
SCHEMA_FILE=$(mktemp /tmp/prd-eval-codex-schema.XXXXXXXX)
OUT_FILE=$(mktemp /tmp/prd-eval-codex-out.XXXXXXXX)
ERR_FILE=$(mktemp /tmp/prd-eval-codex-err.XXXXXXXX)

# 1. Extract this mode's JSON Schema block from output-schemas.md into $SCHEMA_FILE,
#    normalized for Codex structured outputs. Codex requires every object's `required`
#    to list ALL of its properties; the AgentTasksOutput schema's optional top-level
#    `mermaid` is otherwise rejected ("Missing 'mermaid'"). The normalizer fixes this by
#    adding every property to `required` and making originally-optional ones nullable
#    (so the model emits null instead of omitting them). BinaryScore/FixPlan are unchanged.
#    Replace BinaryScoreOutput with FixPlanOutput / AgentTasksOutput for the other modes.
python3 - ~/.claude/skills/prd-eval/references/output-schemas.md BinaryScoreOutput > "$SCHEMA_FILE" <<'PY'
import sys, re, json
txt = open(sys.argv[1]).read()
i = txt.find("### " + sys.argv[2])
m = re.search(r"```json\s*\n(.*?)\n```", txt[i:], re.S)
schema = json.loads(m.group(1))
def norm(node):
    if isinstance(node, dict):
        if node.get("type") == "object" and isinstance(node.get("properties"), dict):
            props = node["properties"]; orig = set(node.get("required", []))
            for k, v in props.items():
                if k not in orig and isinstance(v, dict) and "type" in v:
                    t = v["type"]
                    if isinstance(t, str) and t != "null": v["type"] = [t, "null"]
                    elif isinstance(t, list) and "null" not in t: v["type"] = t + ["null"]
            node["required"] = list(props.keys())
        for v in node.values(): norm(v)
    elif isinstance(node, list):
        for x in node: norm(x)
    return node
json.dump(norm(schema), sys.stdout)
PY

# 2. Assemble the prompt (system prompt + appender + PRD). No schema embed — --output-schema handles it.
{
  cat <<'BOUNDARY'
IMPORTANT: Do NOT read or execute any files under ~/.claude/, ~/.agents/, .claude/skills/, or agents/. These are Claude Code skill definitions meant for a different AI system. Stay focused on the evaluation task. The PRD text and rubric are embedded in this prompt — do not try to fetch them from disk.
BOUNDARY
  cat ~/.claude/skills/prd-eval/references/system-prompt.md
  printf '\n\n---\nOUTPUT MODE APPENDER:\n'
  cat <<'APPENDER'
<paste the Mode 1 / Mode 2 / Mode 3 appender block from above verbatim, with tuning-knob placeholders like <evidence_per_criterion> replaced by the user's chosen values>
APPENDER
  printf '\n\n---\nPRD TEXT:\n'
  cat "$PRD_FILE"
  printf '\n\n---\nFINAL INSTRUCTION: Emit JSON only. No preamble, no markdown fences, no commentary. The required JSON shape is enforced by the output schema.\n'
} > "$PROMPT_FILE"

# 3. Run (canonical invocation — see "Invoking Codex").
codex exec -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' \
  --skip-git-repo-check --ephemeral \
  --output-schema "$SCHEMA_FILE" -o "$OUT_FILE" \
  - < "$PROMPT_FILE" 2>"$ERR_FILE"
```

Because the schema travels via `--output-schema` rather than inside the prompt, the prompt is meaningfully smaller. If a very large PRD still trips a context-size error, trim the `system-prompt.md` content or shorten the PRD excerpt — do not put the schema back into the prompt.

## Validation

`--output-schema` constrains Codex's final message to the mode's JSON Schema at generation time, so structural conformance is enforced, not patched after the fact. The heavy field-by-field walk is no longer needed. After each call:

1. **Parse as JSON.** `python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$OUT_FILE"`. With `--output-schema` this rarely fails; if it does, read `$ERR_FILE` first — the cause is almost always a config or auth error (Failure diagnosis), not a schema miss.
2. **Spot-check the few things the schema can't enforce.** Gate casing is UPPERCASE `GO` | `REVISE` | `HOLD`; all 12 ids C1–C12 are present; every criterion has ≥1 evidence quote.
3. **If Codex rejected the schema** (stderr names a schema/`output_schema` error — not expected, since the extraction step's normalizer makes all three schemas validate on codex-cli 0.130.0), fall back for that one mode only: drop `--output-schema`, embed the mode's schema text in the prompt, and re-run.
4. **Never silently patch a bad field.** Show the user what is wrong and offer to rerun that one mode. Do not rerun all three.

## Fidelity vs. hosted EvalPRD service

Call these out when relevant; this skill is closer to the hosted service than `prd-eval` (in-session) but still not identical.

- **Model differs.** Hosted service pins `claude-sonnet-4-5-20250929` at temperature 0.2 / 0.3. This skill uses `gpt-5.5` at `xhigh`. Expect different phrasing, different edge-case handling, and occasionally different verdicts. Document which evaluator was used when sharing results.
- **Schema enforced, not just prompted.** This skill passes each mode's JSON Schema to `codex exec --output-schema`, so Codex's output is constrained to the schema at generation time — much closer to the hosted service's structured-outputs request than `prd-eval` (in-session) can get. It still has no auto-retry loop on a validation miss; the light Validation spot-check is the only post-hoc guard.
- **Three independent calls, not a conversation.** Matches hosted behavior. Do not reuse a codex session across modes — each call must re-evaluate the PRD from scratch.
- **No inter-model agreement stats are auto-computed.** If the user wants a Claude vs. Codex cross-model agreement stat, run `/prd-eval` and `/prd-eval-codex` on the same PRD and diff the two scorecards manually (or ask for a diff summary).

## Evaluation principles (unchanged from prd-eval)

These apply identically regardless of evaluator. Include them in the prompt so codex enforces them:

- **Strict on gating criteria** — C3, C5, C10, C11, C12. A single ambiguous integration reference fails C5. A subjective "done" fails C10. A missing falsifiable bet or decision thresholds fails C12.
- **Evidence is mandatory.** Every verdict needs at least one direct PRD quote with `{section, page}`. No quote = FAIL.
- **No "quick wins".** The EvalGPT persona forbids the phrase.
- **Plain English, active voice, audit-ready.** No corporate fluff.
- **GxP overlay when relevant.** If the PRD implies regulated workflows, check for audit trails, RBAC, ALCOA+, 21 CFR Part 11 eSignatures, validation plan, HIPAA/PHI, Veeva/Vault / LIMS/EMR integration.

## Readiness gate

- **GO**: ≥10/12 pass AND all of {C3, C5, C10, C11, C12} pass AND <3 compliance gaps
- **REVISE**: 8–9/12 pass (or any gating fails but total ≥10)
- **HOLD**: ≤7/12 pass OR ≥3 compliance gaps

Emit the gate as `GO` / `REVISE` / `HOLD` (uppercase).

## References

- `references/system-prompt.md` — **read and embed in every codex prompt**. Verbatim EvalGPT system prompt with all 12 criterion definitions, pass/fail indicators, examples, failure mode taxonomy, GxP overlay, scoring gates, and output mode appenders. Shared with the `prd-eval` skill.
- `references/rubric.md` — quick-reference table for summaries and smell-test triage.
- `references/output-schemas.md` — verbatim JSON schemas + conformance notes. Extract the relevant schema block to `$SCHEMA_FILE` and pass it via `--output-schema`; do not embed it in the prompt.

## Presenting results

Keep summaries tight. Do not paste raw JSON unless asked.

- **Scorecard summary**: readiness gate, pass/fail count, failed gating criteria (one-line rationale each), top compliance gaps. Note evaluator: "Evaluated by Codex GPT-5.5 (xhigh)".
- **Fix plan summary**: P0 items fully (title + owner + effort), P1/P2 one-liners grouped by priority.
- **Agent tasks summary**: feature breakdown (task count + hours per feature), then total hours and task count.

Close with: "Want the full JSON, a Markdown report, or to drill into a specific criterion/fix/task? Want to rerun the same PRD through `/prd-eval` (in-session Claude) for a cross-model diff?"
