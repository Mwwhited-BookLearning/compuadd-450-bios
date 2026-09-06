#!/usr/bin/env python3
"""
mkpatched.py - derive the patched ROM variants in patched/variants/<name>/ from the byte-exact sources in src/.

    mkpatched.py [--variant xtide|xtide-setup|all]      (run from the bios folder; default: all)

Every patch is a text substitution on src/*.asm (asserted to match exactly), so the changes stay reviewable
in a diff of the two .asm files.  The variants:

  xtide         XTIDE Universal BIOS in the 8 KB slot at EE00h.
                sys.asm   1. post_57_option_rom_c800: the C800h-DFFFh option-ROM scan call becomes a call to
                             post_scan_option_roms_ext, which performs the original scan and then scans
                             EE00h-EFFFh (the stub lives in the FFh fill at the end of the SETUP segment,
                             re-padded to 5800h so nothing else moves).
                miser.asm 2. std_disk_setup no longer forces INT 13h back to the Phoenix driver (F000:E3FE).
                vga.asm      unchanged copy.

  xtide-setup   Everything in `xtide`, plus a third SETUP page "XTIDE Hard Disk Setup" whose fields live in
                CMOS 60h/61h (inside the Phoenix extended checksum range), and a POST step that applies
                those CMOS values to the XTIDE ROMVARS in the shadow-RAM copy of the option ROM before it
                is initialised:
                sys.asm   3. setup_select_page reads three-entry page tables (counts / value arrays /
                             record arrays / descriptors) placed in the free block instead of the two-entry
                             tables at 03CCh.
                          4. PgUp/PgDn wrap at page index 2, "Page x of 3", the init-pages-draw loop runs
                             3 pages, setup_init_page1_fields also initialises page 3.
                          5. setup_field_prev: the page-1 (Basic) special case is keyed on page == 0 instead
                             of page != 1, so page 3 uses the generic path.
                          6. post_scan_option_roms_ext calls xtide_apply_cmos_config between the two scans.
"""
import argparse
import os
import re
import shutil

FILL_RE = re.compile(r"        times 6212 db 0xFF +; 3FBC fill\n")
SCAN_RE = re.compile(r"        mov si, 0xc800 +; 6B46\n        mov cx, 0xe000 +; 6B49\n        call scan_option_roms +; 6B4C\n")
INT13_RE = re.compile(r"        mov word \[bx\], 0xe3fe +; 5654\n        mov word \[bx \+ 2\], 0xf000 +; 5658\n")

# --- XTIDE ROMVARS layout (r638 / "XUB212"; see patched/xtide/src/XTIDE_Universal_BIOS/Inc/RomVars.inc)
ROMVARS_wFlags = 64
ROMVARS_bIdeCnt = 72
ROMVARS_bBootDrv = 73
ROMVARS_bIdleTimeout = 76
ROMVARS_ideVars0 = 78
IDEVARS_drvParamsMaster = 6
IDEVARS_drvParamsSlave = 12
MASTER_FLAGS = ROMVARS_ideVars0 + IDEVARS_drvParamsMaster    # 84: DRVPARAMS.wFlags low byte
SLAVE_FLAGS = ROMVARS_ideVars0 + IDEVARS_drvParamsSlave      # 90

