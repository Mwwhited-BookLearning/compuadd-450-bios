# CONTEXT.md - state of the Compuadd 486 BIOS project (as of 2026-09-06)

Everything needed to continue this work from a fresh clone in a new location. `CLAUDE.md` has the
working rules; this file has the facts, decisions, results and the open list. The docs in `docs/`
hold the full technical detail; this is the map.

## 1. What this is

Reverse engineering and rebuild of the 128 KB BIOS image `BIOS from Compuadd 486 Color Scan 450.BIN`
(SHA-256 `3c3764e589ae29e3e20700336847ff685e41152e26b3d19d77ec92212c7d00c4`) from the owner's Compuadd 486
"Color Scan 450" notebook, a rebadged Chaplet iLuFA 750 (PicoPower chipset, C&T 65535 video, Phoenix
80486 BIOS 1.03 with PhoenixMISER power management). The owner (Matthew Whited) opened the machine and
photographed the boards (`docs/10-teardown-photos-2026-09-05.md`). The ROM is on a 128 KB chip; a spare chip
exists for testing patched images.

Owner's goals, in the order they were stated:
1. Fully disassemble, name and document the ROM with maximum detail. **Done** (every routine and
   variable named, 0 % unclassified in all three modules).
2. Add LBA support so the whole 4 GB CompactFlash card can be used (the Phoenix driver stops at 1 GB).
   **Done as patched variants** using the XTIDE Universal BIOS (see section 4), not yet flashed.
3. A "new BIOS with relocatable call points, optimized", keeping all support, with the XTIDE LBA import,
   a SETUP page for XTIDE if the existing SETUP can be extended (done), a ROM BASIC if room (does not
   fit), and later a Wozmon-style ROM monitor (proposed, accepted in principle). **Relocatable build not
   started beyond design**, see section 6.

## 2. Image layout

| Image offset | Segment | Module | Notes |
|---|---|---|---|
| `00000-07FFF` | `C000` | C&T 65535/A VGA BIOS (32 KB) | option-ROM checksum byte at `7FFF` |
| `08000-0DFFF` | `E800` | PhoenixMISER PT68C268 power management (24 KB) | API table `0000-004B` called at fixed offsets by the system BIOS; 983-byte zero tail `5C29-5FFF` |
| `0E000-0FFFF` | `EE00` | 8 KB zero padding in the original; the XTIDE Universal BIOS in the patched variants | |
| `10000-1FFFF` | `F000` | Phoenix A486 1.03 system BIOS (64 KB) | SETUP `0100-3FBC` (+FF fill to `5800`), core `5800-FFFF` checksummed (byte `FFEF` adjusts it) |

Free space in the original: SETUP-segment fill `3FBC-57FF` (6.2 KB, not checksummed), about 6.3 KB in
eleven core gaps between IBM entry points, MISER tail 983 bytes, VGA 234 bytes. `E05E-E2C2` looks free but
is inside the copyright block that the anti-tamper check sums; never touch `E020-E2C2` or byte `E840`.

Fixed addresses that must keep their offsets (IBM convention, cross-module references, integrity checks):
`F000:0000` banner, `0100` SETUP far entry (MISER calls it), `E020-E2C2` copyright, `E05B` reset entry,
`E2C3` NMI, `E3FE` INT 13h, `E401-E6F0` disk table (MISER writes `E6B1` and `FFEC`), `E6F2` INT 19h,
`E6F5` config table, `E739` INT 14h, `E82E` INT 16h, `E840`, `E987` INT 09h, `EC59` floppy INT 13h,
`EF57` INT 0Eh, `EF5A` (ljmp `E800:002C`), `EFC7` diskette table, `F065` INT 10h, `F0A4` INT 1Dh table,
`F841` INT 12h, `F859` INT 15h, `FA6E` 8x8 font, `FE6E` INT 1Ah, `FEA5` INT 08h, `FEF3`/`FF23` vector
init tables, `FF53` IRET, `FF54` INT 05h, `FFEC-FFEF`, `FFF0` reset vector, `FFF5` date, `FFFE` model;
MISER `E800:0000-004B` API table; VGA `C000:0003` init and `7FFF` checksum. System BIOS -> MISER far calls
go to `E800:0010/0024/0028/002C/0030/0034/0038/0040/0048`.

## 3. Repository layout and tools

The project is published as free software (MIT for own work, GPL v2 for the XTIDE source). The ROM dump,
the split module binaries in `build/`, `disasm/*.asm`, `src/*.asm` and `patched/variants/**` are
**generated locally from the owner's dump and not committed**; `disasm/*-functions.md`, `src/vars.inc`,
labels, tools and docs are. A fresh clone therefore needs the dump (SHA-256 in section 1) before any
regeneration or build step works; without it only the XTIDE build (`tools/build_xtide.sh`) runs.

