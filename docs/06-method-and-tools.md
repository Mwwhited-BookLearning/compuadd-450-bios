# Method and tools

Everything was done statically on the ROM image; no hardware was available. The approach:

1. **Identify the pieces.** `strings` on the image gives the vendor banners; `55 AA` headers and
   the reset vector fix the module boundaries. The system BIOS far-calls `E000:0003` and
   `E800:00xx`, which fixes where the video ROM and the MISER module execute.
2. **Recursive descent from known entry points.** The reset vector, the classic IBM entry
   addresses (`E05B`, `E6F2`, `EC59`, `F065`, …), option-ROM `+3` entries and the MISER API
   table are the roots. Every `call`/`jmp` target found becomes a label.
3. **Teach the disassembler the Phoenix idioms** that break plain recursive descent (below).
4. **Resolve indirect control flow by hand.** For every `jmp cs:[bx+table]` the tool reports the
   table address and the bound check it saw; the table is then declared in the label file with a
   count and item names, which adds its targets to the analysis.
5. **Read the code and name things.** Names, comments and data ranges go into `labels/*.json`;
   nothing is edited in the generated listings.
6. **Document as you go**: the docs in this folder reference labels by name, so a rename in the
   label file is visible everywhere after `tools/run.sh`.

## Tools (all in `tools/`)

