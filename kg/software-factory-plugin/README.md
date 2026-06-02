# Synthetic Knowledge Graph — software-factory-plugin

This directory is a **synthetic Software Factory Knowledge Graph** authored by Satwik as the demo target for `sf-scan`'s Lens 1 dependency-vulnerability scanner. It is not real 8090 product data and was never produced by 8090's Software Factory.

## Provenance

- **Structure** follows 8090's publicly documented [Requirements Writing Guide](https://www.8090.ai/docs/opinions/requirements-writing-guide), [Blueprint Writing Guide](https://www.8090.ai/docs/opinions/blueprint-writing-guide), and [Work Order Writing Guide](https://www.8090.ai/docs/opinions/work-order-writing-guide).
- **Content** is Satwik's own writing, derived from `software-factory-plugin`'s public README and `package.json` on GitHub. No 8090 internal docs were referenced.
- **Purpose** is to exercise the scanner's ontology resolver end-to-end against real dependency findings. The Work Orders' `dependencies-introduced` fields declare the npm packages they would have introduced in a counterfactual Software Factory build of this project — so when OSV.dev returns a finding for `eslint@10.0.2`, the resolver can trace it upward through `WO-004` → `BP-003` → `F-003` → `PRD-001`.

## Why this target

The plan's original primary demo target was `8090-inc/software-factory-harness`. On inspection, sf-harness is a pure documentation + shell-script repo with no `package.json` or `requirements.txt` — nothing for a dependency scanner to consume. `software-factory-plugin` is the same org's other public Software Factory adjacent repo, has a substantial Node.js dependency tree (`pnpm-lock.yaml` + a rich devDependencies block), and is therefore the right target to actually demonstrate Lens 1 working end-to-end.

The scanner is repo-list-agnostic (per requirement R10): once 8090 grants real Software Factory access, this synthetic KG is replaced wholesale by the real KG and the same scanner runs unchanged.

## Layout

```
kg/software-factory-plugin/
├── requirements/
│   ├── product-overview.md           # PRD-001
│   ├── feature-001-plugin-authoring.md
│   ├── feature-002-multi-target-distribution.md
│   └── feature-003-quality-enforcement.md
├── blueprints/
│   ├── foundations/
│   │   └── core-stack.md             # BP-FND-001
│   └── features/
│       ├── bp-001-authoring-validation.md
│       ├── bp-002-multi-target-distribution.md
│       └── bp-003-quality-enforcement.md
└── work-orders/
    ├── wo-001-scaffold.md
    ├── wo-002-validation-pipeline.md
    ├── wo-003-build-targets.md
    ├── wo-004-quality-toolchain.md
    └── wo-005-test-and-husky.md
```

## Deliberate unmapped surface

One transitive dependency category (TypeScript type stubs under `@types/*`) is intentionally not declared in any Work Order's `dependencies-introduced` field. When the scanner finds a CVE in a `@types/*` package, it surfaces under the report's **Unmapped Findings** section — itself a Lens 4 precursor (the KG has a coverage gap that an alignment-debt score would quantify).
