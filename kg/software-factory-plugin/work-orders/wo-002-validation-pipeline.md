---
id: WO-002
title: Manifest validation pipeline
type: work-order
blueprint: BP-001
dependencies-introduced:
  - "npm:zod"
  - "npm:yaml"
files-affected:
  - "src/validate.ts"
  - "src/schema.ts"
  - "plugins/"
---

# WO-002 — Manifest validation pipeline

## Goal

Implement the per-plugin manifest validator described in BP-001. Establishes the canonical `plugins/<name>/plugin.yaml` schema and the validation entry point that downstream build stages depend on.

## Steps

1. Install `zod` for runtime schema validation and `yaml` for parsing the manifest files.
2. Define the canonical plugin manifest schema in `src/schema.ts`.
3. Implement `src/validate.ts` that walks `plugins/*` and validates each manifest, aggregating errors before exit.
4. Wire `pnpm run validate` to invoke `tsx src/validate.ts`.

## Verification

- A well-formed plugin passes; `pnpm run validate` exits 0.
- A malformed plugin (missing required field) exits non-zero with a `field-path: message`-shaped error.
- Errors aggregate across multiple plugins rather than short-circuiting on the first.

## Notes

The schema is intentionally minimal in WO-002 — additional fields land as the per-target emit work orders need them. The schema's authority over the build pipeline is a foundational invariant; do not bypass it in later work orders.
