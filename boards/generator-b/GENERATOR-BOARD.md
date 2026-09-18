# Generator board (Board B)

The board that owns the generator contact. The [controller design](https://docs.origin89.com/hardware/)
decided what it is and why it is a separate board; this file is what was drawn
from that, the rules the layout has to keep, and what the bench has to prove
on the first boards. The schematic is `Generator / Schematic2` in the
EasyEDA project `origin89-fab`, beside the controller's.

Status: **schematic drawn and verified; PCB placed (80 × 55 mm, 2 layers)
and routed with the seven B-10 test pads, contact nets 1.0 mm wide and held
1.5 mm from every other net by a DRC rule, GND routed as a net under both
pours, DRC empty, CN9 pins and test pads named on the silkscreen; five
boards ordered from JLCPCB, assembled, SMD and through-hole alike. Bench
proof happens on those boards, not on a breadboard.**

**Bench, 2026-09-14: the relays switch, but on these boards both relay chains
use each pole's NC and NO terminals and leave the commons unconnected, so
neither the contact nor `FEEDBACK` can close ([bench log](bench/2026-09-14.md)).
The relay rows and the chains below give Omron's pinout; the copper does not
follow it yet.**

**Bench, 2026-09-17: the rework works. Four links per board, `4` to `6` and
`13` to `11` on K1 and on K2, close both chains, and the interlock then passes
end to end: 68 sequences with no failures, the contact opening 4.34 s after the
last kick against a 3.0-6.5 s specification ([bench log](bench/2026-09-17.md)).
Revision B should fix the footprint so the chains run through the commons.**

**Revision B is drawn to the rules below that name their issue**: the chains
through the commons (B-18), a ride-through of controller resets behind a 15 s
window (B-19 to B-21), the timing network off the 74HC123's resistor limit
(B-07), series resistance behind the link's TVS (B-03), a start-input clamp one
shorted part cannot bypass (B-06), and the same 12 V on `+12V` from any bank,
regulated on board A (B-09). Nothing about revision B is proven yet; the
bring-up list below is what proves it.

---

## What it is, in one paragraph

Board A asks for the engine over CN9 with two logic lines: `RUN` (please run)
and `KICK` (I am alive, once a second). Board B closes a dry contact toward
the generator's 2-wire start input only while **both** are true, through two
relays in series driven by two different paths: relay B follows `RUN` as the
controller last said it while it was kicking, a latch clocked by `KICK`;
relay A follows a retriggerable monostable that `KICK` keeps alive for 15 s.
No microcontroller, no firmware. A lost cable, a dead controller, a stuck
GPIO: each one opens at least one relay within the window, by construction,
in a part that runs no code. On revision A relay B followed `RUN` directly
and `RUN` low reset the monostable, so every controller reset opened the
contact at once (#18). `FEEDBACK` goes back to Board A through the
relays' second poles, so the controller learns what the contacts did, not
what it commanded.

## The schematic, block by block

| Block | Parts | What it does |
|---|---|---|
| **CN9 link** | CN9 `B5P-VH` · D1–D3 `SMAJ15A` · R1, R2 100 k | Five wires from Board A (`V12`, `GND`, `GEN_RUN_CMD`, `GEN_WDT_KICK`, `GEN_STATUS` on that side): `+12V`, `GND`, `RUN`, `KICK`, `FEEDBACK`. A TVS on the rail and on each logic line, and a 100 k pull-down on `RUN` and `KICK`; an unplugged cable reads *stop*, never floats. Revision B: `+12V` is board A's regulated 12 V on any bank (`A-20e`), and a 10 k series resistor follows each logic line's TVS before anything reads it (B-03) |
| **3.3 V** | U1 `HT7533-1` · C1 100 n · C2 10 µ | The only rail the logic needs; 28 V-rated input so the 12 V bank's transients do not reach a 6 V part. Unchanged on revision B, fed from the regulated 12 V |
| **Watchdog** | U2 `74HC123D` · R3 1 M · C3 10 µ · C4 100 n | Monostable 1: `KICK` rising edge on 1B retriggers it, `RUN` on 1RD# holds it reset while low, Q on `WD_OK`. Pulse width ≈ 0.45 · R3 · C3 ≈ **4.5 s**. The output is a level, not a pulse: high while kicks keep coming, low a few seconds after they stop, high again at the next kick. Monostable 2 is parked (2A# high, 2B and 2RD# low). Revision B: 1RD# is tied high so `RUN` no longer resets it, and R3 at or below 470 k with C3 about 68 µF give a **15 s** window (B-07, B-20) |
| **RUN latch** (revision B) | U3, a single D flip-flop with asynchronous clear (74LVC1G175 class) · an RC on its clear | `RUN` on D, `KICK` on the clock: Q is what the controller last asked while it was alive. Cleared at power-up by the RC on its clear input, which outlasts the 3.3 V rail's rise. Q drives Q2; `RUN` reaches no coil (B-19) |
| **Relay A** | Q1 `AO3400A` · K1 `G5V-2-DC12` · D4 `1N4148W` · LED1 + R5 | Coil driven by `WD_OK`. Pole 1 (COM 4 → NO 8) is the first series contact; pole 2 (COM 13 → NO 9) is the first feedback contact. The first boards use NC 6 and NC 11 in place of the commons (bench, 2026-09-14); revision B routes the chains through the commons (B-18) |
| **Relay B** | Q2 `AO3400A` · K2 `G5V-2-DC12` · D5 `1N4148W` · LED2 + R6 | Coil driven by `RUN` on revision A, by the RUN latch's Q on revision B (B-19). Pole 1 (COM 4 → NO 8) is the second series contact; pole 2 (COM 13 → NO 9) the second feedback contact, whose NO reaches `FEEDBACK`. Same commons fault on the first boards |
| **Output** | CN10 `KF2EDGR-5.08-2P` · F1 5 × 20 fuse holder · D6 `SMBJ30CA` | The 18/2 pair to the generator. Fuse on `GEN_A`, bidirectional 30 V TVS across the pair at the terminal. Revision B: two TVS in series, each blocking the start input's voltage alone (B-06) |

Contact chain: `CN10.1 → F1 → K1 COM4/NO8 → K2 COM4/NO8 → CN10.2`. Feedback
chain: `GND → K1 COM13/NO9 → K2 COM13/NO9 → CN9.5`, so Board A (which pulls
`FEEDBACK` up) reads low only when both relays are physically closed. Omron's
G5V-2 terminal arrangement (bottom view): coil 1 and 16, pole 1 COM 4 / NC 6 /
NO 8, pole 2 COM 13 / NC 11 / NO 9. The first boards' copper runs the chains
through pins 6/8 and 11/9, NC to NO, with 4 and 13 unconnected; neither chain
closes. The rework, fitted and proven on 2026-09-17: link 4 to 6 and 13 to 11
on each relay. Revision B routes the chains through 4 and 13 (B-18). The
LEDs sit across each relay's coil drive, so they show what the coil got, which
is what the bench wants to see.

### The cable between the two boxes

Five conductors, CN9 to CN9, both boxes on the same cabin wall. Nothing on it
carries more than the two coils (about 100 mA at 12 V), and `RUN` and `KICK`
are 3.3 V levels behind a 100 k pull-down. It is a short indoor link, and it
stays one: the 18/2 to the generator is the cable that leaves the cabin, this one
never does.

- **The crimp decides the wire, not the current.** Both VH contacts
  (`SVH-21T-P1.1`, 22–18 AWG; `SVH-41T-P1.1`, 20–16 AWG) want an insulation
  diameter of **1.7 to 3.0 mm** (JST VH catalogue). That rules out every
  thin-wall multi-conductor cable: alarm/security cable is about 1.1 mm per
  conductor, Cat5e is 24 AWG solid. Neither holds in the insulation crimp,
  and a contact gripping only the strands fatigues at the first bend.
- **Wire, in the order to try.** All three fit the crimp window and come from
  a shelf in Canada:
  1. A **double-ended VH3.96 5P harness**, 22 AWG, straight through, sold in
     0.2–1 m lengths (Amazon.ca and the like), so no crimping at all. The
     boxes then sit side by side, which is where they belong anyway.
  2. **5-wire 18 AWG trailer cable** (Canadian Tire, Princess Auto, NAPA):
     stranded, jacketed, five colours, about 2.7 mm per conductor, 18 AWG is
     the top of the `SVH-21T-P1.1` range. Trailer colours: white `GND` (it
     is the trailer ground too), red `+12V`, yellow `RUN`, green `KICK`,
     brown `FEEDBACK`. Green carries a signal here because a jacketed cable
     with a plug at each end never lands on a terminal strip, which is where
     the green-is-earth rule lives.
  3. **22 AWG UL1015 hookup wire** (Digi-Key Canada), about 2.4 mm over the
     insulation, five colours (red `+12V`, black `GND`, white `RUN`, blue
     `KICK`, yellow `FEEDBACK`), in a PET braided sleeve with heat-shrink at
     both ends, wires 25 mm proud of the sleeve. The common UL1007 kits are
     1.6 mm and miss the window.
- **Length:** under 3 m. Longer runs put a logic pair beside whatever else
  runs along that wall, and nothing in the design was sized for that.
- **Pin 1 to pin 1, and a meter before the first plug:** every pin to its own
  number and to no other. 12 V on a logic pin cannot be plugged the other way
  round to fix it (B-09).
- **No shield.** Indoors, under 3 m, at 1 Hz, there is nothing to shield against.
- **The box:** CN9's window is 8 × 8 mm; five wires in a 6 mm sleeve pass
  it with room, a 5-wire trailer jacket (7–8 mm) only just. Strip the jacket
  back inside the hood if it binds.

### Why these parts

- **G5V-2** — Ag + Au-clad *bifurcated crossbar* contacts, specified from
  **10 µA to 2 A**, failure rate measured at 0.01 mA / 10 mV. The catalogue
  sweep found every 2-wire generator input is switched-to-negative at a few
  milliamps behind a pull-up (DSE 12 V / 6 mA, Generac 5 V current-limited),
  which is the dry-circuit range where plain silver contacts stop making.
  DPDT gives the feedback pole for free. The sweep read the remote-start
  section of each controller's own manual; the two figures above are from
  there.
- **74HC123, not TPL5010** — the TPL5010 was on the candidate list, but its
  `RSTn` is a reset *pulse*; holding a relay open on a pulse needs a latch
  that `RUN` re-arms, which is more parts and a second thing to prove. The
  retriggerable monostable's Q is the level the relay wants.
- **HT7533-1** — 100 mA is a hundred times what the logic draws, and a 28 V
  input rating is the margin a 12 V bank with a charger on it deserves. On
  revision B its input is board A's regulated 12 V (`A-20e`).
- **A single D flip-flop with clear (74LVC1G175 class), revision B** — one
  gate for the RUN latch, a clear pin for the power-up state, 3.3 V from the
  same rail as U2. The 74HC123's parked second monostable was considered for
  the ride-through and cannot do it: a monostable times out, a latch remembers
  what the controller last said.
- **AO3400A** — 42 mA coil at 12 V against a 5.8 A part; the gate is happy
  at 3.3 V.

## Rules the layout keeps (B-nn)

Each rule names the failure it prevents, in the style of
[`LAYOUT-REQUIREMENTS.md`](../controller-a/LAYOUT-REQUIREMENTS.md). This is the only
`B-nn` list; that brief points here rather than keeping a copy that could
drift. B-13 to B-17 came across from it when the two were merged.

| ID | Rule | The failure |
|---|---|---|
| **B-01** | Two relays in series, **two drivers, two sources** (`WD_OK` and `RUN` on revision A; `WD_OK` and the RUN latch's Q on revision B). Never a shared gate net, never a shared driver | A single driver stuck on is one relay, and one welded relay runs the tank dry. The two-in-series claim is only true if nothing common can hold both |
| **B-02** | Relay A is driven only from the watchdog output; the kick line never reaches a relay coil directly. On revision B the kick also clocks relay B's latch: a kick stuck high or low gives no edge, the latch keeps its state, and relay A still opens at the window | A `KICK` stuck high is the failure the monostable exists to catch; wiring it to a coil bypasses the catch |
| **B-03** | `RUN` and `KICK` each carry a pull-down to `GND` at the connector, and their TVS sits at CN9 before anything else. On revision B a series resistor of about 10 k follows each TVS before U2 or U3 reads the line; board A drives 3.3 V through its own 1 k (`A-34`), so the level at U2 stays about 3.2 V against the 74HC123's 2.3 V VIH | An unplugged or cut cable must read *open*, and a surge arriving on the link must be clamped before the 74HC123 sees it. The SMAJ15A clamps at 24 V, far above the 74HC123's input rating, so without the resistor the IC's own clamp diodes take the surge with nothing but the cable limiting it (#23) |
| **B-04** | The output pair (`GEN_A`, `GEN_B`, F1, D6, K1/K2 pole 1) is one physical region at CN10, separated from the logic region (CN9, U1, U2), and **no copper of any other net comes within 1.5 mm of contact copper**, a DRC spacing rule on the four contact nets, not a habit. **Accepted deviation on rev A:** the GND pour is continuous under the contact region and under the relays, held off the contact copper by that 1.5 mm rather than absent there. The pair is isolated from GND (the TVS sits across it, not to it), so what the pour adds is capacitance to a surge, which the clearance keeps small. Step 7 watches `WD_OK` while the contact makes and breaks for exactly this; rev B carries a copper keepout if it moves | The 60 ft pair is the dirtiest thing touching the design; an induced surge that crosses the board under the monostable is a surge under the safety timer |
| **B-05** | Fuse F1 is a 5 × 20 in a holder, rated below the generator kit's own fuse (5 A class → fit **2 A**), replaceable without a tool | A soldered fuse four hours from a road is a dead site; a fuse above the kit's makes the kit's fuse the one that blows, inside a box nobody opens |
| **B-06** | D6 is **bidirectional** and sits across CN10's pins, upstream of the fuse. On revision B it is **two parts in series**, each with a standoff above the site's start-input voltage on its own | The generator input's polarity is never guaranteed (most switch to negative, some carry B+); a unidirectional TVS conducts the wrong way on the wrong set. A single D6 shorted joins CN10's pins with no relay involved and F1 not in the path, the one part outside the interlock that can start the engine; two in series leave one blocking when the other fails (#19). The site's start-input open-circuit voltage, still unmeasured, sizes each part |
| **B-07** | C3 (the timing capacitor) is a ≥ 25 V X7R with the DC-bias derating checked at 3.3 V, and the measured pulse width is written on the schematic after bring-up step 7. No electrolytic anywhere on the board. On revision B R3 is at or below 470 k, well under the 74HC123's 1 M maximum, and C3 is sized for B-20's 15 s window, about 68 µF in parallel X7R parts after derating; the window is measured across temperature and again with a 10 M leakage resistor from `TIMING` to GND | The watchdog delay is a safety timing; a part whose value nobody knows at −20 °C is a delay nobody knows. At 1 M the timing current near the threshold is about a microamp, so board leakage lengthens the window, the unsafe direction, and enough of it holds `WD_OK` high (#22) |
| **B-08** | Every part industrial grade. **Accepted deviation:** the G5V-2 is rated −25 … +65 °C ambient, not −40 | The cabin freezing is the scenario the product exists for; −25 covers the cabin, not the porch. Recorded so a −40 relay is a one-line swap when one is found with the same contacts |
| **B-09** | CN9's pin order **is Board A's**: 1 `+12V`, 2 `GND`, 3 `RUN`, 4 `KICK`, 5 `FEEDBACK`. **Verified against `Controller / Schematic1` for rev A**: there CN9 is 1 `V12`, 2 `GND`, 3 `GEN_RUN_CMD` (PD0), 4 `GEN_WDT_KICK` (PD1), 5 `GEN_STATUS` (PD2). Board A rev B keeps this order but moves the three logic nets off PD0–PD2 and protects them at its end (`A-34`), and pin 1 carries board A's regulated rail, 12 V nominal and not below 10 V at this connector on any bank (`A-20b`, `A-20e`), above the coils' 9 V pull-in, so the `+12V` label stays true, this board has no bank-voltage work, and its coils never see a charging bank (#21, #33). Written on both silkscreens | Two boards that disagree on a locking connector's pin order is 12 V on a logic pin, with a connector that cannot be plugged the other way to fix it |
| **B-09b** | `FEEDBACK` is a bare dry contact to `GND`; **no pull-up exists on either board**. On board A rev A `GEN_STATUS` runs straight to PD2; rev B reaches its pin through a series resistor and clamp, still with no pull-down (`A-34`). Firmware enables that pin's internal pull-up, and treats *high* as "not both closed" | With the pull-up off, an unplugged Board B leaves PD2 floating, and a floating input reads whatever noise is nearest, which can be "both relays closed" on a board that is not there |
| **B-10** | Seven test pads on the PCB (`TP_RUN`, `TP_KICK`, `TP_WD_OK`, `TP_K1_LOW`, `TP_K2_LOW`, `TP_GEN_A`, `TP_GEN_B`), Ø 1.6 mm top copper, placed as board pads by the layout DSL because the schematic has no test-point part; revision B adds `TP_RUN_L` on the latch's Q | Bring-up step 7 is proven at the oscilloscope: stop the kick, watch `WD_OK` fall, watch the contact open. A proof nobody can probe is an assertion |
| **B-11** | Two layers, no impedance work, routed in-house | Nothing on this board has a trace whose impedance matters; paying the layout service would buy the wrong thing |
| **B-12** | Footprint reserved, unpopulated, for a 3-wire (momentary START/STOP) stage driven from `RUN`'s edges. A V2 of *this* board, never a change to Board A or the firmware | The RV and Yamaha market is 3-wire; supporting it must not reopen a proven safety chain |
| **B-13** | Contact traces **1.0 mm** wide, by the `contactTrack` DRC preset. A 1 A-class trace for a few-milliamp contact, because it is the surge path. Rev A measured: 1.0 mm throughout, nearest logic copper 1.92 mm | A thin trace in the surge path is a fuse nobody specified |
| **B-14** | The two relays are not one part failing one way: two drivers and two sources (B-01), rotated 90° to each other. **Accepted deviation on rev A:** they sit corner to corner, bodies 0.3 mm apart, not "physically separated" as the layout brief first asked. On one 80 × 55 board, 20 mm does not decouple heat, vibration, or a surge that reaches both through the pair they share; B-01's two sources do | Series redundancy that fails common-mode is not redundancy |
| **B-15** | U2, C3, R3, C4 and Q1 in one cluster, the `watchdog` placement block: C3 3.6 mm and R3 4.1 mm from their U2 pins, C4 on pin 16, U2 16 mm from K1 | This circuit's job is to be right when the MCU is wrong; its timing node does not share a corner with anything else |
| **B-16** | Flyback diode within 5 mm of its coil pins: D4 4.1 mm from K1.16, D5 4.1 mm from K2.16 | A long flyback loop rings the 12 V rail on every coil release |
| **B-17** | The coil return is the plane, never a trace under U2 | A 42 mA coil switching through a shared return trace is a nudge on a timing node |
| **B-18** | Each chain enters a pole at its **common** (4 for pole 1, 13 for pole 2) and leaves at its **normally open** terminal (8, 9); NC (6, 11) stays unconnected. The relay symbol's pin names are checked against Omron's terminal drawing (K046-E1, bottom view) before fabrication | Revision A ran both chains from NC to NO with the commons unconnected, so neither the contact nor `FEEDBACK` could ever close, whatever the coils did, and five boards needed four solder links each (#7, #44). A symbol whose pins are named wrong passes every connectivity check |
| **B-19** | Relay B's coil is driven by **`RUN` sampled on each `KICK` rising edge**: a D flip-flop (U3) with `RUN` on D and `KICK` on the clock, cleared at power-up by an RC on its clear input that outlasts the 3.3 V rail's rise. `RUN` reaches no relay coil directly and does not reset the monostable | Revision A opened the contact on every controller reset: PD0 stops driving, R1 pulls `RUN` low, Q2 opens and the monostable clears within milliseconds, so a watchdog reset stopped the generator and the firmware hot-restarted it seconds later (#18). Sampling `RUN` on the kick keeps a deliberate stop within one kick and rides through a silent controller only; a delay on `RUN` would have delayed the stop as well |
| **B-20** | The monostable's window is **15 s**, and it alone bounds a silent controller: both lines quiet, a cut cable, a hung controller that kicks no more, each opens the contact at the window. The window is budgeted: board A's watchdog timeout, 8 s nominal and up to 8.8 s from the ±10 % LSI, plus a 3 s allowance for reset-to-first-kick that the controller firmware owns as a requirement, plus margin; the measured window is written on the schematic | Fifteen seconds of a generator running with no controller is harmless; the run that empties the tank is hours. A window under the watchdog plus boot means the ride-through never completes and every reset still stops the engine (#18). The latch of B-19 never holds anything the monostable does not bound |
| **B-21** | Behaviour, as the bench proves it: `RUN` high and kicking, contact closed. `RUN` low while kicking, the deliberate stop, opens within one kick. Both lines quiet, as in a controller reset or a pulled cable, holds the contact up to the window, then opens. Kicks stop with `RUN` high, opens at the window. Supply lost, opens at once. Power-up or plug-in with `RUN` already high closes at the first kick, never before it. Board A's firmware keeps kicking with `RUN` low while stopped and decides within the window after a reset (#18) | A table the bench runs against, so the ride-through is proven case by case rather than argued (bring-up steps 2, 4, 5 and 7 to 11) |

## What the bench proves on the first boards (bring-up step 7)

No breadboard stage: a breadboard proves a proxy (bench relay modules
that are not the G5V-2, a SOIC on an adapter, jumpers that fall out), and a
five-board order costs less than the afternoon. The proof runs on the real
board, with the Nucleo (or Board A) driving `RUN` and `KICK` and a meter
across CN10. A finding becomes a simulator fault, then a revision:

1. `RUN` high, kicks at 1 Hz → both relays close, contact closed, `FEEDBACK`
   low. Scope on `WD_OK` while the contact makes and breaks under the kit's
   own load: it must not move (B-04's pour deviation is accepted on that
   evidence and no other).
2. **Stop the kicks** → `WD_OK` falls after the window, ≈ 4.5 s on revision A
   and ≈ 15 s on revision B (write the measured value on the schematic),
   relay A opens, contact opens, `FEEDBACK` high, with `RUN` still high.
3. Resume kicks → relay A closes again with no other action.
4. `RUN` low while the kicks continue → relay B opens at the next kick, within
   one kick period (at once on revision A), whatever else happens.
5. Pull CN9 → contact opens at the window (at once on revision A), `FEEDBACK`
   reads open at Board A.
6. Hold relay A closed by hand (a welded contact) → `RUN` low still opens the
   pair through relay B; hold relay B → stopping the kick still opens it
   through relay A. Both held is the case the lockout switch and the alarm
   exist for.
7. A brief reset of the controller, both lines quiet for less than the window
   → the contact never opens (revision B; revision A opens at once, #18).
8. Both lines quiet for longer than the window → the contact opens at the
   window and `FEEDBACK` reads open.
9. Power board B up, or plug CN9 in, with `RUN` already high and kicks
   arriving → the contact closes at the first kick and never before it.
10. `KICK` held high, then held low, with `RUN` high → the contact opens at
    the window each time.
11. A brown-out of the 12 V on CN9 with the contact closed → both relays drop
    at once; on recovery the contact closes at the first kick with `RUN` high.
12. The window at room temperature, then with a 10 M resistor from `TIMING`
    to GND, then cold; and board A's reset-to-first-kick time against B-20's
    3 s allowance (B-07, #22).

Every one of these becomes a fault in the simulator before its fix, so the
bench proves a case the simulator already reproduces.

## Still open

- **The relay commons** — the five revision A boards keep their four links
  each, proven on 2026-09-17; revision B routes the chains through the commons
  (B-18). See the [bench logs](bench/2026-09-14.md).
- **The site's own input** — open-circuit voltage and short-circuit current on
  the GenStart 2-wire harness, a meter and a minute
  (the [controller design](https://docs.origin89.com/hardware/), "Still to confirm with GenStart").
  It confirms the relay choice for this site; the choice already covers the
  class. On revision B the open-circuit voltage also sizes each of B-06's two
  series parts.
- **Board A's reset-to-first-kick time** — B-20 allows it 3 s of the window,
  and the controller firmware has to meet that as a requirement, FRAM read
  included (origin89hq/firmware#3). The bench self-test's 60 s delay before its
  sequence is a test setting, not that figure. Measure it once the firmware
  resumes after a reset, on the revision B bench at the latest.
- **Box** — `enclosure/shoe.py`, the same family as the controller's:
  a flat plate carrying the board on four bosses (M3 inserts in a flat
  plate, which any insert press accepts), and a one-piece shoe over it held
  by the four #8 wall screws through columns in its rounded corners, the
  shape a Victron SmartSolar wears. 106 × 81 × 38 mm, the
  height set by the VH plug on CN9 and its cable bend. CN10's plug sits in
  a mouth under the right rim, CN9's cable leaves through a notch in the
  left wall. No lettering and no light pipes: LED1/LED2 show what each coil
  got, which is a bench question, answered with the shoe off. MJF PA12,
  gates green.
- **The −20 °C decision** — belongs to the behaviour, not to this board, and
  is still to be made.
