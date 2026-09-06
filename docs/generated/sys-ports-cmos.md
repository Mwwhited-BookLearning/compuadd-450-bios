## I/O ports

| Port | Meaning | in | out | Used by |
|---|---|---|---|---|
| 00Ah | DMA1 mask | 0 | 1 | `sub_A02F` |
| 00Bh | DMA1 mode | 0 | 2 | `post_05_dma_test`, `sub_A02F` |
| 00Ch | DMA1 clear flip-flop | 0 | 2 | `sub_A02F` |
| 00Dh | DMA1 master clear | 0 | 1 | `post_05_dma_test` |
| 020h | PIC1 command | 1 | 22 | `init_pics_and_fpu`, `int1A_00_get_ticks`, `int70_rtc_irq`, `int74_irq12_mouse`, `int75_fpu_error`, `int_default_handler` … |
| 021h | PIC1 data/mask | 8 | 11 | `post_25_init_ivt`, `post_34_timer_tick_test`, `post_35_shutdown_test`, `post_38_memory_test`, `scan_option_roms`, `sub_AA57` … |
| 024h | chipset config index (word) | 0 | 32 | `chipset_cfg_200_update`, `chipset_speed_table_program`, `post_03_chipset_init`, `post_50_chipset_table`, `post_53_platform_init`, `post_cold_entry` … |
| 026h | chipset config data (word) | 12 | 20 | `chipset_cfg_200_update`, `chipset_speed_table_program`, `post_03_chipset_init`, `post_50_chipset_table`, `post_53_platform_init`, `post_cold_entry` … |
| 040h | PIT ch0 | 8 | 2 | `boot_call_bootsector_a`, `pit_ch0_init_mode2` |
| 041h | PIT ch1 (refresh) | 0 | 2 | `wait_refresh_cycles` |
| 042h | PIT ch2 (speaker) | 4 | 6 | `beep_code_and_halt`, `beep_delay_pit2`, `beep_lo`, `sub_2363` |
| 043h | PIT control | 4 | 20 | `beep_code_and_halt`, `beep_delay_pit2`, `beep_lo`, `boot_call_bootsector_a`, `pit_ch0_init_mode2`, `post_04_timer_init` … |
| 060h | KBC data | 30 | 20 | `ebda_setup`, `int15_89_enter_pmode`, `int74_irq12_mouse`, `kbd_special_dispatch`, `keyboard_lock_check`, `memtest_run_blocks` … |
| 061h | port B (speaker/parity/refresh) | 19 | 21 | `beep_code_and_halt`, `beep_lo`, `int15_87_move_block_prelude`, `parity_check_port61`, `post_08_refresh_test`, `post_09_memory_prepare` … |
| 064h | KBC command/status | 32 | 42 | `ebda_setup`, `int15_89_enter_pmode`, `int15_C2_05_init`, `int74_irq12_mouse`, `kbd_normal_key`, `kbd_special_dispatch` … |
| 070h | CMOS index / NMI enable | 1 | 39 | `cmos_read`, `cmos_write`, `platform_cfg_from_cmos_3F`, `post_02_cmos_shutdown_byte_test`, `post_3A_timer2_test`, `post_53_platform_init` … |
| 071h | CMOS data | 21 | 10 | `platform_cfg_from_cmos_3F`, `post_02_cmos_shutdown_byte_test`, `post_3A_timer2_test`, `post_53_platform_init`, `post_cold_entry`, `post_kbc_sysflag_cmos_b3` … |
| 080h | POST code | 3 | 56 | `a20_enable_and_enter_pmode`, `int15_87_move_block_prelude`, `pmode_unexpected_int`, `post_01_cpu_reg_test`, `post_02_cmos_shutdown_byte_test`, `post_03_chipset_init` … |
| 081h | DMA page ch2 | 0 | 1 | `sub_A02F` |
| 08Dh | resume magic word (chipset) | 1 | 2 | `ret_58E7` |
| 08Fh | DMA page refresh | 0 | 2 | `post_52_a20_and_pmode_memsize`, `ret_5AB7` |
| 0A0h | PIC2 command | 3 | 15 | `init_pics_and_fpu`, `int70_rtc_irq`, `int71_irq9_redirect`, `int74_irq12_mouse`, `int75_fpu_error`, `int_default_handler` … |
| 0A1h | PIC2 data/mask | 7 | 7 | `fpu_detect`, `int15_83_event_wait`, `int15_86_wait`, `int15_C2_05_init`, `int1A_05_set_rtc_date`, `sub_675E` |
| 0D0h | DMA2 status/command | 0 | 1 | `post_05_dma_test` |
| 0D4h | DMA2 mask | 0 | 1 | `post_05_dma_test` |
| 0D6h | DMA2 mode | 0 | 1 | `post_05_dma_test` |
| 0DAh | DMA2 master clear | 0 | 1 | `post_05_dma_test` |
| 0EDh | I/O delay (dummy write) | 0 | 235 | `beep_code_and_halt`, `beep_delay_pit2`, `beep_lo`, `chipset_cfg_200_update`, `chipset_speed_table_program`, `cmos_read` … |
| 0F0h | FPU busy clear | 0 | 1 | `int75_fpu_error` |
| 0F1h | FPU reset | 0 | 1 | `init_pics_and_fpu` |
| 1F1h |  | 0 | 3 | `sub_9CE9` |
| 1F7h | IDE status/command | 1 | 1 | `probe_hd_controller` |
| 1FFh | platform config byte (from CMOS 3Fh) | 0 | 2 | `platform_cfg_from_cmos_3F`, `post_53_platform_init` |
| 201h | game port | 1 | 0 | `int15_84_joystick` |
| 26Eh | Super I/O index | 1 | 4 | `superio_init_26E`, `superio_read_reg`, `superio_write_reg` |
| 388h |  | 0 | 1 | `fm_synth_all_notes_off` |
| 3B8h | MDA mode control | 0 | 3 | `post_rtc_init`, `video_ram_test_and_mode` |
| 3C0h | VGA attribute | 0 | 1 | `post_2C_video_init` |
| 3D4h | CGA/VGA CRTC index | 0 | 5 | `int10_00_set_mode` |
| 3D6h | C&T extension index | 0 | 1 | `int15_5F_platform_video` |
| 3D7h |  | 0 | 1 | `int15_5F_platform_video` |
| 3DAh | CGA/VGA status | 2 | 0 | `post_2C_video_init` |
| 3F2h | FDC digital output | 0 | 3 | `int1A_00_get_ticks`, `sub_9F3C`, `sub_9F68` |
| 3F4h | FDC status | 2 | 0 | `sub_A19F`, `sub_AC0C` |
| 3F5h | FDC data | 1 | 1 | `sub_A1E0`, `sub_A253` |
| 3F6h | IDE control / FDC | 0 | 3 | `floppy_hd_reset_detect`, `probe_hd_controller`, `sub_9CE9` |
| 3F7h | FDC digital input | 1 | 1 | `sub_A2B7`, `sub_AAB8` |

