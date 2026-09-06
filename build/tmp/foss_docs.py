import re

def rw(p, fn):
    s = open(p, encoding="utf-8").read(); t = fn(s); assert t != s, p
    open(p, "w", encoding="utf-8", newline="\n").write(t)

GETTING_STARTED = '''## What is in this repository, and what is not

This is a free-software project (MIT, see `LICENSE`) about a proprietary ROM. The repository holds the
analysis, not the firmware:

- **included**: the disassembler and build tools (`tools/`), the label databases that carry every routine
  and variable name (`labels/`), the documentation of the firmware and of the hardware it drives (`docs/`),
  the XTIDE Universal BIOS source used by the patched variants (`patched/xtide/src`, GPL v2), the patch
  generator, and the emulator tests.
- **not included**: the ROM dump itself, the generated listings (`disasm/*.asm`), the byte-exact sources
  (`src/*.asm`) and the patched variant sources (`patched/variants/`). Each of those is the Phoenix and
  C&T firmware in another encoding, so they are regenerated locally from your own dump and ignored by git.
  Third-party datasheets and driver disks are downloaded into `drv/` by `tools/fetch_drv.sh` rather than
  redistributed; `docs/09-references.md` lists every source.

### Getting started with your own ROM dump

1. Dump the 128 KB BIOS ROM of a Compuadd 486 Color Scan 450 (or Chaplet iLuFA 750 / Halikan NBD 486 with
   the same Phoenix A486 1.03 + PhoenixMISER firmware) and save it in this folder as
   `BIOS from Compuadd 486 Color Scan 450.BIN`. The image the labels were made for has SHA-256
   `3c3764e589ae29e3e20700336847ff685e41152e26b3d19d77ec92212c7d00c4`; another revision will still
   disassemble, but labels will be off wherever the code differs.
2. In WSL (or any Linux with Python 3 and NASM): `bash tools/setup-wsl.sh`, put NASM 2.16.03 on the PATH or
   in `build/nasm/`, then follow *Regenerating*, *Rebuilding the ROM from source* and *Building the ROM
   variants* below. `bash tools/build.sh` must print `IDENTICAL`, which proves the labels, sources and
   tools agree with your dump before anything else is trusted.

### Hardware documentation

The teardown produced hardware notes that stand on their own, independent of the BIOS work:
[docs/07-hardware.md](docs/07-hardware.md) (resource map, PicoPower chipset registers as used by the
firmware, trackball interface, docking station, the CompactFlash card),
[docs/09-references.md](docs/09-references.md) (the Chaplet origin of the machine, firmware pedigree, where
every datasheet and driver was found) and
[docs/10-teardown-photos-2026-09-05.md](docs/10-teardown-photos-2026-09-05.md) (boards and chips as
photographed), plus the generated [chipset register cross-reference](docs/generated/chipset-registers.md)
and [I/O-port and CMOS maps](docs/generated/sys-ports-cmos.md).

'''

LICENSING = '''
## Licensing

- Tools, label databases, documentation and build scripts: MIT (`LICENSE`).
- XTIDE Universal BIOS (`patched/xtide/src`): GPL v2, with the one local change recorded in
  `patched/xtide/CHANGES.txt`. A patched ROM image you build contains that GPL code.
- Phoenix system BIOS, PhoenixMISER and the C&T VGA BIOS: not included; you supply your own dump for your
  own machine, and the generated listings and sources stay on your disk.
'''

def rd(s):
    s = s.replace("## What is in the image\n", GETTING_STARTED + "## What is in the image\n", 1)
    s = s.replace("| [disasm/](disasm/) | Generated, labelled listings (`*.asm`) and function inventories (`*-functions.md`) - read-only views with addresses and bytes |",
                  "| [disasm/](disasm/) | Function inventories (`*-functions.md`, in the repo) and the labelled listings (`*.asm`, generated locally from your dump, not in the repo) |")
    s = s.replace("| [src/](src/) | **Re-assemblable NASM source** for the three modules (`tools/mkasm.py`), verified byte-exact: `bash tools/build.sh` rebuilds the identical 128 KB image |",
                  "| [src/](src/) | **Re-assemblable NASM source** for the three modules (`tools/mkasm.py`, generated locally, not in the repo), verified byte-exact: `bash tools/build.sh` rebuilds the identical 128 KB image; `vars.inc` (RAM variable offsets) is tracked |")
    s = s.replace("| [patched/](patched/) | **Patched ROM as assembly**: `variants/xtide/` and `variants/xtide-setup/` (`sys/miser/vga.asm` derived from `src/` by `tools/mkpatched.py`)",
                  "| [patched/](patched/) | **Patched ROM as assembly**: `variants/xtide/` and `variants/xtide-setup/` (`sys/miser/vga.asm` derived from `src/` by `tools/mkpatched.py`, generated locally)")
    s = s.rstrip("\n") + "\n" + LICENSING
    return s
rw("README.md", rd)

