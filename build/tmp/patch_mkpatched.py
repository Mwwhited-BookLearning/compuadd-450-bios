p = "tools/mkpatched.py"
s = open(p, encoding="utf-8").read()
old = '''    s = sub1(s, re.compile(r"        mov byte \\[bp \\+ 0x25\\], 1 +; 1F50\\n"
                           r"        db 0xE8, 0xCA, 0x06 +; 1F54  call setup_select_page\\n"
                           r"        mov byte \\[bp \\+ 0x2b\\], 0 +; 1F57\\n"
                           r"        mov cx, 6 +; 1F5B\\n"
                           r"        call setup_init_fields_range +; 1F5E\\n"),'''
new = '''    s = sub1(s, re.compile(r"        mov byte \\[bp \\+ (0x25|setup_frame\\.page)\\], 1 +; 1F50[^\\n]*\\n"
                           r"        db 0xE8, 0xCA, 0x06 +; 1F54  call setup_select_page\\n"
                           r"        mov byte \\[bp \\+ (0x2b|setup_frame\\.field_index)\\], 0 +; 1F57[^\\n]*\\n"
                           r"        mov cx, 6 +; 1F5B\\n"
                           r"        call setup_init_fields_range +; 1F5E\\n"),'''
assert old in s, "1F50 pattern"
s = s.replace(old, new)
old2 = '''    s = sub1(s, "        cmp byte [bp + 0x25], 1                  ; 2542\\n        je short loc_257F                        ; 2546\\n",
             "        cmp byte [bp + 0x25], 0                  ; 2542 (patched) Basic page only\\n        jne short loc_257F                       ; 2546 (patched)\\n", "field_prev page test")'''
new2 = '''    s = sub1(s, re.compile(r"        cmp byte \\[bp \\+ (0x25|setup_frame\\.page)\\], 1 +; 2542[^\\n]*\\n        je short loc_257F +; 2546\\n"),
             "        cmp byte [bp + setup_frame.page], 0      ; 2542 (patched) Basic page only\\n        jne short loc_257F                       ; 2546 (patched)\\n", "field_prev page test")'''
assert old2 in s, "2542 pattern"
s = s.replace(old2, new2)
# the variant sources include vars.inc: copy it next to them
old3 = '''        shutil.copyfile("src/vga.asm", os.path.join(d, "vga.asm"))'''
new3 = '''        shutil.copyfile("src/vga.asm", os.path.join(d, "vga.asm"))
        if os.path.exists("src/vars.inc"):
            shutil.copyfile("src/vars.inc", os.path.join(d, "vars.inc"))'''
assert old3 in s, "copy vars.inc"
s = s.replace(old3, new3)
# the generated helper uses the symbolic frame fields too
s = s.replace('''              "        mov byte [bp + 0x25], 1\\n"
              "        call setup_select_page\\n"
              "        mov byte [bp + 0x2b], 0\\n"
              "        mov cx, 6\\n"
              "        call setup_init_fields_range\\n"
              "        mov byte [bp + 0x25], 2\\n"
              "        call setup_select_page\\n"
              "        mov byte [bp + 0x2b], 0\\n"''',
              '''              "        mov byte [bp + setup_frame.page], 1\\n"
              "        call setup_select_page\\n"
              "        mov byte [bp + setup_frame.field_index], 0\\n"
              "        mov cx, 6\\n"
              "        call setup_init_fields_range\\n"
              "        mov byte [bp + setup_frame.page], 2\\n"
              "        call setup_select_page\\n"
              "        mov byte [bp + setup_frame.field_index], 0\\n"''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("mkpatched patched")
