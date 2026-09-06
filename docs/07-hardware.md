# Hardware the BIOS expects

What the code touches, matched against the real machine: a Compuadd 450 ColorScan notebook
(486, STN colour LCD, trackball, PS/2 keyboard port, serial and parallel ports, audio in/out)
with a "Mini-Dock" port replicator carrying an NE2000-compatible Ethernet interface and SCSI.

Confidence: **confirmed** = the ROM programs the device; **inferred** = strings or indirect
evidence; **absent** = nothing in the ROM refers to it.

## Resource map

| Device | I/O ports | IRQ | DMA | Where the BIOS uses it | Confidence |
|---|---|---|---|---|---|
| CPU 486 (DX/SX/DX2/DX4, Cyrix variants recognised) | – | – | – | `print_cpu_type` names via INT 15h C9h; CR0.ET from CMOS 33h; speed switching via chipset reg 300h (`set_cpu_speed`, POST B0-B3) | confirmed |
| FPU (486DX internal or 387) | F0h (busy clear), F1h (reset) | 13 | – | `fpu_detect`, `int75_fpu_error` | confirmed |
| Notebook chipset (Phoenix/PicoPower, `PT68C268`) | 24h/26h word index/data; 8Dh resume magic; 1FFh config byte; SMI generation (reg 6 bit 12 software SMI, SMRAM window via regs 1/2 bits 103h, SMBASE 60000h); reg 1 bits 4-7 = SMI event code, reg 7 bits 8-10 = Fn hot-key code (brightness/contrast/volume) | 15 (PM event, masked/unmasked around MISER init) | – | ~50 register writes in POST, MISER private RAM window (regs 200h/207h bit 7), CPU speed (300h), DRAM banks, resume status (reg 1 bit 8) | confirmed; IRQ15 role is inferred |
| DRAM (1-64 MB sized in protected mode) | – | – | – | `pmode_dram_sizing`, `size_extended_memory`; refresh via PIT ch1 / port 61h bit 4 | confirmed |
| 8237 DMA ×2 | 00h-0Fh, C0h-DEh, page regs 81h-8Fh | – | ch2 floppy; ch4 cascade | POST 05h/06h tests; `floppy_dma_setup` programs ch2 (modes 42h/46h/4Ah, page 81h) for diskette transfers. No other DMA user. | confirmed |
| 8259 PIC ×2 | 20h/21h, A0h/A1h | 2 cascade, 9 → INT 0Ah | – | `init_pics_and_fpu` (ICW2 08h/70h), POST 22h/23h, EOI in every IRQ handler | confirmed |
| 8254 PIT | 40h-43h | 0 | – | ch0 18.2 Hz tick (`pit_ch0_init_mode2`), ch1 refresh (count 12h), ch2 speaker/beeps | confirmed |
| Keyboard controller (8042 class) | 60h, 64h | 1 (keyboard), 12 (aux) | – | POST 27h self test, command byte 65h/7Ch, A20 via output port (D1h), input port bit 5 = manufacturing jumper, `kbd_special_dispatch`, `int09_kbd_irq`. MISER's `KeyboardPMSR` uses Phoenix MultiKey extensions: `A1h` version, `CAh` mode, `B8h-BDh` extended RAM, `D5h-D8h` version/config, `CBh` low-power | confirmed |
| Internal trackball (KBC auxiliary device) | 60h/64h | 12 | – | KBC A7h/A8h/A9h/D4h, `int74_irq12_mouse`, INT 15h C2h services (EBDA state); CMOS 59h bit 5 → equipment word bit 2; SETUP `TrackBall` | confirmed |
| External PS/2 keyboard (also the dock "KYB" DIN) | 60h/64h | 1 | – | keyboard channel of the KBC; keyboard-only, a mouse there is ignored | confirmed |
| RTC / CMOS (MC146818 class, 128 bytes) | 70h/71h | 8 | – | POST 3Bh, INT 1Ah, `int70_rtc_irq`, Phoenix bytes 1Fh/33h/34h/3Fh/58h/59h; MISER re-points INT 70h while suspended to fix the clock on wake-up | confirmed |
| Speaker | 61h bits 0-1, PIT ch2 | – | – | beeps, POST beep codes, memory-test click | confirmed |
| Super I/O (National/SMC class) | 26Eh/26Fh index/data | – | – | `superio_init_26E`, `superio_configure_from_cmos` from CMOS 10h/59h; MISER rewrites registers 02h-04h on resume (`pcmcia_resume_versaport`) | confirmed |
| COM1 / COM2 (Super I/O UARTs) | 3F8h-3FFh, 2F8h-2FFh | 4, 3 | – | `serial_port_init`, `detect_equipment`, INT 14h; also probes 3E8h/2E8h (COM3/4, e.g. an internal modem or dock serial) | confirmed |
| LPT (Super I/O, "PRINTER" on dock; VersaPort) | 3BCh, 378h, 278h (+ `rom_option_extra_lpt`) | 7 (not used by BIOS) | – | `parallel_port_detect`, INT 17h; VersaPort mode (standard / bidirectional / EPP 1.7 / 1.9 / external floppy) set through the Super I/O | confirmed |
| Floppy (internal, or external on VersaPort) | 3F0h-3F7h (3F2h DOR, 3F4h/3F5h FIFO, 3F7h DIR) | 6 | 2 | INT 13h floppy driver at A10B.., `diskette_param_table`, `floppy_detect_drives`, 40:3E-41/8B/90/91; chipset regs 81h/82h shadow the DOR/CCR writes (MISER saves/restores them) | confirmed |
| IDE hard disk (one channel, up to two drives) | 1F0h-1F7h, 3F6h | 14 | – (PIO only) | `hd_init`, `int13_hd_handler`, IDENTIFY DEVICE for auto-detect; see [08](08-int13-hard-disk.md) | confirmed |
| C&T 65535/A video, STN colour panel, CRT out (dock "CRT") | 3B4h-3BAh, 3C0h-3CFh, 3D4h-3DAh, 3D6h/3D7h (C&T extensions), 46E8h/102h (VGA enable), 4AE8h | – (IRQ2/9 vertical retrace not used) | – | whole VGA ROM; system BIOS `int15_5F_platform_video`; SETUP `Display Device`, `MaxContrast/SmartMap`, `Normal/Reverse` | confirmed |
| FM synthesiser (OPL2/AdLib compatible) | 388h/389h | – | – | `fm_synth_all_notes_off` at POST (registers B0h-B8h := 0). The PCM side is the DSP in the next row | confirmed for FM |
| Sound Blaster-compatible DSP (PCM audio, SPEAKER/LINE jacks) | 220h-22Fh: 226h reset, 22Ah read data, 22Ch write command / write-status | not visible (SB default 5 or 7) | not visible (SB default 1) | MISER `sb_dsp_reset` (reset, waits for `AAh`, POST F1h-F4h) and `sb_dsp_speaker_off` (`D3h` + vendor command `FDh`; `EFh` in the reset path) around suspend. Vendor commands point at an ESS/Crystal-class SB clone | confirmed at 220h |
| PCMCIA controller (Intel 82365SL compatible), 2 sockets | 3E0h/3E1h index/data (socket A index 00h-3Fh, socket B 40h-7Fh) | – (card IRQs steered by Card Services) | – | MISER `pcmcia_card_detect` reads Interface Status of both sockets before suspend | confirmed |
| Game port | 201h | – | – | INT 15h 84h joystick service, one probe in `detect_equipment` – generic Phoenix code, no evidence of a physical port | inferred (probably absent) |
| Panel control / status port 1FFh | 1FFh | – | – | **write**: LCD brightness (bits 3-7) and contrast (bits 0-2), kept in CMOS 3Fh, written by `platform_cfg_from_cmos_3F` / `post_53_platform_init` and changed by the Fn keys through MISER's SMI handler `pm_evt_fn_hotkey`; **read by MISER as the battery gauge**: `show_power_meter` uses bits 1-5 (0-31), `apm_0A_get_power_status` computes battery life % = ((value & 3Fh) x 80) / 51 | confirmed |
| Battery / AC sensing | chipset regs 1, 12h, 0, 9 via 24h/26h; gauge on 1FFh | 15 (best guess) | – | AC present = reg 1 bit 3; battery installed = reg 12h bit 0 clear; battery low/critical = reg 0 bits 12-13 debounced with reg 9 bit 8 (`apm_0B_get_pm_event`); POWER METER overlay (`show_power_meter`) | confirmed (register meanings inferred from use) |
| Docking station NE2000 (UMC UM9003AF, DIP-switch configured) | typically 300h-31Fh (switch selectable) | typically 3/5/10/11 (switch) | – | **absent**: no access to 300h-33Fh, no dock detection | absent |
| Docking station SCSI (50-pin external) | unknown (adapter dependent) | unknown | unknown | **absent**: no SCSI code in the ROM; an option ROM on the adapter would be found by `scan_option_roms` in C800h-DFFFh – but note MISER's pop-up SETUP uses hidden RAM at C800:0000-4FFF as scratch, so an option ROM there may conflict | absent |

