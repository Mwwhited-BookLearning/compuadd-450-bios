#!/usr/bin/env python3
"""
romdis.py - 16-bit real-mode recursive-descent disassembler for ROM BIOS modules.

Built for the Compuadd 486 "Color Scan 450" BIOS teardown.  Runs under WSL with
the capstone python bindings (see setup-wsl.sh).

Usage:
    romdis.py --bin sys.bin --seg 0xF000 --labels labels/sys.json --out disasm/sys.asm
           [--report disasm/sys-functions.md] [--entry E05B ...]

The label file drives everything that cannot be derived from the bytes alone:

{
  "entries":  ["E05B"],                       # extra code entry points (hex offsets in segment)
  "labels":   {"E05B": {"name": "reset_entry", "comment": "..."}},
  "data":     [["E00E", "E011", "IBM compat signature"]],   # inclusive-exclusive ranges never decoded
  "strings":  [["E020", "E053"]],             # ranges forced to be emitted as text
  "tables":   [{"at": "1234", "count": 8, "kind": "near_ptr", "name": "ivt_init", "func": true}],
  "linear":   [["1000", "1100"]],             # force linear decode of a range (unreachable code)
  "linkreg":  [["5800", "10000"]],            # ranges where the bp/di/si link-register idiom is trusted
  "inline_string_calls": ["D309"],            # `call X` followed by a NUL-terminated message
  "selectors": ["0038", "0040"]               # protected-mode selectors that alias this segment
}

Heuristics specific to Phoenix ROM code (stack-less early POST):
  * `mov bp/di/si/bx/dx/cx, imm16` immediately followed by `jmp rel`  => imm16 is a return
    address.  It is added as a code entry and labelled ret_XXXX.
  * `push imm16` immediately followed by `jmp rel`                    => same (fake call).
  * `jmp reg16` is treated as a return (path terminates).
"""
import argparse
import json
import os
import sys
from collections import defaultdict

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_16, CS_OP_IMM, CS_OP_REG, CS_OP_MEM
    from capstone.x86 import X86_GRP_JUMP, X86_GRP_CALL, X86_GRP_RET, X86_GRP_IRET
except ImportError:
    sys.exit("capstone not found - run tools/setup-wsl.sh and use ~/.venv-bios/bin/python")

RET_REGS = {"bp", "di", "si", "bx", "dx", "cx", "ax"}


def h(v):
    return int(v, 16) if isinstance(v, str) else v


