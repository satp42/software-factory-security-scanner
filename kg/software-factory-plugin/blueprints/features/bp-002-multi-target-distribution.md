---
id: BP-002
title: Multi-Target Distribution Pipeline
type: blueprint
blueprint_type: feature
feature: F-002
---

# BP-002 — Multi-Target Distribution Pipeline

## Decision

The build pipeline is a sequence of TypeScript scripts under `src/`, each handling one stage of the plugin emission process. Each stage reads from the previous stage's output (or from the canonical `plugins/` source) and writes to a target-specific subdirectory of `dist/`.

## Stage list

1. **typecheck** — `tsc --noEmit` against `src/`.
2. **build:hooks** — compile the in-repo hook scripts.
3. **validate** — confirm every plugin source passes BP-001's validator.
4. **build:standalone** — emit per-target bundles.

## Target registration

Each target is a file in `src/targets/<name>.ts` exporting an `emit(plugin, outputDir)` function. The dispatcher in `src/build-standalone.ts` discovers them via filesystem convention.

## Idempotency

`rimraf` cleans `dist/` and `dist-ts/` before each build so re-runs don't accumulate cruft. All emit functions write to fresh directories — no in-place mutation.

## Scaffold command

`pnpm run scaffold` invokes `src/scaffold.ts`, which uses `yaml` to write the canonical manifest skeleton and copies a starter skill file from `src/templates/`.