IRQ summary from the ROM's point of view: 0 timer, 1 keyboard, 2 cascade, 3 COM2, 4 COM1, 6
floppy, 8 RTC, 9 redirected to INT 0Ah, 12 trackball, 13 FPU, 14 IDE, 15 masked/unmasked by
MISER (power-management event, best guess). **Free for add-in cards: 5, 7 (LPT unused), 10, 11**;
IRQ 9 works too if nothing else redirects it. DMA channels 1, 3, 5, 6, 7 are unused.

## PicoPower chipset registers (inferred)

Every access to the 16-bit registers behind index port `24h` / data port `26h` is listed in
[docs/generated/chipset-registers.md](generated/chipset-registers.md). What the code does with
them gives these working meanings (best guesses, no datasheet):

| Register | Observed use |
|---|---|
| `0000` | power-management timer / status: written `0788h` to restart the PM timer (`pm_timer_reload`), bits 12-13 = battery low / critical, bit 13 tested before suspend; `&= 88h` while the speaker beeps |
| `0001` | power/speed/event control: bit 3 = AC adapter present, bit 8 = resume flag, bits 4-7 = SMI event code (read by `pm_state_run`, acknowledged with `0Fh`; `smm_setup` also sets them), low byte `F7h`/`FFh` written constantly; values `20F7h` (slow), `77F7h` (standby), `9FF7h`/`7FF7h` (full speed) |
| `0002` | bank/refresh control: bits `103h` open the SMRAM window with reg `1`; `&= ~13FFh` around sleep; bits 0-9 cleared and polled by `chipset_reg2_field_clear_wait` |
| `0003` | disk/peripheral power: bit 1 pulsed around IDE timer commands, `2EC0h` written on resume, bit 0 |
| `0006` | SMI/event control: bit 12 = software SMI trigger, bit 14 (`4000h`) set while an event is handled, bit 7 = sleep clock, `4FFFh` before RSM reset, `4383h`/`0303h` in the card-present states |
| `0007` | event source: bits 8-10 = Fn hot-key code (`pm_evt_fn_hotkey`), bits 3-4 set and bit 5 cleared before the save-to-disk power-off |
| `0009`-`000C` | four device timers / enables: bit 8 toggled together (`chipset_regs9_C_bit8_set`), bit 7 cleared on standby; reg 9 bit 8 also read as the battery-low debounce |
| `000D` | four 3-bit timeout fields: bits 1-3 LCD Dim, 4-6 Suspend, 7-9 System Sleep, 10-12 (fixed 7) - written by `pm_chipset_regs_from_config`; `0800h` / `0` while a PCMCIA card blocks sleeping |
| `000E` | APM/interrupt gating: `3E18h` during an APM call, `3E10h` after; bit 8 (`chipset_reg0E_bit8`); bit 11 set before power-off |
| `0010` | `0`/`1` written when entering/leaving sleep states (clock gate, best guess); polled until stable by `chipset_reg10_wait_stable` |
| `0011` | `0100h` (standby) / `0200h` (system sleep) state code |
| `0012` | status: bit 0 = no battery installed, bit 5 cleared/set around IRQ re-enable |
| `0013` | cleared by `smm_setup` |
| `0040` | bit 12 = software-SMI pending, cleared by the SETUP-return SMI handler |
| `0081`, `0082` | shadow copies of the diskette DOR (`3F2h`) and CCR (`3F7h`) writes |
| `0086` | low byte saved/restored around SMM entry (chipset state byte) |
| `0100`-`0102` | memory configuration (`0100` read at PM init; `0101`/`0102` saved by save-to-disk) |
| `0103` | bit 0 = 1 hides SMRAM (normal RAM visible at 6000:xxxx), 0 exposes it |
| `0200`, `0207` | memory-window control: bit 7 opens the hidden RAM at `DC00`/`DF00`, bit 12 = F000 shadow enable (`shadow_enable_from_ram`), bits 2-3 shadow write enable for the pop-up, `0C8Fh`/`1FFFh` = everything writable, `1300h`/`1F80h` re-shadow patterns |
| `0201`-`0206` | shadow copies of the DMA page registers and, for `0203`-`0206`, the DRAM bank sizes (bit 8 = bank present, bits 0-5 size code, bits 6-7 multiplier - `std_memory_size`) |
| `0300` | CPU clock speed (values `00h/01h/02h` from ROM options `AF5D-AF5F`, `set_cpu_speed`; MISER writes `01E7h`/`01DDh` at init) |
| `0304`-`0307` | saved by save-to-disk (bank timing, not decoded) |

