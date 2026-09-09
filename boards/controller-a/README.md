# Origin89 Controller, board A

![Development stage](https://img.shields.io/badge/development%20stage-prototype-orange.svg) First revision ordered, not yet measured.

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
Rules the layout has to keep, numbered and with their reasons:
[LAYOUT-REQUIREMENTS.md](LAYOUT-REQUIREMENTS.md).
Firmware: the `o89-stm32` and `o89-esp32` workspaces in the Origin89 code repository.

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
| A | 2026-09-09 | First fabrication at JLCPCB, from this layout. Gerber check all clear. Not yet measured. |