# --- the new SETUP page ------------------------------------------------------------------------------
# (label, CMOS index, mask, shift, default, [values...])  value strings are padded to a common width
XT_FIELDS = [
    ("XTIDE Settings", 0x60, 0x01, 0, 0, ["BIOS Default", "Custom"]),
    ("IDE Controllers", 0x60, 0x02, 1, 0, ["Primary Only", "Both Channels"]),
    ("Default Boot Drive", 0x60, 0x0C, 2, 0, ["Hard Disk 80h", "Hard Disk 81h", "Floppy A:"]),
    ("Block Mode Transfers", 0x60, 0x10, 4, 0, ["Enabled", "Disabled"]),
    ("Drive Write Cache", 0x60, 0x60, 5, 0, ["Disabled", "Drive Default", "Enabled"]),
    ("Master Translation", 0x61, 0x03, 0, 0, ["Auto", "CHS", "LARGE", "LBA"]),
    ("Slave Translation", 0x61, 0x0C, 2, 0, ["Auto", "CHS", "LARGE", "LBA"]),
    ("Drive Standby Timer", 0x61, 0x70, 4, 0, ["Disabled", "1 minute", "5 minutes", "10 minutes", "20 minutes"]),
]
XT_TITLE = "**  XTIDE Hard Disk Setup  **"
XT_HELP = [
    "Applied at the next boot when",
    "XTIDE Settings is 'Custom';",
    "'BIOS Default' = ROM values.",
    "",
    "Both Channels also probes",
    "170h / IRQ 15.",
    "",
    "Set Hard Disk Type on Page 1",
    "to 'Not Installed'.",
    "",
    "Ctrl held during POST skips",
    "XTIDE for one boot.",
]
LABEL_ROW0, LABEL_COL = 7, 4
VALUE_COL = 31
HELP_ROW0, HELP_COL = 7, 47
TITLE_ROW = 5
FRAME_VALUE_ARRAY = 0x100          # frame offset of the page-3 value bytes ([bp+2C] table entry); 0xE5/0xF9 are pages 1/2
ORIG_DESCRIPTORS = ("0x1D, 0x04, 0x27, 0x0A, 0x69, 0x0A, 0x0E, 0x04, 0x06, 0x2C, 0x0B, 0x0E, 0x2A, 0x06, 0x1B, 0x05, "
                    "0x4C, 0x11, 0x8F, 0x11, 0x08, 0x04, 0x07, 0x83, 0x12, 0x00, 0x00, 0x00")


def sub1(s, pattern, repl, what):
    r = pattern if isinstance(pattern, re.Pattern) else re.compile(re.escape(pattern))
    n = len(r.findall(s))
    assert n == 1, "%s: expected exactly one match, found %d" % (what, n)
    return r.sub(repl, s, 1)


def asm_str(text):
    return ", ".join(["0x%02X" % b for b in text.encode("cp437")] + ["0x00"])