def d09(s):
    s = s.replace("Research done 2026-09-04 with web searches; downloaded material is kept in `drv/` (git-ignored,\nre-fetch with `bash tools/fetch_drv.sh`).",
                  "Research done 2026-09-04 with web searches. Downloaded material is third-party and is not part of\nthe repository; `bash tools/fetch_drv.sh` re-creates the local cache in `drv/` (git-ignored) from the\nsources listed at the end of this document.")
    s = s.rstrip("\n") + '''

## Downloaded reference material (not redistributed)

Everything `tools/fetch_drv.sh` fetches into `drv/`, with the original location, so the material can be
found again without this repository carrying copies.

| Folder | File | Source |
|---|---|---|
| `chipset-picopower/` | `PT86C768_Redwood1_2_199404.pdf` (the notebook chipset family datasheet) | [bitsavers](http://www.bitsavers.org/components/picoPower/PT86C768_Redwood1_2_199404.pdf) |
| `chipset-picopower/` | `AN928_Active_Power_Management_Using_SuperIO_1994.pdf` | [bitsavers](http://www.bitsavers.org/components/picoPower/AN928_Active_Power_Management_Using_SuperIO_1994.pdf) |
| `chipset-picopower/` | `PT82C206F-LV_Integrated_Peripheral_Controller.pdf` | [bitsavers](http://www.bitsavers.org/components/picoPower/PT82C206F-LV_Integrated_Peripheral_Controller.pdf) |
| `chipset-picopower/` | `picopower-chipset-list-tlb.doc` (TLB chipset list) | [mpoli.fi](https://files.mpoli.fi/unpacked/software/dos/utils/misc/tlb_v252.zip/chipset.doc) |
| `video-ct65535/` | `CHIPS.TXT`, `VGABIOS.TXT`, `VGAREGS.TXT` (vgadoc) | [NYU mirror](https://cs.nyu.edu/~mwalfish/classes/ut/f09-cs395t/ref/hardware/vgadoc/CHIPS.TXT), [MIT mirror](https://pdos.csail.mit.edu/6.828/2008/readings/hardware/vgadoc/VGABIOS.TXT), [MIT mirror](https://pdos.csail.mit.edu/6.828/2016/readings/hardware/vgadoc/VGAREGS.TXT) |
| `power-phoenixmiser/` | PHDISK 1.7 disk image and archive listing | [archive.org cd-rom_and_phdisk](https://archive.org/details/cd-rom_and_phdisk) |
| `computer-compuadd/` | CompuAdd 386/486 mouse, system-utilities and VGA driver disk images | [archive.org compuadd286386486utilitiesanddrivers](https://archive.org/details/compuadd286386486utilitiesanddrivers) |
| `computer-chaplet/` | Chaplet / iLuFA 750 / Halikan NBD 486 pages, FCC ID GXL | [macdat.net](https://www.macdat.net/laptops/chaplet/ilufa_750.php), [macdat.net](https://www.macdat.net/laptops/chaplet/halikan_nbd486.php), [fccid.io/GXL](https://fccid.io/GXL) |
| `network-um9003af/` | UMC UM9003AF drivers | [vogonsdrivers 838](https://vogonsdrivers.com/getfile.php?fileid=838&menustate=0), [vogonsdrivers 854](https://vogonsdrivers.com/getfile.php?fileid=854&menustate=0), elektroda |
| `mouse-ps2/` | CuteMouse 2.1b4 | [ibiblio](https://www.ibiblio.org/pub/micro/pc-stuff/freedos/files/dos/ctmouse/2.1b4/ctmouse.zip), [cutemouse.sourceforge.net](http://cutemouse.sourceforge.net/) |
| `xtide/` | XTIDE Universal BIOS r638 release binaries (`ide_386.bin` etc.), used only to compare against the source build | [xtideuniversalbios.org/binaries/r638](https://www.xtideuniversalbios.org/binaries/r638/); source: [SVN trunk r638](https://www.xtideuniversalbios.org/svn/xtideuniversalbios/trunk/) (included in `patched/xtide/src` under the GPL) |
'''
    return s
rw("docs/09-references.md", d09)

def d06(s):
    return s.replace("| `fetch_drv.sh` | downloads reference documents and drivers into `drv/` (git-ignored) |",
                     "| `fetch_drv.sh` | downloads the third-party reference documents and drivers listed in [09-references.md](09-references.md#downloaded-reference-material-not-redistributed) into `drv/` (git-ignored; nothing in `drv/` is redistributed) |")
rw("docs/06-method-and-tools.md", d06)

def cl(s):
    s = s.replace("## Ground rules\n", """## Ground rules

- **This is a public free-software repository about a proprietary ROM.** Never commit the ROM dump, the
  split module binaries, `disasm/*.asm`, `src/*.asm` or `patched/variants/**` (all reproduce the firmware
  bytes) or anything from `drv/` (third-party datasheets, disk images). `.gitignore` covers them; if a new
  generated file reproduces ROM bytes, add it there too. Quoting strings and short excerpts in the docs is
  fine. Own work is MIT (`LICENSE`), the XTIDE source is GPL v2.
""", 1)
    s = s.replace("- `build/` and `drv/` are git-ignored. `drv/` holds downloaded reference material",
                  "- `build/`, `drv/`, the ROM dump and the ROM-derived generated files are git-ignored. `drv/` holds downloaded reference material")
    return s
rw("CLAUDE.md", cl)

def cx(s):
    s = s.replace("## 3. Repository layout and tools\n",
                  """## 3. Repository layout and tools

The project is published as free software (MIT for own work, GPL v2 for the XTIDE source). The ROM dump,
the split module binaries in `build/`, `disasm/*.asm`, `src/*.asm` and `patched/variants/**` are
**generated locally from the owner's dump and not committed**; `disasm/*-functions.md`, `src/vars.inc`,
labels, tools and docs are. A fresh clone therefore needs the dump (SHA-256 in section 1) before any
regeneration or build step works; without it only the XTIDE build (`tools/build_xtide.sh`) runs.
""", 1)
    return s
rw("CONTEXT.md", cx)
print("docs ok")