## Interrupt vectors installed by the ROM

| INT | Owner | Notes |
|---|---|---|
| 02h, 05h, 08h-1Fh, 70h-77h | system BIOS | tables `ivt_init_08_1F`, `ivt_init_70_77` |
| 10h, 1Fh, 43h, 6Dh, 42h | VGA ROM | 10h/6Dh = `int10_handler`, 42h = saved system INT 10h, 1Fh/43h fonts |
| 13h, 40h, 41h, 46h, 76h | `hd_init` | 13h hard disk, 40h floppy (old 13h), 41h/46h parameter tables, 76h IRQ14 |
| 15h AH=53h | MISER (via system BIOS) | APM |
| INT 08h/09h/13h/15h chained | MISER | `chain_prev_vector_058E`, `chain_prev_vector_ss10` – hooks for activity monitoring (keyboard, disk, timer) that drive the sleep timers |

## Software the hardware needs on the DOS side

| Device | Firmware support | DOS / Windows software needed |
|---|---|---|
| Power management | APM 1.x via INT 15h 53h; INT 15h 90h/91h device-busy hooks; hot key and POWER METER inside MISER | DOS `POWER.EXE` (MS-DOS 6, APM client) or the Compuadd/Phoenix `POWER` driver; Windows 3.1 `POWER.DRV`; the save-to-disk partition is created with `PHDISK.EXE` (named in the MISER error text) |
| Trackball / external mouse | INT 15h C2h pointing-device services (all 8 subfunctions, state in the EBDA), IRQ12 handler | a PS/2 mouse driver (`MOUSE.COM`/`MOUSE.SYS` 8.x or later, or Logitech `MOUSE.EXE`) – see the trackball section below |
| Video | full INT 10h VGA plus C&T 5Fh functions; INT 15h 5Fh platform hooks | DOS: none; Windows 3.1: the Chips & Technologies 65535 display driver set (`CHIPS.DRV` family) uses the 5Fh functions for panel/CRT switching |
| Keyboard | full INT 09h/16h with enhanced-keyboard (101/102) detection; Ctrl+Alt+Up/Down switch the CPU speed (`hotkey_cpu_speed_*`, ROM options AF56-AF58) | none |
| A20 gate | INT 15h AH=24h (`int15_24_a20_gate_service`) plus the KBC output port | HIMEM.SYS uses the INT 15h 24h interface automatically |
| Serial / parallel | INT 14h / INT 17h; Super I/O configured from SETUP | none for BIOS use; Windows uses `COMM.DRV`; EPP 1.7/1.9 mode is set in SETUP (VersaPort) |
| Floppy | INT 13h with 360K/1.2M/720K/1.44M/2.88M types; external drive via VersaPort | none |
| Hard disk | INT 13h CHS only, 47 types + auto-detect; no LBA, no INT 13h extensions | none for ≤ 528 MB; larger disks/CF cards need a disk manager overlay (`Ontrack DDO`, `EZ-Drive`) or the planned LBA BIOS patch |
| PCMCIA | card-detect only (MISER); no Card/Socket Services in ROM | a Card & Socket Services stack for 82365-compatible controllers (SystemSoft CardSoft, Phoenix PCM+, or the free `PCMCIA` drivers), plus per-card enablers |
| FM audio | silenced at POST only | game/application AdLib support directly on 388h |
| PCM audio (Sound Blaster-compatible DSP at 220h) | reset and muted by MISER around suspend (`sb_dsp_reset`, `sb_dsp_speaker_off`) | Sound Blaster settings (`SET BLASTER=A220 I? D? T?`) – IRQ and DMA come from the vendor's docs/driver, the BIOS never programs them; Windows 3.1 needs the vendor's SB-compatible driver |
| Dock NE2000 (UM9003AF) | none | UMC packet driver / NDIS driver from `um9003af.zip`; configure I/O and IRQ to match the DIP switches (avoid 3F8h/2F8h/3E8h/2E8h and IRQ 3/4/12/14; IRQ 5, 10, 11 are free) |
| Dock SCSI | none | adapter option ROM (INT 13h) for booting, or an ASPI manager + `ASPIDISK.SYS` under DOS |