def xtide_stub(with_setup):
    """post_scan_option_roms_ext (+ xtide_apply_cmos_config) that replaces the 3FBC fill; re-padded to 5800h."""
    out = [
        "; ---------------------------------------------------------------------------------------------",
        "; (patched) Extended option-ROM scan: the original C800h-DFFFh pass, then EE00h-EFFFh where the",
        "; XTIDE Universal BIOS option ROM is embedded (image offset 0E000h).  scan_option_roms checks the",
        "; 55AAh signature and the 8-bit checksum before far-calling the init entry at +3.",
        "post_scan_option_roms_ext:",
        "        mov si, 0xc800",
        "        mov cx, 0xe000",
        "        call scan_option_roms",
    ]
    if with_setup:
        out.append("        call xtide_apply_cmos_config")
    out += [
        "        mov si, 0xee00",
        "        mov cx, 0xf000",
        "        call scan_option_roms",
        "        ret",
        "",
    ]
    if with_setup:
        out += [
            "; ---------------------------------------------------------------------------------------------",
            "; (patched) Apply the SETUP page-3 values (CMOS 60h/61h) to the XTIDE ROMVARS in the shadow-RAM",
            "; copy of the option ROM at EE00:0000.  POST 53h shadows E0000-EFFFF in 16 KB blocks (chipset reg",
            "; 200h bits 8-11); reg 207h bit 11 write-enables the EC000-EFFFF block while the bytes are patched.",
            "; The option-ROM checksum byte at EE00:1FFF is recomputed so scan_option_roms accepts the image.",
            "; CMOS 60h: bit0 custom, bit1 two controllers, bits2-3 boot drive, bit4 block mode off, bits5-6 write cache",
            "; CMOS 61h: bits0-1 master translation, bits2-3 slave translation, bits4-6 standby timer",
            "xtide_apply_cmos_config:",
            "        pusha",
            "        push ds",
            "        push es",
            "        mov al, 0x60",
            "        call cmos_read",
            "        test al, 1",
            "        jz .done                                ; 'BIOS Default': leave the ROM as built",
            "        mov bl, al",
            "        mov al, 0x61",
            "        call cmos_read",
            "        mov bh, al",
            "        mov ax, 0xee00",
            "        mov es, ax",
            "        cmp word [es:0], 0xaa55",
            "        jne .done",
            "        cmp word [es:6], 'XU'                   ; ROMVARS.rgbSign = 'XUB212'",
            "        jne .done",
            "        cmp word [es:8], 'B2'",
            "        jne .done",
            "        mov dx, 0x24                            ; reg 207h |= 0800h (write enable EC000-EFFFF shadow)",
            "        mov ax, 0x207",
            "        out dx, ax",
            "        out 0xed, al",
            "        mov dx, 0x26",
            "        in ax, dx",
            "        push ax                                 ; original 207h",
            "        or ah, 0x08",
            "        push ax",
            "        mov dx, 0x24",
            "        mov ax, 0x207",
            "        out dx, ax",
            "        out 0xed, al",
            "        pop ax",
            "        mov dx, 0x26",
            "        out dx, ax",
            "        ; --- controllers",
            "        mov al, 1",
            "        test bl, 0x02",
            "        jz .one_ctrl",
            "        inc al",
            ".one_ctrl:",
            "        mov [es:%d], al                          ; ROMVARS.bIdeCnt" % ROMVARS_bIdeCnt,
            "        ; --- boot drive",
            "        mov al, bl",
            "        shr al, 2",
            "        and al, 3",
            "        mov si, xt_boot_drive_tab",
            "        call .lookup",
            "        mov [es:%d], al                          ; ROMVARS.bBootDrv" % ROMVARS_bBootDrv,
            "        ; --- standby timer",
            "        mov al, bh",
            "        shr al, 4",
            "        and al, 7",
            "        mov si, xt_standby_tab",
            "        call .lookup",
            "        mov [es:%d], al                          ; ROMVARS.bIdleTimeout" % ROMVARS_bIdleTimeout,
            "        ; --- master drive flags: bits0-1 write cache, bits2-3 translation, bit4 block mode",
            "        mov al, bh",
            "        and al, 3",
            "        mov si, xt_translate_tab",
            "        call .lookup",
            "        mov cl, al",
            "        call .common_flags",
            "        mov al, [es:%d]" % MASTER_FLAGS,
            "        and al, 0xe0",
            "        or al, cl",
            "        mov [es:%d], al                          ; ideVars0.drvParamsMaster.wFlags (low byte)" % MASTER_FLAGS,
            "        ; --- slave drive flags",
            "        mov al, bh",
            "        shr al, 2",
            "        and al, 3",
            "        mov si, xt_translate_tab",
            "        call .lookup",
            "        mov cl, al",
            "        call .common_flags",
            "        mov al, [es:%d]" % SLAVE_FLAGS,
            "        and al, 0xe0",
            "        or al, cl",
            "        mov [es:%d], al                          ; ideVars0.drvParamsSlave.wFlags (low byte)" % SLAVE_FLAGS,
            "        ; --- option-ROM checksum byte",
            "        xor si, si",
            "        xor al, al",
            "        mov cx, 0x1fff",
            ".sum:",
            "        add al, [es:si]",
            "        inc si",
            "        loop .sum",
            "        neg al",
            "        mov [es:0x1fff], al",
            "        pop ax                                  ; restore reg 207h",
            "        push ax",
            "        mov dx, 0x24",
            "        mov ax, 0x207",
            "        out dx, ax",
            "        out 0xed, al",
            "        pop ax",
            "        mov dx, 0x26",
            "        out dx, ax",
            ".done:",
            "        pop es",
            "        pop ds",
            "        popa",
            "        ret",
            ".lookup:                                        ; AL := [cs:si + AL]",
            "        xor ah, ah",
            "        add si, ax",
            "        mov al, [cs:si]",
            "        ret",
            ".common_flags:                                  ; CL |= translation<<2 | block mode | write cache from BL",
            "        shl cl, 2",
            "        test bl, 0x10",
            "        jnz .no_block",
            "        or cl, 0x10                             ; FLG_DRVPARAMS_BLOCKMODE",
            ".no_block:",
            "        mov al, bl",
            "        shr al, 5",
            "        and al, 3",
            "        mov si, xt_cache_tab",
            "        call .lookup",
            "        or cl, al",
            "        ret",
            "xt_boot_drive_tab:  db 0x80, 0x81, 0x00, 0x80",
            "xt_standby_tab:     db 0, 12, 60, 120, 240, 0, 0, 0      ; ATA standby units of 5 s",
            "xt_translate_tab:   db 3, 0, 1, 2                        ; Auto, CHS(normal), LARGE, assisted LBA",
            "xt_cache_tab:       db 1, 0, 2, 1                        ; DISABLE, DEFAULT, ENABLE, (DISABLE)",
            "",
        ]
        out += setup_page_data()
    out.append("        times (0x5800 - ($ - $$)) db 0xFF     ; re-pad to the start of the core segment")
    out.append("")
    return "\n".join(out)


