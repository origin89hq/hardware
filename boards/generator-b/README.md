# Origin89 generator board, board B

![Development stage](https://img.shields.io/badge/development%20stage-prototype-orange.svg) First boards assembled. On the bench since 2026-09-14: both relay chains skip the relay commons as built, so nothing closes. With four links per board, 4 to 6 and 13 to 11 on each relay, the interlock passes: 68 sequences, no failures, the contact dropping 4.34 s after the last kick ([2026-09-17](bench/2026-09-17.md)).

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

First bench contact, 2026-09-14 ([bench log](bench/2026-09-14.md)): driven
from board A, both coils energize and both relays click, but the contact chain
and the feedback chain are wired from each relay pole's NC terminal to its NO
terminal (pins 6 to 8 and 11 to 9), and the commons, pins 4 and 13, are
unconnected. Neither chain can close. A rework of four wire links is proposed
and not yet tried.

## Revisions

| Revision | Export | What changed |
| --- | --- | --- |
| first boards | 2026-09-09 | Gerbers and BOM of the layout the five assembled boards were made from; pick-and-place, schematic, STEP and DXF exported the same day. Bench, 2026-09-14: K1 and K2 are wired NC to NO with their commons unconnected, so CN10 and `FEEDBACK` cannot close ([bench log](bench/2026-09-14.md)). |