| Script | Purpose |
|---|---|
| `setup-wsl.sh` | one-time: creates `~/.venv-bios` in WSL Ubuntu and installs `capstone` (the Windows side had no Python; Ubuntu's Python is PEP-668 locked so a venv is bootstrapped with `get-pip.py`) |
| `split.sh IMAGE OUTDIR` | cuts the image into `vga.bin`, `miser.bin`, `pad.bin`, `sys.bin` and prints 8-bit sums and SHA-1s |
| `romdis.py` | the disassembler (capstone, 16-bit mode). Input: a module binary, its segment and a label file. Output: the labelled listing and a function inventory with POST codes and analysis notes |
| `run.sh` | regenerates everything: split, then `romdis.py` for the three modules |
| `outline.py LISTING LABEL` | prints the straight-line path from a label (calls, jumps, POST codes, ROM-stack calls) to sketch a flow without reading every instruction |
| `range.sh LISTING START END` | prints the listing between two offsets, keeping the label lines |
| `portmap.py LISTING` | I/O-port and CMOS-index usage tables (`docs/generated/*.md`) |
| `func.sh LISTING LABEL` | prints one labelled routine |
| `coverage.py` | classifies every byte of each module as code / identified data / 00h-FFh fill / unclassified (the README table) |
| `scan_entries.py LISTING BIN SEG` | proposes entry points inside undecoded runs (previous byte `ret`/`iret`/`nop`, plausible prologue); candidates are reviewed and added to the label file |
| `check_plantuml.py DOC...` | renders every PlantUML block through the public server to catch syntax errors |
| `fetch_drv.sh` | downloads the third-party reference documents and drivers listed in [09-references.md](09-references.md#downloaded-reference-material-not-redistributed) into `drv/` (git-ignored; nothing in `drv/` is redistributed) |
| `chipsetmap.py` | cross-reference of every chipset register access (index port 24h) plus the static init tables -> `docs/generated/chipset-registers.md` |
| `tables.py` | decodes the fixed-disk, diskette, SETUP-record and VGA mode-parameter tables -> `docs/generated/tables.md` |
| `varsmap.py` | RAM variable reference `docs/generated/variables.md`: every region/structure of `labels/vars.json` with the functions that access each variable (from `romdis.py --varxrefs`) and the touched-but-unnamed offsets |
| `misertext.py` | decodes all PhoenixMISER text, screen rows, box records and error messages -> `docs/generated/miser-text.md` |
| `mkasm.py --module M --nasm PATH` | emits `src/M.asm`, re-assemblable NASM source verified byte-exact against the ROM (instructions NASM would re-encode are kept as `db`) |
| `build.sh` | assembles `src/*.asm` and rebuilds the 128 KB image in `build/rebuilt/rom.bin`, comparing its SHA-256 with the original |
| `mkpatched.py [--variant xtide\|xtide-setup\|all]` | derives `patched/variants/<variant>/{sys,miser,vga}.asm` from `src/` by asserted text substitutions: extended option-ROM scan stub (EE00h-EFFFh), MISER save-to-disk keeping the live INT 13h, and for `xtide-setup` the third SETUP page (tables, records, strings, CMOS-to-ROMVARS apply routine) |
| `build_xtide.sh` | assembles the XTIDE Universal BIOS r638 source in `patched/xtide/src` (makefile "386" module set, `-DIDE_CONTROLLER_COUNT=1`) -> `build/xtide/ide_386.bin` |
| `mkxub.py` | pads the assembled XTIDE image to its declared 8 KB and writes the option-ROM checksum byte -> `build/xtide/xub.bin` |
| `build_patched.sh [xtide\|xtide-setup\|all]` | runs mkpatched and build_xtide, assembles each variant, concatenates VGA / MISER / XTIDE / system BIOS into `build/patched/<variant>/rom.bin` and prints the byte-difference summary (see [11-patched-rom.md](11-patched-rom.md)) |
| `emu_setup.py ROM [keys]` | runs the SETUP utility from a built image under the Unicorn CPU emulator with an emulated INT 10h screen, scripted INT 16h keys, CMOS and chipset ports; prints the screen at every key request (how the third page was tested) |
| `test_xtide_apply.py` | Unicorn unit test of `xtide_apply_cmos_config` in the `xtide-setup` image: ROMVARS bytes, checksum, chipset write-enable sequence, register preservation |

### RAM variables (`labels/vars.json`)

Memory operands are resolved to named RAM variables. `romdis.py` tracks DS and ES through each function
(immediate loads, `push cs / pop ds`, constant segment words read from ROM, values agreed by every caller,
including callers that dispatch through the declared pointer tables), turns `seg:off` into a linear
address and looks it up in the **regions** of `vars.json`: `ivt` (0000:0000, vectors named automatically),
`bda` (0040:0000, IBM layout plus the Phoenix bytes), `miser_ram` (DC00:0000), `miser_stack`, `smram`,
`popup_scratch`, `boot_sector`. **Structures** apply to base-register operands where `struct_use` says so:
`setup_frame` for `[bp+n]` inside the SETUP segment, `setup_field_rec` for `[bx+n]` in functions that call
`setup_field_record`, `miser_device_rec` for `[si+n]` in the record accessors. When the segment cannot be
proven, per-module `assume` rules pick the likely one and the name is printed with a trailing `?`.

In the listings the name goes into the comment column (`; bda.reset_flag`). In the NASM sources the operand
itself is symbolic, `mov word [0x400 + bda.reset_flag], 0x1234` or `[bp + setup_frame.page]`, through
`struc` definitions in the generated `src/vars.inc`; the expressions evaluate to the original displacement,
so the rebuild stays byte-exact (assumed segments keep the numeric operand and only get the comment).

### Label file format

```json
{
  "entries":  ["E05B"],                                  // extra roots (hex offsets)
  "labels":   {"E05B": {"name": "post_entry", "comment": "..."}},
  "data":     [["E401", "E6F1", "fixed disk parameter table"]],   // never decoded
  "strings":  [["E020", "E053"]],                        // emitted as text
  "tables":   [{"at": "FEF3", "count": 24, "kind": "near_ptr", "name": "ivt_init_08_1F",
                "func": true, "items": ["int08_timer_irq", "..."]}],
  "linear":   [],                                        // force-decode ranges
  "linkreg":  [],                                        // ranges where `mov di,ret ; jmp sub` is trusted
  "inline_string_calls": ["D309"],                       // call followed by a NUL-terminated message
  "selectors": ["0008", "0010", "0020", "0038", "0040"]  // pmode selectors aliasing this segment
}
```

Table kinds: `near_ptr` (word offsets, optional `stride (for pointer tables embedded in a struct table only the pointer words are marked as data)`, `items` names the targets), `far_ptr`
(only same-segment targets are followed), `word` / `byte` / `struct` (data only).

### Idioms the disassembler understands

| Idiom | Recognition | Effect |
|---|---|---|
| ROM stack, near | `mov sp, imm` … `jmp sub` in a block that loaded `SS` from `cs:[FFF3]` or from `CS` | the word at `imm` is a return address: labelled `ret_XXXX`, added as a root; `tbl_XXXX` marks the word |
| ROM stack, far | `mov sp, imm` … `ljmp seg:off` outside the module | the dword at `imm` is a far return address; followed when its segment is this module |
| return through register | `mov di, imm` … `jmp di` inside one block | `imm` is added as a jump target |
| inline message | `call print_inline_msg` | the NUL-terminated text after the call is marked as a string and decoding resumes after it |
| protected-mode aliases | `ljmp 0038:XXXX`, `lcall 0010:XXXX` | selectors listed in the label file are treated as this segment |
| jump tables | `jmp cs:[bx+disp]` / `jmp cs:[di+disp]` | reported in the analysis notes with the last `cmp reg, imm` seen; declared by hand |
| POST codes | `mov al, imm ; out 80h, al` | collected into the function inventory |
| RAM stack detection | `mov ss, reg` where `reg` was not loaded from `CS` | switches off the ROM-stack idiom for that block, so `mov sp, 0080` on a real stack is not misread |

Two heuristics were tried and removed: treating `mov bp/di/si, imm` before any `jmp` as a
link-register call (this BIOS never uses it, and it mis-labelled message pointers), and
treating printable runs as strings when deciding whether a target is code (Phoenix code is full
of `push ax/bx/cx/dx` = `PSQR` sequences that look like text).

## Known gaps

- Every routine in the three modules now carries a name; the labels are still best guesses and
  the comments say so where the evidence is thin. Bytes that remain unclassified are below 0.5 %
  per module (mostly one-off constants).
- The chipset register meanings (ports `24h/26h`, PicoPower PT86C268) are inferred from usage
  only; the register notes in [07](07-hardware.md) and [03](03-phoenixmiser.md) are not from a
  datasheet.
- The 486 test-register instructions (`mov tr3..tr7`) inside `cpu_tlb_test` and the 32-bit APM
  entry thunk `apm_pm32_entry_thunk` are shown as data bytes because the 16-bit capstone decoder
  cannot represent them; their meaning is in the label comments.
- ROM checksum: the VGA module sums to zero on its own; the MISER + padding + system BIOS
  regions do not sum to zero individually, so the system-BIOS checksum test covers a range
  (`rom_checksum_params` at `ACD3`) that was not worked out.
- The video BIOS INT 10h 12h BL=89h/9Ah/92h calls made by PhoenixMISER are no-ops in this
  C&T ROM (left over from another video BIOS).
