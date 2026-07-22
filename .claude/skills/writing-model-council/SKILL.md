---
name: writing-model-council
description: Query GPT-5.5 (Codex), Gemini 3.1 Pro, and Claude (CLI) in parallel against a single prompt or prompt file. Produces a Perplexity-style three-section convergence report (Where Models Agree / Where Models Disagree / Unique Discoveries) plus a recommended synthesis. Use when stuck on a hard creative or strategic writing question and multi-model triangulation breaks the loop. Triggers - "writing council", "model council", "consult the council", "ask all models", "multi-model writing", "council prompt".
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# writing-model-council

Ask three frontier models the same writing/strategy question, then synthesize where they agree, where they diverge, and what each found that the others missed. Output mirrors the Perplexity multi-model comparison format.

## When to use

- A creative or strategic writing problem has cycled through 3+ single-model iterations without converging
- A voice/tone question where you want triangulation across models (e.g., "what would Chamath actually say here")
- A pre-commit gut-check on a tricky decision where you want independent opinions

## Workflow

### Step 0: Resolve input

The user invokes the skill with either:
- A file path: `/writing-model-council ~/path/to/prompt.md`
- An inline prompt: `/writing-model-council "What's the sharpest one-line definition of operating leverage?"`

If file path, use it directly. If inline, write the prompt to `$RUN_DIR/prompt.md` (created in Step 1).

### Step 1: Create run directory

```bash
TS=$(date +%Y%m%d-%H%M%S)
if [ -n "$CLAUDE_JOB_DIR" ]; then
  RUN_DIR="$CLAUDE_JOB_DIR/council-$TS"
else
  RUN_DIR="$HOME/projects/outbound/council-$TS"
fi
mkdir -p "$RUN_DIR"
echo "RUN_DIR=$RUN_DIR"
```

### Step 2: Invoke the orchestrator

```bash
python3 ~/.claude/skills/writing-model-council/scripts/run_council.py \
  --prompt "<prompt-path>" \
  --out-dir "$RUN_DIR"
```

The orchestrator fans out 3 parallel subprocess calls (codex, gemini, claude), each with a 5-minute timeout, and writes:
- `codex.txt` — GPT-5.5 output
- `gemini.txt` — Gemini 3.1 Pro output
- `claude.txt` — Claude (CLI default) output
- `status.json` — per-model status manifest (success/error, duration, exit code)

The script returns when all three models complete or time out. Total wall-clock is bounded by the slowest model (~5 min worst case).

**If running in a background job (CLAUDE_JOB_DIR is set):** invoke the orchestrator with `run_in_background: true` and wait for the completion notification. Otherwise, run it synchronously with `timeout: 360000` (6 min).

### Step 3: Verify outputs

```bash
cat "$RUN_DIR/status.json"
wc -l "$RUN_DIR"/{codex,gemini,claude}.txt 2>/dev/null
```

For each model whose `status.json` entry shows `"status": "ok"`, read the full output file. For any that show `"status": "err"` or `"status": "timeout"`, exclude that model from the synthesis and annotate the gap in the final report.

### Step 4: Synthesize the convergence report

Read all three output files. Produce a single markdown report at `$RUN_DIR/council_report.md` with this exact structure:

```markdown
# Council Report: <one-line prompt summary>

**Prompt:** `<path or inline>`
**Run dir:** `<absolute path>`
**Date:** <ISO date>
**Models:** GPT-5.5 (Codex), Claude Opus 4.7, Gemini 3.1 Pro

## Where Models Agree

| Finding | GPT-5.5 | Claude | Gemini | Evidence |
|---|:---:|:---:|:---:|---|
| <finding shared by ≥2 of 3 models> | ✓ | ✓ | ✓ | <1-line citation from each model's output> |

## Where Models Disagree

| Topic | GPT-5.5 position | Claude position | Gemini position | Why they differ |
|---|---|---|---|---|
| <topic> | <terse summary> | <terse summary> | <terse summary> | <1-line interpretation> |

## Unique Discoveries

| Model | Unique finding | Why it matters |
|---|---|---|
| GPT-5.5 | <something only GPT raised> | <impact> |
| Claude | <something only Claude raised> | <impact> |
| Gemini | <something only Gemini raised> | <impact> |

## Recommended Synthesis

<One paragraph: the convergent answer, plus the strongest unique insights worth incorporating. End with an actionable next step.>
```

**Synthesis rules:**
- "Agree" rows require an explicit, verifiable claim from ≥2 of the 3 model outputs. Don't infer agreement; cite it.
- "Disagree" rows must show the actual divergence in each model's words (paraphrased ≤15 words per cell).
- "Unique Discoveries" must be genuinely unique — not just phrased differently. If two models said the same thing in different words, it goes in "Agree".
- If a model timed out or errored, mark its column "(N/A — <reason>)" and proceed with the remaining models.

### Step 5: Present

Print the report inline in chat. Print the absolute path of `council_report.md`. Print the run directory so the user can inspect raw model outputs.

If the prompt explicitly asks for candidate outputs (e.g., "write 3 versions of X"), include a separate **Candidates** section listing each model's top candidates side-by-side, scored against any rubric the prompt provided.

## Failure modes

| Failure | Handling |
|---|---|
| Codex auth error | Surface error; tell user to run `codex login`. Continue with the other 2 models. |
| Gemini auth error | Surface error; tell user to check `GEMINI_API_KEY` env var or run `gemini auth`. Continue with the other 2 models. |
| Claude CLI not found | Skip the Claude column. The synthesizing session is also Claude, so note "Claude column from synthesizer" in the report. |
| One model times out | Annotate "(N/A — timeout)" in the agreement/disagreement tables. |
| All models fail | Stop. Report the failure and the run dir for inspection. Do not produce a synthesis. |
| Output >100KB per model | Save full output. Summarize the first 50KB for synthesis context. Note the truncation. |

## Reference: CLI invocations

(For diagnostics if the orchestrator misbehaves. The orchestrator handles these directly.)

- **Codex (GPT-5.5):**
  ```bash
  codex exec -m gpt-5.5 \
    -c 'model_reasoning_effort="high"' \
    --skip-git-repo-check --ephemeral \
    -o "$OUT" "$PROMPT" < /dev/null
  ```
- **Gemini 3.1 Pro:**
  ```bash
  gemini --prompt "$PROMPT" -p --approval-mode plan > "$OUT" 2>&1
  ```
- **Claude (CLI default):**
  ```bash
  claude -p "$PROMPT" > "$OUT" 2>&1
  ```

## Notes

- This skill is read-only — it does not modify project source files. It writes only to the run directory under `$CLAUDE_JOB_DIR/` or `~/projects/outbound/`.
- Each run is fresh. No caching across runs.
- v1 has no retry logic. If a model fails, exclude it from synthesis.
- Skill is scoped to writing/strategy tasks. For code review use `codex-code-review`; for long video/audio use `meeting-processor`.
