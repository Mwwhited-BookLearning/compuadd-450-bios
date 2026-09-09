#!/usr/bin/env python3
"""
mkasm.py - emit re-assemblable NASM source for a module, verified byte-exact against the ROM.

The listing files in disasm/ are read-only views (address, bytes, mnemonic).  This tool produces
src/<module>.asm: the same labels and comments, but in NASM syntax with `org 0`, so that

    nasm -f bin src/sys.asm -o build/rebuilt/sys.bin

reproduces the original 64 KB module bit for bit.  Every instruction is verified: the source is
assembled once with a listing, each source line's bytes are compared with the ROM, and lines that
NASM would encode differently (it picks shorter forms) are rewritten as `db` with the mnemonic in
a comment, then the file is assembled again.  Branch targets use the labels, data is emitted as
`db`, FFh/00h fill as `times`.

    mkasm.py --module sys --nasm PATH/nasm[.exe]     (run from the bios folder after tools/run.sh)
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import romdis  # noqa: E402
from capstone.x86 import X86_GRP_JUMP, X86_GRP_CALL, X86_OP_MEM  # noqa: E402

MODS = {"sys": ("build/sys.bin", 0xF000), "vga": ("build/vga.bin", 0xC000), "miser": ("build/miser.bin", 0xE800)}
RESERVED = {"wait", "in", "out", "int", "loop", "and", "or", "xor", "not", "seg", "wrt", "strict", "byte", "word", "dword", "short", "near", "far",
            "rep", "repe", "repne", "lock", "times", "db", "dw", "dd", "org", "bits", "equ", "sti", "cli", "hlt", "nop", "ret", "retf", "iret", "call", "jmp",
            "ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "cs", "ds", "es", "ss", "fs", "gs", "al", "ah", "bl", "bh", "cl", "ch", "dl", "dh", "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}
STRING_OPS = ("movs", "stos", "lods", "scas", "cmps", "ins", "outs")
PREFIXES = ("rep ", "repe ", "repne ", "repz ", "repnz ", "lock ")


def nasm_name(n):
    n = re.sub(r"[^A-Za-z0-9_.]", "_", n)
    if n[0].isdigit():
        n = "_" + n
    if n.lower() in RESERVED:
        n += "_"
    return n


class Emitter:
    def __init__(self, m):
        self.m = m
        self.lines = []       # source lines
        self.check = {}       # source line index -> (offset, expected bytes)
        self.fallback = set()  # offsets forced to db

    def label(self, off):
        nm = self.m.name_of(off)
        if not nm:
            return None
        if not hasattr(self, "_uniq"):
            self._uniq = {}
            seen = {}
            for o in sorted(set(self.m.kind) | set(self.m.names)):
                n = self.m.name_of(o)
                if not n:
                    continue
                base = nasm_name(n)
                if base in seen and seen[base] != o:
                    base = "%s_%04X" % (base, o)
                seen.setdefault(base, o)
                self._uniq[o] = base
        return self._uniq.get(off, nasm_name(nm))

    def covered(self):
        if not hasattr(self, "_cov"):
            c = bytearray(self.m.size)
            for o, i in self.m.insns.items():
                for k in range(1, i.size):
                    if o + k < self.m.size:
                        c[o + k] = 1
            self._cov = c
        return self._cov

    def target_text(self, insn, off_target):
        lab = self.label(off_target)
        if lab and off_target < self.m.size and not self.covered()[off_target]:
            return lab
        return "0x%04X" % off_target

    def convert(self, insn):
        """capstone Intel syntax -> NASM; returns None when a db fallback is wanted."""
        mn = insn.mnemonic
        ops = insn.op_str
        prefix = ""
        for p in PREFIXES:
            if mn.startswith(p):
                prefix, mn = p, mn[len(p):]
        # string instructions: drop the operands, keep an explicit segment override if unusual
        if mn.startswith(STRING_OPS):
            a32 = "a32 " if ("esi" in ops or "edi" in ops) else ""
            segp = ""
            m3 = re.search(r"(cs|ss|es|fs|gs):\[e?si\]", ops)
            if m3 and not (m3.group(1) == "es" and mn.startswith(("stos", "ins", "scas"))):
                segp = m3.group(1) + " "
            return (prefix + a32 + segp + mn).strip()
        # far jumps / calls
        if mn in ("ljmp", "lcall"):
            m2 = re.match(r"0x([0-9a-f]+):0x([0-9a-f]+)", ops)
            if not m2:
                return None
            return "%s 0x%s:0x%s" % ("jmp" if mn == "ljmp" else "call", m2.group(1).upper(), m2.group(2).upper())
        # branches with immediate target
        groups = insn.groups
        if (X86_GRP_JUMP in groups or X86_GRP_CALL in groups or mn in ("loop", "loope", "loopne", "jcxz", "jecxz")) and re.fullmatch(r"0x[0-9a-f]+", ops):
            tgt = int(ops, 16) & 0xFFFF
            t = self.target_text(insn, tgt)
            if mn in ("loop", "loope", "loopne", "jcxz", "jecxz"):
                return "%s %s" % (mn, t)
            if mn == "jmp":
                return "jmp %s %s" % ("short" if insn.size == 2 else "near", t)
            if mn == "call":
                return "call %s" % t
            return "%s %s %s" % (mn, "short" if insn.size == 2 else "near", t)
        # renamed mnemonics
        mn = {"pushaw": "pusha", "popaw": "popa", "pushal": "pushad", "popal": "popad"}.get(mn, mn)
        if mn in ("retf", "ret", "iret") and insn.bytes[0] == 0x66:
            mn = "o32 " + mn
        s = ops
        s = s.replace("word ptr ", "word ").replace("byte ptr ", "byte ").replace("dword ptr ", "dword ").replace("qword ptr ", "").replace("ptr ", "")
        s = re.sub(r"\b(cs|ds|es|ss|fs|gs):\[", r"[\1:", s)
        if mn in ("fnsave", "frstor", "lgdt", "lidt", "sgdt", "sidt", "fnstcw", "fldcw"):
            s = s.replace("dword ", "").replace("word ", "")
        if mn == "mov" and re.search(r"\b(cr|dr|tr)\d", s):
            pass
        if "xmm" in s or "st(" in s:
            return None
        s = self.symbolic_mem(insn, s)
        return (prefix + mn + (" " + s if s else "")).strip()

    def symbolic_mem(self, insn, s):
        """Replace the displacement of a memory operand with its vars.inc expression when the segment is proven."""
        if getattr(self.m, "vars", None) is None:
            return s
        for op in insn.operands:
            if op.type != X86_OP_MEM:
                continue
            r = self.m.resolve_mem_expr(insn, op)
            if not r or not r[1]:
                continue
            expr, _ = r
            disp = op.mem.disp & 0xFFFF
            m1 = re.search(r"\[([^\]]*)\]", s)
            if not m1:
                continue
            inner = m1.group(1)
            # capstone prints small displacements in decimal, larger ones as 0x..; negative ones as "- 0x.."
            new_inner = None
            for c in ("0x%x" % disp, "%d" % disp):
                if inner.endswith("+ " + c) or inner == c or inner.endswith(":" + c):
                    new_inner = inner[:-len(c)] + expr
                    break
            neg = (0x10000 - disp) & 0xFFFF
            if new_inner is None and neg:
                for c in ("0x%x" % neg, "%d" % neg):
                    if inner.endswith("- " + c):
                        new_inner = inner[:-len("- " + c)] + "+ " + expr
                        break
            if new_inner is not None:
                s = s[:m1.start(1)] + new_inner + s[m1.end(1):]
        return s

    def emit_insn(self, off, insn):
        text = None if off in self.fallback else self.convert(insn)
        cmt = self.m.auto_comment(insn) if hasattr(self.m, "auto_comment") else ""
        if text is None:
            hexs = ", ".join("0x%02X" % b for b in insn.bytes)
            text = "db %s" % hexs
            cmt = ("%s %s" % (insn.mnemonic, self.m.fmt_operands(insn))).strip() + (" ; " + cmt if cmt else "")
        line = "        %-40s ; %04X%s" % (text, off, ("  " + cmt) if cmt else "")
        self.check[len(self.lines)] = (off, bytes(insn.bytes))
        self.lines.append(line)

    def emit_data(self, start, end):
        d = self.m.data[start:end]
        off = start
        while off < end:
            # fill runs
            b = d[off - start]
            run = 0
            while off + run < end and d[off - start + run] == b:
                run += 1
            if run >= 8 and b in (0, 0xFF):
                self.check[len(self.lines)] = (off, bytes([b]) * run)
                self.lines.append("        times %d db 0x%02X%s ; %04X fill" % (run, b, " " * 20, off))
                off += run
                continue
            n = min(16, end - off)
            chunk = d[off - start: off - start + n]
            asc = "".join(chr(x) if 0x20 <= x < 0x7F else "." for x in chunk)
            self.check[len(self.lines)] = (off, bytes(chunk))
            self.lines.append("        db %s ; %04X %s" % (", ".join("0x%02X" % x for x in chunk), off, asc))
            off += n

    def build(self, title):
        m = self.m
        self.lines = ["; %s" % title, "; re-assemblable NASM source generated by tools/mkasm.py from the labelled analysis (labels are best guesses)",
                      "; nasm -f bin -i src/ %s -o module.bin  reproduces the ROM module byte for byte", "        bits 16", "        org 0",
                      "%include \"vars.inc\"          ; RAM variable / structure offsets (generated from labels/vars.json)", ""]
        self.check = {}
        off = 0
        while off < m.size:
            nm = self.label(off)
            if nm or off in m.comments:
                self.lines.append("")
                if off in m.comments:
                    for c in m.comments[off].split("\n"):
                        self.lines.append("; %s" % c)
                if nm:
                    self.lines.append("%s:" % nm)
            for s, e, c in m.data_ranges:
                if s == off and c:
                    self.lines.append("; [data] %s" % c)
            if off in m.insns:
                insn = m.insns[off]
                self.emit_insn(off, insn)
                off += insn.size
            else:
                end = off + 1
                while end < m.size and end not in m.insns and m.name_of(end) is None and end not in m.comments \
                        and not any(s == end for s, _, _ in m.data_ranges):
                    end += 1
                self.emit_data(off, end)
                off = end
        return "\n".join(self.lines) + "\n"


def self_line_is_times(line):
    return line.lstrip().startswith("times ")


def parse_listing(path):
    """NASM -l listing -> {source line number: bytes}"""
    out = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"^\s*(\d+)\s+([0-9A-F]{8})\s+([0-9A-F\-]+|<rep [^>]*>)?\s*(.*)$", line.rstrip("\n"))
        if not m:
            continue
        ln = int(m.group(1))
        hx = (m.group(3) or "").replace("-", "")
        if hx.startswith("<rep"):
            continue
        if re.fullmatch(r"[0-9A-F]*", hx) and hx:
            out.setdefault(ln, bytearray()).extend(bytes.fromhex(hx))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", required=True, choices=MODS)
    ap.add_argument("--nasm", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    binpath, seg = MODS[a.module]
    data = open(binpath, "rb").read()
    spec = json.load(open("labels/%s.json" % a.module))
    m = romdis.Module(data, seg, spec)
    m.segname = "%04X" % seg
    m.analyze()
    em = Emitter(m)
    outpath = a.out or "src/%s.asm" % a.module
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    if m.vars is not None:
        m.write_vars_inc(os.path.join(os.path.dirname(outpath), "vars.inc"))
    os.makedirs("build/rebuilt", exist_ok=True)
    title = "%s module, segment %04X" % (a.module, seg)
    err_fallback = set()
    for rnd in range(12):
        em.fallback |= err_fallback
        src = em.build(title)
        em.fallback -= err_fallback
        open(outpath, "w", newline="\n").write(src)
        lst = "build/rebuilt/%s.lst" % a.module
        outbin = "build/rebuilt/%s.bin" % a.module
        r = subprocess.run([a.nasm, "-f", "bin", "-i", os.path.dirname(outpath) + "/", outpath, "-o", outbin, "-l", lst], capture_output=True, text=True)
        if r.returncode != 0:
            errs = set(int(x) for x in re.findall(r":(\d+): error", r.stderr))
            new = 0
            for ln in errs:
                off = em.check.get(ln - 1, (None,))[0]
                if off is not None and off in m.insns and off not in err_fallback:
                    err_fallback.add(off); new += 1
            print("round %d: nasm errors on %d lines (%d newly forced to db to continue)" % (rnd, len(errs), new))
            if new == 0:
                print(r.stderr[:2000]); sys.exit("nasm failed")
            continue
        if err_fallback:
            err_fallback = set()
        got = parse_listing(lst)
        bad = 0
        for idx, (off, exp) in em.check.items():
            g = bytes(got.get(idx + 1, b""))
            if self_line_is_times(em.lines[idx]):
                continue
            if g != exp:
                if off in em.fallback:
                    continue
                if off in m.insns:
                    em.fallback.add(off)
                bad += 1
        result = open(outbin, "rb").read()
        print("round %d: %d mismatching lines, output %d bytes, %s" % (rnd, bad, len(result), "IDENTICAL" if result == data else "differs"))
        if result == data and bad == 0:
            break
    n_db = len(em.fallback)
    print("%s: %d instructions kept as mnemonics, %d written as db (encodings NASM would change)" % (a.module, len(m.insns) - n_db, n_db))


if __name__ == "__main__":
    main()
