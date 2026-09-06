#!/usr/bin/env python3
"""
test_xtide_apply.py - unit test for xtide_apply_cmos_config (patched variant xtide-setup) under Unicorn: loads
build/patched/xtide-setup/rom.bin, calls the routine with several CMOS 60h/61h settings and checks the ROMVARS
bytes, the option-ROM checksum, the chipset write-enable sequence and that registers/stack are preserved.

    python tools/test_xtide_apply.py        (after bash tools/build_patched.sh xtide-setup; needs pip install unicorn)
"""
import re, sys
from unicorn import *
from unicorn.x86_const import *

rom = open("build/patched/xtide-setup/rom.bin", "rb").read()
lst = open("build/patched/xtide-setup/sys.lst", encoding="utf-8", errors="replace").read()
def sym(name):
    m = re.search(r"^\s*\d+ ([0-9A-F]{8}) .*?\b%s:" % re.escape(name), lst, re.M)
    if not m:
        m = re.search(r"^\s*\d+\s+%s:" % re.escape(name), lst, re.M)  # label on its own line: address of next line
        assert m, name
        after = lst[m.end():]
        m2 = re.search(r"^\s*\d+ ([0-9A-F]{8}) ", after, re.M)
        return int(m2.group(1), 16)
    return int(m.group(1), 16)
APPLY = sym("xtide_apply_cmos_config")
print("xtide_apply_cmos_config at F000:%04X" % APPLY)

def run(cmos60, cmos61):
    uc = Uc(UC_ARCH_X86, UC_MODE_16)
    uc.mem_map(0, 0x100000)
    uc.mem_write(0xC0000, rom[0:0x8000]); uc.mem_write(0xE8000, rom[0x8000:0xE000]); uc.mem_write(0xEE000, rom[0xE000:0x10000]); uc.mem_write(0xF0000, rom[0x10000:])
    cmos = bytearray(128); cmos[0x60] = cmos60; cmos[0x61] = cmos61
    state = {"cidx": 0, "chip": 0, "regs": {0x207: 0x0000, 0x200: 0x1F00}, "log": []}
    def hin(uc, port, size, ud):
        if port == 0x71: return cmos[state["cidx"] & 0x7F]
        if port == 0x26: return state["regs"].get(state["chip"], 0)
        return 0
    def hout(uc, port, size, value, ud):
        if port == 0x70: state["cidx"] = value
        elif port == 0x71: cmos[state["cidx"] & 0x7F] = value & 0xFF
        elif port == 0x24: state["chip"] = value
        elif port == 0x26: state["regs"][state["chip"]] = value; state["log"].append("reg %03X := %04X" % (state["chip"], value))
    uc.hook_add(UC_HOOK_INSN, hin, None, 1, 0, UC_X86_INS_IN)
    uc.hook_add(UC_HOOK_INSN, hout, None, 1, 0, UC_X86_INS_OUT)
    # stack at 0000:7000, push a return address that points at a HLT sentinel in RAM
    uc.mem_write(0x0500, b"\xF4")
    uc.reg_write(UC_X86_REG_SS, 0); uc.reg_write(UC_X86_REG_SP, 0x7000 - 2); uc.mem_write(0x7000 - 2, (0x0500).to_bytes(2, "little"))
    uc.reg_write(UC_X86_REG_CS, 0xF000); uc.reg_write(UC_X86_REG_DS, 0xF000)
    uc.reg_write(UC_X86_REG_AX, 0x1234); uc.reg_write(UC_X86_REG_BX, 0x5678)
    try:
        uc.emu_start(0xF0000 + APPLY, 0xF0500, timeout=2_000_000, count=2_000_000)
    except UcError as e:
        print("  emulation error:", e, "at %04X:%04X" % (uc.reg_read(UC_X86_REG_CS), uc.reg_read(UC_X86_REG_IP)))
    ip = uc.reg_read(UC_X86_REG_IP)
    xub = uc.mem_read(0xEE000, 0x2000)
    assert uc.reg_read(UC_X86_REG_AX) == 0x1234 and uc.reg_read(UC_X86_REG_BX) == 0x5678 and uc.reg_read(UC_X86_REG_SP) == 0x7000, "registers/stack not preserved"
    return xub, state, ip

orig = rom[0xE000:0x10000]
print("original: bIdeCnt %d bBootDrv %02X idle %d master %02X slave %02X sum %02X" % (orig[72], orig[73], orig[76], orig[84], orig[90], sum(orig) & 0xFF))
cases = [
    (0x00, 0x00, "BIOS Default -> untouched"),
    (0x01, 0x00, "Custom, all defaults"),
    (0x01 | 0x02 | (1 << 2) | 0x10 | (2 << 5), (2 | (3 << 2) | (3 << 4)), "2 ctrl, boot 81h, block off, cache enable, master LARGE, slave LBA, standby 10 min"),
    (0x01 | (2 << 2) | (1 << 5), (1 | (2 << 2) | (4 << 4)), "boot floppy, cache default, master CHS, slave LARGE, standby 20 min"),
]
ok = True
for c60, c61, desc in cases:
    xub, st, ip = run(c60, c61)
    s = sum(xub) & 0xFF
    print("case %02X/%02X %s\n   bIdeCnt %d bBootDrv %02X idle %3d master %02X slave %02X checksum-sum %02X  ip=%04X  chipset: %s" % (
        c60, c61, desc, xub[72], xub[73], xub[76], xub[84], xub[90], s, ip, "; ".join(st["log"])))
    if c60 & 1 == 0:
        ok &= bytes(xub) == orig
    else:
        exp_cnt = 2 if c60 & 2 else 1
        exp_boot = [0x80, 0x81, 0x00, 0x80][(c60 >> 2) & 3]
        exp_idle = [0, 12, 60, 120, 240, 0, 0, 0][(c61 >> 4) & 7]
        tr = [3, 0, 1, 2]; cache = [1, 0, 2, 1][(c60 >> 5) & 3]; block = 0 if c60 & 0x10 else 0x10
        exp_m = (orig[84] & 0xE0) | (tr[c61 & 3] << 2) | block | cache
        exp_s = (orig[90] & 0xE0) | (tr[(c61 >> 2) & 3] << 2) | block | cache
        good = (xub[72], xub[73], xub[76], xub[84], xub[90], s) == (exp_cnt, exp_boot, exp_idle, exp_m, exp_s, 0)
        good &= bytes(xub[:72]) == orig[:72] and bytes(xub[91:0x1FFF]) == orig[91:0x1FFF] and xub[74:76] == orig[74:76] and xub[77:84] == orig[77:84] and xub[85:90] == orig[85:90]
        good &= st["log"] == ["reg 207 := 0800", "reg 207 := 0000"]
        if not good: print("   MISMATCH: expected cnt %d boot %02X idle %d master %02X slave %02X sum 0" % (exp_cnt, exp_boot, exp_idle, exp_m, exp_s))
        ok &= good
print("ALL OK" if ok else "FAILURES")
