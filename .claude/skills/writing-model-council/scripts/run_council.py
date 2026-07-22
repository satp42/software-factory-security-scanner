#!/usr/bin/env python3
"""
writing-model-council orchestrator.

Fans out a single prompt to GPT-5.5 (Codex), Gemini 3.1 Pro, and Claude (CLI)
in parallel via 3 subprocess.run calls. Each call has a 5-minute timeout.
Outputs land in <out-dir>/{codex,gemini,claude}.txt plus a status.json.

Usage:
    python3 run_council.py --prompt <path> --out-dir <dir>

Exit code is 0 if at least one model succeeded; 1 if all failed.
"""
import argparse
import concurrent.futures
import json
import pathlib
import shutil
import subprocess
import sys
import time

TIMEOUT_SECS = 300  # 5 min per model


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run_codex(prompt_text: str, out_path: pathlib.Path) -> dict:
    """Invoke OpenAI Codex (GPT-5.5) via codex exec."""
    binary = _which("codex")
    if not binary:
        return {
            "model": "GPT-5.5 (Codex)",
            "status": "skipped",
            "reason": "codex CLI not found on PATH",
            "out_path": str(out_path),
            "duration_s": 0,
        }

    start = time.time()
    try:
        # codex exec writes the agent's final answer to -o file.
        # --ephemeral = no session persistence; --skip-git-repo-check = don't require git.
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
            timeout=TIMEOUT_SECS,
            text=True,
        )
        duration = round(time.time() - start, 1)
        # codex writes the agent message to -o, but if -o was ignored, append stdout.
        if not out_path.exists() or out_path.stat().st_size == 0:
            out_path.write_text(proc.stdout or "")
        status = "ok" if proc.returncode == 0 and out_path.stat().st_size > 0 else "err"
        return {
            "model": "GPT-5.5 (Codex)",
            "status": status,
            "returncode": proc.returncode,
            "duration_s": duration,
            "out_path": str(out_path),
            "stderr_tail": (proc.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        return {
            "model": "GPT-5.5 (Codex)",
            "status": "timeout",
            "duration_s": TIMEOUT_SECS,
            "out_path": str(out_path),
        }
    except Exception as e:
        return {
            "model": "GPT-5.5 (Codex)",
            "status": "err",
            "reason": str(e),
            "duration_s": round(time.time() - start, 1),
            "out_path": str(out_path),
        }


def run_gemini(prompt_text: str, out_path: pathlib.Path) -> dict:
    """Invoke Gemini 3.1 Pro via the gemini CLI in headless mode."""
    binary = _which("gemini")
    if not binary:
        return {
            "model": "Gemini 3.1 Pro",
            "status": "skipped",
            "reason": "gemini CLI not found on PATH",
            "out_path": str(out_path),
            "duration_s": 0,
        }

    start = time.time()
    try:
        # --prompt = non-interactive headless mode (alias of -p, don't pass both).
        # --approval-mode plan = read-only, no permission prompts.
        # --output-format text = clean stdout without ANSI/JSON wrapping.
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
            timeout=TIMEOUT_SECS,
            text=True,
        )
        duration = round(time.time() - start, 1)
        out_path.write_text(proc.stdout or "")
        status = "ok" if proc.returncode == 0 and len(proc.stdout or "") > 0 else "err"
        return {
            "model": "Gemini 3.1 Pro",
            "status": status,
            "returncode": proc.returncode,
            "duration_s": duration,
            "out_path": str(out_path),
            "stderr_tail": (proc.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        return {
            "model": "Gemini 3.1 Pro",
            "status": "timeout",
            "duration_s": TIMEOUT_SECS,
            "out_path": str(out_path),
        }
    except Exception as e:
        return {
            "model": "Gemini 3.1 Pro",
            "status": "err",
            "reason": str(e),
            "duration_s": round(time.time() - start, 1),
            "out_path": str(out_path),
        }


def run_claude(prompt_text: str, out_path: pathlib.Path) -> dict:
    """Invoke Claude via the local claude CLI (one-shot non-interactive mode)."""
    binary = _which("claude")
    if not binary:
        return {
            "model": "Claude (CLI)",
            "status": "skipped",
            "reason": "claude CLI not found on PATH",
            "out_path": str(out_path),
            "duration_s": 0,
        }

    start = time.time()
    try:
        # -p = print mode (one-shot, non-interactive).
        # Pass prompt via stdin to avoid arg-length limits.
        proc = subprocess.run(
            [binary, "-p"],
            input=prompt_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECS,
            text=True,
        )
        duration = round(time.time() - start, 1)
        out_path.write_text(proc.stdout or "")
        status = "ok" if proc.returncode == 0 and len(proc.stdout or "") > 0 else "err"
        return {
            "model": "Claude (CLI)",
            "status": status,
            "returncode": proc.returncode,
            "duration_s": duration,
            "out_path": str(out_path),
            "stderr_tail": (proc.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        return {
            "model": "Claude (CLI)",
            "status": "timeout",
            "duration_s": TIMEOUT_SECS,
            "out_path": str(out_path),
        }
    except Exception as e:
        return {
            "model": "Claude (CLI)",
            "status": "err",
            "reason": str(e),
            "duration_s": round(time.time() - start, 1),
            "out_path": str(out_path),
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True, help="Path to prompt file")
    p.add_argument("--out-dir", required=True, help="Directory for outputs")
    args = p.parse_args()

    prompt_path = pathlib.Path(args.prompt).expanduser().resolve()
    out_dir = pathlib.Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not prompt_path.exists():
        print(f"ERROR: prompt file not found: {prompt_path}", file=sys.stderr)
        return 2

    prompt_text = prompt_path.read_text()
    print(f"Prompt: {prompt_path} ({len(prompt_text):,} chars)")
    print(f"Out dir: {out_dir}")
    print(f"Models: GPT-5.5 (Codex), Gemini 3.1 Pro, Claude (CLI)")
    print(f"Timeout per model: {TIMEOUT_SECS}s")
    print("Fanning out 3 parallel calls...", flush=True)

    runners = {
        "codex": (run_codex, out_dir / "codex.txt"),
        "gemini": (run_gemini, out_dir / "gemini.txt"),
        "claude": (run_claude, out_dir / "claude.txt"),
    }

    results = {}
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = {
            ex.submit(fn, prompt_text, out_path): key
            for key, (fn, out_path) in runners.items()
        }
        for fut in concurrent.futures.as_completed(futures):
            key = futures[fut]
            try:
                results[key] = fut.result()
            except Exception as e:
                results[key] = {"model": key, "status": "err", "reason": str(e)}
            print(f"  [{key}] -> {results[key].get('status')} ({results[key].get('duration_s', '?')}s)", flush=True)

    wall = round(time.time() - t0, 1)
    summary = {
        "prompt_path": str(prompt_path),
        "out_dir": str(out_dir),
        "wall_clock_s": wall,
        "results": results,
    }
    (out_dir / "status.json").write_text(json.dumps(summary, indent=2))
    print("\n=== status.json ===")
    print(json.dumps(summary, indent=2))

    ok_count = sum(1 for r in results.values() if r.get("status") == "ok")
    return 0 if ok_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
