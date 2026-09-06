#!/usr/bin/env python3
"""
emu_setup.py - run the Phoenix SETUP utility from a built ROM image under the Unicorn CPU emulator with an
emulated text screen (INT 10h), scripted keystrokes (INT 16h), CMOS and chipset index/data ports, and print the
screen every time SETUP asks for a key.  Used to test the patched SETUP page without hardware.

    python tools/emu_setup.py build/patched/xtide-setup/rom.bin [key ...]
    keys: pgdn pgup down up right left enter esc f4 f5 f6 space y n plus minus   (default script walks to page 3)

The first key answers the "<Hit any Key>" CMOS-correction screen that appears because the emulated CMOS starts
empty.  Requires: pip install unicorn (in the WSL venv).
"""
import sys
from unicorn import *
from unicorn.x86_const import *

rom = open(sys.argv[1], "rb").read()
KEYS = {"pgdn": 0x5100, "pgup": 0x4900, "down": 0x5000, "up": 0x4800, "right": 0x4D00, "left": 0x4B00, "enter": 0x1C0D, "esc": 0x011B,
        "f4": 0x3E00, "f5": 0x3F00, "f6": 0x4000, "space": 0x3920, "y": 0x1579, "n": 0x316E, "plus": 0x0D2B, "minus": 0x0C2D}
script = [KEYS[k] for k in sys.argv[2:]] if len(sys.argv) > 2 else [KEYS["pgdn"], KEYS["pgdn"], KEYS["down"], KEYS["down"], KEYS["right"], KEYS["esc"], KEYS["f6"]]

uc = Uc(UC_ARCH_X86, UC_MODE_16)
uc.mem_map(0, 0x100000)
uc.mem_write(0xC0000, rom[0:0x8000]); uc.mem_write(0xE8000, rom[0x8000:0xE000]); uc.mem_write(0xEE000, rom[0xE000:0x10000]); uc.mem_write(0xF0000, rom[0x10000:])
# BDA
def w16(addr, v): uc.mem_write(addr, (v & 0xFFFF).to_bytes(2, "little"))
w16(0x413, 640); uc.mem_write(0x449, b"\x03"); w16(0x44A, 80); w16(0x44C, 4000); w16(0x463, 0x3D4); uc.mem_write(0x484, b"\x18"); uc.mem_write(0x485, b"\x10\x00")
w16(0x410, 0x4021); uc.mem_write(0x417, b"\x00\x00")
# CMOS with valid checksums
cmos = bytearray(128)
cmos[0x00], cmos[0x02], cmos[0x04] = 0x56, 0x34, 0x12; cmos[0x06], cmos[0x07], cmos[0x08], cmos[0x09] = 0x07, 0x06, 0x09, 0x26; cmos[0x32] = 0x20
cmos[0x0A] = 0x26; cmos[0x0B] = 0x02; cmos[0x0D] = 0x80; cmos[0x0E] = 0x00
cmos[0x10] = 0x40; cmos[0x12] = 0x00; cmos[0x14] = 0x21; cmos[0x15], cmos[0x16] = 0x80, 0x02; cmos[0x17], cmos[0x18] = 0x00, 0x1C; cmos[0x30], cmos[0x31] = 0x00, 0x1C
cmos[0x34] = 0x00; cmos[0x3F] = 0x00
s = sum(cmos[0x10:0x2E]); cmos[0x2E], cmos[0x2F] = (s >> 8) & 0xFF, s & 0xFF
s = sum(cmos[0x40:0x7E]); cmos[0x7E], cmos[0x7F] = (s >> 8) & 0xFF, s & 0xFF
state = {"cidx": 0, "chip": 0, "regs": {0x200: 0x1F00, 0x207: 0}, "p61": 0, "p3da": 0, "keys": list(script), "shots": [], "kbwait": 0, "cmos_writes": []}
screen = [[(0x20, 0x07) for _ in range(80)] for _ in range(25)]
cur = {"r": 0, "c": 0}

def hin(uc, port, size, ud):
    if port == 0x71: return cmos[state["cidx"] & 0x7F]
    if port == 0x26: return state["regs"].get(state["chip"], 0)
    if port == 0x61: state["p61"] ^= 0x10; return state["p61"]
    if port == 0x3DA: state["p3da"] ^= 0x09; return state["p3da"]
    if port == 0x64: return 0x10  # KBC: input buffer empty, no output
    return 0
