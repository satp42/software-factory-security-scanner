#!/usr/bin/env python3
"""
writing-model-council batch orchestrator.

Fans out N recipient prompts × 3 models = 3N parallel CLI calls with controlled
concurrency. Each (recipient, model) gets its own output file. Produces a
manifest JSON with per-call status + duration.

Input JSON format:
[
  {"id": "01-crispr", "prompt": "..."},
  {"id": "02-replimune", "prompt": "..."},
  ...
]

Output layout:
  <out-dir>/
    <id>/
      codex.txt
      gemini.txt
      claude.txt
    manifest.json

Usage:
    python3 run_council_batch.py \
      --input <path-to-recipients.json> \
      --out-dir <dir> \
      [--max-workers 15] \
      [--timeout 300]

Exit 0 if at least 80% of calls succeeded; 1 if more than 20% failed.
"""
import argparse
import concurrent.futures
import json
import pathlib
import shutil
import subprocess
import sys
import time


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _strip_codex_ansi(text: str) -> str:
    """Codex writes a clean message via -o flag. If -o was missing, fall back to stdout."""
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def run_model(model: str, prompt_text: str, out_path: pathlib.Path, timeout: int) -> dict:
    """Dispatch to the right CLI based on model name."""
    binary = _which({"codex": "codex", "gemini": "gemini", "claude": "claude"}[model])
    if not binary:
        return {"model": model, "status": "skipped", "reason": f"{model} CLI not found"}

    start = time.time()
    try:
        if model == "codex":
            proc = subprocess.run(
                [
                    binary, "exec",
                    "-m", "gpt-5.5",
                    "-c", 'model_reasoning_effort="high"',
                    "--skip-git-repo-check",
                    "--ephemeral",
                    "-o", str(out_path),
                    prompt_text,
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            if not out_path.exists() or out_path.stat().st_size == 0:
                out_path.write_text(proc.stdout or "")
            status = "ok" if proc.returncode == 0 and out_path.stat().st_size > 0 else "err"
            return {
                "model": model, "status": status, "returncode": proc.returncode,
                "duration_s": round(time.time() - start, 1),
                "stderr_tail": (proc.stderr or "")[-300:],
            }

        elif model == "gemini":
            proc = subprocess.run(
                [
                    binary,
                    "--prompt", prompt_text,
                    "-m", "gemini-3-pro-preview",  # default is 2.5; pin to 3 Pro
                    "--approval-mode", "plan",
                    "--skip-trust",
                    "--output-format", "text",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            out_path.write_text(proc.stdout or "")
            status = "ok" if proc.returncode == 0 and len(proc.stdout or "") > 0 else "err"
            return {
                "model": model, "status": status, "returncode": proc.returncode,
                "duration_s": round(time.time() - start, 1),
                "stderr_tail": (proc.stderr or "")[-300:],
            }

        elif model == "claude":
            proc = subprocess.run(
                [binary, "-p"],
                input=prompt_text,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True,
            )
            out_path.write_text(proc.stdout or "")
            status = "ok" if proc.returncode == 0 and len(proc.stdout or "") > 0 else "err"
            return {
                "model": model, "status": status, "returncode": proc.returncode,
                "duration_s": round(time.time() - start, 1),
                "stderr_tail": (proc.stderr or "")[-300:],
            }

    except subprocess.TimeoutExpired:
        return {"model": model, "status": "timeout", "duration_s": timeout}
    except Exception as e:
        return {"model": model, "status": "err", "reason": str(e),
                "duration_s": round(time.time() - start, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to recipients JSON")
    ap.add_argument("--out-dir", required=True, help="Directory for outputs")
    ap.add_argument("--max-workers", type=int, default=15, help="Concurrent calls")
    ap.add_argument("--timeout", type=int, default=300, help="Per-call timeout seconds")
    args = ap.parse_args()

    recipients = json.loads(pathlib.Path(args.input).expanduser().read_text())
    out_dir = pathlib.Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    models = ["codex", "gemini", "claude"]
    tasks = []
    for r in recipients:
        rid = r["id"]
        rdir = out_dir / rid
        rdir.mkdir(parents=True, exist_ok=True)
        for m in models:
            tasks.append({
                "id": rid,
                "model": m,
                "prompt": r["prompt"],
                "out_path": rdir / f"{m}.txt",
            })

    print(f"Recipients: {len(recipients)}")
    print(f"Total calls: {len(tasks)}  ({len(recipients)} × {len(models)} models)")
    print(f"Max workers: {args.max_workers}  ·  Timeout: {args.timeout}s per call")
    print(f"Out dir: {out_dir}")
    print("Starting batch...\n", flush=True)

    t0 = time.time()
    results = []
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futures = {
            ex.submit(run_model, t["model"], t["prompt"], t["out_path"], args.timeout):
                (t["id"], t["model"])
            for t in tasks
        }
        for fut in concurrent.futures.as_completed(futures):
            rid, model = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"model": model, "status": "err", "reason": str(e)}
            r["id"] = rid
            results.append(r)
            completed += 1
            status = r.get("status", "?")
            dur = r.get("duration_s", "?")
            print(f"  [{completed:>3}/{len(tasks)}] {rid:<28} {model:<6} -> {status} ({dur}s)",
                  flush=True)

    wall = round(time.time() - t0, 1)
    by_status = {}
    for r in results:
        s = r.get("status", "?")
        by_status[s] = by_status.get(s, 0) + 1

    manifest = {
        "input": args.input,
        "out_dir": str(out_dir),
        "wall_clock_s": wall,
        "total_calls": len(tasks),
        "by_status": by_status,
        "results": results,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\nWall clock: {wall}s")
    print(f"By status: {by_status}")
    ok_pct = (by_status.get("ok", 0) / len(tasks)) * 100
    print(f"Success rate: {ok_pct:.1f}%")
    return 0 if ok_pct >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
