---
id: F-002
title: Multi-Target Distribution Pipeline
type: feature-requirements
product: PRD-001
---

# F-002 — Multi-Target Distribution Pipeline

## Behavior

A single build command produces validated, host-runnable plugin bundles for every configured target. Adding a new target is a matter of registering a new build step, not modifying any per-plugin source.

## Requirements

- **R-002.1.** A scaffold command generates the canonical plugin source layout from scratch.
- **R-002.2.** A build command produces host-specific bundles for every registered target in one run.
- **R-002.3.** A standalone bundle command produces a self-contained, distributable artifact per target.
- **R-002.4.** All build steps are idempotent — running the build twice produces byte-equivalent output (modulo timestamps).
- **R-002.5.** A `clean` command removes generated artifacts without touching source.

## Acceptance examples

- **AE-002.1.** Running `pnpm run scaffold` in an empty directory produces a working plugin source layout.
- **AE-002.2.** Running `pnpm run build` produces output directories for every registered host target.
- **AE-002.3.** Running `pnpm run clean && pnpm run build` produces the same output as a single `pnpm run build`.
