---
id: BP-003
title: Quality Enforcement Toolchain
type: blueprint
blueprint_type: feature
feature: F-003
---

# BP-003 — Quality Enforcement Toolchain

## Decision

Quality enforcement runs through five tools, all coordinated by pnpm scripts:

- **TypeScript compiler** (`tsc --noEmit`) — verifies the codebase typechecks against the strict config.
- **ESLint** (flat config; `eslint.config.mjs`) with `typescript-eslint` + `@eslint/js` — verifies TypeScript style and catches a curated set of common bugs.
- **Prettier** + `eslint-config-prettier` — keeps formatting concerns out of ESLint's domain.
- **remark-cli** with `remark-frontmatter`, `remark-preset-lint-consistent`, `remark-preset-lint-recommended` — verifies Markdown structure across `plugins/`.
- **Vitest** — unit tests for `src/` helpers.

## Pre-commit hook

`husky` installs a git hook that runs `pnpm run validate` before every commit. Authors who introduce broken manifests are caught locally rather than at PR time.

## CI

All five steps run on every push and PR. None are deferred to a nightly job — fast feedback is the priority.

## Dependency stewardship

Devtools are pinned to current major versions in `package.json` and resolved deterministically via `pnpm-lock.yaml`. The dependency-vulnerability scanner (sf-scan Lens 1) runs against this lockfile.
