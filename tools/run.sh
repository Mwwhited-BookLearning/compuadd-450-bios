#!/usr/bin/env bash
# Regenerate every listing from the ROM image + label files. Run inside WSL from the bios folder:
#   bash tools/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${HOME}/.venv-bios/bin/python"
IMG="BIOS from Compuadd 486 Color Scan 450.BIN"
bash tools/split.sh "$IMG" build >/dev/null
mkdir -p disasm
$PY tools/romdis.py --bin build/sys.bin   --seg F000 --labels labels/sys.json   --out disasm/sys.asm   --report disasm/sys-functions.md   --varxrefs build/sys-vars.json   --title "Phoenix 80486 system BIOS (F000 segment)"
$PY tools/romdis.py --bin build/vga.bin   --seg C000 --labels labels/vga.json   --out disasm/vga.asm   --report disasm/vga-functions.md   --varxrefs build/vga-vars.json   --title "Chips & Technologies 65535/A VGA BIOS (C000 segment)"
$PY tools/romdis.py --bin build/miser.bin --seg E800 --labels labels/miser.json --out disasm/miser.asm --report disasm/miser-functions.md --varxrefs build/miser-vars.json --title "PhoenixMISER PT68C268 power-management module (E800 segment)"
$PY tools/portmap.py disasm/sys.asm >/dev/null
$PY tools/portmap.py disasm/miser.asm >/dev/null
$PY tools/portmap.py disasm/vga.asm >/dev/null
$PY tools/chipsetmap.py
$PY tools/tables.py
$PY tools/coverage.py
$PY tools/misertext.py
$PY tools/varsmap.py
