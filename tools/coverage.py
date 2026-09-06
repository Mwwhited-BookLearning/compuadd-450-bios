#!/usr/bin/env python3
"""coverage.py - classify every byte of each module as code / identified data / 00-FF fill / other.

    coverage.py            (run from the bios folder after tools/run.sh)
"""
import json
import re

for mod, size, seg in [("sys", 65536, "F000"), ("miser", 24576, "E800"), ("vga", 32768, "C000")]:
    code = bytearray(size)
    for line in open("disasm/%s.asm" % mod, encoding="utf-8", errors="replace"):
        m = re.match(r"^%s:([0-9A-F]{4}) ((?:[0-9A-F]{2} )+)\s*([a-z]\S*)" % seg, line)
        if m and m.group(3) != "db":
            off = int(m.group(1), 16)
            for i in range(len(m.group(2).split())):
                code[off + i] = 1
    j = json.load(open("labels/%s.json" % mod))
    ident = bytearray(size)
    fillr = bytearray(size)
    for r in j["data"] + [[a, b] for a, b in j["strings"]]:
        isfill = len(r) > 2 and ("fill" in r[2].lower() or "pad" in r[2].lower())
        for i in range(int(r[0], 16), min(int(r[1], 16), size)):
            (fillr if isfill else ident)[i] = 1
    for t in j["tables"]:
        a = int(t["at"], 16)
        kind = t.get("kind", "near_ptr"); esz = {"near_ptr": 2, "far_ptr": 4, "word": 2, "byte": 1, "struct": 1}[kind]
        stride = t.get("stride", esz)
        if kind == "struct":
            esz = stride
        for k in range(t["count"]):
            for i in range(a + k * stride, min(a + k * stride + (esz if stride != esz else stride), size)):
                ident[i] = 1
    raw = open("build/%s.bin" % mod, "rb").read()
    fill = sum(1 for i in range(size) if not code[i] and not ident[i] and (fillr[i] or raw[i] in (0, 0xFF)))
    c = sum(code)
    d = sum(1 for i in range(size) if ident[i] and not code[i])
    other = size - c - d - fill
    labels = len(re.findall(r"^[A-Za-z_][A-Za-z0-9_]*:(?:\s|$)", open("disasm/%s.asm" % mod, encoding="utf-8", errors="replace").read(), re.M))
    print("%-6s code %5d (%4.1f%%)  identified data %5d (%4.1f%%)  00/FF fill %5d (%4.1f%%)  unclassified %5d (%4.1f%%)  labels %d"
          % (mod, c, 100.0 * c / size, d, 100.0 * d / size, fill, 100.0 * fill / size, other, 100.0 * other / size, labels))
