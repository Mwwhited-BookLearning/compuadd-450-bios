import json, re

# ---------------- vars.json: better names from the code contexts
p = "labels/vars.json"
d = json.load(open(p))
mr = d["regions"]["miser_ram"]["vars"]
def setv(off, name, size=1, comment=None):
    v = {"name": name, "size": size}
    if comment: v["comment"] = comment
    mr[off] = v
setv("0010", "saved_int09_vector", 4, "original IVT entries saved by save_hooked_vectors (activity hooks chain to these)")
setv("0014", "saved_int10_vector", 4)
setv("0018", "saved_int15_vector", 4)
setv("001C", "saved_int16_vector", 4)
setv("0040", "api_word_40", 2)
mr.pop("0046", None)
setv("0044", "api_byte_44", 1); setv("0045", "api_byte_45", 1); setv("0046", "state_byte_46", 1)
setv("0112", "pm_init_flag", 1, "set by miser_post_hook")
setv("0113", "video_index_regs_save", 5, "video_index_regs_snapshot / restore")
setv("0118", "suspend_saved_ss", 2, "SS:SP of the caller saved by enter_suspend, restored on resume/abort")
setv("011A", "suspend_saved_sp", 2)
setv("011C", "suspend_entry_byte", 1)
setv("011D", "suspend_saved_bx", 2)
setv("011F", "suspend_saved_eax", 4)
setv("0125", "suspend_saved_bl", 1); setv("0126", "suspend_saved_ah", 1)
setv("0127", "standby_state", 1, "standby_enter / suspend_abort_restore")
setv("028A", "standby_28A", 2)
setv("0C09", "std_state_C09", 1, "save-to-disk progress byte (std_save_to_disk)")
setv("1425", "std_stack_save", 4, "SS:SP saved before the private save-to-disk stack (lss sp)")
setv("1457", "pic_probe_byte", 1); setv("1458", "pic_probe_done", 1, "1 once std_detect_pic_vector_bases has run")
setv("145C", "pic_probe_145C", 1); setv("145D", "pic_probe_145D", 1)
setv("150C", "std_saved_150C", 1); setv("150D", "std_saved_150D", 1)
d["regions"]["smram"]["vars"]["01F0"] = {"name": "smm_template_eip_slot_rel", "size": 2, "comment": "+1F0h inside the 512-byte state template (91F0h = EIP slot), addressed as [si+1F0h]"}
sf = d["structs"]["setup_frame"]["fields"]
sf["24"] = {"name": "saved_video_page", "size": 1, "comment": "video page active when SETUP started (INT 10h 0Fh BH)"}
json.dump(d, open(p, "w"), indent=1)
print("vars.json updated")

# ---------------- sys.json: label fixes in the SETUP engine
p = "labels/sys.json"
s = open(p, encoding="utf-8").read()
ren = {"setup_list_field_edit": "list_field_load_from_cmos",
       "setup_list_field_draw": "list_field_next_value",
       "setup_cmos_read_field": "setup_ext_checksum_to_shadow"}
for a, b in ren.items():
    n = len(re.findall(r"\b%s\b" % a, s))
    s = re.sub(r"\b%s\b" % a, b, s)
    print("renamed %s -> %s (%d)" % (a, b, n))
open(p, "w", encoding="utf-8", newline="\n").write(s)

# ---------------- tables.py: record column headers by the verified handler roles
p = "tools/tables.py"
s = open(p, encoding="utf-8").read()
old = "| Page | # | Row | Col | Value strings | Next | Draw | Prev | Enter | CMOS read | CMOS write | CMOS index | Mask | Max | Shift | Default | Type | Kind |"
new = "| Page | # | Row | Col | Value strings | Next (+4) | Load (+6) | Prev (+C) | Enter (+E) | Store (+10) | Post-store (+12) | CMOS index | Mask | Max | Shift | Default | Type | Kind |"
assert old in s; s = s.replace(old, new)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("tables.py header updated")

# ---------------- mkpatched.py: the record handler names
p = "tools/mkpatched.py"
s = open(p, encoding="utf-8").read()
old = '"        dw setup_list_field_draw, setup_list_field_edit, setup_key_default, setup_field_common",'
new = '"        dw list_field_next_value, list_field_load_from_cmos, setup_key_default, setup_field_common",'
assert old in s; s = s.replace(old, new)
old = '"        dw list_field_prev_value, setup_key_default, list_field_write_cmos, setup_cmos_read_field",'
new = '"        dw list_field_prev_value, setup_key_default, list_field_write_cmos, setup_ext_checksum_to_shadow",'
assert old in s; s = s.replace(old, new)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("mkpatched updated")
