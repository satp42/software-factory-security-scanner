---
id: WO-005
title: Test runner and pre-commit hook
type: work-order
blueprint: BP-003
dependencies-introduced:
  - "npm:vitest"
  - "npm:husky"
files-affected:
  - "package.json"
  - ".husky/pre-commit"
  - "src/__tests__/"
---

# WO-005 — Test runner and pre-commit hook

## Goal

Round out BP-003 with Vitest for unit tests and Husky for the pre-commit validation hook. Authors get instant local feedback before code reaches CI.

## Steps

1. Install `vitest` as the unit test runner; co-locate tests under `src/__tests__/` or alongside source as `*.test.ts`.
2. Install `husky` and run `husky` once to provision the `.husky/` directory.
3. Author `.husky/pre-commit` to invoke `pnpm run validate`.
4. Wire pnpm script entries: `test` (vitest run), `prepare` (husky install).

## Verification

- `pnpm run test` runs the in-tree test suite and exits 0 when all tests pass.
- A commit attempted with a malformed plugin manifest is rejected by the pre-commit hook.

## Notes

Vitest is chosen over Jest for speed and ESM-native semantics; the project is `"type": "module"` per BP-FND-001 so Vitest is the natural fit.
