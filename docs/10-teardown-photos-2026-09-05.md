# Teardown photos, 2026-09-05: RAM board and BIOS/PCMCIA daughtercard

The owner opened the machine and photographed two internal boards. This is a plain transcription
of what the boards and chips say, matched against the earlier findings in
[07-hardware.md](07-hardware.md) and [09-references.md](09-references.md). Nothing here comes
from the ROM disassembly — it is physical evidence only, kept separate so it can be checked
against the code independently.

## RAM daughtercard, PCB "223100000 REV 0.1"

A small card on its own connector, not a socketed SIMM. Populated with 8 DRAMs in SOJ packages,
silkscreened `U1`-`U8` around a keyed header `CN1`:

```
NEC UK
424400-70L
9419MSL31
```

on every chip. `424400-70L` is NEC's 4M x4-bit (16 Mbit) fast-page DRAM, 70 ns access; `9419` is
the date code (1994, week 19). Eight x4 parts wired together give a 32-bit-wide bank, matching the
486's memory bus. One small SMD part (`C1`, a decoupling capacitor) sits by the connector. A
rubber/foam pad is glued to the board near `U5`-`U8`, presumably a cushion against the chassis lid
rather than a functional part.

This is most likely the machine's built-in DRAM (or a factory memory-upgrade card fitted at the
factory rather than a field-installable SIMM) referred to as "4 MB standard / 20 MB max" for the
sibling iLuFA 750 in [09-references.md](09-references.md#the-machine-is-a-chaplet-systems-taiwan-design).
Eight 16 Mbit chips would be a 16 MB bank if wired as one rank, or 2 x 8 MB banks if split — the
photo doesn't show enough of the connector pinout to tell which; `CN1` is the only way this board
talks to the rest of the system, so bus width/interleave can't be read off the silkscreen alone.

## Mainboard section, PCB "218000401 REV 1.0"

This is the section of the mainboard directly under the PCMCIA cage and floppy assembly. Four
things worth recording:

### The BIOS/firmware chips: 3 parts, plus a "SystemSoft PCMCIA" label that turns out not to be one of them

Three small ICs sit in a row along the board edge, each carrying its own adhesive label:

| Label (as printed) | What it is |
|---|---|
| `CHIPS FLAT-PANEL/CRT BIOS VER. © 1990-1993, CHIPS AND TECHNOLOGIES, INC. ALL RIGHTS RESERVED` | the C&T 65535/A VGA BIOS — matches [04-vga-bios.md](04-vga-bios.md) |
| `PhoenixMISER™ © Phoenix 1992, F186161` | the PhoenixMISER power-management module — matches [03-phoenixmiser.md](03-phoenixmiser.md) |
| `PhoenixBIOS™ © 1993, A92711` | the Phoenix system BIOS core — matches [01](01-system-bios-post.md)/[02](02-system-bios-runtime.md) |

The dumped 128 KB `.BIN` is one flat, contiguous read of the `E0000`-`FFFFF` shadow window (VGA
at `E000`, MISER at `E800`, system BIOS + SETUP at `F000`, per the map in the top-level
[README](../README.md#runtime-memory-map)); the chipset shadowing 3 separate physical ROMs into
that one CPU-visible window is consistent with what the code already showed (12 x 16 KB + 1 x
64 KB shadow segments, per the PicoPower `chipset.doc` finding in 09). So finding 3 chips here
that line up one-for-one with VGA/MISER/system-BIOS is confirmation, not a surprise.

A 4th sticker sitting right next to those three, reading `SystemSoft® PCMCIA © 1992-1993 AN5798`,
first looked like an undumped 4th ROM. A follow-up photo rules that out: the same
`SystemSoft® PCMCIA © 1992-1993` sticker (different serial, `AM8922`) turns up stuck directly to
the bare metal chassis rail that carries the PCMCIA card-ejector mechanism — no PCB, no chip leads,
nothing nearby it could be labelling except the sheet-metal cage itself. So this is a compliance/
QA sticker SystemSoft applied to (or licensed for) the physical PCMCIA socket assembly — most
likely a mechanical/electrical conformance sign-off tied to their Card and Socket Services
qualification testing — not a firmware chip. Read back with that in mind, the one next to the ROM
row is the same kind of label, just placed near the PCMCIA cage bracket that happens to be next to
the ROMs on this board, not a 4th IC. **No SystemSoft PCMCIA chip exists to dump; the "no Card/
Socket Services in ROM" finding in [07-hardware.md](07-hardware.md#resource-map) and
[09-references.md](09-references.md#software-located) stands as before.**

### PCMCIA controller is confirmed as Cirrus Logic, not generic 82365SL

The controller chip itself reads:

```
CIRRUS LOGIC
CL-PD6720-QC-B
24633-316CE
9402 N JAPAN-U
© 1993 CIRRUS LOGIC INC
1993 QUADTEL CORP
```

`CL-PD6720` is Cirrus Logic's single-socket-pair PC Card controller — but the board has 2 sockets,
so either a second `PD672x` is elsewhere on the board (not photographed) or this one part serves
both. It's register-compatible with the Intel 82365SL, which is what [07-hardware.md](07-hardware.md#resource-map)
already assumed by inference ("PCMCIA controller (Intel 82365SL compatible)"); this photo upgrades
that line from inferred to a named part number. The Quadtel copyright alongside Cirrus Logic's is
notable too — Quadtel was a BIOS vendor bought by Phoenix in 1993, so this may be an OEM'd/licensed
BIOS core for the controller rather than Cirrus Logic's own.

### Sound chipset is ESS, not a Creative/SB clone part

A separate small board, `P/N 21906450 REV 1.5`, carries:

- `IP32500 ES488-F` (marked `9327`, i.e. week 27 1993) — this is an ESS Technology ES488(-F), the
  ISA bus-interface half of an ESS AudioDrive chipset (normally paired with an ES1688-class codec,
  not photographed here).
- An `LM386M-1` (National Semiconductor) audio power amplifier.

This confirms the Sound Blaster-compatible DSP that [07-hardware.md](07-hardware.md#resource-map)
already placed at `220h-22Fh` (reset/mute sequence only, no IRQ/DMA programming by the BIOS) is an
ESS design, and names the actual op-amp behind the SPEAKER/LINE jacks.

### Cooling and PCMCIA power

A small brushless fan (`Densitron DPF25A055`, 5 V DC, marked "PANCAKE FAN") sits next to the
PCMCIA cage, along with several Rubycon electrolytic caps (`50V 4.7 µF` x3 and others) near the
card slots — PCMCIA `Vpp`/`Vcc` switching filtering, most likely, rather than anything to do with
the fan. A partial sticker near the ROM row reads something like `...DX2-50`, consistent with the
486DX2 the BIOS's CPU-detection code already expects.

## Net effect on the existing docs

- [07-hardware.md](07-hardware.md) PCMCIA row: part number can be upgraded from "Intel 82365SL
  compatible" (inferred) to "Cirrus Logic CL-PD6720-QC-B" (confirmed by chip marking).
- [07-hardware.md](07-hardware.md) audio row: the DSP can be named as an ESS ES488-F-based
  AudioDrive design rather than left as "an ESS/Crystal-class SB clone" guess.
- [09-references.md](09-references.md) "still to find" list is unchanged: the `SystemSoft PCMCIA`
  sticker turned out to be a QA/compliance label on the PCMCIA cage hardware (seen again, different
  serial, stuck to bare chassis metal with no chip nearby), not a firmware chip, so a Card/Socket
  Services stack is still something to source separately rather than something to dump off this
  board.
