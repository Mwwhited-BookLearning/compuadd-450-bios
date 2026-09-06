#!/usr/bin/env bash
# build.sh - assemble the NASM sources in src/ and rebuild the 128 KB ROM image.
#
#   bash tools/build.sh            # assembles src/{vga,miser,sys}.asm -> build/rebuilt/*.bin and build/rebuilt/rom.bin
#
# NASM is looked up in $NASM, then in PATH, then in build/nasm/*/nasm.exe (Windows build usable from Git Bash and WSL).
# The result is compared with the original image; a byte-identical rebuild proves the sources are complete.
set -e
cd "$(dirname "$0")/.."
IMG="BIOS from Compuadd 486 Color Scan 450.BIN"
NASM="${NASM:-$(command -v nasm || true)}"
if [ -z "$NASM" ]; then NASM=$(ls build/nasm/*/nasm.exe 2>/dev/null | head -1); fi
[ -n "$NASM" ] || { echo "nasm not found (set NASM=...)"; exit 1; }
mkdir -p build/rebuilt
for m in vga miser sys; do
  "$NASM" -f bin -i src/ "src/$m.asm" -o "build/rebuilt/$m.bin" -l "build/rebuilt/$m.lst"
  printf "%-6s %6d bytes\n" "$m" "$(stat -c %s "build/rebuilt/$m.bin" 2>/dev/null || wc -c < "build/rebuilt/$m.bin")"
done
# image layout: 0x00000 VGA (32 KB) | 0x08000 MISER (24 KB) | 0x0E000 padding (8 KB) | 0x10000 system BIOS (64 KB)
if [ -f src/pad.bin ]; then PAD=src/pad.bin; else PAD=build/pad.bin; fi
cat build/rebuilt/vga.bin build/rebuilt/miser.bin "$PAD" build/rebuilt/sys.bin > build/rebuilt/rom.bin
echo "rom.bin: $(wc -c < build/rebuilt/rom.bin) bytes"
if command -v sha256sum >/dev/null; then
  a=$(sha256sum "$IMG" | cut -c1-64); b=$(sha256sum build/rebuilt/rom.bin | cut -c1-64)
  if [ "$a" = "$b" ]; then echo "IDENTICAL to the original image ($a)"; else echo "DIFFERS from the original image"; echo " original $a"; echo " rebuilt  $b"; fi
fi
