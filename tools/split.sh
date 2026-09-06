#!/usr/bin/env bash
# Split the 128 KB ROM image into its constituent modules.
#   bash tools/split.sh "BIOS from Compuadd 486 Color Scan 450.BIN" build/
#
# File offset  Size    Module                                   Runtime address
# 0x00000      0x8000  Chips & Tech 65535/A VGA BIOS (opt ROM)  C000:0000
# 0x08000      0x6000  PhoenixMISER PT68C268 power mgmt module  (see docs/02-phoenixmiser.md)
# 0x0E000      0x2000  padding (all 00 except a few CMOS bytes)  -
# 0x10000      0x10000 Phoenix 80486 system BIOS                F000:0000
set -euo pipefail
SRC="$1"; OUT="${2:-build}"
mkdir -p "$OUT"
dd if="$SRC" of="$OUT/vga.bin"   bs=1 skip=$((0x00000)) count=$((0x8000))  status=none
dd if="$SRC" of="$OUT/miser.bin" bs=1 skip=$((0x08000)) count=$((0x6000))  status=none
dd if="$SRC" of="$OUT/pad.bin"   bs=1 skip=$((0x0E000)) count=$((0x2000))  status=none
dd if="$SRC" of="$OUT/sys.bin"   bs=1 skip=$((0x10000)) count=$((0x10000)) status=none
for f in vga miser pad sys; do
  printf '%-6s %6d bytes  sum8=%3d  ' "$f" "$(stat -c %s "$OUT/$f.bin")" \
    "$(od -An -tu1 -v "$OUT/$f.bin" | tr -s ' ' '\n' | awk 'NF{s+=$1} END{print s%256}')"
  sha1sum "$OUT/$f.bin" | cut -c1-40
done
