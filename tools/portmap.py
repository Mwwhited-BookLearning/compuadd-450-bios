#!/usr/bin/env python3
"""
portmap.py - summarise I/O port and CMOS register usage from a romdis listing.

    portmap.py disasm/sys.asm [--cmos-read cmos_read] [--cmos-write cmos_write] > docs/generated/sys-ports.md

Emits two markdown tables: I/O ports touched by `in`/`out` with immediate port numbers
(and `dx` after `mov dx, imm`), and CMOS indexes passed to the read/write helpers or
written directly to port 70h.
"""
import re
import sys
from collections import defaultdict

LINE = re.compile(r"^([0-9A-F]{4}):([0-9A-F]{4}) ((?:[0-9A-F]{2} )+)\s+(\S+)\s*(.*?)(?:\s+; (.*))?$")
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s|$)")

PORTS = {
    0x00: "DMA1 ch0 addr", 0x01: "DMA1 ch0 count", 0x02: "DMA1 ch1 addr", 0x03: "DMA1 ch1 count",
    0x04: "DMA1 ch2 addr", 0x05: "DMA1 ch2 count", 0x06: "DMA1 ch3 addr", 0x07: "DMA1 ch3 count",
    0x08: "DMA1 status/command", 0x0A: "DMA1 mask", 0x0B: "DMA1 mode", 0x0C: "DMA1 clear flip-flop",
    0x0D: "DMA1 master clear", 0x0F: "DMA1 write mask", 0x20: "PIC1 command", 0x21: "PIC1 data/mask",
    0x22: "chipset index (OPTi-style)", 0x24: "chipset config index (word)", 0x26: "chipset config data (word)",
    0x40: "PIT ch0", 0x41: "PIT ch1 (refresh)", 0x42: "PIT ch2 (speaker)", 0x43: "PIT control",
    0x60: "KBC data", 0x61: "port B (speaker/parity/refresh)", 0x64: "KBC command/status",
    0x70: "CMOS index / NMI enable", 0x71: "CMOS data", 0x80: "POST code", 0x81: "DMA page ch2",
    0x82: "DMA page ch3", 0x83: "DMA page ch1", 0x87: "DMA page ch0", 0x89: "DMA page ch6",
    0x8A: "DMA page ch7", 0x8B: "DMA page ch5", 0x8D: "resume magic word (chipset)", 0x8F: "DMA page refresh",
    0x92: "PS/2 system control", 0xA0: "PIC2 command", 0xA1: "PIC2 data/mask",
    0xC0: "DMA2 ch4 addr", 0xC2: "DMA2 ch5 addr", 0xC4: "DMA2 ch6 addr", 0xC6: "DMA2 ch7 addr",
    0xD0: "DMA2 status/command", 0xD4: "DMA2 mask", 0xD6: "DMA2 mode", 0xD8: "DMA2 clear flip-flop",
    0xDA: "DMA2 master clear", 0xDE: "DMA2 write mask", 0xED: "I/O delay (dummy write)",
    0xF0: "FPU busy clear", 0xF1: "FPU reset", 0x1F0: "IDE data", 0x1F7: "IDE status/command",
    0x1FF: "platform config byte (from CMOS 3Fh)", 0x201: "game port", 0x26E: "Super I/O index", 0x26F: "Super I/O data",
    0x278: "LPT3", 0x2E8: "COM4", 0x2F8: "COM2", 0x2FB: "COM2 LCR", 0x378: "LPT2", 0x3B4: "MDA CRTC index",
    0x3B8: "MDA mode control", 0x3BA: "MDA status", 0x3BC: "LPT1", 0x3C0: "VGA attribute", 0x3C2: "VGA misc output",
    0x3C4: "VGA sequencer index", 0x3C6: "VGA DAC mask", 0x3CC: "VGA misc output read", 0x3D4: "CGA/VGA CRTC index",
    0x3D6: "C&T extension index", 0x3D8: "CGA mode control", 0x3DA: "CGA/VGA status", 0x3E8: "COM3",
    0x3F0: "FDC", 0x3F2: "FDC digital output", 0x3F4: "FDC status", 0x3F5: "FDC data", 0x3F6: "IDE control / FDC",
    0x3F7: "FDC digital input", 0x3F8: "COM1", 0x3FB: "COM1 LCR",
}
CMOS = {
    0x00: "RTC seconds", 0x01: "seconds alarm", 0x02: "minutes", 0x03: "minutes alarm", 0x04: "hours",
    0x05: "hours alarm", 0x06: "day of week", 0x07: "day of month", 0x08: "month", 0x09: "year",
    0x0A: "status A", 0x0B: "status B", 0x0C: "status C", 0x0D: "status D (battery)", 0x0E: "diagnostic status",
    0x0F: "shutdown status", 0x10: "floppy types", 0x12: "hard disk types", 0x14: "equipment", 0x15: "base mem lo",
    0x16: "base mem hi", 0x17: "ext mem lo", 0x18: "ext mem hi", 0x19: "HD0 ext type", 0x1A: "HD1 ext type",
    0x1F: "Phoenix: options", 0x2E: "checksum hi", 0x2F: "checksum lo", 0x30: "ext mem found lo", 0x31: "ext mem found hi",
    0x32: "century", 0x33: "info flags (bit7 128K, bit4 FPU?)", 0x34: "Phoenix: CPU speed / POST flags", 0x3F: "platform config -> port 1FFh",
    0x58: "Phoenix: suspend flags", 0x59: "Phoenix: pointer/mouse flags",
}


