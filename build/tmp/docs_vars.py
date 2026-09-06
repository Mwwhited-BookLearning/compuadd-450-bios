def rw(p, fn):
    s = open(p, encoding="utf-8").read(); t = fn(s); assert t != s, p
    open(p, "w", encoding="utf-8", newline="\n").write(t)

def d05(s):
    s = s.replace("`+4` next-value handler (`+`, Right), `+6` draw handler, `+8` alternate handler, `+A` common (`setup_field_common`), `+C` previous-value handler (`-`, Left), `+E` Enter/edit handler, `+10` CMOS-read handler, `+12` CMOS-write handler,",
                  "`+4` next-value handler (`+`, Right), `+6` load handler (CMOS shadow -> value array, falling back to the default when the value is out of range), `+8` alternate key handler, `+A` common (`setup_field_common`), `+C` previous-value handler (`-`, Left), `+E` Enter/edit handler, `+10` store handler (value array -> CMOS shadow), `+12` post-store handler (extended checksum update),")
    s = s.replace("The generic\nhandlers are `setup_list_field_edit` / `setup_list_field_draw` / `list_field_prev_value` /\n`list_field_write_cmos` for option lists,",
                  "The generic\nhandlers are `list_field_next_value` / `list_field_load_from_cmos` / `list_field_prev_value` /\n`list_field_write_cmos` / `setup_ext_checksum_to_shadow` for option lists,")
    s = s.replace("**Work area.** `setup_main` (`1934`) needs 4 KB of RAM for its frame.",
                  "**Work area.** `setup_main` (`1934`) needs 4 KB of RAM for its frame. In the listings and sources the\nframe fields appear as `setup_frame.<name>` and the record fields as `setup_field_rec.<name>` (defined in\n`labels/vars.json`, reference in [generated/variables.md](generated/variables.md#structures)).")
    return s
rw("docs/05-setup-utility.md", d05)

def d06(s):
    s = s.replace("| `misertext.py` |", "| `varsmap.py` | RAM variable reference `docs/generated/variables.md`: every region/structure of `labels/vars.json` with the functions that access each variable (from `romdis.py --varxrefs`) and the touched-but-unnamed offsets |\n| `misertext.py` |", 1)
    s = s.replace("### Label file format\n", """### RAM variables (`labels/vars.json`)

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
""", 1)
    return s
rw("docs/06-method-and-tools.md", d06)

def rd(s):
    s = s.replace("[PhoenixMISER text and screens](docs/generated/miser-text.md) |",
                  "[PhoenixMISER text and screens](docs/generated/miser-text.md), [RAM variables and structures](docs/generated/variables.md) (BDA, IVT, MISER private RAM, SMRAM, SETUP frame and records, with the functions that touch each) |")
    s = s.replace("Instructions that NASM would encode differently from the original assembler",
                  "Memory operands are symbolic where the segment is proven, `mov word [0x400 + bda.reset_flag], 0x1234`,\n`mov byte [bp + setup_frame.page], 1`, `[miser_ram.std_enabled]`, through `struc` offsets in `src/vars.inc`\ngenerated from `labels/vars.json`; the listings show the same names in the comment column.\n\nInstructions that NASM would encode differently from the original assembler")
    return s
rw("README.md", rd)

def d03(s):
    return s.replace("## Private RAM\n", "## Private RAM\n\nThe complete offset map with the functions touching each variable is generated in\n[generated/variables.md](generated/variables.md#miser_ram-dc000-df800); the listings name these\nlocations `miser_ram.<name>`.\n", 1)
rw("docs/03-phoenixmiser.md", d03)

def d02(s):
    return s.replace("| 40:96/97 (24) |", "| (all) | see [generated/variables.md](generated/variables.md#bda-00400-00500) for every BDA byte with its accessors | |\n| 40:96/97 (24) |", 1)
rw("docs/02-system-bios-runtime.md", d02)
print("docs ok")