class Module:
    def __init__(self, data, seg, labelspec):
        self.data = data
        self.seg = seg
        self.size = len(data)
        self.md = Cs(CS_ARCH_X86, CS_MODE_16)
        self.md.detail = True
        self.insns = {}            # offset -> capstone insn
        self.kind = {}             # offset -> 'sub' | 'loc' | 'ret' | 'tbl'
        self.names = {}            # offset -> name
        self.comments = {}         # offset -> comment
        self.xrefs = defaultdict(set)
        self.data_ranges = []      # (start, end, comment)
        self.string_ranges = []
        self.tables = []
        self.entries = []
        self.linear = []
        self.notes = defaultdict(list)   # offset -> list of analysis notes
        self.romstack = {}               # ROM-stack word offset -> return address it holds
        # RAM variable naming (labels/vars.json): segment tracking + region lookup, see resolve_mem()
        self.modname = {0xF000: "sys", 0xC000: "vga", 0xE800: "miser"}.get(seg, "%04X" % seg)
        self.vars = None
        self.segstate = None             # insn offset -> {"ds": seg|"cs"|None, "es": ...}
        self.func_of = {}                # insn offset -> function start offset
        self.var_xrefs = defaultdict(set)   # "region.name" -> {"module:function"}
        vpath = labelspec.get("vars_file", os.path.join("labels", "vars.json")) if isinstance(labelspec, dict) else None
        if vpath and os.path.exists(vpath):
            self.vars = json.load(open(vpath))
        self.load_spec(labelspec)

    # ------------------------------------------------------------------ spec
    def load_spec(self, spec):
        for e in spec.get("entries", []):
            self.entries.append(h(e))
        for k, v in spec.get("labels", {}).items():
            off = h(k)
            if isinstance(v, str):
                v = {"name": v}
            if "name" in v:
                self.names[off] = v["name"]
            if "comment" in v:
                self.comments[off] = v["comment"]
        for r in spec.get("data", []):
            self.data_ranges.append((h(r[0]), h(r[1]), r[2] if len(r) > 2 else ""))
        for r in spec.get("strings", []):
            self.string_ranges.append((h(r[0]), h(r[1])))
            self.data_ranges.append((h(r[0]), h(r[1]), "string"))
        for t in spec.get("tables", []):
            self.tables.append(t)
        for r in spec.get("linear", []):
            self.linear.append((h(r[0]), h(r[1])))
        self.linkreg = [(h(r[0]), h(r[1])) for r in spec.get("linkreg", [])]
        # functions that consume a NUL-terminated string placed immediately after the CALL
        self.inline_str = set(h(x) for x in spec.get("inline_string_calls", []))
        # protected-mode selectors whose base is this module (far jmp/call through them stays here)
        self.selectors = set(h(x) for x in spec.get("selectors", []))

    def in_data(self, off):
        for s, e, _ in self.data_ranges:
            if s <= off < e:
                return True
        return False

    def in_module(self, off):
        return 0 <= off < self.size

    def linkreg_ok(self, off):
        """Link-register call idiom is only trusted inside configured ranges (opt-in; off when none given)."""
        return any(s <= off < e for s, e in self.linkreg)

    def looks_like_text(self, off, n=4):
        """True if `n` printable ASCII bytes start at off (a message, not a return address)."""
        if off + n > self.size:
            return False
        return all(0x20 <= b < 0x7F or b in (0x0D, 0x0A, 0x09) for b in self.data[off:off + n])

    # ------------------------------------------------------------ labelling
    def label(self, off, kind, src=None):
        if not self.in_module(off):
            return
        rank = {"tbl": 0, "loc": 1, "ret": 2, "sub": 3}
        if off not in self.kind or rank[kind] > rank[self.kind[off]]:
            self.kind[off] = kind
        if src is not None:
            self.xrefs[off].add(src)

    def name_of(self, off):
        if off in self.names:
            return self.names[off]
        k = self.kind.get(off)
        if k is None:
            return None
        return {"sub": "sub_", "loc": "loc_", "ret": "ret_", "tbl": "tbl_"}[k] + "%04X" % off

    # ------------------------------------------------------------ tables
    def expand_tables(self):
        for t in self.tables:
            at = h(t["at"])
            cnt = t["count"]
            kind = t.get("kind", "near_ptr")
            name = t.get("name", "tbl_%04X" % at)
            self.names.setdefault(at, name)
            self.kind.setdefault(at, "tbl")
            if kind == "near_ptr":
                stride = t.get("stride", 2)
                end = at + cnt * stride
                if stride == 2:
                    self.data_ranges.append((at, end, "table %s (%d near ptrs)" % (name, cnt)))
                else:  # pointers embedded in a struct table: only the pointer words are data
                    for i in range(cnt):
                        self.data_ranges.append((at + i * stride, at + i * stride + 2, "table %s (%d near ptrs, stride %d)" % (name, cnt, stride)))
                for i in range(cnt):
                    p = at + i * stride
                    tgt = self.data[p] | (self.data[p + 1] << 8)
                    if self.in_module(tgt) and not self.in_data(tgt):
                        self.label(tgt, "sub" if t.get("func", True) else "loc", src=p)
                        self.entries.append(tgt)
                        if t.get("items"):
                            self.names.setdefault(tgt, t["items"][i])
            elif kind == "far_ptr":
                end = at + cnt * 4
                self.data_ranges.append((at, end, "table %s (%d far ptrs)" % (name, cnt)))
                for i in range(cnt):
                    p = at + i * 4
                    tgt = self.data[p] | (self.data[p + 1] << 8)
                    sg = self.data[p + 2] | (self.data[p + 3] << 8)
                    if sg == self.seg and self.in_module(tgt) and not self.in_data(tgt):
                        self.label(tgt, "sub", src=p)
                        self.entries.append(tgt)
                        if t.get("items"):
                            self.names.setdefault(tgt, t["items"][i])
            elif kind in ("word", "byte", "struct"):
                stride = t.get("stride", 2 if kind == "word" else 1)
                self.data_ranges.append((at, at + cnt * stride, "table %s (%d x %d bytes)" % (name, cnt, stride)))

    # ------------------------------------------------------------ decoding
    def decode_at(self, off):
        if off in self.insns:
            return self.insns[off]
        if not self.in_module(off) or self.in_data(off):
            return None
        chunk = self.data[off:off + 15]
        for insn in self.md.disasm(chunk, off, 1):
            # refuse to overlap already-decoded instructions or data
            for b in range(off, off + insn.size):
                if b != off and b in self.insns:
                    return None
                if self.in_data(b):
                    return None
            self.insns[off] = insn
            return insn
        return None

    def imm_target(self, insn):
        for op in insn.operands:
            if op.type == CS_OP_IMM:
                return op.imm & 0xFFFF
        return None

    def analyze(self):
        self.expand_tables()
        work = list(dict.fromkeys(self.entries))
        for e in work:
            self.label(e, self.kind.get(e, "sub"))
        for s, e in self.linear:
            work.append(s)
        seen = set()
        while work:
            off = work.pop()
            prev = None
            regs = {}          # r16 -> imm16 known within this straight-line block
            last_cmp = None    # (imm, addr) of the most recent `cmp r, imm` in this block
            ram_stack = False  # set once the block loads SS from anything but the reset-vector word
            while True:
                if off in seen:
                    break
                insn = self.decode_at(off)
                if insn is None:
                    if self.in_module(off) and not self.in_data(off) and off not in self.insns:
                        self.notes[off].append("undecodable / overlaps existing code")
                    break
                seen.add(off)
                groups = insn.groups
                mn = insn.mnemonic
                nxt = off + insn.size
                is_jump = X86_GRP_JUMP in groups or mn.startswith("loop") or mn in ("jcxz", "jecxz")
                is_call = X86_GRP_CALL in groups
                is_ret = X86_GRP_RET in groups or X86_GRP_IRET in groups

                if is_ret:
                    break

                if mn == "cmp" and len(insn.operands) == 2 and insn.operands[1].type == CS_OP_IMM:
                    last_cmp = (insn.operands[1].imm & 0xFFFF, off)
                # `mov ss, <anything but cs:[FFF3]>` means a real RAM stack: disable the ROM-stack idiom
                if mn == "mov" and len(insn.operands) == 2 and insn.operands[0].type == CS_OP_REG \
                        and insn.reg_name(insn.operands[0].reg) == "ss":
                    src = insn.operands[1]
                    if src.type == CS_OP_MEM and (src.mem.disp & 0xFFFF) == 0xFFF3:
                        ram_stack = False          # mov ss, cs:[FFF3]  (= F000)
                    elif src.type == CS_OP_REG and regs.get(insn.reg_name(src.reg)) == "CS":
                        ram_stack = False          # mov ax, cs ; mov ss, ax
                    else:
                        ram_stack = True
                elif mn == "mov" and len(insn.operands) == 2 and insn.operands[0].type == CS_OP_REG \
                        and insn.operands[1].type == CS_OP_REG and insn.reg_name(insn.operands[1].reg) == "cs":
                    regs[insn.reg_name(insn.operands[0].reg)] = "CS"
                # track `mov r16, imm16` so `jmp reg` / ROM-stack idioms can be resolved
                if mn == "mov" and len(insn.operands) == 2 and insn.operands[0].type == CS_OP_REG \
                        and insn.operands[1].type == CS_OP_IMM:
                    regs[insn.reg_name(insn.operands[0].reg)] = insn.operands[1].imm & 0xFFFF
                elif insn.operands and insn.operands[0].type == CS_OP_REG and not is_jump and not is_call \
                        and mn not in ("cmp", "test", "out", "push") \
                        and not (mn == "mov" and len(insn.operands) == 2 and insn.operands[1].type == CS_OP_REG
                                 and insn.reg_name(insn.operands[1].reg) == "cs"):
                    regs.pop(insn.reg_name(insn.operands[0].reg), None)

                if is_call:
                    if mn == "lcall":
                        # far call ptr16:16 -> capstone gives two imm ops: seg, off
                        imms = [op.imm for op in insn.operands if op.type == CS_OP_IMM]
                        if len(imms) == 2 and ((imms[0] & 0xFFFF) == self.seg or (imms[0] & 0xFFFF) in self.selectors):
                            tgt = imms[1] & 0xFFFF
                            self.label(tgt, "sub", src=off)
                            work.append(tgt)
                        else:
                            self.notes[off].append("far call outside module")
                    else:
                        tgt = self.imm_target(insn)
                        if tgt is not None and insn.operands[0].type == CS_OP_IMM:
                            self.label(tgt, "sub", src=off)
                            work.append(tgt)
                            if tgt in self.inline_str:
                                # skip the NUL-terminated message that follows the call
                                e = nxt
                                while e < self.size and self.data[e] != 0:
                                    e += 1
                                e = min(e + 1, self.size)
                                self.data_ranges.append((nxt, e, "inline message for " + (self.name_of(tgt) or "%04X" % tgt)))
                                self.string_ranges.append((nxt, e))
                                nxt = e
                                regs = {}
                        else:
                            self.notes[off].append("indirect call")
                    prev = insn
                    off = nxt
                    continue

                if is_jump:
                    op0 = insn.operands[0]
                    if mn == "ljmp":
                        imms = [op.imm for op in insn.operands if op.type == CS_OP_IMM]
                        if len(imms) == 2 and ((imms[0] & 0xFFFF) == self.seg or (imms[0] & 0xFFFF) in self.selectors):
                            tgt = imms[1] & 0xFFFF
                            self.label(tgt, "loc", src=off)
                            work.append(tgt)
                        else:
                            self.notes[off].append("far jump outside module")
                            # `mov sp, tbl ; ljmp far_stub` where the stub is RETF: the far return
                            # address (offset, segment) is the ROM dword at tbl.
                            if "sp" in regs and not ram_stack and self.in_module(regs["sp"] + 3):
                                tbl = regs["sp"]
                                ro = self.data[tbl] | (self.data[tbl + 1] << 8)
                                rs = self.data[tbl + 2] | (self.data[tbl + 3] << 8)
                                if rs == self.seg and self.in_module(ro) and not self.in_data(ro):
                                    self.data_ranges.append((tbl, tbl + 4, "ROM stack dword -> far return address"))
                                    self.label(tbl, "tbl")
                                    self.romstack[tbl] = ro
                                    self.label(ro, "ret", src=off)
                                    work.append(ro)
                        break
                    if op0.type == CS_OP_IMM:
                        tgt = op0.imm & 0xFFFF
                        self.label(tgt, "loc", src=off)
                        work.append(tgt)
                        if mn == "jmp":
                            # Phoenix stack-less call idioms:
                            #   mov sp, tbl ; jmp sub        -> sub's RET pops ROM word at tbl
                            #   mov bp/di/si, ret ; jmp sub  -> sub ends with `jmp bp/di/si`
                            #   push ret ; jmp sub           -> sub ends with RET
                            rets = []
                            if "sp" in regs and not ram_stack:
                                tbl = regs["sp"]
                                if self.in_module(tbl + 1):
                                    r = self.data[tbl] | (self.data[tbl + 1] << 8)
                                    self.data_ranges.append((tbl, tbl + 2, "ROM stack word -> return address"))
                                    self.label(tbl, "tbl")
                                    self.romstack[tbl] = r
                                    rets.append(r)
                            if self.linkreg_ok(off):
                                for lr in ("bp", "di", "si"):
                                    if lr in regs:
                                        rets.append(regs[lr])
                                if prev is not None and prev.mnemonic == "push" and prev.operands[0].type == CS_OP_IMM:
                                    rets.append(prev.operands[0].imm & 0xFFFF)
                            for ret in rets:
                                if self.in_module(ret) and not self.in_data(ret) and not self.looks_like_text(ret) \
                                        and (self.linkreg_ok(ret) or ret in self.romstack.values()):
                                    self.label(ret, "ret", src=off)
                                    self.label(tgt, "sub", src=off)
                                    work.append(ret)
                            break
                        # conditional: fall through
                        prev = insn
                        off = nxt
                        continue
                    else:
                        if op0.type == CS_OP_REG and insn.reg_name(op0.reg) in regs:
                            tgt = regs[insn.reg_name(op0.reg)]
                            if self.in_module(tgt) and not self.in_data(tgt):
                                self.notes[off].append("-> %04X (register set in this block)" % tgt)
                                self.label(tgt, "loc", src=off)
                                work.append(tgt)
                        elif op0.type == CS_OP_REG and insn.reg_name(op0.reg) in RET_REGS:
                            self.notes[off].append("return via register")
                        elif op0.type == CS_OP_MEM and op0.mem.base != 0 and op0.mem.disp > 0:
                            # jump table `jmp cs:[bx+disp]` - report the table and the bound-check seen
                            hint = "jump table at %04X" % (op0.mem.disp & 0xFFFF)
                            if last_cmp is not None:
                                hint += " (last cmp imm=%d @%04X)" % last_cmp
                            self.notes[off].append(hint)
                        else:
                            self.notes[off].append("indirect jump")
                        break

                # `mov reg, imm16` pointing at a label gets an annotation later
                prev = insn
                off = nxt

    # ------------------------------------------------------------ output
    def fmt_operands(self, insn):
        s = insn.op_str
        # symbolic replacement for immediate branch/call targets
        mn = insn.mnemonic
        if (X86_GRP_JUMP in insn.groups or X86_GRP_CALL in insn.groups or mn.startswith("loop")
                or mn in ("jcxz",)) and mn not in ("ljmp", "lcall"):
            if insn.operands and insn.operands[0].type == CS_OP_IMM:
                tgt = insn.operands[0].imm & 0xFFFF
                nm = self.name_of(tgt)
                if nm:
                    return nm
        if mn in ("ljmp", "lcall"):
            imms = [op.imm for op in insn.operands if op.type == CS_OP_IMM]
            if len(imms) == 2:
                sg, tg = imms[0] & 0xFFFF, imms[1] & 0xFFFF
                nm = self.name_of(tg) if (sg == self.seg or sg in self.selectors) else None
                return "%04X:%s" % (sg, nm or "%04X" % tg)
        return s

    def auto_comment(self, insn):
        notes = list(self.notes.get(insn.address, []))
        # annotate immediates that match labels (mov reg, offset)
        if insn.mnemonic in ("mov", "push") and not (X86_GRP_JUMP in insn.groups):
            for op in insn.operands:
                if op.type == CS_OP_IMM:
                    v = op.imm & 0xFFFF
                    nm = self.name_of(v)
                    if nm and v in self.insns:
                        notes.append("-> " + nm)
        # port I/O hints
        if insn.mnemonic in ("in", "out"):
            for op in insn.operands:
                if op.type == CS_OP_IMM:
                    p = op.imm & 0xFF
                    d = PORTS.get(p)
                    if d:
                        notes.append("port %02Xh: %s" % (p, d))
        if insn.mnemonic == "int":
            for op in insn.operands:
                if op.type == CS_OP_IMM:
                    notes.append(INTS.get(op.imm & 0xFF, ""))
        # RAM variables touched by memory operands
        if self.vars is not None:
            for op in insn.operands:
                if op.type == CS_OP_MEM:
                    r = self.resolve_mem(insn, op)
                    if r:
                        notes.append(r)
        return "; ".join(n for n in notes if n)

    # ------------------------------------------------------------ RAM variables
    SEGREGS = {"ds", "es", "cs", "ss", "fs", "gs"}
    GPRS = ("ax", "bx", "cx", "dx", "si", "di", "bp", "sp")

    def function_bounds(self):
        starts = sorted(o for o in set(self.kind) | set(self.names)
                        if o in self.insns and self.name_of(o) and not self.name_of(o).startswith("loc_"))
        return list(zip(starts, starts[1:] + [self.size]))

    def rom_word(self, off):
        if 0 <= off < self.size - 1:
            return self.data[off] | (self.data[off + 1] << 8)
        return None

    def compute_segments(self):
        """Track DS/ES per instruction: segment loads inside each function (immediates, `push cs/pop ds`,
        `mov ds, cs:[word]` constants) plus the incoming DS/ES agreed by every caller (fixpoint over 3 rounds)."""
        bounds = self.function_bounds()
        incoming = {a: ({"ds": None, "es": None}, set()) for a, _ in bounds}
        for _round in range(3):
            self.segstate = {}
            self.func_of = {}
            callsites = defaultdict(list)     # callee -> [(state at call, weak set)]
            for a, b in bounds:
                entry, entry_weak = incoming.get(a, ({"ds": None, "es": None}, set()))
                regs = {}
                seg = dict(entry)
                weak = set(entry_weak)      # segment registers whose value is only inherited from *some* callers
                pushed = []
                off = a
                while off < b:
                    insn = self.insns.get(off)
                    if insn is None:
                        off += 1
                        continue
                    self.segstate[off] = (dict(seg), frozenset(weak))
                    self.func_of[off] = a
                    mn = insn.mnemonic
                    ops = insn.operands
                    rn = insn.reg_name

                    def val_of(op):
                        if op.type == CS_OP_IMM:
                            return op.imm & 0xFFFF
                        if op.type == CS_OP_REG:
                            n = rn(op.reg)
                            if n == "cs":
                                return "cs"
                            if n in ("ds", "es"):
                                return seg.get(n)
                            if n in self.GPRS:
                                return regs.get(n)
                            return None
                        if op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                            sr = rn(op.mem.segment) if op.mem.segment else "ds"
                            if sr == "cs" or (sr == "ds" and seg.get("ds") == "cs"):
                                return self.rom_word(op.mem.disp & 0xFFFF)
                        return None

                    if mn == "mov" and len(ops) == 2 and ops[0].type == CS_OP_REG:
                        d = rn(ops[0].reg)
                        v = val_of(ops[1])
                        if d in self.GPRS:
                            if v is None:
                                regs.pop(d, None)
                            else:
                                regs[d] = v
                        elif d in ("ds", "es"):
                            seg[d] = v
                            weak.discard(d)
                    elif mn in ("xor", "sub") and len(ops) == 2 and ops[0].type == CS_OP_REG and ops[1].type == CS_OP_REG \
                            and ops[0].reg == ops[1].reg and rn(ops[0].reg) in self.GPRS:
                        regs[rn(ops[0].reg)] = 0
                    elif mn == "push" and ops:
                        pushed.append(val_of(ops[0]))
                    elif mn == "pop" and ops and ops[0].type == CS_OP_REG:
                        v = pushed.pop() if pushed else None
                        d = rn(ops[0].reg)
                        if d in ("ds", "es"):
                            seg[d] = v
                            weak.discard(d)
                        elif d in self.GPRS:
                            if v is None:
                                regs.pop(d, None)
                            else:
                                regs[d] = v
                    elif mn in ("lds", "les"):
                        seg["ds" if mn == "lds" else "es"] = None
                        weak.discard("ds" if mn == "lds" else "es")
                        if ops and ops[0].type == CS_OP_REG:
                            regs.pop(rn(ops[0].reg), None)
                    elif mn in ("popa", "popaw", "popad", "popal"):
                        regs = {}
                    elif mn in ("call", "jmp") and ops and ops[0].type == CS_OP_MEM and ops[0].mem.disp:
                        # dispatch through a pointer table: every table entry is a callee reached with this state
                        for tgt in self.table_targets(ops[0].mem.disp & 0xFFFF):
                            if tgt in incoming:
                                callsites[tgt].append((dict(seg), set(weak)))
                        if mn == "jmp":
                            regs = {}
                            seg = dict(entry)
                            weak = set(entry_weak)
                            pushed = []
                    elif mn in ("call", "jmp") and ops and ops[0].type == CS_OP_IMM:
                        tgt = ops[0].imm & 0xFFFF
                        if tgt in incoming:
                            callsites[tgt].append((dict(seg), set(weak)))
                        if mn == "jmp":
                            regs = {}
                            seg = dict(entry)
                            weak = set(entry_weak)
                            pushed = []
                    elif (X86_GRP_RET in insn.groups) or (X86_GRP_IRET in insn.groups) or mn in ("ret", "retf", "iret", "iretw", "ljmp"):
                        regs = {}
                        seg = dict(entry)
                        weak = set(entry_weak)
                        pushed = []
                    elif ops and ops[0].type == CS_OP_REG and rn(ops[0].reg) in self.GPRS and mn not in ("cmp", "test", "push"):
                        regs.pop(rn(ops[0].reg), None)
                    off += insn.size
            # incoming state for the next round: every known caller agrees
            new_in = {}
            for a, _ in bounds:
                st = {"ds": None, "es": None}
                wk = set()
                for k in ("ds", "es"):
                    known = set()
                    unknown = 0
                    anyweak = False
                    for cs_state, cs_weak in callsites.get(a, []):
                        v = cs_state.get(k)
                        if v is None:
                            unknown += 1
                        else:
                            known.add(v)
                            anyweak |= k in cs_weak
                    if len(known) == 1:
                        st[k] = known.pop()
                        if unknown or anyweak:
                            wk.add(k)       # agreed by every caller that knows, but not by all callers
                new_in[a] = (st, wk)
            incoming = new_in

    def table_targets(self, at):
        """Near-pointer targets of the table declared at `at` (labels/*.json tables), [] if none."""
        if not hasattr(self, "_tbl_targets"):
            self._tbl_targets = {}
            for t in self.tables:
                if t.get("kind", "near_ptr") != "near_ptr":
                    continue
                a = h(t["at"]); stride = t.get("stride", 2)
                tg = []
                for i in range(t["count"]):
                    p = a + i * stride
                    w = self.rom_word(p)
                    if w is not None and self.in_module(w):
                        tg.append(w)
                self._tbl_targets[a] = tg
        return self._tbl_targets.get(at, [])

    def struct_for(self, insn, basereg):
        """Structure applying to [basereg+disp] at this instruction, from vars.json struct_use."""
        rules = self.vars.get("struct_use", {}).get(self.modname, [])
        fstart = self.func_of.get(insn.address)
        fname = self.name_of(fstart) if fstart is not None else None
        for r in rules:
            if r.get("reg") != basereg:
                continue
            if "range" in r:
                s, e = int(r["range"][0], 16), int(r["range"][1], 16)
                if not (s <= insn.address < e):
                    continue
            if "functions" in r and fname not in r["functions"]:
                continue
            if "calls" in r:
                if fstart is None or not self.function_calls(fstart, r["calls"]):
                    continue
            return r["struct"]
        return None

    def function_calls(self, fstart, target_name):
        if not hasattr(self, "_fcalls"):
            self._fcalls = {}
        key = (fstart, target_name)
        if key not in self._fcalls:
            bounds = dict(self.function_bounds())
            end = bounds.get(fstart, fstart)
            found = False
            off = fstart
            while off < end:
                insn = self.insns.get(off)
                if insn is None:
                    off += 1
                    continue
                if insn.mnemonic == "call" and insn.operands and insn.operands[0].type == CS_OP_IMM:
                    if self.name_of(insn.operands[0].imm & 0xFFFF) == target_name:
                        found = True
                        break
                off += insn.size
            self._fcalls[key] = found
        return self._fcalls[key]

    def region_lookup(self, linear):
        """linear address -> (region name, 'region.var[+d]' text) or None."""
        for rname, r in self.vars.get("regions", {}).items():
            s, e = int(r["start"], 16), int(r["end"], 16)
            if s <= linear < e:
                rel = linear - s
                for k, v in r.get("vars", {}).items():
                    vo = int(k, 16)
                    sz = v.get("size", 1) if isinstance(v, dict) else 1
                    nm = v["name"] if isinstance(v, dict) else v
                    if vo <= rel < vo + sz:
                        return rname, "%s.%s" % (rname, nm) + ("+%d" % (rel - vo) if rel != vo else "")
                if r.get("auto") == "ivt":
                    return rname, "ivt.int%02Xh.%s" % (rel // 4, "off" if rel % 4 < 2 else "seg") + ("+1" if rel % 2 else "")
                return rname, "%s+0x%X" % (rname, rel)
        return None

    def struct_field(self, sname, disp):
        st = self.vars.get("structs", {}).get(sname)
        if not st:
            return None
        for k, v in st.get("fields", {}).items():
            fo = int(k, 16)
            sz = v.get("size", 1)
            if fo <= disp < fo + sz:
                return "%s.%s" % (sname, v["name"]) + ("+%d" % (disp - fo) if disp != fo else "")
        return "%s+0x%X" % (sname, disp)

    def resolve_mem(self, insn, op):
        if self.segstate is None:
            self.compute_segments()
        mem = op.mem
        rn = insn.reg_name
        disp = mem.disp & 0xFFFF
        base = rn(mem.base) if mem.base else None
        index = rn(mem.index) if mem.index else None
        sr = rn(mem.segment) if mem.segment else ("ss" if base in ("bp", "sp") else "ds")
        text = None
        if base and not index:
            sname = self.struct_for(insn, base)
            if sname:
                text = self.struct_field(sname, disp)
        if text is None and sr != "cs":
            state, weak = self.segstate.get(insn.address, ({}, frozenset()))
            segval = state.get(sr) if sr in ("ds", "es") else None
            assumed = sr in weak
            if segval == "cs":
                return None
            if (base or index) and (assumed or disp < 0x100):
                return None        # array/struct access: only worth naming with a proven segment and a real address
            if segval is None and sr in ("ds", "es"):
                if base is None and not index or disp >= 0x100:
                    for lo, hi, sg in self.vars.get("assume", {}).get(self.modname, []):
                        if int(lo, 16) <= disp < int(hi, 16):
                            segval = int(sg, 16)
                            assumed = True
                            break
            if isinstance(segval, int):
                if segval in (0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
                    linear = disp          # protected-mode data selector with base 0
                else:
                    linear = ((segval << 4) + disp) & 0xFFFFF
                r = self.region_lookup(linear)
                if r:
                    text = r[1] + ("?" if assumed else "")
                    if base or index:
                        text += "[%s]" % "+".join(x for x in (base, index) if x)
        if text:
            f = self.func_of.get(insn.address)
            key = text.rstrip("?").split("[")[0]
            self.var_xrefs[key].add("%s:%s" % (self.modname, self.name_of(f) if f is not None else "?"))
        return text

    def resolve_mem_expr(self, insn, op):
        """NASM expression for the displacement of a memory operand, or None.  Returns (expr, proven): expr uses the
        struc symbols from vars.inc (region.var / struct.field) and evaluates to exactly the original displacement;
        proven is False when the segment register value was assumed rather than tracked."""
        if self.vars is None:
            return None
        if self.segstate is None:
            self.compute_segments()
        mem = op.mem
        rn = insn.reg_name
        disp = mem.disp & 0xFFFF
        base = rn(mem.base) if mem.base else None
        index = rn(mem.index) if mem.index else None
        sr = rn(mem.segment) if mem.segment else ("ss" if base in ("bp", "sp") else "ds")
        if base and not index:
            sname = self.struct_for(insn, base)
            if sname:
                st = self.vars["structs"][sname]
                for k, v in st.get("fields", {}).items():
                    fo = int(k, 16)
                    if fo <= disp < fo + v.get("size", 1):
                        return ("%s.%s" % (sname, v["name"]) + (" + %d" % (disp - fo) if disp != fo else ""), True)
                return None
        if sr == "cs":
            return None
        state, weak = self.segstate.get(insn.address, ({}, frozenset()))
        segval = state.get(sr) if sr in ("ds", "es") else None
        if not isinstance(segval, int):
            return None
        if (base or index) and (sr in weak or disp < 0x100):
            return None
        if segval in (0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
            segbase = 0
        else:
            segbase = (segval << 4) & 0xFFFFF
        linear = (segbase + disp) & 0xFFFFF
        for rname, r in self.vars.get("regions", {}).items():
            s, e = int(r["start"], 16), int(r["end"], 16)
            if not (s <= linear < e):
                continue
            rel = linear - s
            field = None
            for k, v in r.get("vars", {}).items():
                vo = int(k, 16)
                sz = v.get("size", 1) if isinstance(v, dict) else 1
                nm = v["name"] if isinstance(v, dict) else v
                if vo <= rel < vo + sz:
                    field = ("%s.%s" % (rname, nm), rel - vo)
                    break
            if field is None and r.get("auto") == "ivt":
                field = ("ivt.int%02Xh_%s" % (rel // 4, "off" if rel % 4 < 2 else "seg"), rel % 2)
            if field is None:
                return None
            fname, delta = field
            fixed = s - segbase          # region start relative to the segment base
            parts = []
            if fixed > 0:
                parts.append("0x%X" % fixed)
            parts.append(fname)
            if fixed < 0:
                parts.append("- 0x%X" % (-fixed))
            expr = " + ".join(parts).replace("+ - ", "- ")
            if delta:
                expr += " + %d" % delta
            return (expr, sr not in weak)
        return None

    def write_vars_inc(self, path):
        """NASM include with one `struc` per region and per structure, so that region.var / struct.field are the
        offsets used in the sources (relative to the region start; the sources add the segment-dependent base)."""
        lines = ["; vars.inc - RAM variable and structure offsets generated by tools/romdis.py from labels/vars.json",
                 "; region.name = offset of the variable inside its region (bda = 0040:0000, ivt = 0000:0000, miser_ram = DC00:0000, ...);",
                 "; code running with DS = 0 adds 0x400 to reach the BDA, with DS = 0040 it uses the offset directly.", ""]

        def emit_struc(name, fields, total=None):
            lines.append("struc %s" % name)
            pos = 0
            for off, fname, size in sorted(fields):
                if off > pos:
                    lines.append("        resb %d" % (off - pos))
                    pos = off
                if off < pos:
                    continue      # overlapping declaration; first one wins
                lines.append(".%s: resb %d" % (fname, size))
                pos = off + size
            if total is not None and total > pos:
                lines.append("        resb %d" % (total - pos))
            lines.append("endstruc")
            lines.append("")

        for rname, r in self.vars.get("regions", {}).items():
            total = int(r["end"], 16) - int(r["start"], 16)
            fields = []
            for k, v in r.get("vars", {}).items():
                fields.append((int(k, 16), v["name"] if isinstance(v, dict) else v, v.get("size", 1) if isinstance(v, dict) else 1))
            if r.get("auto") == "ivt":
                for n in range(256):
                    fields.append((n * 4, "int%02Xh_off" % n, 2))
                    fields.append((n * 4 + 2, "int%02Xh_seg" % n, 2))
            if total > 0xFFFF:
                total = None
            emit_struc(rname, fields, total)
        for sname, st in self.vars.get("structs", {}).items():
            emit_struc(sname, [(int(k, 16), v["name"], v.get("size", 1)) for k, v in st.get("fields", {}).items()])
        open(path, "w", newline="\n").write("\n".join(lines) + "\n")

    def write_var_xrefs(self, path):
        out = {k: sorted(v) for k, v in self.var_xrefs.items()}
        json.dump(out, open(path, "w"), indent=1, sort_keys=True)

    def is_printable(self, b):
        return 0x20 <= b < 0x7F

    def emit_data(self, out, start, end):
        off = start
        while off < end:
            # string detection
            run = 0
            while off + run < end and self.is_printable(self.data[off + run]):
                run += 1
            forced = any(s <= off < e for s, e in self.string_ranges)
            if run >= 4 or (forced and run >= 1):
                s = self.data[off:off + run].decode("ascii")
                # trailing NUL / high-bit terminator
                term = ""
                if off + run < end and self.data[off + run] in (0, 0x24):
                    term = ",%02Xh" % self.data[off + run]
                    run += 1
                out.write("%s:%04X %-28s db  %s%s\n" % (self.segname, off, "", quote(s), term))
                off += run
                continue
            n = min(16, end - off)
            # stop at start of a printable run >= 4
            for i in range(1, n):
                r = 0
                while off + i + r < end and self.is_printable(self.data[off + i + r]):
                    r += 1
                if r >= 4:
                    n = i
                    break
            chunk = self.data[off:off + n]
            hexs = " ".join("%02X" % b for b in chunk)
            asc = "".join(chr(b) if self.is_printable(b) else "." for b in chunk)
            out.write("%s:%04X %-28s db  %-47s ; %s\n" % (self.segname, off, "", hexs, asc))
            off += n

    def write_listing(self, path, title):
        self.segname = "%04X" % self.seg
        with open(path, "w", newline="\n") as out:
            out.write("; %s\n" % title)
            out.write("; segment %04X, %d (0x%X) bytes; generated by tools/romdis.py - labels are best guesses\n" %
                      (self.seg, self.size, self.size))
            out.write(";\n")
            off = 0
            while off < self.size:
                # label line
                nm = self.name_of(off)
                if nm or off in self.comments:
                    out.write("\n")
                    if nm:
                        xr = sorted(self.xrefs.get(off, []))
                        xs = ""
                        if nm.startswith("loc_"):
                            xs = "  ; in %s" % self.enclosing_function(off)
                        if xr:
                            xs += ("; xrefs: " if xs else "  ; xrefs: ") + ", ".join("%04X" % x for x in xr[:12])
                            if len(xr) > 12:
                                xs += ", +%d more" % (len(xr) - 12)
                        out.write("%s:%s\n" % (nm, xs))
                    if off in self.comments:
                        for line in self.comments[off].split("\n"):
                            out.write("        ; %s\n" % line)
                # data range comments
                for s, e, c in self.data_ranges:
                    if s == off and c:
                        out.write("        ; [data] %s\n" % c)
                if off in self.insns:
                    insn = self.insns[off]
                    hexs = " ".join("%02X" % b for b in insn.bytes)
                    text = "%-7s %s" % (insn.mnemonic, self.fmt_operands(insn))
                    cmt = self.auto_comment(insn)
                    line = "%s:%04X %-28s %s" % (self.segname, off, hexs, text.rstrip())
                    if cmt:
                        line = "%-72s ; %s" % (line, cmt)
                    out.write(line + "\n")
                    off += insn.size
                else:
                    # find end of data run (next insn start or next label)
                    end = off + 1
                    while end < self.size and end not in self.insns and self.name_of(end) is None \
                            and end not in self.comments and not any(s == end for s, _, _ in self.data_ranges):
                        end += 1
                    self.emit_data(out, off, end)
                    off = end

    def enclosing_function(self, off):
        """Nearest preceding label of kind sub/ret (best-effort owner of an address)."""
        best = None
        for o in set(self.kind) | set(self.names):
            k = self.kind.get(o)
            if o <= off and (k in ("sub", "ret") or o in self.names) and (best is None or o > best):
                best = o
        return self.name_of(best) if best is not None else "?"

    def post_codes(self):
        """Find `mov al, imm8` immediately followed by `out 80h, al`."""
        found = []
        for off in sorted(self.insns):
            insn = self.insns[off]
            if insn.mnemonic == "out" and len(insn.operands) == 2 and insn.operands[0].type == CS_OP_IMM \
                    and (insn.operands[0].imm & 0xFF) == 0x80:
                # walk back one instruction
                prev = None
                for back in range(1, 6):
                    if off - back in self.insns and self.insns[off - back].address + self.insns[off - back].size == off:
                        prev = self.insns[off - back]
                        break
                if prev is not None and prev.mnemonic == "mov" and prev.operands[1].type == CS_OP_IMM \
                        and prev.reg_name(prev.operands[0].reg) == "al":
                    found.append((prev.address, prev.operands[1].imm & 0xFF, self.enclosing_function(prev.address)))
        return found

    def write_report(self, path, title):
        subs = sorted(o for o, k in self.kind.items() if k in ("sub", "ret") or o in self.entries)
        with open(path, "w", newline="\n") as out:
            out.write("# %s - function inventory\n\n" % title)
            out.write("Generated by `tools/romdis.py`. Names are best guesses; `sub_XXXX` = unnamed.\n\n")
            out.write("| Address | Name | Callers | Comment |\n|---|---|---|---|\n")
            for o in subs:
                if o not in self.insns:
                    continue
                nm = self.name_of(o) or "sub_%04X" % o
                xr = sorted(self.xrefs.get(o, []))
                xs = ", ".join("%04X" % x for x in xr[:6]) + (" …" if len(xr) > 6 else "")
                cm = self.comments.get(o, "").split("\n")[0]
                out.write("| %04X:%04X | `%s` | %s | %s |\n" % (self.seg, o, nm, xs, cm))
            code = len(self.insns)
            cbytes = sum(i.size for i in self.insns.values())
            out.write("\nCoverage: %d instructions, %d code bytes of %d (%.1f%%).\n" %
                      (code, cbytes, self.size, 100.0 * cbytes / self.size))
            posts = self.post_codes()
            if posts:
                out.write("\n## POST checkpoint codes (port 80h)\n\n")
                out.write("Order is by address, not execution order.\n\n| Address | Code | In function |\n|---|---|---|\n")
                for addr, code, fn in posts:
                    out.write("| %04X:%04X | %02Xh | `%s` |\n" % (self.seg, addr, code, fn))
            und = sorted(self.notes.items())
            if und:
                out.write("\n## Analysis notes\n\n")
                for o, ns in und:
                    out.write("- %04X: %s\n" % (o, "; ".join(ns)))


def quote(s):
    return "'" + s.replace("'", "''") + "'"


# Reference tables used for inline comments ---------------------------------
PORTS = {
    0x00: "DMA1 ch0 addr", 0x01: "DMA1 ch0 count", 0x02: "DMA1 ch1 addr", 0x03: "DMA1 ch1 count",
    0x04: "DMA1 ch2 addr", 0x05: "DMA1 ch2 count", 0x06: "DMA1 ch3 addr", 0x07: "DMA1 ch3 count",
    0x08: "DMA1 status/command", 0x0A: "DMA1 mask", 0x0B: "DMA1 mode", 0x0C: "DMA1 clear flip-flop",
    0x0D: "DMA1 master clear", 0x0F: "DMA1 write mask",
    0x20: "PIC1 command", 0x21: "PIC1 data/mask",
    0x40: "PIT ch0 (timer tick)", 0x41: "PIT ch1 (DRAM refresh)", 0x42: "PIT ch2 (speaker)", 0x43: "PIT control",
    0x60: "KBC data", 0x61: "port B (speaker/parity/refresh)", 0x64: "KBC command/status",
    0x70: "CMOS index / NMI enable", 0x71: "CMOS data",
    0x80: "POST diagnostic code", 0x81: "DMA page ch2", 0x82: "DMA page ch3", 0x83: "DMA page ch1",
    0x87: "DMA page ch0", 0x89: "DMA page ch6", 0x8A: "DMA page ch7", 0x8B: "DMA page ch5", 0x8F: "DMA page refresh",
    0x92: "PS/2 system control (A20/reset)",
    0xA0: "PIC2 command", 0xA1: "PIC2 data/mask",
    0xC0: "DMA2 ch4 addr", 0xC2: "DMA2 ch5 addr", 0xC4: "DMA2 ch6 addr", 0xC6: "DMA2 ch7 addr",
    0xD0: "DMA2 status/command", 0xD4: "DMA2 mask", 0xD6: "DMA2 mode", 0xD8: "DMA2 clear flip-flop",
    0xDA: "DMA2 master clear", 0xDE: "DMA2 write mask",
    0xF0: "FPU busy clear", 0xF1: "FPU reset",
}
INTS = {
    0x10: "video", 0x11: "equipment list", 0x12: "memory size", 0x13: "disk", 0x14: "serial",
    0x15: "system services", 0x16: "keyboard", 0x17: "printer", 0x18: "ROM BASIC / boot fail",
    0x19: "bootstrap", 0x1A: "time", 0x40: "diskette (relocated)", 0x42: "video (relocated)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--seg", required=True, type=lambda x: int(x, 16))
    ap.add_argument("--labels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report")
    ap.add_argument("--title", default="")
    ap.add_argument("--entry", action="append", default=[])
    ap.add_argument("--varxrefs", help="write the RAM-variable cross-reference collected while listing (JSON)")
    a = ap.parse_args()
    data = open(a.bin, "rb").read()
    spec = {}
    if a.labels and os.path.exists(a.labels):
        spec = json.load(open(a.labels))
    for e in a.entry:
        spec.setdefault("entries", []).append(e)
    m = Module(data, a.seg, spec)
    m.analyze()
    m.write_listing(a.out, a.title or os.path.basename(a.bin))
    if a.report:
        m.write_report(a.report, a.title or os.path.basename(a.bin))
    if a.varxrefs:
        m.write_var_xrefs(a.varxrefs)
    cbytes = sum(i.size for i in m.insns.values())
    print("%s: %d insns, %d/%d bytes (%.1f%%) decoded, %d labels" %
          (a.bin, len(m.insns), cbytes, m.size, 100.0 * cbytes / m.size, len(m.kind)))


if __name__ == "__main__":
    main()
