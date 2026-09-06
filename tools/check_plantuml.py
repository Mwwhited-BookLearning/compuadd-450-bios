#!/usr/bin/env python3
"""
check_plantuml.py - syntax-check every ```plantuml block in the given markdown files by
rendering it through the public PlantUML server (needs network). Prints one line per block.

    check_plantuml.py README.md docs/*.md
"""
import re
import sys
import zlib
import urllib.request

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def encode(text):
    data = zlib.compress(text.encode("utf-8"), 9)[2:-4]   # raw deflate
    out = []
    for i in range(0, len(data), 3):
        b = data[i:i + 3] + b"\0" * (3 - len(data[i:i + 3]))
        n = (b[0] << 16) | (b[1] << 8) | b[2]
        out.append(ALPHABET[(n >> 18) & 63] + ALPHABET[(n >> 12) & 63] + ALPHABET[(n >> 6) & 63] + ALPHABET[n & 63])
    return "".join(out)


def blocks(path):
    text = open(path, encoding="utf-8").read()
    for m in re.finditer(r"```plantuml\n(.*?)```", text, re.S):
        line = text[:m.start()].count("\n") + 1
        yield line, m.group(1)


def main():
    bad = 0
    for path in sys.argv[1:]:
        for line, src in blocks(path):
            url = "https://www.plantuml.com/plantuml/svg/" + encode(src)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) check_plantuml"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8", "replace")
                    status = r.status
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                status = e.code
            err = "Syntax Error" in body or status >= 400
            m = re.search(r"Syntax Error\?.*?(?=<)|line (\d+)", body)
            print("%s:%d  %s  (%d bytes, HTTP %d)%s" % (path, line, "ERROR" if err else "ok", len(body), status,
                                                        "  " + m.group(0) if (err and m) else ""))
            bad += err
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
