#!/usr/bin/env python3
"""
outline.py - print the "main path" through a listing produced by romdis.py.

Starting at a label, follow fall-through, unconditional near jumps and the Phoenix
ROM-stack idiom (`mov sp, tbl ; jmp sub` returns to the word stored at tbl).  Calls
are printed but not descended into.  Conditional branches are printed with their
target and the fall-through path is taken.  Handy for sketching POST as a sequence.

Usage:  outline.py disasm/sys.asm post_start [--max 400]
"""
import re
import sys

LINE = re.compile(r"^([0-9A-F]{4}):([0-9A-F]{4}) ((?:[0-9A-F]{2} )+)\s+(\S+)\s*(.*?)(?:\s+; (.*))?$")
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s|$)")


def load(path):
    insns = {}
    labels = {}
    cur = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        m = LABEL.match(line)
        if m:
            cur = m.group(1)
            continue
        m = LINE.match(line)
        if not m:
            # ROM stack word lines look like:  F000:58E5   db  E7 58 ...
            continue
        seg, off, hexs, mn, ops, cmt = m.groups()
        off = int(off, 16)
        nbytes = len(hexs.split())
        insns[off] = (mn, ops.strip(), cmt or "", nbytes)
        if cur:
            labels.setdefault(cur, off)
            cur = None   # only the first instruction after a label belongs to it
    return insns, labels


def outline(path, start, maxlines):
    insns, labels = load(path)
    off = labels.get(start)
    if off is None:
        off = int(start, 16)
    inv = {v: k for k, v in labels.items()}
    seen = set()
    n = 0
    sp_tbl = None
    data = None
    while off in insns and off not in seen and n < maxlines:
        seen.add(off)
        mn, ops, cmt, size = insns[off]
        lbl = inv.get(off)
        if lbl:
            print("%04X %s:" % (off, lbl))
        if mn == "mov" and ops.startswith("sp, 0x"):
            sp_tbl = int(ops.split("0x")[1], 16)
        if mn == "mov" and ops.startswith("al, ") and off + size in insns and insns[off + size][0] == "out" \
                and insns[off + size][1].startswith("0x80"):
            print("%04X     POST %s" % (off, ops[4:]))
        if mn in ("call", "int", "lcall"):
            print("%04X     %s %s" % (off, mn, ops))
            n += 1
            off += size
            continue
        if mn in ("ret", "retf", "iret"):
            print("%04X     %s" % (off, mn))
            break
        if mn == "hlt":
            print("%04X     hlt" % off)
        if mn == "ljmp":
            print("%04X     %s %s" % (off, mn, ops))
            break
        if mn == "jmp":
            tgt = labels.get(ops)
            if tgt is None:
                print("%04X     jmp %s   %s" % (off, ops, cmt))
                break
            if sp_tbl is not None and tgt in insns and lbl_is_sub(ops):
                # ROM-stack call: the callee's RET pops the word at sp_tbl
                if data is None:
                    data = read_words(path)
                ret = data.get(sp_tbl)
                print("%04X     romcall %s   (returns to %04X)" % (off, ops, ret if ret is not None else -1))
                sp_tbl = None
                if ret is not None:
                    off = ret
                    n += 1
                    continue
            print("%04X     jmp %s" % (off, ops))
            off = tgt
            n += 1
            continue
        if mn.startswith("j") or mn.startswith("loop"):
            print("%04X     %s %s" % (off, mn, ops))
            n += 1
            off += size
            continue
        off += size
    print("-- stopped at %04X" % off)


def lbl_is_sub(name):
    return not name.startswith("loc_")


def read_words(path):
    """Collect ROM-stack words: lines `SEG:OFF  db  XX YY` directly under a tbl_ label."""
    words = {}
    prev_lbl = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        m = LABEL.match(raw)
        if m:
            prev_lbl = m.group(1)
            continue
        m = re.match(r"^[0-9A-F]{4}:([0-9A-F]{4})\s+db\s+([0-9A-F]{2}) ([0-9A-F]{2})", raw)
        if m and prev_lbl and prev_lbl.startswith("tbl_"):
            words[int(m.group(1), 16)] = int(m.group(3) + m.group(2), 16)
            prev_lbl = None
    return words


if __name__ == "__main__":
    a = sys.argv[1:]
    mx = 400
    if "--max" in a:
        i = a.index("--max")
        mx = int(a[i + 1])
        del a[i:i + 2]
    outline(a[0], a[1], mx)
