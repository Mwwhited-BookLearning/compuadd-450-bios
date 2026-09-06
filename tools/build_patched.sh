#!/usr/bin/env bash
# build_patched.sh - build the patched ROM variants entirely from assembly: Phoenix modules
# (patched/variants/<name>/*.asm) + XTIDE Universal BIOS (patched/xtide/src) in the 8 KB slot.
#
#   bash tools/build_patched.sh                # both variants
#   bash tools/build_patched.sh xtide          # XTIDE in the slot, nothing else                -> build/patched/xtide/rom.bin
#   bash tools/build_patched.sh xtide-setup    # + third SETUP page for the XTIDE settings      -> build/patched/xtide-setup/rom.bin
#
# Environment: SKIP_GEN=1 skips tools/mkpatched.py (use the .asm files as they are), NASM=/path/to/nasm,
# PY=/path/to/python (default: the WSL venv), IDE_CONTROLLER_COUNT=n for the XTIDE build (default 1).
# Steps: mkpatched.py (src/*.asm -> patched/variants/*/), build_xtide.sh (XTIDE source -> build/xtide/xub.bin),
# assemble the three Phoenix modules of each variant, concatenate VGA | MISER | XTIDE | system BIOS.
set -e
cd "$(dirname "$0")/.."
IMG="BIOS from Compuadd 486 Color Scan 450.BIN"
PY="${PY:-$HOME/.venv-bios/bin/python}"; command -v "$PY" >/dev/null 2>&1 || PY=python3
NASM="${NASM:-$(command -v nasm || true)}"
if [ -z "$NASM" ]; then NASM=$(ls build/nasm/*/nasm.exe 2>/dev/null | head -1); fi
[ -n "$NASM" ] || { echo "nasm not found (set NASM=...)"; exit 1; }
export NASM PY
case "${1:-all}" in
  xtide) VARIANTS="xtide" ;;
  xtide-setup) VARIANTS="xtide-setup" ;;
  all) VARIANTS="xtide xtide-setup" ;;
  *) echo "usage: $0 [xtide|xtide-setup|all]"; exit 1 ;;
esac
if [ "${SKIP_GEN:-0}" != 1 ]; then
  "$PY" tools/mkpatched.py --variant "${1:-all}"
fi
bash tools/build_xtide.sh
[ "$(wc -c < build/xtide/xub.bin)" -eq 8192 ] || { echo "xub.bin is not 8 KB"; exit 1; }
for v in $VARIANTS; do
  echo "== variant $v"
  out=build/patched/$v
  mkdir -p "$out"
  for m in vga miser sys; do
    "$NASM" -f bin -i "patched/variants/$v/" "patched/variants/$v/$m.asm" -o "$out/$m.bin" -l "$out/$m.lst"
    printf "%-6s %6d bytes\n" "$m" "$(wc -c < "$out/$m.bin")"
  done
  [ "$(wc -c < $out/vga.bin)" -eq 32768 ] || { echo "vga module is not 32 KB"; exit 1; }
  [ "$(wc -c < $out/sys.bin)" -eq 65536 ] || { echo "sys module is not 64 KB"; exit 1; }
  [ "$(wc -c < $out/miser.bin)" -eq 24576 ] || { echo "miser module is not 24 KB"; exit 1; }
  cat "$out/vga.bin" "$out/miser.bin" build/xtide/xub.bin "$out/sys.bin" > "$out/rom.bin"
  echo "$out/rom.bin: $(wc -c < "$out/rom.bin") bytes"
  cmp -l "$IMG" "$out/rom.bin" | awk 'BEGIN{n=0;s=0;x=0;p=0} {n++; o=$1-1; if (o>=65536) s++; else if (o>=57344) x++; else if (o>=32768) p++} END {printf "changed bytes vs original: %d total (system BIOS %d, XTIDE slot %d, MISER %d)\n", n, s, x, p}'
  sha256sum "$out/rom.bin"
done
