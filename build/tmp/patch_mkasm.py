p = "tools/mkasm.py"
s = open(p, encoding="utf-8").read()
old = '''        if "xmm" in s or "st(" in s:
            return None
        return (prefix + mn + (" " + s if s else "")).strip()
'''
new = '''        if "xmm" in s or "st(" in s:
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
            m1 = re.search(r"\\[([^\\]]*)\\]", s)
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
'''
assert old in s
s = s.replace(old, new)
s = s.replace("from capstone.x86 import X86_GRP_JUMP, X86_GRP_CALL  # noqa: E402",
              "from capstone.x86 import X86_GRP_JUMP, X86_GRP_CALL, X86_OP_MEM  # noqa: E402")
old2 = '''                      "; nasm -f bin %s -o module.bin  reproduces the ROM module byte for byte", "        bits 16", "        org 0", ""]'''
new2 = '''                      "; nasm -f bin -i src/ %s -o module.bin  reproduces the ROM module byte for byte", "        bits 16", "        org 0",
                      "%include \\"vars.inc\\"          ; RAM variable / structure offsets (generated from labels/vars.json)", ""]'''
assert old2 in s
s = s.replace(old2, new2)
old3 = '''        r = subprocess.run([a.nasm, "-f", "bin", outpath, "-o", outbin, "-l", lst], capture_output=True, text=True)'''
new3 = '''        r = subprocess.run([a.nasm, "-f", "bin", "-i", os.path.dirname(outpath) + "/", outpath, "-o", outbin, "-l", lst], capture_output=True, text=True)'''
assert old3 in s
s = s.replace(old3, new3)
old4 = '''    em = Emitter(m)
    outpath = a.out or "src/%s.asm" % a.module
    os.makedirs(os.path.dirname(outpath), exist_ok=True)'''
new4 = '''    em = Emitter(m)
    outpath = a.out or "src/%s.asm" % a.module
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    if m.vars is not None:
        m.write_vars_inc(os.path.join(os.path.dirname(outpath), "vars.inc"))'''
assert old4 in s
s = s.replace(old4, new4)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("mkasm patched")
