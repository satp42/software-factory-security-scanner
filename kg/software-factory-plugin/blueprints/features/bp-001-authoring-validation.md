---
id: BP-001
title: Authoring + Validation Pipeline
type: blueprint
blueprint_type: feature
feature: F-001
---

# BP-001 — Authoring + Validation Pipeline

## Decision

Plugin sources live under `plugins/<plugin-name>/` with a fixed sub-layout. A `zod` schema describes the plugin manifest shape. A validator script reads every plugin's manifest, runs the schema check, and reports failures with `path: message` precision.

## Source layout

```
plugins/
  <plugin-name>/
    plugin.yaml        # canonical manifest
    skills/            # markdown skill files
    hooks/             # optional pre/post hooks
```

## Validator design

- One pass per plugin under `plugins/`.
- For each plugin: load `plugin.yaml`, parse with `yaml`, validate with `zod`'s `safeParse`.
- Aggregate all errors before exiting — authors see the full failure surface, not just the first failure.

## Schema authority

The `zod` schema is the single source of truth. Future IDE tooling (autocomplete, hover) generates from the same schema via `zod-to-json-schema` (not in v1).