def setup_page_data():
    """Page tables, descriptor, field records and strings for the third SETUP page."""
    n = len(XT_FIELDS)
    out = [
        "; ---------------------------------------------------------------------------------------------",
        "; (patched) Third SETUP page: XTIDE Hard Disk Setup.  Same record format as pages 1-2 (see docs/05):",
        "; +0 row, +1 col, +2 value strings, +4 next, +6 load-from-CMOS, +8/+E key handlers, +A common,",
        "; +C previous, +10 store-to-CMOS, +12 checksum update, +14 CMOS index, +15 mask, +16 max, +18 shift,",
        "; +19 default, +1A/+1C secondary handlers, +1E type, +1F kind 66h (option list).",
        "xt_page_counts:     db 0x13, 0x05, %d                    ; last field index per page" % (n - 1),
        "xt_page_values:     dw 0x00E5, 0x00F9, 0x%04X            ; value arrays (frame offsets)" % FRAME_VALUE_ARRAY,
        "xt_page_records:    dw 0x014C, 0x1874, xt_rec_0          ; record arrays",
        "xt_page_descriptors:",
        "        db %s ; pages 1-2, copied from 03D6" % ORIG_DESCRIPTORS,
        "        dw 0x%02X%02X, xt_title                       ; title row/col, string" % (TITLE_ROW, (80 - len(XT_TITLE)) // 2),
        "        dw xt_labels",
        "        db %d" % n,
        "        dw 0x%02X%02X                                 ; label block row/col" % (LABEL_ROW0, LABEL_COL),
        "        dw xt_help",
        "        db %d" % len(XT_HELP),
        "        dw 0x%02X%02X                                 ; help block row/col" % (HELP_ROW0, HELP_COL),
    ]
    for i, (label, idx, mask, shift, default, values) in enumerate(XT_FIELDS):
        out += [
            "xt_rec_%d:                                      ; %s" % (i, label),
            "        db %d, %d" % (LABEL_ROW0 + i, VALUE_COL),
            "        dw xt_str_%d" % i,
            "        dw list_field_next_value, list_field_load_from_cmos, setup_key_default, setup_field_common",
            "        dw list_field_prev_value, setup_key_default, list_field_write_cmos, setup_ext_checksum_to_shadow",
            "        db 0x%02X, 0x%02X" % (idx, mask),
            "        dw %d" % (len(values) - 1),
            "        db %d, %d" % (shift, default),
            "        dw setup_nop_handler, setup_nop_handler",
            "        db 0x00, 0x66",
        ]
    out.append("xt_title:   db %s" % asm_str(XT_TITLE))
    out.append("xt_labels:")
    for label, idx, mask, shift, default, values in XT_FIELDS:
        w = max(len(v) for v in values)
        line = label.ljust(VALUE_COL - LABEL_COL - 1) + "[" + " " * w + "]"
        out.append("        db %s" % asm_str(line))
    out.append("xt_help:")
    for h in XT_HELP:
        out.append("        db %s" % asm_str(h))
    for i, (label, idx, mask, shift, default, values) in enumerate(XT_FIELDS):
        w = max(len(v) for v in values)
        out.append("xt_str_%d:" % i)
        for v in values:
            out.append("        db %s" % asm_str(v.ljust(w)))
    out.append("")
    return out


def patch_sys_xtide(s, with_setup):
    s = sub1(s, SCAN_RE,
             "        call post_scan_option_roms_ext        ; 6B46 (patched) C800-DFFF scan + EE00-EFFF scan for XTIDE\n"
             "        times 6 nop                              ; 6B49 (patched) keeps the following code in place\n", "scan call site")
    s = sub1(s, FILL_RE, lambda m: xtide_stub(with_setup), "3FBC fill")
    return s


def patch_sys_setup_page(s):
    # 3. page tables
    for old, new in (("0x3cc", "xt_page_counts"), ("0x3ce", "xt_page_values"), ("0x3d2", "xt_page_records"), ("0x3d6", "xt_page_descriptors")):
        s = sub1(s, re.compile(r"        mov si, %s( +); (26[0-9A-F]{2})\n" % old),
                 lambda m, new=new: "        mov si, %s%s; %s (patched) 3-page table\n" % (new, " " * max(1, 41 - 8 - len(new) - 1), m.group(2)), "setup_select_page " + old)
    # 4. page count constants
    s = sub1(s, "        cmp al, 1                                ; 266D\n", "        cmp al, 2                                ; 266D (patched) last page index\n", "pgdn wrap")
    s = sub1(s, "        mov al, 1                                ; 268A\n", "        mov al, 2                                ; 268A (patched) last page index\n", "pgup wrap")
    s = sub1(s, "        mov al, 1                                ; 2923\n", "        mov al, 2                                ; 2923 (patched) 'Page x of 3'\n", "page number")
    s = sub1(s, "        mov cx, 2                                ; 25F6\n", "        mov cx, 3                                ; 25F6 (patched) draw 3 pages\n", "pages draw loop")
    s = sub1(s, re.compile(r"        mov byte \[bp \+ (0x25|setup_frame\.page)\], 1 +; 1F50[^\n]*\n"
                           r"        db 0xE8, 0xCA, 0x06 +; 1F54  call setup_select_page\n"
                           r"        mov byte \[bp \+ (0x2b|setup_frame\.field_index)\], 0 +; 1F57[^\n]*\n"
                           r"        mov cx, 6 +; 1F5B\n"
                           r"        call setup_init_fields_range +; 1F5E\n"),
             "        call xt_setup_init_pages_2_3             ; 1F50 (patched) init page 2 and page 3 fields\n"
             "        times 14 nop                             ; 1F53 (patched)\n", "setup_init_page1_fields")
    # 5. cursor-up special case keyed on page 0
    s = sub1(s, re.compile(r"        cmp byte \[bp \+ (0x25|setup_frame\.page)\], 1 +; 2542[^\n]*\n        je short loc_257F +; 2546\n"),
             "        cmp byte [bp + setup_frame.page], 0      ; 2542 (patched) Basic page only\n        jne short loc_257F                       ; 2546 (patched)\n", "field_prev page test")
    # the init helper goes right after the apply routine tables: append to the stub block (before the re-pad)
    helper = ("xt_setup_init_pages_2_3:                        ; (patched) replaces the page-2 init at 1F50\n"
              "        mov byte [bp + setup_frame.page], 1\n"
              "        call setup_select_page\n"
              "        mov byte [bp + setup_frame.field_index], 0\n"
              "        mov cx, 6\n"
              "        call setup_init_fields_range\n"
              "        mov byte [bp + setup_frame.page], 2\n"
              "        call setup_select_page\n"
              "        mov byte [bp + setup_frame.field_index], 0\n"
              "        mov cx, %d\n"
              "        call setup_init_fields_range\n"
              "        ret\n\n" % len(XT_FIELDS))
    s = sub1(s, "        times (0x5800 - ($ - $$)) db 0xFF", helper + "        times (0x5800 - ($ - $$)) db 0xFF", "re-pad anchor")
    return s


def patch_miser_xtide(m):
    return sub1(m, INT13_RE, "        times 9 nop                              ; 5654 (patched) keep the current INT 13h handler (XTIDE) instead of forcing F000:E3FE\n",
                "std_disk_setup INT 13h store")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="all", choices=["xtide", "xtide-setup", "all"])
    a = ap.parse_args()
    variants = ["xtide", "xtide-setup"] if a.variant == "all" else [a.variant]
    src_sys = open("src/sys.asm", encoding="utf-8").read()
    src_miser = open("src/miser.asm", encoding="utf-8").read()
    for v in variants:
        d = os.path.join("patched", "variants", v)
        os.makedirs(d, exist_ok=True)
        s = patch_sys_xtide(src_sys, with_setup=(v == "xtide-setup"))
        if v == "xtide-setup":
            s = patch_sys_setup_page(s)
        open(os.path.join(d, "sys.asm"), "w", encoding="utf-8", newline="\n").write(s)
        open(os.path.join(d, "miser.asm"), "w", encoding="utf-8", newline="\n").write(patch_miser_xtide(src_miser))
        shutil.copyfile("src/vga.asm", os.path.join(d, "vga.asm"))
        if os.path.exists("src/vars.inc"):
            shutil.copyfile("src/vars.inc", os.path.join(d, "vars.inc"))
        print("%s: sys.asm, miser.asm, vga.asm written" % d)


if __name__ == "__main__":
    main()
