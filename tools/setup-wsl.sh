#!/usr/bin/env bash
# One-time setup for the disassembly tooling. Run inside WSL (Ubuntu):
#   bash tools/setup-wsl.sh
# Ubuntu's python has no pip and PEP-668 blocks --user installs, so a venv is used.
set -euo pipefail
VENV="${HOME}/.venv-bios"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv --without-pip "$VENV"
  curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
  "$VENV/bin/python" /tmp/get-pip.py --quiet
fi
"$VENV/bin/pip" install --quiet capstone unicorn
"$VENV/bin/python" -c 'import capstone, unicorn; print("capstone", capstone.__version__, "unicorn", unicorn.__version__, "ready in", "'"$VENV"'")'
