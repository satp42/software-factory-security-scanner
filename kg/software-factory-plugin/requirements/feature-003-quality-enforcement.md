---
id: F-003
title: Quality Enforcement (Lint, Typecheck, Test, Hooks)
type: feature-requirements
product: PRD-001
---

# F-003 — Quality Enforcement

## Behavior

The repository enforces a consistent quality bar across all plugin contributions: TypeScript builds cleanly, ESLint passes, Markdown lints, all tests pass, and pre-commit hooks catch regressions before they land.

## Requirements

- **R-003.1.** A typecheck step verifies the TypeScript code compiles cleanly with no errors.
- **R-003.2.** A lint step verifies TypeScript code follows the project's ESLint configuration.
- **R-003.3.** A Markdown lint step verifies all `.md` and `.mdc` files under `plugins/` follow shared style rules.
- **R-003.4.** A unit test runner verifies behavior of any TypeScript helpers used in the build pipeline.
- **R-003.5.** A pre-commit hook runs the validation pipeline so malformed plugins cannot be committed.
- **R-003.6.** All quality steps run in CI and block merge on failure.

## Acceptance examples

- **AE-003.1.** A PR that introduces a TypeScript error fails CI at the typecheck step.
- **AE-003.2.** A PR that introduces an ESLint violation fails CI at the lint step.
- **AE-003.3.** A PR that introduces malformed Markdown frontmatter fails CI at the Markdown lint step.
- **AE-003.4.** A local commit that introduces a validation error is blocked by the pre-commit hook.
