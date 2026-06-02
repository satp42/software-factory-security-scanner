#!/usr/bin/env bash
# Demo invocation: multi-target scan against 8090's public sf-plugin
# (clean) and OWASP NodeGoat (deliberately vulnerable). The synthetic
# Knowledge Graph at kg/software-factory-plugin/ supplies the ontology.
#
# Run from the repository root:
#   ./examples/scan-command.sh
#
# Outputs land in ./reports/.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

sf-scan scan \
  --repo https://github.com/8090-inc/software-factory-plugin \
  --repo https://github.com/OWASP/NodeGoat \
  --kg ./kg/software-factory-plugin \
  --out ./reports