def hout(uc, port, size, value, ud):
    if port == 0x70: state["cidx"] = value
    elif port == 0x71:
        i = state["cidx"] & 0x7F
        if cmos[i] != value & 0xFF: state["cmos_writes"].append("%02X:%02X->%02X" % (i, cmos[i], value & 0xFF))
        cmos[i] = value & 0xFF
    elif port == 0x24: state["chip"] = value
    elif port == 0x26: state["regs"][state["chip"]] = value
uc.hook_add(UC_HOOK_INSN, hin, None, 1, 0, UC_X86_INS_IN)
uc.hook_add(UC_HOOK_INSN, hout, None, 1, 0, UC_X86_INS_OUT)

def putc(ch, attr, advance=True):
    r, c = cur["r"], cur["c"]
    if ch == 13: cur["c"] = 0; return
    if ch == 10: cur["r"] = min(24, r + 1); return
    if ch == 8: cur["c"] = max(0, c - 1); return
    if ch == 7: return
    if 0 <= r < 25 and 0 <= c < 80: screen[r][c] = (ch, attr)
    if advance:
        c += 1
        if c >= 80: c = 0; r = min(24, r + 1)
        cur["r"], cur["c"] = r, c
def sync_cursor(): w16(0x450, (cur["r"] << 8) | cur["c"])
def shot(tag):
    lines = ["".join(chr(ch) if 32 <= ch < 127 else ("." if ch else " ") for ch, a in row).rstrip() for row in screen]
    while lines and not lines[-1]: lines.pop()
    state["shots"].append((tag, lines))

def r8(reg): return uc.reg_read(reg) & 0xFF
def set_flag(mask, on):
    f = uc.reg_read(UC_X86_REG_EFLAGS)
    uc.reg_write(UC_X86_REG_EFLAGS, (f | mask) if on else (f & ~mask))

