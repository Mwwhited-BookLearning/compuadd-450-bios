#!/usr/bin/env bash
# Print the listing lines whose address falls in [START, END) - e.g.  tools/range.sh disasm/sys.asm 5E22 6500
# Label / comment lines directly preceding an in-range instruction are included.
f="$1"; s=$((16#$2)); e=$((16#$3))
awk -v s="$s" -v e="$e" '
  /^[0-9A-F][0-9A-F][0-9A-F][0-9A-F]:[0-9A-F][0-9A-F][0-9A-F][0-9A-F] / {
    o = strtonum("0x" substr($1, 6, 4));
    if (o >= s && o < e) { if (pend != "") printf "%s", pend; pend = ""; print substr($0, 1, 112) }
    else pend = "";
    next
  }
  /^$/ { next }
  { pend = pend $0 "\n" }
' "$f"
