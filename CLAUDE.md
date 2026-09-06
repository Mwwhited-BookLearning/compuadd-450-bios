# CLAUDE.md - working rules for the Compuadd 486 BIOS project

This folder is a complete reverse-engineering and rebuild project for the 128 KB BIOS of a Compuadd 486
"Color Scan 450" notebook. Read `CONTEXT.md` first for the state of the work and the decisions already
made; this file is about *how* to work here. Do not re-derive anything that `CONTEXT.md`, the docs or the
label files already record.

## Ground rules

- **This is a public free-software repository about a proprietary ROM.** Never commit the ROM dump, the
  split module binaries, `disasm/*.asm`, `src/*.asm` or `patched/variants/**` (all reproduce the firmware
  bytes) or anything from `drv/` (third-party datasheets, disk images). `.gitignore` covers them; if a new
  generated file reproduces ROM bytes, add it there too. Quoting strings and short excerpts in the docs is
  fine. Own work is MIT (`LICENSE`), the XTIDE source is GPL v2.

- The label databases are the source of truth: `labels/sys.json`, `labels/vga.json`, `labels/miser.json`
  (code: names, comments, data ranges, tables) and `labels/vars.json` (RAM variables and structures).
  Never hand-edit anything under `disasm/`, `src/`, `patched/variants/` or `docs/generated/`; those are
  generated. Change the JSON, regenerate, verify, commit.
- Every regeneration of `src/` must end with `bash tools/build.sh` printing `IDENTICAL`, and every change
  to the patched variants must end with `bash tools/build_patched.sh` reproducing the expected hashes
  (see `CONTEXT.md`) plus the two emulator tests passing. If it does not, the change is wrong, not the check.
- Commit and push as work lands, with descriptive messages. The owner asked to be kept informed of
  results, not asked for permission at each step ("just keep decoding... you don't need to stop to let me
  know until it's done"). Report faithfully: state what was verified and how, and say plainly what has
  not run on the real machine (nothing patched has, as of the date in `CONTEXT.md`).
- Maximum detail is wanted. Name every routine and every variable; a `loc_`/`sub_`/`tbl_` placeholder or a
  bare `[0x472]` is a gap, not a finished state.
- Keep documentation in sync in the same commit: `README.md` (index, coverage table, build options),
  `docs/01..11`, and the PlantUML/Salt diagrams (`tools/check_plantuml.py FILE...` renders them through the
  PlantUML server; run it after editing a diagram).

## Environment

- Windows host, tools run in **WSL** with the venv `~/.venv-bios/bin/python` (capstone + unicorn);
  `bash tools/setup-wsl.sh` creates it. There is no Python on the Windows side and Git Bash has no
  `python3`, so run everything through `wsl -e bash -c '...'`. Wrap long steps in `timeout`.
- NASM 2.16.03: the Windows build lives in `build/nasm/nasm-2.16.03/nasm.exe` (git-ignored; download it
  again after a fresh clone, or put a Linux `nasm` on the PATH). The scripts find it in `$NASM`, the PATH
  or `build/nasm/*/nasm.exe`. A Windows `nasm.exe` run from WSL needs relative output paths (the build
  scripts already do this).
- Never inline Python in a `wsl -e bash -c '...'` heredoc: any apostrophe in the code breaks the quoting.
  Write helper scripts to `build/tmp/` (git-ignored) with the Write tool and run them.
- `build/`, `drv/`, the ROM dump and the ROM-derived generated files are git-ignored. `drv/` holds downloaded reference material (chipset, video, MISER,
  Compuadd/Chaplet docs, the XTIDE release binaries and source zips). After a move without those folders,
  the XTIDE release binary `drv/xtide/ide_386.bin` is only needed for the optional comparison in
  `patched/xtide/CHANGES.txt`; the build uses the source in `patched/xtide/src`.

## Regeneration pipeline (run from this folder, inside WSL)

```
bash tools/run.sh                                  # split image -> disasm/*.asm, *-functions.md, docs/generated/*  (~1 min)
~/.venv-bios/bin/python tools/mkasm.py --module sys   --nasm build/nasm/nasm-2.16.03/nasm.exe   # src/sys.asm   (~5 min)
~/.venv-bios/bin/python tools/mkasm.py --module miser --nasm build/nasm/nasm-2.16.03/nasm.exe   # src/miser.asm
~/.venv-bios/bin/python tools/mkasm.py --module vga   --nasm build/nasm/nasm-2.16.03/nasm.exe   # src/vga.asm
bash tools/build.sh                                # must print IDENTICAL
bash tools/build_patched.sh                        # both variants -> build/patched/<variant>/rom.bin
~/.venv-bios/bin/python tools/test_xtide_apply.py  # must print ALL OK
~/.venv-bios/bin/python tools/emu_setup.py build/patched/xtide-setup/rom.bin space pgdn pgdn down right esc f4
```

`tools/mkpatched.py` derives the variant sources from `src/` with asserted text substitutions; when a
regenerated `src/` changes the text of a patched line, the assertion fails and the pattern in
`mkpatched.py` must be widened (the patterns already accept numeric or symbolic operands).

## Conventions in the label files

- `labels/*.json`: `labels` (offset -> name/comment), `entries`, `data` (ranges never decoded, with a
  comment), `strings`, `tables` (`near_ptr`/`far_ptr`/`struct`/`word`/`byte`, `stride`, `items`, `func`),
  `linear`, `linkreg`, `inline_string_calls`, `selectors`. Offsets are hex strings within the module.
- `labels/vars.json`: `regions` keyed by linear address range (`ivt`, `bda`, `miser_ram`, `smram`, ...),
  `structs` with fields, `struct_use` (which base register in which code range or function uses which
  struct), `assume` (per-module fallback segment by displacement range). Names print as `region.name`;
  a trailing `?` in a listing means the segment was assumed. In `src/` only proven references are
  symbolic; the rest keep numeric operands with the name in the comment.
- Label comments are written for a reader of the listing: what the routine does, which ports/CMOS/chipset
  registers it touches, who calls it. Use the established vocabulary (see `docs/06`).
- Pitfalls already hit: `0F 24/26` byte patterns are ordinary `and` instructions except inside the TLB
  test (`C4F4-C600`, `E740-E760`); struct-embedded pointer tables mark only the pointer words as data;
  in MISER, small constants collide with label addresses (private-RAM offsets), so never relocate
  non-`cs:` displacements there; system-BIOS immediates with a zero low byte (`0x9100`, `0xB000`) are
  constants even when a label exists at that address.

## Patched images and safety

- The Phoenix/C&T code is the owner's copy for this one machine; the XTIDE Universal BIOS source in
  `patched/xtide/src` is GPL v2 with the local change listed in `patched/xtide/CHANGES.txt`. Keep that
  notice current if the source is touched again.
- Nothing patched has been flashed. Any statement about the patched images must say they were verified
  under the Unicorn emulator only. The owner has a spare ROM chip for the first test.
- Fixed addresses that must never move (IBM compatibility, cross-module calls, anti-tamper check) are
  listed in `CONTEXT.md`; the copyright block `F000:E020-E2C2` and byte `E840` must not change at all.
