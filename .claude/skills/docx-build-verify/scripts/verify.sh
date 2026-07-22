#!/usr/bin/env bash
# docx-build-verify: build a .docx via docx-js, convert to PDF, extract page images.
# Usage: verify.sh <generator.js> [output-dir]
set -euo pipefail

GEN="${1:?usage: verify.sh <generator.js> [output-dir]}"
OUT_DIR="${2:-$(dirname "$GEN")}"

if [ ! -f "$GEN" ]; then
  echo "ERROR: generator script not found: $GEN" >&2
  exit 1
fi

# 1. Build .docx
echo "==> Building .docx via $GEN"
NODE_PATH="$(npm root -g)" node "$GEN"

# 2. Find the most recent .docx in the output directory
DOCX="$(ls -t "$OUT_DIR"/*.docx 2>/dev/null | head -1)"
if [ -z "$DOCX" ]; then
  echo "ERROR: no .docx found in $OUT_DIR after generation" >&2
  exit 1
fi
echo "==> Generated: $DOCX"

# 3. Convert to PDF via LibreOffice
echo "==> Converting to PDF via soffice"
soffice --headless --convert-to pdf "$DOCX" --outdir "$OUT_DIR" >/dev/null

PDF="${DOCX%.docx}.pdf"
if [ ! -f "$PDF" ]; then
  echo "ERROR: PDF not generated: $PDF" >&2
  exit 1
fi
echo "==> PDF: $PDF"

# 4. Extract page images
PAGE_PREFIX="$OUT_DIR/page"
echo "==> Extracting page images at 150 DPI"
rm -f "$PAGE_PREFIX"-*.jpg 2>/dev/null || true
pdftoppm -jpeg -r 150 "$PDF" "$PAGE_PREFIX"

# 5. Report
PAGES="$(ls "$PAGE_PREFIX"-*.jpg 2>/dev/null | wc -l | tr -d ' ')"
echo
echo "==> SUCCESS"
echo "    docx:   $DOCX"
echo "    pdf:    $PDF"
echo "    pages:  $PAGES"
echo "    images: $PAGE_PREFIX-*.jpg"
echo
echo "Inspect page images before presenting to the user."
