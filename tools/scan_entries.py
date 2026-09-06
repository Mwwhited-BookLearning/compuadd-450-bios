#!/usr/bin/env python3
"""
scan_entries.py - propose extra code entry points inside undecoded regions of a listing.

A byte offset is proposed when the previous instruction ended with ret/retf/iret (C3/CB/CF) or
a nop/int3 pad, and the bytes at the offset look like a routine prologue (push/pushf/pusha,
cli, mov ax|bx|dx imm, segment loads).  The proposals are printed as JSON so they can be
reviewed and pasted into labels/<module>.json "entries".

    scan_entries.py disasm/miser.asm build/miser.bin E800 [--min-run 32]
"""
import re
import sys

PROLOGUE = {0x60, 0x9C, 0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57, 0x1E, 0x06, 0xFA, 0xFC, 0xB8, 0xBA, 0xBB,
            0xBE, 0xBF, 0x8C, 0x8B, 0x33, 0x2E, 0x80, 0xE8, 0x66, 0x0F}


def main():
    asm, binpath, seg = sys.argv[1:4]
    minrun = 32
    if "--min-run" in sys.argv:
        minrun = int(sys.argv[sys.argv.index("--min-run") + 1])
    data = open(binpath, "rb").read()
    code = bytearray(len(data))
    for line in open(asm, encoding="utf-8", errors="replace"):
        m = re.match(r"^%s:([0-9A-F]{4}) ((?:[0-9A-F]{2} )+)\s+(\S+)" % seg, line)
        if m and m.group(3) != "db":
            off = int(m.group(1), 16)
            for i in range(len(m.group(2).split())):
                code[off + i] = 1
    out = []
    i = 0
    while i < len(data):
        if code[i]:
            i += 1
            continue
        j = i
        while j < len(data) and not code[j]:
            j += 1
        run = data[i:j]
        if j - i >= minrun and any(b not in (0, 0xFF) for b in run):
            # candidates inside this run
            for k in range(i, j):
                prev = data[k - 1] if k > 0 else 0xC3
                if (prev in (0xC3, 0xCB, 0xCF, 0x90, 0xCC) or k == i) and data[k] in PROLOGUE and data[k] not in (0, 0xFF):
                    # reject printable text
                    if all(0x20 <= b < 0x7F for b in data[k:k + 4]):
                        continue
                    out.append("%04X" % k)
        i = j
    print(len(out), "candidates")
    print('"entries_candidates": [' + ", ".join('"%s"' % o for o in out) + "]")


if __name__ == "__main__":
    main()
