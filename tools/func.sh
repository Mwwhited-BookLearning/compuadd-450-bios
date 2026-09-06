#!/usr/bin/env bash
# Print one routine from a listing: from LABEL up to the next non-loc_ label (or MAX lines).
#   tools/func.sh disasm/vga.asm int10_06_scroll_up [MAX]
f="$1"; l="$2"; max="${3:-400}"
awk -v L="$l" -v max="$max" '
  index($0, L ":") == 1 { p = 1 }
  p && /^[A-Za-z_][A-Za-z0-9_]*:([ \t]|$)/ && index($0, L ":") != 1 && $0 !~ /^loc_/ { exit }
  p { print substr($0, 1, 110); n++; if (n >= max) exit }
' "$f"
