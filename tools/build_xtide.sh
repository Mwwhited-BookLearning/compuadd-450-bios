#!/usr/bin/env bash
# build_xtide.sh - assemble the XTIDE Universal BIOS (r638 source in patched/xtide/src) for the Compuadd 450.
#
#   bash tools/build_xtide.sh        # -> build/xtide/ide_386.bin (+ .lst), then build/xtide/xub.bin (8 KB, checksummed)
#
# Reproduces the makefile's "386" small target (DEFINES_386) with one addition, -DIDE_CONTROLLER_COUNT=1
# (see patched/xtide/CHANGES.txt).  Include directories are taken from the makefile's HEADERS/LIBS lines.
# Requires nasm (PATH, $NASM, or build/nasm/*/nasm.exe) and python for tools/mkxub.py (or PY=...).
set -e
cd "$(dirname "$0")/.."
ROOT=$PWD
PY="${PY:-$HOME/.venv-bios/bin/python}"; command -v "$PY" >/dev/null 2>&1 || PY=python3
NASM="${NASM:-$(command -v nasm || true)}"
if [ -z "$NASM" ]; then NASM=$(ls build/nasm/*/nasm.exe 2>/dev/null | head -1); fi
[ -n "$NASM" ] || { echo "nasm not found (set NASM=...)"; exit 1; }
case "$NASM" in /*) ;; *) NASM="$ROOT/$NASM" ;; esac
XT=patched/xtide/src/XTIDE_Universal_BIOS
mkdir -p build/xtide
# include paths: every HEADERS/LIBS directory listed literally in the makefile
INC=$(grep -E '^(HEADERS|LIBS) \+?= ' "$XT/makefile" | grep -v '\$(' | sed -E 's/^[A-Z]+ \+?= //' | tr -d '\r' | sed 's/^/-I/' | tr '\n' ' ')
# DEFINES_386 = DEFINES_AT + USE_386 MODULE_ADVANCED_ATA MODULE_WIN9X_CMOS_HACK; DEFINES_AT = DEFINES_COMMON + USE_AT USE_286 MODULE_IRQ MODULE_COMPATIBLE_TABLES
DEFS="-DMODULE_STRINGS_COMPRESSED -DMODULE_HOTKEYS -DMODULE_8BIT_IDE -DMODULE_EBIOS -DMODULE_SERIAL -DMODULE_SERIAL_FLOPPY -DMODULE_POWER_MANAGEMENT -DNO_ATAID_VALIDATION -DCLD_NEEDED -DEXTRA_LOOP_UNROLLING_SMALL"
DEFS="$DEFS -DUSE_AT -DUSE_286 -DMODULE_IRQ -DMODULE_COMPATIBLE_TABLES -DUSE_386 -DMODULE_ADVANCED_ATA -DMODULE_WIN9X_CMOS_HACK"
DEFS="$DEFS -DIDE_CONTROLLER_COUNT=${IDE_CONTROLLER_COUNT:-1}"
( cd "$XT" && "$NASM" Src/Main.asm -f bin $INC -Worphan-labels -Ox $DEFS -o ../../../../build/xtide/ide_386.bin -l ../../../../build/xtide/ide_386.lst )
printf "xtide  %6d bytes (build/xtide/ide_386.bin)\n" "$(wc -c < build/xtide/ide_386.bin)"
"$PY" tools/mkxub.py --in build/xtide/ide_386.bin --out build/xtide/xub.bin
