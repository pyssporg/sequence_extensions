#!/usr/bin/env bash
# Create the venv at the repository root and install the distribution editable
# with the dev and GUI extras (engine plus seq_ext_gui). Idempotent: safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

PY=python3.11
VENV=.venv

if [ ! -d "$VENV" ]; then
  "$PY" -m venv "$VENV"
fi

"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -e ".[dev,gui]"

"$VENV/bin/python" -c "import seq_ext_gui, sequence_extensions"  # smoke check

echo
echo "Venv ready: $(cd "$VENV" && pwd)"
echo "  source .venv/bin/activate"
echo "  seq-ext-gui --project-root examples/flow_runner"
