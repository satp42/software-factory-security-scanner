---
id: WO-001
title: Scaffold project skeleton
type: work-order
blueprint: BP-FND-001
dependencies-introduced:
  - "npm:tsx"
  - "npm:typescript"
  - "npm:@types/node"
files-affected:
  - "package.json"
  - "tsconfig.json"
  - "src/index.ts"
  - "pnpm-workspace.yaml"
---

# WO-001 — Scaffold project skeleton

## Goal

Initialize the repository with TypeScript, pnpm workspaces, and the build-script runtime. Establish the foundation laid out in BP-FND-001 so subsequent Work Orders have a working `pnpm` + `tsx` environment.

## Steps

1. `pnpm init` with `"type": "module"`.
2. Install `typescript`, `tsx`, `@types/node` as devDependencies.
3. Create `tsconfig.json` with strict ES2022 settings.
4. Create `pnpm-workspace.yaml` declaring `plugins/*` and `src/` as workspace roots.
5. Create a stub `src/index.ts` confirming `tsx src/index.ts` runs.

## Verification

- `pnpm install` succeeds.
- `pnpm exec tsx src/index.ts` runs without error.
- `pnpm exec tsc --noEmit` succeeds.
