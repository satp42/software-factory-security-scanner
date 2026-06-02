---
id: WO-004
title: Lint, format, and Markdown toolchain
type: work-order
blueprint: BP-003
dependencies-introduced:
  - "npm:eslint"
  - "npm:@eslint/js"
  - "npm:typescript-eslint"
  - "npm:eslint-config-prettier"
  - "npm:prettier"
  - "npm:remark-cli"
  - "npm:remark-frontmatter"
  - "npm:remark-preset-lint-consistent"
  - "npm:remark-preset-lint-recommended"
files-affected:
  - "eslint.config.mjs"
  - ".remarkrc.mjs"
  - "package.json"
---

# WO-004 — Lint, format, and Markdown toolchain

## Goal

Wire up the static-analysis surface described in BP-003: ESLint for TypeScript, Prettier for formatting, remark for Markdown. All three run in CI; failures block merge.

## Steps

1. Install ESLint 10.x with `@eslint/js`, `typescript-eslint`, `eslint-config-prettier`.
2. Author `eslint.config.mjs` (flat config) — strict TypeScript + Prettier compatibility.
3. Install Prettier 3.x for formatting.
4. Install `remark-cli` + `remark-frontmatter` + the two `remark-preset-lint-*` packages.
5. Author `.remarkrc.mjs` registering both lint presets.
6. Wire the pnpm script entries: `lint`, `lint:ts`, `lint:md`.

## Verification

- `pnpm run lint:ts` exits 0 on well-formed code; non-zero with a clear violation message on a deliberate ESLint error.
- `pnpm run lint:md` exits 0 on well-formed Markdown; non-zero on a deliberate frontmatter violation.

## Notes

Markdown lint scope is intentionally limited to `plugins/**/*.{md,mdc}` so the project's own documentation (root README, design docs) is exempt from the same strict rules.