| Path | Role |
|---|---|
| `labels/sys.json`, `vga.json`, `miser.json` | all code knowledge (names, comments, data ranges, tables) |
| `labels/vars.json` | RAM variables and structures (BDA, IVT, MISER private RAM `DC00`, SMRAM, SETUP frame and field record, MISER device record) |
| `disasm/*.asm`, `disasm/*-functions.md` | generated listings (address, bytes, mnemonic, names in comments) and function inventories |
| `src/{sys,vga,miser}.asm`, `src/vars.inc` | generated NASM sources, **byte-exact** (`bash tools/build.sh` -> IDENTICAL); symbolic memory operands where the segment is proven; instructions NASM would re-encode are `db` with the mnemonic in a comment (13 % sys, 7 % MISER, 17 % VGA) |
| `patched/variants/xtide/`, `patched/variants/xtide-setup/` | derived sources of the two patched variants (`tools/mkpatched.py`) |
| `patched/xtide/src/` | XTIDE Universal BIOS trunk r638 (`XTIDE_Universal_BIOS/`, `Assembly_Library/`, GPL v2), one local change (`-DIDE_CONTROLLER_COUNT`) in `patched/xtide/CHANGES.txt` |
| `docs/01..11` | hand-written docs (POST, runtime, MISER, VGA, SETUP, method/tools, hardware, INT 13h, references, teardown photos, patched ROM) with PlantUML/Salt |
| `docs/generated/` | I/O-port and CMOS maps, chipset register cross-reference, decoded tables, MISER text, RAM variables |
| `tools/romdis.py` | capstone recursive-descent disassembler driven by the label JSON; DS/ES tracking and variable resolution; `--varxrefs` |
| `tools/run.sh` | regenerates listings and all generated docs (portmap, chipsetmap, tables, coverage, misertext, varsmap) |
| `tools/mkasm.py` | listing -> NASM source, verified byte-exact by round-tripping through NASM (db fallback for encodings NASM would change) |
| `tools/build.sh` | assembles `src/`, rebuilds the image, compares SHA-256 |
| `tools/mkpatched.py` | asserted text substitutions `src/` -> `patched/variants/<v>/`; generates the SETUP page 3 data and the CMOS-apply routine |
| `tools/build_xtide.sh`, `tools/mkxub.py` | assemble XTIDE r638 with the makefile's "386" module set and `-DIDE_CONTROLLER_COUNT=1`; pad to 8 KB and write the option-ROM checksum |
| `tools/build_patched.sh [xtide\|xtide-setup\|all]` | full variant build -> `build/patched/<v>/rom.bin` |
| `tools/emu_setup.py ROM [keys]` | runs the real SETUP under Unicorn with emulated INT 10h screen / INT 16h keys / CMOS / chipset ports, prints the screen at each key |
| `tools/test_xtide_apply.py` | Unicorn unit test of the CMOS -> ROMVARS apply routine |
| `tools/coverage.py`, `scan_entries.py`, `portmap.py`, `chipsetmap.py`, `tables.py`, `misertext.py`, `varsmap.py`, `check_plantuml.py`, `setup-wsl.sh`, `split.sh` | analysis and doc generators, environment |

Git-ignored: `build/` (all outputs, NASM, temp scripts in `build/tmp/`), `drv/` (18 MB of downloaded
references: PicoPower/PT86C768 datasheets and the AN928 SuperIO power note, Chaplet/iLuFA pages, CompuAdd
utility disk images, PHDISK 1.7 disk image, C&T 65535 register text files, UM9003 network driver, XTIDE
release binaries r638 and the beta3/master zips). The XTIDE build does not need `drv/`.

## 4. Results so far

**Coverage.** sys 59.3 % code / 20.3 % data / 20.4 % fill / 0 unclassified, 2536 labels; MISER
84.5 / 11.0 / 4.5 / 0, 1270 labels; VGA 55.6 / 42.0 / 2.3 / 0, 1131 labels. No `sub_` placeholders remain;
`loc_` labels print their owning routine. RAM references named: 991 (sys), 528 (MISER), 464 (VGA), about a
third with an assumed segment (`?`).

**Key findings** (details in the docs): Phoenix ROM-stack idiom for stack-less POST; POST checkpoint list;
shadow RAM set up at POST 53h in 16 KB blocks via chipset regs 200h (enable) / 207h (write enable) through
index/data ports 24h/26h; MISER runs SMM (SMBASE 30000h -> 60000h, SMI handler in ROM, RSM trampolines,
pop-up SETUP inside SMM), save-to-disk engine (PHDISK partition type A0h or SAVE2DSK.BIN, CMOS 58h bit 7
doubles as Quick Boot), Fn keys via chipset reg 7, Sound Blaster DSP at 220h, MultiKey KBC commands;
SETUP is table-driven (32-byte field records, generic option-list handlers, CMOS shadow in a 4 KB frame,
extended checksum over CMOS 40h-7Dh); Ctrl+Alt hot keys: Del, S (SETUP), F3 (SETUP), F4 (display toggle),
F8 (power meter), Up/Down (CPU speed); second IDE device possible only as slave on the single 1F0h channel
(IRQ 15 belongs to MISER); C&T extended modes 640x480 / 800x600 / 1024x768, 132-column text.

**Patched variants** (hashes to expect from `bash tools/build_patched.sh`):

