# Origin89 Controller, board A

![Development stage](https://img.shields.io/badge/development%20stage-prototype-orange.svg) First revision fabricated. On the bench since 2026-09-14: SWD, both crystals, the RTC and its backup cell, FRAM, NOR, CAN in loopback, the analogue inputs, the watchdog, RS-485 across all three channels, three DS18B20s and the ESP32's radio receive all pass. Switching the ESP32 rail after ten minutes off corrupted the MCU 22 times out of 22 and is open; brown-out is unmeasured; board B's interlock waits on a board B wiring fault.

This is the board that makes the decisions. An STM32G0B1 runs the control
logic; an ESP32-C6 module carries the radio; three RS-485 channels, one CAN
bus and two VE.Direct ports talk to the site's equipment; 1-Wire reads
temperature probes; FRAM and NOR flash hold state and the event log. It runs
from a 12 V battery bank directly. The generator contact is on
[board B](../generator-b/README.md), so no single fault on this board can
hold a genset running.

100 × 125 mm, 1.6 mm FR-4, four M3 mounting holes. All field wiring enters on
one edge through one gland plate.

Design source: [`easyeda/origin89-controller.eprj2`](easyeda/), the EasyEDA
Pro project of this board alone.
Fabrication outputs: [`build/2026-09-09/`](build/2026-09-09/), Gerbers,
[bill of materials](build/2026-09-09/bom.csv),
[pick-and-place](build/2026-09-09/pick-and-place.csv), schematic PDF, STEP
and DXF.
Revision B, not yet fabricated: [`easyeda/origin89-controller-revb.eprj2`](easyeda/),
exported to [`build/2026-09-19/`](build/2026-09-19/): Gerbers,
[bill of materials](build/2026-09-19/bom.csv),
[pick-and-place](build/2026-09-19/pick-and-place.csv), schematic PDF and DXF.
Rules the layout has to keep, numbered and with their reasons:
[LAYOUT-REQUIREMENTS.md](LAYOUT-REQUIREMENTS.md).
Firmware: [origin89hq/firmware](https://github.com/origin89hq/firmware); its
`docs/ARCHITECTURE.md` is the system design this board implements.

## Status of the exports

`build/2026-09-09/` is the export of this layout from the project that
holds the board alone. The revision A boards, the first JLCPCB order, were
made from the same layout exported nine days earlier from the project that
also held the generator and camera; that file differs from this Gerber set
only in 2 mm² of unconnected top-copper islands near (+17.8, −42.1), and
both pass `tools/validate_gerbers.py`. The fab's production package is kept
outside this repository with the rest of the order paperwork.

The pick-and-place is the one to assemble from: the crystal X1 moved 0.112 mm
in X after the first pick-and-place was written, and this file has it where
the boards were assembled. The STEP is in millimetres and carries every part
but U8, the chip antenna, which has no model; CN9's model was not a STEP one
at export time, so check its height against the JST drawing before trusting
the enclosure clearance there. `board.dxf` holds every layer in one file.

The mounting holes on the fabricated boards carry no copper on any layer,
read from the fab's own CAM: the two in the antenna band have nothing within
4 mm, and the two at the bottom edge meet the ground pour at the A-02
keep-out radius, under solder mask. A-03 holds.

## Revisions

| Revision | Export | What changed |
| --- | --- | --- |
| A | 2026-09-09 | First fabrication at JLCPCB, from this layout. Gerber check all clear. First bench session on 2026-09-14: both processors boot; SWD, both crystals, the RTC, FRAM, NOR, CAN in loopback, the analogue inputs, the watchdog, RS-485 between all three channels at 115200 8N1 and 9600 8N2, a DS18B20, the RTC across a power loss on its CR2032, and the ESP32's rail and UART to the MCU work. As built, the STM32 cannot program the ESP32 over serial, because the module's IO8 boot strap is unconnected; with IO8 held high by a hand-held wire to a 4.7 kΩ pull-up, the ESP32 entered serial download mode, took its first firmware through the STM32, and from then on restarted into download mode on command with no wire. The ESP32 received 11 Wi-Fi networks and 30 BLE devices. Board B's interlock could not be proven because board B's relay chains cannot close ([board B bench log](../generator-b/bench/2026-09-14.md)); brown-out is not yet measured, and a self-test crash at the ESP32 rail switch is open ([bench log](bench/2026-09-14.md)). Silkscreen check against the rev B rule `A-33`: fails, the silkscreen carries designators only (#12). |
| B | 2026-09-19 | Not fabricated. Drawn and routed against the rev B rules in [LAYOUT-REQUIREMENTS.md](LAYOUT-REQUIREMENTS.md) (#54): an input chain for 12 V and 24 V banks with a 12 V buck (`A-20`, `A-20e`); current limiters on CN9's 12 V, the 4-pin RS-485 port's 5 V and the 1-Wire supply (`A-20b`, `A-20c`, `A-24`); an isolated listener on each of two VE.Direct ports, with an isolation gap in the copper (`A-38`); series resistors and clamps on the CN9 and selector lines (`A-34`, `A-36`); the ESP32 rail switch, EN supervisor and IO8 pull-up (`A-23`, `A-39`); a tank-loop supply (`A-20d`); a button (`A-42`); the RTC cell connector moved inboard (`A-25`); indicator current cut to 0.2–0.5 mA (`A-14`) and a red FAULT LED; pin, bus and board labels on the silkscreen (`A-33`). EasyEDA DRC 0 errors. Gerber check all clear; silkscreen check against `A-33` passes, no required label missing. This export has no STEP or fabrication-layer PDF. No bench work yet. |
