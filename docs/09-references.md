# External references and what they tell us about the machine

Research done 2026-09-04 with web searches. Downloaded material is third-party and is not part of
the repository; `bash tools/fetch_drv.sh` re-creates the local cache in `drv/` (git-ignored) from the
sources listed at the end of this document.

## The machine is a Chaplet Systems (Taiwan) design

Evidence chain:

- The system BIOS OEM string is `NBE BIOS For STN Panel.[94070501]`. Chaplet named its notebook
  series `NBA`, `NBC`, `NBD` (Halikan NBA386SX 1991, NBA486 1992, NBD 486 1993); `NBE` is the
  next letter, and the build date 1994-07-05 matches Chaplet's 1994 products.
- The owner's dock label says the notebook was OEM'd by Chaplet Systems Inc.
- Chaplet's early-1994 model, the **iLuFA 750**, has the same feature set as the Compuadd 450
  ColorScan: Chips & Technologies 65535 video, 9.5" passive-matrix colour (or active) 640×480
  LCD, trackball, 2 PCMCIA slots (2 × Type II / 1 × Type III), parallel, serial, VGA out, PS/2,
  dock connector, line in / line out, 486SX-25/33, DX2-50/66 or DX4-75/100, 4 MB standard /
  20 MB max, 250 MB 2.5" IDE, 1.44 MB floppy, NiMH battery
  ([MacDat iLuFA 750](https://www.macdat.net/laptops/chaplet/ilufa_750.php)).
- Known rebrands of that model: **Halikan 750** (Chaplet's own brand) and **Comtrade
  "Sound WinNote 486"** – note the MISER credits list a *Sound* engineer, and the audio jacks.
  The Compuadd 450 ColorScan is another rebrand of the same design.
- The previous Chaplet 486, the Halikan NBD 486 (1993), used the PicoPower Evergreen PT86C168
  or ALi M1219 chipset with Cirrus video; the 1994 design moved to the PT86C268 (the hybrid
  3.3 V / 5 V Evergreen) and C&T 65535
  ([MacDat NBD 486](https://www.macdat.net/laptops/chaplet/halikan_nbd486.php)).
- FCC grantee code `GXL` (Chaplet Systems USA Inc) lists notebooks granted 1994-03/04
  (`E4XD23SA/MA/TA`), 1994-08/09 (`S4XD2M`, `S4XD2S`), 1994-11 (`E4D23S/T`), plus an external
  floppy drive `SFD-B01` (1994-08-26) – the VersaPort external floppy – and a docking station
  `GDK200` (1996) ([fccid.io GXL](https://fccid.io/GXL)). The `E4XD23xx` series granted spring
  1994 is the most likely FCC identity of the "NBE" board (S = STN colour, M = mono, T = TFT).

So, to the question "what other computers use the same dock": any rebrand of the Chaplet iLuFA
750 / NBE-series chassis – Halikan 750, Comtrade Sound WinNote 486, Compuadd 450 ColorScan – and
possibly the later iLuFA 770/780 (Pentium, October 1994) if the dock connector was kept. The
"Mini-Dock RD-E01" itself has no FCC record under GXL, so it was probably certified with the
notebook or by the OEM.

## Firmware pedigree

| Component | Finding | Source |
|---|---|---|
| Phoenix `A486 Version 1.03` | A 1999 forum post from a notebook owner quotes exactly `PhoenixBIOS for PicoPower PT86C268 (Evergreen)`, `2.40-A486 Version 1.03` and reports Phoenix had no update | [nickles.de](https://www.nickles.de/forum/mainboards-bios-prozessoren-ram/1999/bios-update-phoenix-a486-von-v1-03-oder-2-4-53422.html) |
| PicoPower PT86C268 | "Evergreen HV Core Logic Chip (Hybrid 3.3v/5.0v)", 486/386DX core logic, 256 KB shadow RAM in C0000-FFFFF organised as 12 × 16 KB + 1 × 64 KB (which explains why the BIOS runs from shadow RAM and patches its own disk table) | TLB `chipset.doc` ([mpoli.fi](https://files.mpoli.fi/unpacked/software/dos/utils/misc/tlb_v252.zip/chipset.doc)) |
| `PT68C268` in the MISER string | typo/variant of PT86C268; no part of that name exists elsewhere | – |
| PicoPower datasheets | the Evergreen datasheet is not online; bitsavers has the related Redwood PT86C768 (1994), Vesuvius PT86C521 and the PT82C206F-LV peripheral controller, plus AN928 on Super I/O power management | [bitsavers picoPower](http://www.bitsavers.org/components/picoPower/) |
| C&T 65535 | 1993 "high performance mobile controller", 1 MB, 32-bit core, ISA, TFT/STN panel support | [VGA Museum](https://www.vgamuseum.info/index.php/cpu/item/183-chips-technologies-f65535) |
| C&T INT 10h 5Fh functions | the public `CHIPS.TXT` documents 5F00 get controller info, 5F01 set emulation, 5F02 auto-emulation, 5F03 set power-on video configuration, 5F90-5F92 save/restore; this ROM implements 5F00, 5F02-5F04, 5F51-5F5F, 5FA0-5FA1 instead (see [04](04-vga-bios.md)) | [CHIPS.TXT](https://cs.nyu.edu/~mwalfish/classes/ut/f09-cs395t/ref/hardware/vgadoc/CHIPS.TXT) |
| PhoenixMISER / PHDISK | PHDISK creates the save-to-disk partition sized to installed RAM; the POST error appears when the partition is missing; the PHDISK version must match the MISER version | [archive.org PHDISK 1.7](https://archive.org/details/cd-rom_and_phdisk), [computerhope](https://www.computerhope.com/issues/ch000348.htm) |
| CompuAdd | Austin TX, founded 1982, closed its 110 stores and filed Chapter 11 in 1993, emerged November 1993, sold to Dimeling, Schrieber & Park in September 1994 – so this 1994-07 BIOS is from the company's last year, when it resold OEM notebooks | [Wikipedia](https://en.wikipedia.org/wiki/CompuAdd) |
| Sibling model | CompuAdd Express 425 / 425XL (1993, 486S-25) | [worthpoint](https://www.worthpoint.com/worthopedia/vintage-laptop-computer-1993-compuadd-1811653906) |

## Software located

| Item | Where | Local copy |
|---|---|---|
| UMC UM9003 DOS packet / WfW / NetWare / OS/2 drivers | [vogonsdrivers 838](https://vogonsdrivers.com/getfile.php?fileid=838&menustate=0); also `um9003af.zip` on driverguide / elektroda / driverzone (setup program that writes the card's EEPROM) | `drv/network-um9003af/` |
| Generic NE2000 packet driver | [vogonsdrivers 854](https://vogonsdrivers.com/getfile.php?fileid=854&menustate=) | `drv/network-um9003af/` |
| PHDISK 1.7 | [archive.org](https://archive.org/details/cd-rom_and_phdisk) | `drv/power-phoenixmiser/` |
| CompuAdd 386/486 utilities, mouse and VGA driver disks (desktop line, may still hold the CompuAdd mouse driver) | [archive.org](https://archive.org/details/compuadd286386486utilitiesanddrivers) | `drv/computer-compuadd/*.img` |
| C&T VGA programming docs (vgadoc) | NYU / MIT mirrors | `drv/video-ct65535/` |
| PicoPower family datasheets | bitsavers | `drv/chipset-picopower/` |
| CuteMouse (PS/2 DOS mouse driver, `/P` forces PS/2) | [cutemouse.sourceforge.net](http://cutemouse.sourceforge.net/) | `drv/mouse-ps2/` (home page only; download the release zip manually) |

Still to find: the C&T 65535 Windows 3.1 display driver set (`CHIPS` `.DRV`), the Phoenix
`POWER` DOS/Windows APM client that pairs with MISER, a PHDISK version matching MISER 1992
(the 1.7 archive may be newer than this ROM), the Intel 82365SL datasheet for the PCMCIA
controller, and any Compuadd 450 manual.

## Entering SETUP after boot

The ROM keeps the SETUP hot key alive after POST: the INT 15h AH=4Fh keyboard-intercept path
(`int15_4F_setup_hotkey_check`, `8695`) compares each scancode with the ROM option byte at
`AF65` and, when SETUP is not already running (`40:B5` bit 0), clears the Ctrl/Alt shift state
and far-calls PhoenixMISER API 34h (`os_environment_check`). MISER refuses if Windows enhanced
mode answers INT 2Fh AX=1600h, or if the Phoenix power TSR (INT 2Fh AH=54h) objects; otherwise it
saves its state and calls `setup_far_entry` (`F000:0100`). SETUP's own text ("Returning to DOS
will not interfere with resident applications") confirms it is meant to be run from the DOS
prompt. So with a fast-booting CF card, press **Ctrl+Alt+S at the DOS prompt** (not inside
Windows). The other entry is F2 at any POST/boot error prompt.

## Downloaded reference material (not redistributed)

Everything `tools/fetch_drv.sh` fetches into `drv/`, with the original location, so the material can be
found again without this repository carrying copies.

| Folder | File | Source |
|---|---|---|
| `chipset-picopower/` | `PT86C768_Redwood1_2_199404.pdf` (the notebook chipset family datasheet) | [bitsavers](http://www.bitsavers.org/components/picoPower/PT86C768_Redwood1_2_199404.pdf) |
| `chipset-picopower/` | `AN928_Active_Power_Management_Using_SuperIO_1994.pdf` | [bitsavers](http://www.bitsavers.org/components/picoPower/AN928_Active_Power_Management_Using_SuperIO_1994.pdf) |
| `chipset-picopower/` | `PT82C206F-LV_Integrated_Peripheral_Controller.pdf` | [bitsavers](http://www.bitsavers.org/components/picoPower/PT82C206F-LV_Integrated_Peripheral_Controller.pdf) |
| `chipset-picopower/` | `picopower-chipset-list-tlb.doc` (TLB chipset list) | [mpoli.fi](https://files.mpoli.fi/unpacked/software/dos/utils/misc/tlb_v252.zip/chipset.doc) |
| `video-ct65535/` | `CHIPS.TXT`, `VGABIOS.TXT`, `VGAREGS.TXT` (vgadoc) | [NYU mirror](https://cs.nyu.edu/~mwalfish/classes/ut/f09-cs395t/ref/hardware/vgadoc/CHIPS.TXT), [MIT mirror](https://pdos.csail.mit.edu/6.828/2008/readings/hardware/vgadoc/VGABIOS.TXT), [MIT mirror](https://pdos.csail.mit.edu/6.828/2016/readings/hardware/vgadoc/VGAREGS.TXT) |
| `power-phoenixmiser/` | PHDISK 1.7 disk image and archive listing | [archive.org cd-rom_and_phdisk](https://archive.org/details/cd-rom_and_phdisk) |
| `computer-compuadd/` | CompuAdd 386/486 mouse, system-utilities and VGA driver disk images | [archive.org compuadd286386486utilitiesanddrivers](https://archive.org/details/compuadd286386486utilitiesanddrivers) |
| `computer-chaplet/` | Chaplet / iLuFA 750 / Halikan NBD 486 pages, FCC ID GXL | [macdat.net](https://www.macdat.net/laptops/chaplet/ilufa_750.php), [macdat.net](https://www.macdat.net/laptops/chaplet/halikan_nbd486.php), [fccid.io/GXL](https://fccid.io/GXL) |
| `network-um9003af/` | UMC UM9003AF drivers | [vogonsdrivers 838](https://vogonsdrivers.com/getfile.php?fileid=838&menustate=0), [vogonsdrivers 854](https://vogonsdrivers.com/getfile.php?fileid=854&menustate=0), elektroda |
| `mouse-ps2/` | CuteMouse 2.1b4 | [ibiblio](https://www.ibiblio.org/pub/micro/pc-stuff/freedos/files/dos/ctmouse/2.1b4/ctmouse.zip), [cutemouse.sourceforge.net](http://cutemouse.sourceforge.net/) |
| `xtide/` | XTIDE Universal BIOS r638 release binaries (`ide_386.bin` etc.), used only to compare against the source build | [xtideuniversalbios.org/binaries/r638](https://www.xtideuniversalbios.org/binaries/r638/); source: [SVN trunk r638](https://www.xtideuniversalbios.org/svn/xtideuniversalbios/trunk/) (included in `patched/xtide/src` under the GPL) |
