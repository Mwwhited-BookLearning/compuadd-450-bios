#!/usr/bin/env python3
"""
mkxub.py - turn the XTIDE Universal BIOS build output into the 8 KB option-ROM image that goes into the
padding slot (image offset 0x0E000, segment EE00h) of the patched ROM.

    mkxub.py [--in build/xtide/ide_386.bin] [--out build/xtide/xub.bin] [--controllers N]

Steps: verify the option-ROM header and the ROMVARS layout of an XUB 2.1.2 (r638) build, optionally
override ROMVARS.bIdeCnt (normally already 1 from -DIDE_CONTROLLER_COUNT=1 in the source build), pad to the
declared ROM size (8192 bytes) and write the checksum byte so the 8-bit sum is zero - the Phoenix option-ROM
scan checks it.  This replaces the Tools/checksum.pl step of the XTIDE makefile.
ROMVARS in the r638 layout: bIdeCnt at 72, bBootDrv at 73, ideVars0 (1F0h, 3F0h, 16-bit ATA, IRQ 14) at 78.
"""
import argparse
import os
import struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="build/xtide/ide_386.bin")
    ap.add_argument("--out", default="build/xtide/xub.bin")
    ap.add_argument("--controllers", type=int, default=None, help="override ROMVARS.bIdeCnt (default: keep the built value)")
    a = ap.parse_args()
    d = bytearray(open(a.inp, "rb").read())
    assert d[0:2] == b"\x55\xAA", "not an option ROM"
    assert d[6:12] == b"XUB212", "not an XTIDE Universal BIOS 2.1.2 image"
    base, ctrl, dev, irq = struct.unpack_from("<HHBB", d, 78)
    assert (base, ctrl, irq) == (0x1F0, 0x3F0, 14), "unexpected ROMVARS layout: ideVars0 = %03X/%03X irq %d" % (base, ctrl, irq)
    size = d[2] * 512
    assert len(d) <= size, "image larger than its declared ROM size"
    if a.controllers is not None:
        d[72] = a.controllers
    print("input %s: %d bytes, ROM size %d, version %s, controllers %d, boot drive %02Xh"
          % (a.inp, len(d), size, d[0x2C:0x3D].split(b"\0")[0].decode("ascii", "replace"), d[72], d[73]))
    d += b"\x00" * (size - len(d))
    d[-1] = 0
    d[-1] = (-sum(d)) & 0xFF
    assert sum(d) & 0xFF == 0
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "wb").write(d)
    print("written %s (%d bytes, checksum byte %02Xh)" % (a.out, len(d), d[-1]))


if __name__ == "__main__":
    main()
