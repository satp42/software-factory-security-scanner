---
id: WO-003
title: Multi-target build pipeline
type: work-order
blueprint: BP-002
dependencies-introduced:
  - "npm:rimraf"
files-affected:
  - "src/build-standalone.ts"
  - "src/build-hooks.ts"
  - "src/scaffold.ts"
  - "src/targets/"
  - "package.json"
---

# WO-003 — Multi-target build pipeline

## Goal

Implement the staged build pipeline described in BP-002. Each pnpm script invokes one stage; the orchestrating `pnpm run build` runs them in sequence.

## Steps

1. Install `rimraf` for cross-platform `dist/` cleanup.
2. Implement `src/build-hooks.ts` for compiling in-repo hook scripts.
3. Implement `src/build-standalone.ts` that loads every target from `src/targets/<name>.ts` and emits per-target bundles into `dist/<name>/`.
4. Implement `src/scaffold.ts` that writes the canonical manifest skeleton + a starter skill file.
5. Wire the pnpm script entries: `clean`, `build:hooks`, `build:standalone`, `scaffold`, `build`.

## Verification

- `pnpm run clean && pnpm run build` produces `dist/<target>/` directories for every registered target.
- `pnpm run scaffold` in an empty plugin directory creates a runnable starter plugin.
- Repeated `pnpm run build` calls produce byte-equivalent output (modulo timestamps).

## Notes

Target registration is filesystem-driven: any file matching `src/targets/<name>.ts` is loaded. New targets land by adding files; no central registry edits required.
