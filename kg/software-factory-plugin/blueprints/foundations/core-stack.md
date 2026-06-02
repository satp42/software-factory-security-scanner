---
id: BP-FND-001
title: Core Stack — Node.js + TypeScript + pnpm
type: blueprint
blueprint_type: foundation
product: PRD-001
---

# BP-FND-001 — Core Stack

## Decision

The project is implemented in **TypeScript** running on **Node.js**, with **pnpm** as the package manager and **tsx** as the runtime for TypeScript scripts (no bundling step required for the build-time scripts themselves).

## Rationale

- **TypeScript** gives us schema-first thinking for both the plugin manifest validator and the build pipeline. Type errors surface during development, not during `pnpm run build`.
- **pnpm** with workspace support handles the multi-target layout cleanly — each plugin can live as a workspace member with its own dependencies if needed, without duplicating storage.
- **tsx** lets us execute TypeScript build scripts directly without a separate compile step, keeping the developer loop fast.

## Conventions applied across all features

- Module system: ESM (`"type": "module"`).
- TypeScript target: ES2022, strict mode on.
- File layout: `src/` for build scripts, `plugins/` for plugin sources, `dist/` and `dist-ts/` for build output (gitignored).
- Package manager: pnpm 10.x; `pnpm-lock.yaml` is committed.

## Cross-feature constraints

- All build steps written in TypeScript, executed via `tsx`.
- All schemas defined with `zod` for runtime validation; the same schema definition powers the validator and any future generator.
- All YAML files parsed with `yaml` rather than the JSON-only stdlib parser.