| Variant | SHA-256 of `rom.bin` | Change outside the XTIDE slot |
|---|---|---|
| `xtide` | `1be449c5304e1c013b257b50f42a1f968b2423c34fd20c0bd16f6bc45d4819d9` | 28 bytes sys (scan hook at `6B46` + stub at `3FBC`), 9 bytes MISER (`std_disk_setup` no longer forces INT 13h to `F000:E3FE`) |
| `xtide-setup` | `899c3a780ae6e945f711276a2c626586af3560497d17bf9865cf068db890da30` | + third SETUP page (CMOS 60h/61h), page tables relocated to the free block, PgUp/PgDn/"Page x of 3"/init-loop constants, `setup_field_prev` keyed on page 0, `xtide_apply_cmos_config` patches ROMVARS in the `EE00` shadow copy (reg 207h bit 11) before the scan |

The XTIDE part assembled with NASM 2.16.03 differs from the published `ide_386.bin` only in the build
date and 36 reg,reg direction bits. Verified under Unicorn only: `test_xtide_apply.py` ALL OK,
`emu_setup.py` shows the page, wrap-around, value cycling, exit menu, F4 writes `60h/61h` + checksum.
SETUP guidance for the patched images: Hard Disk Type = Not Installed on page 1. Details: `docs/11`.

**Measured but not built.** A relocatable/optimized rebuild would save about 1.3 KB from encodings and
0.5 KB from duplicated fragments; the value is consolidating the gaps into two blocks of ~6 KB and ~7 KB.
Removing the Phoenix hard-disk driver (`7B5E-8598`, 2618 bytes contiguous, plus 424 bytes of autodetect
and 1795 bytes of SETUP fields) is possible once XTIDE is proven on hardware; the INT 13h entry must keep
routing floppies to `EC59`, and MISER's call into the standby routine at `8503` must be checked first.
Microsoft ROM BASIC is 32 KB and cannot fit; a 2-4 KB Tiny BASIC or the monitor can.

## 5. Decisions already made (do not reopen)

- Byte-exact sources stay strict: only proven segment references become symbolic operands; NASM
  re-encodings stay as `db`. Optimization belongs to the separate relocatable build.
- XTIDE is embedded as an option ROM in the slot and initialised by extending the option-ROM scan, not by
  rewriting the Phoenix driver. The Phoenix INT 13h stays for floppies and as the chain target.
- XTIDE settings live in CMOS 60h/61h (inside the extended checksum) and are applied to the shadow copy
  at POST; all-zero CMOS = XTIDE built-in defaults. `IDE_CONTROLLER_COUNT=1` in the ROM build.
- Variant sources are generated from `src/` by text substitution so the diff against `src/` is the patch.
- The ROM monitor (Wozmon-style: examine/deposit memory, ports, CMOS, chipset registers, run, INT 18h
  entry, POST hot key, far entry) is the preferred "extra" over a Tiny BASIC; both are pending.
- Docs numbering: `docs/10` is the owner's teardown-photos note; the patched-ROM doc is `docs/11`.

## 6. Open work, in the intended order

1. **Flash test** of `xtide-setup` (owner, spare chip). Watch: XTIDE detects the CF card and boots,
   Ctrl+Alt+S shows page 3, F4 saves and the next boot applies the values, save-to-disk still works.
2. **Relocatable/optimized build** (`tools/mkreloc.py`, design surveyed in detail): label-ize address
   immediates and pointer tables; anchor the fixed addresses of section 2 with elastic `times`; optimize
   only the system-BIOS core `5800-FFFF` (SETUP segment, MISER and VGA stay at original encodings because
   small constants collide with their label addresses); strict pass must reproduce the original bytes,
   optimized pass verified instruction by instruction with relocated operands mapped, plus an audit of
   unrelocated constants equal to moved addresses; recompute `FFEF` (sys core sum) and `7FFF` (VGA).
   Relocation rules found: exact label match -> relocate except low-byte-00 code labels; `cs:` displacements
   always; non-`cs:` direct displacements only on label match in the core; IVT-slot stores of instruction
   addresses need new labels; MISER never for non-`cs:` displacements.
3. **Apply the XTIDE hook and SETUP page to the relocatable build** so the final image is relocatable,
   optimized and LBA-capable; optionally the `xtide-lean` variant without the Phoenix hard-disk driver.
4. **ROM monitor** in the free block (about 2 KB), then a Tiny BASIC on INT 18h if wanted.
5. Naming polish: remaining `?` (assumed-segment) references, the generic `state_*`/`std_*` names in
   `miser_ram`, and the two "touched but unnamed" entries in `docs/generated/variables.md`.

## 7. How to resume

1. Clone, run `bash tools/setup-wsl.sh` in WSL, put NASM 2.16.03 in `build/nasm/` (or on the PATH).
2. `bash tools/build.sh` -> IDENTICAL; `bash tools/build_patched.sh` -> the two hashes above; run the two
   emulator tests. If all pass, the environment is right.
3. Pick up section 6. For any label work: edit JSON -> `bash tools/run.sh` -> `mkasm.py` for the touched
   modules -> `build.sh` -> `build_patched.sh` + tests -> docs -> commit.