def main():
    a = sys.argv[1:]
    path = a[0]
    rd = "cmos_read"
    wr = "cmos_write"
    if "--cmos-read" in a:
        rd = a[a.index("--cmos-read") + 1]
    if "--cmos-write" in a:
        wr = a[a.index("--cmos-write") + 1]
    ports = defaultdict(lambda: {"in": set(), "out": set(), "fn": set()})
    cmos = defaultdict(lambda: {"r": set(), "w": set(), "d": set(), "fn": set()})
    cur = "?"
    last_al = None
    last_ah = None
    last_dx = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        m = LABEL.match(raw)
        if m:
            if not m.group(1).startswith("loc_"):
                cur = m.group(1)
            continue
        m = LINE.match(raw.rstrip("\n"))
        if not m:
            continue
        seg, off, hexs, mn, ops, cmt = m.groups()
        off = int(off, 16)
        ops = ops.strip()
        if mn == "mov":
            mm = re.match(r"(al|ah|dx), 0x([0-9a-f]+)$", ops)
            if mm:
                v = int(mm.group(2), 16)
                if mm.group(1) == "al":
                    last_al = v
                elif mm.group(1) == "ah":
                    last_ah = v
                else:
                    last_dx = v
            elif ops.startswith("dx,"):
                last_dx = None
        if mn in ("call", "ret", "jmp", "ljmp", "lcall", "int"):
            last_dx = None if mn != "int" else last_dx
            if mn in ("call", "lcall"):
                last_dx = None   # DX is a parameter register for helpers, not a port
        if mn in ("in", "out"):
            parts = [p.strip() for p in ops.split(",")]
            port = parts[0] if mn == "out" else parts[1]
            pv = None
            if port.startswith("0x"):
                pv = int(port, 16)
            elif port == "dx" and last_dx is not None:
                pv = last_dx
            if pv is not None:
                ports[pv][mn].add(off)
                ports[pv]["fn"].add(cur)
                if mn == "out" and pv == 0x70 and last_al is not None and cur not in (rd, wr):
                    idx = last_al & 0x7F
                    cmos[idx]["d"].add(off)     # direct 70h/71h access (direction not resolved)
                    cmos[idx]["fn"].add(cur)
        if mn == "call":
            if ops == rd and last_al is not None:
                cmos[last_al & 0x7F]["r"].add(off)
                cmos[last_al & 0x7F]["fn"].add(cur)
            elif ops == wr and last_ah is not None:
                cmos[last_ah & 0x7F]["w"].add(off)
                cmos[last_ah & 0x7F]["fn"].add(cur)
    print("## I/O ports\n")
    print("| Port | Meaning | in | out | Used by |")
    print("|---|---|---|---|---|")
    for p in sorted(ports):
        d = ports[p]
        fns = ", ".join("`%s`" % f for f in sorted(d["fn"])[:6]) + (" …" if len(d["fn"]) > 6 else "")
        print("| %03Xh | %s | %d | %d | %s |" % (p, PORTS.get(p, ""), len(d["in"]), len(d["out"]), fns))
    print("\n## CMOS registers\n")
    print("| Index | Meaning | reads | writes | direct 70h/71h | Used by |")
    print("|---|---|---|---|---|---|")
    for i in sorted(cmos):
        d = cmos[i]
        fns = ", ".join("`%s`" % f for f in sorted(d["fn"])[:6]) + (" …" if len(d["fn"]) > 6 else "")
        print("| %02Xh | %s | %d | %d | %d | %s |" % (i, CMOS.get(i, ""), len(d["r"]), len(d["w"]), len(d["d"]), fns))


if __name__ == "__main__":
    main()
