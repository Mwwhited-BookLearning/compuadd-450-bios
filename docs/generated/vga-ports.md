## I/O ports

| Port | Meaning | in | out | Used by |
|---|---|---|---|---|
| 042h | PIT ch2 (speaker) | 2 | 2 | `sub_50D0` |
| 043h | PIT control | 0 | 2 | `sub_50D0` |
| 061h | port B (speaker/parity/refresh) | 2 | 2 | `sub_50D0` |
| 085h |  | 1 | 0 | `sub_24CE` |
| 102h |  | 0 | 1 | `sub_2902` |
| 3B4h | MDA CRTC index | 1 | 1 | `sub_4DD0`, `vga_init_main` |
| 3B8h | MDA mode control | 1 | 4 | `sub_215E`, `sub_224E`, `sub_2A11` |
| 3BFh |  | 0 | 1 | `sub_224E` |
| 3C0h | VGA attribute | 4 | 11 | `sub_13D9`, `sub_31EE`, `sub_3F6F`, `sub_441C`, `sub_4DD0`, `sub_4F68` … |
| 3C2h | VGA misc output | 0 | 6 | `sub_224E`, `sub_2981`, `sub_51C6`, `vga_init_main` |
| 3C3h |  | 0 | 1 | `sub_2902` |
| 3C4h | VGA sequencer index | 5 | 24 | `int10_07_scroll_down`, `int10_0A_write_char`, `int10_1B_functionality_state`, `int10_ext_functions`, `sub_188B`, `sub_28DB` … |
| 3C6h | VGA DAC mask | 3 | 11 | `int10_00_set_mode`, `int10_10_palette_dac`, `sub_0C93`, `sub_28DB`, `sub_4D82`, `sub_4EFC` … |
| 3C7h |  | 2 | 2 | `sub_4D82`, `sub_4EFC`, `sub_527F` |
| 3C8h |  | 1 | 6 | `sub_31EE`, `sub_529C`, `vga_init_main` |
| 3CAh |  | 1 | 1 | `sub_4DD0`, `sub_51C6` |
| 3CCh | VGA misc output read | 5 | 1 | `sub_215E`, `sub_224E`, `sub_4DD0`, `sub_51C6`, `vga_init_main` |
| 3CEh |  | 4 | 62 | `int10_07_scroll_down`, `int10_0A_write_char`, `int10_0C_write_pixel`, `int10_0D_read_pixel`, `sub_0EFC`, `sub_13D9` … |
| 3D4h | CGA/VGA CRTC index | 2 | 1 | `sub_0D6B`, `sub_2BBB` |
| 3D6h | C&T extension index | 4 | 38 | `int10_00_set_mode`, `sub_0C46`, `sub_0E28`, `sub_1302`, `sub_15B9`, `sub_16B3` … |
| 3D8h | CGA mode control | 0 | 1 | `int10_07_scroll_down` |
| 3D9h |  | 0 | 1 | `int10_0B_set_palette` |
| 3DAh | CGA/VGA status | 1 | 1 | `int10_07_scroll_down` |
| 46E8h |  | 0 | 1 | `int10_12_bl20_alt_prtsc` |
| 4AE8h |  | 0 | 1 | `sub_2902` |

## CMOS registers

| Index | Meaning | reads | writes | direct 70h/71h | Used by |
|---|---|---|---|---|---|