def hook_intr(uc, intno, ud):
    ax = uc.reg_read(UC_X86_REG_AX); ah, al = ax >> 8, ax & 0xFF
    if intno == 0x10:
        bx = uc.reg_read(UC_X86_REG_BX); cx = uc.reg_read(UC_X86_REG_CX); dx = uc.reg_read(UC_X86_REG_DX)
        if ah == 0x00:
            for r in range(25):
                for c in range(80): screen[r][c] = (0x20, 0x07)
            cur["r"] = cur["c"] = 0; uc.mem_write(0x449, bytes([al & 0x7F]))
        elif ah == 0x01: pass
        elif ah == 0x02: cur["r"], cur["c"] = dx >> 8, dx & 0xFF; sync_cursor()
        elif ah == 0x03: uc.reg_write(UC_X86_REG_DX, (cur["r"] << 8) | cur["c"]); uc.reg_write(UC_X86_REG_CX, 0x0607)
        elif ah == 0x05: pass
        elif ah in (0x06, 0x07):
            top, left, bot, right = cx >> 8, cx & 0xFF, dx >> 8, dx & 0xFF; attr = bx >> 8
            if al == 0:
                for r in range(top, min(bot, 24) + 1):
                    for c in range(left, min(right, 79) + 1): screen[r][c] = (0x20, attr)
            else:
                for _ in range(al):
                    for r in range(top, bot + 1) if ah == 0x06 else range(bot, top - 1, -1):
                        for c in range(left, right + 1):
                            src = r + 1 if ah == 0x06 else r - 1
                            screen[r][c] = screen[src][c] if top <= src <= bot else (0x20, attr)
        elif ah == 0x08:
            ch, a = screen[cur["r"]][cur["c"]]; uc.reg_write(UC_X86_REG_AX, (a << 8) | ch)
        elif ah in (0x09, 0x0A):
            attr = (bx & 0xFF) if ah == 0x09 else screen[cur["r"]][cur["c"]][1]
            r, c = cur["r"], cur["c"]
            for i in range(cx):
                if c + i < 80: screen[r][c + i] = (al, attr)
        elif ah == 0x0E: putc(al, screen[cur["r"]][cur["c"]][1]); sync_cursor()
        elif ah == 0x0F: uc.reg_write(UC_X86_REG_AX, 0x5003); uc.reg_write(UC_X86_REG_BX, bx & 0xFF)
        elif ah == 0x13:
            es = uc.reg_read(UC_X86_REG_ES); bp = uc.reg_read(UC_X86_REG_BP); attr = bx & 0xFF
            save = (cur["r"], cur["c"]); cur["r"], cur["c"] = dx >> 8, dx & 0xFF
            data = uc.mem_read(es * 16 + bp, cx * (2 if al & 2 else 1))
            for i in range(cx):
                if al & 2: putc(data[2 * i], data[2 * i + 1])
                else: putc(data[i], attr)
            if not (al & 1): cur["r"], cur["c"] = save
            sync_cursor()
        elif ah == 0x12: pass
        elif ah == 0x1C: uc.reg_write(UC_X86_REG_AX, 0x1C00 | 0x1C); uc.reg_write(UC_X86_REG_BX, 1)
        elif ah == 0x5F: uc.reg_write(UC_X86_REG_AX, 0x005F); uc.reg_write(UC_X86_REG_DX, 0)
        else: state.setdefault("unk10", set()).add(ah)
    elif intno == 0x16:
        if ah in (0x00, 0x10):
            shot("key #%d requested (%s)" % (len(script) - len(state["keys"]) + 1, ("%04X" % state["keys"][0]) if state["keys"] else "none left"))
            if not state["keys"]:
                uc.emu_stop(); return
            uc.reg_write(UC_X86_REG_AX, state["keys"].pop(0))
        elif ah in (0x01, 0x11):
            state["kbwait"] += 1
            if state["keys"] and state["kbwait"] % 50 == 0: uc.reg_write(UC_X86_REG_AX, state["keys"][0]); set_flag(0x40, False)
            else: set_flag(0x40, True)
        elif ah == 0x02: uc.reg_write(UC_X86_REG_AX, ax & 0xFF00)
        else: uc.reg_write(UC_X86_REG_AX, 0)
    elif intno == 0x15:
        if ah == 0x4F: set_flag(1, True)   # keyboard intercept: pass the key on
        elif ah == 0x88: uc.reg_write(UC_X86_REG_AX, 7168); set_flag(1, False)
        elif ah == 0xC0: set_flag(1, True)
        else: set_flag(1, True)
    elif intno == 0x1A:
        uc.reg_write(UC_X86_REG_CX, 0); uc.reg_write(UC_X86_REG_DX, 0); set_flag(1, False)
    elif intno == 0x11: uc.reg_write(UC_X86_REG_AX, 0x4021)
    elif intno == 0x12: uc.reg_write(UC_X86_REG_AX, 640)
    elif intno == 0x19: state["reboot"] = True; uc.emu_stop()
    else: state.setdefault("unk", set()).add(intno)
uc.hook_add(UC_HOOK_INTR, hook_intr)

# far-call setup_far_entry F000:0100 with a far return to a HLT sentinel at 0000:0600
uc.mem_write(0x0600, b"\xF4")
uc.reg_write(UC_X86_REG_SS, 0x3000); uc.reg_write(UC_X86_REG_SP, 0xFFFC)
uc.mem_write(0x3FFFC, (0x0600).to_bytes(2, "little") + (0x0000).to_bytes(2, "little"))
uc.reg_write(UC_X86_REG_DS, 0); uc.reg_write(UC_X86_REG_ES, 0)
uc.reg_write(UC_X86_REG_CS, 0xF000)
try:
    uc.emu_start(0xF0100, 0x0600, timeout=60_000_000, count=400_000_000)
    print("stopped at %04X:%04X" % (uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)))
except UcError as e:
    print("emulation error:", e, "at %04X:%04X" % (uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)))
shot("final")
for tag, lines in state["shots"]:
    print("=" * 30, tag)
    for i, l in enumerate(lines): print("%2d|%s" % (i, l))
print("CMOS writes:", state["cmos_writes"])
print("unknown INT 10h functions:", sorted(state.get("unk10", [])), "unknown INTs:", sorted(state.get("unk", [])), "reboot:", state.get("reboot"))