Things the BIOS does **not** know about: PCI, Plug and Play, an on-board modem, a second IDE
channel, the sound card's mixer, or any network boot.

## Trackball: how the BIOS exposes it and what a driver must do

The trackball is a PS/2-protocol device on the keyboard controller's auxiliary channel. The ROM
implements the standard IBM PS/2 pointing-device interface, so a plain PS/2 mouse driver is the
right software; there is no Compuadd-specific protocol.

What POST does (`post_keyboard_test`, `67CE-6845`):

1. `A9h` (test aux port) – a non-zero result prints `Pointer device failure`.
2. `D4h FFh` (reset the aux device) and reads the acknowledge and BAT bytes; the device ID byte
   read back must be 0.
3. **Reads CMOS 59h bit 5 and only then sets bit 2 of the equipment word `40:10`** ("pointing
   device installed"). That CMOS bit is what SETUP's `TrackBall [On/Off]` field controls
   (best guess from the code; the SETUP field table itself is not decoded).
4. Unmasks IRQ8, writes KBC command byte `65h` (keyboard IRQ on, translate on, **aux interrupt
   off, aux device disabled**), and writes output port `49h` via `D1h`.

So after POST the trackball is present but *disabled*; IRQ12 is masked at the PIC until a driver
asks for it. The services a driver uses (`INT 15h AH=C2h`, dispatch at `C766`):

| AL | Routine | Effect |
|---|---|---|
| 00 | `int15_C2_00_enable_disable` | BH=0 disable (`F5h`) / BH=1 enable (`F4h`) the device; enable fails with AH=05h unless a handler was installed first |
| 01 | `int15_C2_01_reset` | KBC command byte 65h, `FFh` reset, reads the two response bytes into BH/BL |
| 02 | `int15_C2_02_set_sample_rate` | BH = rate index (table `C830`: 10, 20, 40, 60, 80, 100, 200) |
| 03 | `int15_C2_03_set_resolution` | BH = 0..3 |
| 04 | `int15_C2_04_get_type` | BH = device ID |
| 05 | `int15_C2_05_init` | BH = packet size 1-8, resets the device (3 tries), then **unmasks IRQ12** (`A1h` bit 4); on failure disables aux (`A7h`) and returns AH=03h |
| 06 | `int15_C2_06_ext_cmds` | status / scaling |
| 07 | `int15_C2_07_set_handler` | ES:BX = far handler, stored in the EBDA (offsets 22h/24h), flag bit 7 at EBDA 27h |

`int74_irq12_mouse` (`C64D`) reads each byte, tracks acknowledge/resend/BAT bytes, assembles a
packet of the size given by AL=05h in the EBDA (`28h..`), and calls the user handler with the
packet words on the stack (the standard PS/2 BIOS calling convention).

Practical checklist when the trackball does nothing:

- In SETUP, `TrackBall` must be `On`. With it off, `40:10` bit 2 is clear and most PS/2 drivers
  (Microsoft `MOUSE.COM` 8.x/9.x included) decide there is no PS/2 mouse and fall back to probing
  serial ports.
- Use a PS/2 driver, not a serial or bus one: MS-DOS `MOUSE.COM` 8.20 or later (9.01 from
  Windows 3.11 works well), Logitech `MOUSE.EXE`, or `CTMOUSE` (CuteMouse) with `/P` to force
  PS/2. In Windows 3.1x Setup choose *Microsoft, or IBM PS/2* as the mouse type and let the DOS
  driver stay loaded, or use the PS/2 driver directly.
- The DOS editor (`EDIT`, QBasic) only shows a cursor when a DOS mouse driver is resident.
- If POST printed `Pointer device failure`, the aux channel test itself failed (KBC or trackball
  hardware, or the trackball disconnected internally).
- The dock's `KYB` port is keyboard-only; an external PS/2 mouse there cannot work on this
  machine. An external mouse would have to be serial (COM1/COM2).
- MISER's activity hooks watch keyboard and disk traffic for the sleep timers; a driver that
  disables the aux port at unload (`C200` with BH=0) leaves the trackball off until the next
  driver enables it, which is normal.

## Docking station (from the owner's hardware notes, 2026-09-04)

Unit: CompuAdd Port Replicator "Mini-Dock" model RD-E01, made in Taiwan, probably OEM'd by
Chaplet Systems. Power adapter AC-E01, 18 V DC / 2.2 A. Rear panel: SCSI (50-pin external),
CRT (DB15), SERIAL (DB9), PRINTER (DB25), SPEAKER and LINE audio jacks, LAN (RJ45 with TX/RX
LEDs), a round DIN connector labelled KYB (PS/2 keyboard port; a PS/2 mouse plugged in there does
not work), DC input.

Network daughtercard: Chaplet EM-8634U-C REV.A1 with a UMC UM9003AF NE2000-compatible
controller, UM9095L support chip, UM61256AK-15 SRAM buffer, Atmel AT93C46 MAC EEPROM, YCL
20F001N 10BaseT filter, 20 MHz crystal, DIP switches for I/O address and IRQ. Generic NE2000
drivers do not work with it; the vendor package (`um9003af.zip`) is the next thing to try.

How that squares with the BIOS:

| Dock feature | What the BIOS does |
|---|---|
| NE2000 NIC | Nothing. No I/O in 300h-33Fh, no dock detection. A boot ROM on the card would be picked up by `scan_option_roms` in the C800h-DFFFh window during POST 57h; otherwise the card exists only to a DOS driver. |
| IRQ/I/O conflicts | POST claims IRQ3/IRQ4 for COM2/COM1 and also probes 3E8h/2E8h (COM3/COM4) in `detect_equipment`. A NIC DIP-switched to IRQ 3/4 or to an address the Super I/O decodes will collide; IRQ 5, 10 or 11 are free from the BIOS's point of view (IRQ 12 is the trackball, 13 the FPU, 14 the IDE disk, 8 the RTC). |
| SCSI | No SCSI support in the ROM at all; a SCSI host adapter in the dock must carry its own option ROM (INT 13h hook) to be bootable, or rely on a DOS ASPI driver. |
| CRT | Handled by the C&T VGA ROM (`Display Device [CRT / LCD / LCD & CRT]`) and the INT 15h 5Fh platform hooks; the dock only passes the signal through. |
| Serial / printer | The same Super I/O ports as on the notebook, passed through. |
| Audio jacks | Pass-through of the on-board audio; the BIOS only silences the FM synthesiser. |
| Round DIN "KYB" (PS/2 keyboard) | Wired to the keyboard channel of the keyboard controller only, which is why a PS/2 mouse there does nothing: the BIOS drives pointing devices exclusively through the KBC auxiliary channel (commands A7h/A8h/D4h, IRQ12), and that channel is taken by the internal trackball. A mouse on the keyboard channel answers the POST reset with a BAT byte like a keyboard but never gets the aux-side enable, so its packets are discarded as bad scancodes. |

## The 4 GB CompactFlash card

The owner's 4 GB CF card in the IDE bay currently needs a special boot loader to reach 1 GB. That
matches the driver exactly: `ata_identify_to_table` stores the raw IDENTIFY geometry (for a
4 GB card typically 7769 cylinders × 16 heads × 63 sectors), `hd_08_get_params` can only report
10 cylinder bits (max 1024) and the task-file mapping only goes beyond 1024 cylinders through
the non-standard DH bits 5-7 that DOS never uses. So DOS sees at most 1024 × 16 × 63 × 512 =
528 MB, and a boot-loader with its own LBA code is the only way past that. The LBA patch sketched
in [08](08-int13-hard-disk.md) (translated geometry in AH=08h plus LBA addressing in the task
file, optionally the AH=41h-48h extensions) would remove the need for the loader.
