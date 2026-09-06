## I/O ports

| Port | Meaning | in | out | Used by |
|---|---|---|---|---|
| 020h | PIC1 command | 0 | 2 | `call_vga_rom_init_e000`, `sub_535F` |
| 021h | PIC1 data/mask | 7 | 22 | `call_vga_rom_init_e000`, `miser_post_hook`, `sub_0825`, `sub_083D`, `sub_0BE0`, `sub_0CB8` … |
| 024h | chipset config index (word) | 0 | 22 | `chipset_reg_read`, `chipset_reg_write`, `pm_chipset_init`, `resume_a_body`, `sub_213D`, `sub_48B1` … |
| 026h | chipset config data (word) | 12 | 11 | `chipset_reg_read`, `chipset_reg_write`, `pm_chipset_init`, `resume_a_body`, `sub_213D`, `sub_48B1` … |
| 060h | KBC data | 8 | 4 | `sub_0815`, `sub_0A6D`, `sub_0A89`, `sub_0AB1`, `sub_36C3`, `sub_4824` … |
| 061h | port B (speaker/parity/refresh) | 6 | 8 | `resume_a_body`, `sub_0849`, `sub_084F`, `sub_206C`, `sub_55F6`, `sub_55FE` … |
| 064h | KBC command/status | 14 | 9 | `sub_0815`, `sub_0820`, `sub_0A6D`, `sub_0A89`, `sub_0AB1`, `sub_0AD0` … |
| 070h | CMOS index / NMI enable | 0 | 8 | `resume_a_body`, `sub_1FEC`, `sub_1FFE`, `sub_213D`, `sub_5207`, `sub_5581` … |
| 071h | CMOS data | 5 | 2 | `resume_a_body`, `sub_1FEC`, `sub_1FFE`, `sub_5207`, `sub_5581`, `sub_559D` |
| 080h | POST code | 2 | 47 | `apm_00_installation_check`, `apm_01_connect_real_mode`, `apm_02_connect_16bit_pm`, `apm_03_connect_32bit_pm`, `apm_04_disconnect`, `apm_05_cpu_idle` … |
| 081h | DMA page ch2 | 1 | 0 | `resume_a_body` |
| 08Dh | resume magic word (chipset) | 1 | 5 | `miser_post_hook`, `restart_post_resume_a`, `restart_post_resume_b`, `sub_497F` |
| 0A0h | PIC2 command | 1 | 3 | `call_vga_rom_init_e000`, `sub_2A31`, `sub_535F` |
| 0A1h | PIC2 data/mask | 8 | 22 | `call_vga_rom_init_e000`, `miser_post_hook`, `sub_0825`, `sub_083D`, `sub_0BE0`, `sub_0CB8` … |
| 0F0h | FPU busy clear | 0 | 2 | `sub_27A8`, `sub_556C` |
| 1F2h |  | 0 | 3 | `sub_2A31`, `sub_2B59`, `sub_2BFE` |
| 1F6h |  | 0 | 1 | `sub_2A31` |
| 1F7h | IDE status/command | 2 | 3 | `call_vga_rom_init_e000`, `sub_2A31`, `sub_2B59`, `sub_2BFE` |
| 1FFh | platform config byte (from CMOS 3Fh) | 2 | 1 | `apm_0A_get_power_status`, `pm_chipset_init`, `sub_385B` |
| 3C0h | VGA attribute | 0 | 2 | `sub_0DC3`, `sub_0DCE` |
| 3C2h | VGA misc output | 0 | 2 | `sub_0BE0`, `sub_0CB8` |
| 3C4h | VGA sequencer index | 0 | 8 | `sub_0BE0`, `sub_0CB8` |
| 3CCh | VGA misc output read | 2 | 0 | `sub_0BE0`, `sub_0CB8` |
| 3CEh |  | 0 | 6 | `sub_0BE0`, `sub_0CB8`, `sub_20CE`, `sub_210B` |
| 3D4h | CGA/VGA CRTC index | 3 | 3 | `sub_20CE`, `sub_210B` |
| 3D6h | C&T extension index | 0 | 10 | `sub_0BE0`, `sub_0CB8`, `sub_385B`, `sub_3884` |
| 3DAh | CGA/VGA status | 3 | 4 | `sub_0DC3`, `sub_479A`, `sub_47CB` |
| 3E0h |  | 0 | 2 | `pcmcia_card_detect` |
| 3F6h | IDE control / FDC | 1 | 4 | `sub_2A93`, `sub_2AAC`, `sub_5738` |

## CMOS registers

| Index | Meaning | reads | writes | direct 70h/71h | Used by |
|---|---|---|---|---|---|
| 0Ch | status C | 0 | 0 | 1 | `sub_213D` |
| 0Fh | shutdown status | 0 | 0 | 1 | `resume_a_body` |
| 13h |  | 0 | 0 | 3 | `sub_5581`, `sub_559D` |
| 14h | equipment | 0 | 0 | 1 | `sub_5207` |
| 44h |  | 0 | 0 | 2 | `sub_1FEC`, `sub_1FFE` |
