#!/usr/bin/env bash
# Runs the PsychInterview regression tests against an app folder.
# Usage: tools/tests/run_all.sh /path/to/app-folder   (default: repo root, i.e. ../.. from here)
# Needs: python3 + playwright (Chromium), python-docx, node. Outputs go to tools/tests/out/.
set -u
T="$(cd "$(dirname "$0")" && pwd)"; APP="${1:-$(cd "$T/../.." && pwd)}"; OUT="$T/out"; FX="$T/fixtures/case_full.json"
mkdir -p "$OUT"; cd "$T"
echo "== every document type exports, reopens; every screen loads";  timeout 300 python3 t_regress.py "$T" "$APP" "$FX" "$OUT" | tail -2
echo "== case Word export, both layouts";                          timeout 180 python3 t_export.py  "$T" "$APP" "$FX" "$OUT" | tail -1
echo "== slides, 5 designs, pptx + pdf";                           timeout 300 python3 t_slides.py  "$T" "$APP" "$FX" "$OUT" | tail -2
echo "== Google Docs/Slides export (Google is simulated)";         timeout 300 python3 t_google.py  "$T" "$APP" "$FX" 2>&1 | tail -2
echo "== linked documents read new case fields";                   node t_linked.js "$APP/index.html" "$FX"
echo "Passing = every 'errors' line is [] and no Traceback."
