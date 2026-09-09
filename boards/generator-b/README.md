# Origin89 generator board, board B

![Development stage](https://img.shields.io/badge/development%20stage-prototype-orange.svg) First boards assembled, bench proof pending.

This board owns the generator contact. Board A asks for the engine over a
five-wire link with two logic lines, `RUN` and a once-a-second `KICK`; this
board closes a dry contact toward the genset's two-wire start input only while
both are true, through two relays in series driven by two different paths. A
stuck controller, a stuck GPIO or a lost link each opens at least one relay by
construction, and the relays' second poles report what the contacts did. There
is no microcontroller on it.

80 × 55 mm, two layers, contact nets 1.0 mm wide and held 1.5 mm from every
other net by a DRC rule, seven test pads.

Design source: [`easyeda/origin89-generator.eprj2`](easyeda/), the EasyEDA
Pro project of this board alone.
What it is and why, the `B-nn` rules and what the bench has to prove on the
first boards: [GENERATOR-BOARD.md](GENERATOR-BOARD.md).

Fabrication outputs, export of 2026-09-09: [`build/2026-09-09/`](build/2026-09-09/),
the Gerbers, the [bill of materials](build/2026-09-09/bom.csv), the
[pick-and-place](build/2026-09-09/pick-and-place.csv), the schematic PDF,
the STEP model with every part on it, and one DXF of every layer.

## Status

Schematic drawn and verified, PCB placed and routed, DRC clean. Five boards
ordered from JLCPCB and assembled. Bench proof happens on those boards. The
Gerber check in `tools/` has no rule file for this board yet; this board's
`B-nn` rules are checked on the bench.

## Revisions

| Revision | Export | What changed |
| --- | --- | --- |
| first boards | 2026-09-09 | Gerbers and BOM of the layout the five assembled boards were made from; pick-and-place, schematic, STEP and DXF exported the same day. |