## CMOS registers

| Index | Meaning | reads | writes | direct 70h/71h | Used by |
|---|---|---|---|---|---|
| 00h | RTC seconds | 0 | 0 | 4 | `post_cold_entry`, `setup_gdt_idt_low_ram`, `shutdown_07_memtest_fail`, `sub_D1E7` |
| 0Ah | status A | 2 | 1 | 1 | `post_3B_rtc_test`, `post_rtc_init`, `sub_D140`, `sub_D15D` |
| 0Bh | status B | 17 | 7 | 1 | `int15_83_event_wait`, `int15_86_wait`, `int1A_01_set_ticks`, `int1A_02_get_rtc_time`, `int1A_03_set_rtc_time`, `int1A_04_get_rtc_date` … |
| 0Ch | status C | 5 | 0 | 1 | `int70_rtc_irq`, `post_3B_rtc_test`, `post_rtc_init`, `sub_D140` |
| 0Dh | status D (battery) | 1 | 0 | 1 | `post_28_cmos_checksum`, `post_rtc_init` |
| 0Eh | diagnostic status | 15 | 6 | 1 | `boot_jump_to_sector`, `cmos_hd_type_check`, `int15_5F_platform_video`, `platform_cfg_from_cmos_3F`, `post_28_cmos_checksum`, `post_29_video_config` … |
| 0Fh | shutdown status | 0 | 2 | 7 | `pmode_exit_via_reset`, `post_02_cmos_shutdown_byte_test`, `post_35_shutdown_test`, `post_cold_entry`, `post_prepare_boot`, `shutdown_09_blockmove_return` |
| 10h | floppy types | 2 | 0 | 0 | `superio_configure_from_cmos`, `wait_f1_f2_key` |
| 11h |  | 0 | 0 | 1 | `sub_C499` |
| 12h | hard disk types | 1 | 0 | 0 | `cmos_hd_type_check` |
| 14h | equipment | 1 | 0 | 0 | `post_29_video_config` |
| 15h | base mem lo | 2 | 0 | 0 | `post_56_cmos_memsize_check`, `size_extended_memory` |
| 16h | base mem hi | 2 | 0 | 0 | `post_56_cmos_memsize_check`, `size_extended_memory` |
| 17h | ext mem lo | 1 | 0 | 0 | `post_56_cmos_memsize_check` |
| 18h | ext mem hi | 1 | 0 | 0 | `post_56_cmos_memsize_check` |
| 1Ah | HD1 ext type | 0 | 0 | 2 | `sub_9CBC`, `sub_9CCF` |
| 1Fh | Phoenix: options | 11 | 0 | 0 | `boot_fail_message`, `keyboard_lock_check`, `post_29_video_config`, `post_2C_video_init`, `post_2E_option_rom_c000`, `post_38_memory_test` … |
| 30h | ext mem found lo | 4 | 2 | 0 | `int15_88_ext_mem_size`, `memtest_with_display`, `post_56_cmos_memsize_check`, `size_extended_memory` |
| 31h | ext mem found hi | 4 | 2 | 0 | `int15_88_ext_mem_size`, `memtest_with_display`, `post_56_cmos_memsize_check`, `size_extended_memory` |
| 32h | century | 1 | 5 | 2 | `int1A_03_set_rtc_time`, `int1A_04_get_rtc_date`, `int1A_05_set_rtc_date`, `sub_3B0F`, `sub_3B1E` |
| 33h | info flags (bit7 128K, bit4 FPU?) | 2 | 3 | 4 | `post_3A_timer2_test`, `post_55_cmos_33_check`, `post_kbc_sysflag_cmos_b3`, `shutdown_06_memtest_pass`, `shutdown_09_blockmove_return`, `size_extended_memory` |
| 34h | Phoenix: CPU speed / POST flags | 4 | 0 | 6 | `apply_cpu_speed_from_cmos`, `post_53_platform_init`, `post_56_cmos_memsize_check`, `post_57_call_miser`, `post_rtc_init`, `ret_5AB7` … |
| 3Fh | platform config -> port 1FFh | 0 | 0 | 3 | `platform_cfg_from_cmos_3F`, `post_53_platform_init` |
| 4Bh |  | 0 | 7 | 0 | `int1A_02_get_rtc_time`, `int1A_04_get_rtc_date`, `int1A_dispatch` |
| 58h | Phoenix: suspend flags | 0 | 0 | 2 | `post_rtc_init`, `ret_5DAD` |
| 59h | Phoenix: pointer/mouse flags | 2 | 0 | 0 | `sub_675E`, `superio_configure_from_cmos` |
| 5Eh |  | 2 | 0 | 0 | `int15_5F_platform_video`, `sub_CCFC` |
