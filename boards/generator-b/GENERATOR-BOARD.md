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

---

## What it is, in one paragraph

Board A asks for the engine over CN9 with two logic lines: `RUN` (please run)
and `KICK` (I am alive, once a second). Board B closes a dry contact toward
the generator's 2-wire start input only while **both** are true, through two
relays in series driven by two different paths: relay B follows `RUN`
directly; relay A follows a retriggerable monostable that `KICK` keeps alive
and `RUN` low resets. No microcontroller, no firmware. A lost cable, a dead
controller, a stuck GPIO: each one opens at least one relay, by construction,
in a part that runs no code. `FEEDBACK` goes back to Board A through the
relays' second poles, so the controller learns what the contacts did, not
what it commanded.

## The schematic, block by block

| Block | Parts | What it does |
|---|---|---|
| **CN9 link** | CN9 `B5P-VH` · D1–D3 `SMAJ15A` · R1, R2 100 k | Five wires from Board A (`V12`, `GND`, `GEN_RUN_CMD`, `GEN_WDT_KICK`, `GEN_STATUS` on that side): `+12V`, `GND`, `RUN`, `KICK`, `FEEDBACK`. A TVS on the rail and on each logic line, and a 100 k pull-down on `RUN` and `KICK`; an unplugged cable reads *stop*, never floats |
| **3.3 V** | U1 `HT7533-1` · C1 100 n · C2 10 µ | The only rail the logic needs; 28 V-rated input so the 12 V bank's transients do not reach a 6 V part |
| **Watchdog** | U2 `74HC123D` · R3 1 M · C3 10 µ · C4 100 n | Monostable 1: `KICK` rising edge on 1B retriggers it, `RUN` on 1RD# holds it reset while low, Q on `WD_OK`. Pulse width ≈ 0.45 · R3 · C3 ≈ **4.5 s**. The output is a level, not a pulse: high while kicks keep coming, low a few seconds after they stop, high again at the next kick. Monostable 2 is parked (2A# high, 2B and 2RD# low) |
| **Relay A** | Q1 `AO3400A` · K1 `G5V-2-DC12` · D4 `1N4148W` · LED1 + R5 | Coil driven by `WD_OK`. Pole 1 (COM 6 → NO 8) is the first series contact; pole 2 (COM 11 → NO 9) is the first feedback contact |
| **Relay B** | Q2 `AO3400A` · K2 `G5V-2-DC12` · D5 `1N4148W` · LED2 + R6 | Coil driven by `RUN`. Pole 1 (COM 6 → NO 8) is the second series contact; pole 2 the second feedback contact, whose NO reaches `FEEDBACK` |
| **Output** | CN10 `KF2EDGR-5.08-2P` · F1 5 × 20 fuse holder · D6 `SMBJ30CA` | The 18/2 pair to the generator. Fuse on `GEN_A`, bidirectional 30 V TVS across the pair at the terminal |

Contact chain: `CN10.1 → F1 → K1 COM6/NO8 → K2 COM6/NO8 → CN10.2`. Feedback
chain: `GND → K1 COM11/NO9 → K2 COM11/NO9 → CN9.5`, so Board A (which pulls
`FEEDBACK` up) reads low only when both relays are physically closed. The
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
  input rating is the margin a 12 V bank with a charger on it deserves.
- **AO3400A** — 42 mA coil at 12 V against a 5.8 A part; the gate is happy
  at 3.3 V.

## Rules the layout keeps (B-nn)

Each rule names the failure it prevents, in the style of
[`LAYOUT-REQUIREMENTS.md`](../controller-a/LAYOUT-REQUIREMENTS.md). This is the only
`B-nn` list; that brief points here rather than keeping a copy that could
drift. B-13 to B-17 came across from it when the two were merged.

| ID | Rule | The failure |
|---|---|---|
| **B-01** | Two relays in series, **two drivers, two sources** (`WD_OK` and `RUN`). Never a shared gate net, never a shared driver | A single driver stuck on is one relay, and one welded relay runs the tank dry. The two-in-series claim is only true if nothing common can hold both |
| **B-02** | Relay A is driven only from the watchdog output; the kick line never reaches a relay coil directly | A `KICK` stuck high is the failure the monostable exists to catch; wiring it to a coil bypasses the catch |
| **B-03** | `RUN` and `KICK` each carry a pull-down to `GND` at the connector, and their TVS sits at CN9 before anything else | An unplugged or cut cable must read *open*, and a surge arriving on the link must be clamped before the 74HC123 sees it |
| **B-04** | The output pair (`GEN_A`, `GEN_B`, F1, D6, K1/K2 pole 1) is one physical region at CN10, separated from the logic region (CN9, U1, U2), and **no copper of any other net comes within 1.5 mm of contact copper**, a DRC spacing rule on the four contact nets, not a habit. **Accepted deviation on rev A:** the GND pour is continuous under the contact region and under the relays, held off the contact copper by that 1.5 mm rather than absent there. The pair is isolated from GND (the TVS sits across it, not to it), so what the pour adds is capacitance to a surge, which the clearance keeps small. Step 7 watches `WD_OK` while the contact makes and breaks for exactly this; rev B carries a copper keepout if it moves | The 60 ft pair is the dirtiest thing touching the design; an induced surge that crosses the board under the monostable is a surge under the safety timer |
| **B-05** | Fuse F1 is a 5 × 20 in a holder, rated below the generator kit's own fuse (5 A class → fit **2 A**), replaceable without a tool | A soldered fuse four hours from a road is a dead site; a fuse above the kit's makes the kit's fuse the one that blows, inside a box nobody opens |
| **B-06** | D6 is **bidirectional** and sits across CN10's pins, upstream of the fuse | The generator input's polarity is never guaranteed (most switch to negative, some carry B+); a unidirectional TVS conducts the wrong way on the wrong set |
| **B-07** | C3 (the timing capacitor) is a ≥ 25 V X7R with the DC-bias derating checked at 3.3 V, and the measured pulse width is written on the schematic after bring-up step 7. No electrolytic anywhere on the board | The watchdog delay is a safety timing; a part whose value nobody knows at −20 °C is a delay nobody knows |
| **B-08** | Every part industrial grade. **Accepted deviation:** the G5V-2 is rated −25 … +65 °C ambient, not −40 | The cabin freezing is the scenario the product exists for; −25 covers the cabin, not the porch. Recorded so a −40 relay is a one-line swap when one is found with the same contacts |
| **B-09** | CN9's pin order **is Board A's**: 1 `+12V`, 2 `GND`, 3 `RUN`, 4 `KICK`, 5 `FEEDBACK`. **Verified against `Controller / Schematic1`**: there CN9 is 1 `V12`, 2 `GND`, 3 `GEN_RUN_CMD` (PD0), 4 `GEN_WDT_KICK` (PD1), 5 `GEN_STATUS` (PD2). Written on both silkscreens | Two boards that disagree on a locking connector's pin order is 12 V on a logic pin, with a connector that cannot be plugged the other way to fix it |
| **B-09b** | `FEEDBACK` is a bare dry contact to `GND`; **no pull-up exists on either board**. Board A's `GEN_STATUS` runs straight to PD2. Firmware enables PD2's internal pull-up, and treats *high* as "not both closed" | With the pull-up off, an unplugged Board B leaves PD2 floating, and a floating input reads whatever noise is nearest, which can be "both relays closed" on a board that is not there |
| **B-10** | Seven test pads on the PCB (`TP_RUN`, `TP_KICK`, `TP_WD_OK`, `TP_K1_LOW`, `TP_K2_LOW`, `TP_GEN_A`, `TP_GEN_B`), Ø 1.6 mm top copper, placed as board pads by the layout DSL because the schematic has no test-point part | Bring-up step 7 is proven at the oscilloscope: stop the kick, watch `WD_OK` fall, watch the contact open. A proof nobody can probe is an assertion |
| **B-11** | Two layers, no impedance work, routed in-house | Nothing on this board has a trace whose impedance matters; paying the layout service would buy the wrong thing |
| **B-12** | Footprint reserved, unpopulated, for a 3-wire (momentary START/STOP) stage driven from `RUN`'s edges. A V2 of *this* board, never a change to Board A or the firmware | The RV and Yamaha market is 3-wire; supporting it must not reopen a proven safety chain |
| **B-13** | Contact traces **1.0 mm** wide, by the `contactTrack` DRC preset. A 1 A-class trace for a few-milliamp contact, because it is the surge path. Rev A measured: 1.0 mm throughout, nearest logic copper 1.92 mm | A thin trace in the surge path is a fuse nobody specified |
| **B-14** | The two relays are not one part failing one way: two drivers and two sources (B-01), rotated 90° to each other. **Accepted deviation on rev A:** they sit corner to corner, bodies 0.3 mm apart, not "physically separated" as the layout brief first asked. On one 80 × 55 board, 20 mm does not decouple heat, vibration, or a surge that reaches both through the pair they share; B-01's two sources do | Series redundancy that fails common-mode is not redundancy |
| **B-15** | U2, C3, R3, C4 and Q1 in one cluster, the `watchdog` placement block: C3 3.6 mm and R3 4.1 mm from their U2 pins, C4 on pin 16, U2 16 mm from K1 | This circuit's job is to be right when the MCU is wrong; its timing node does not share a corner with anything else |
| **B-16** | Flyback diode within 5 mm of its coil pins: D4 4.1 mm from K1.16, D5 4.1 mm from K2.16 | A long flyback loop rings the 12 V rail on every coil release |
| **B-17** | The coil return is the plane, never a trace under U2 | A 42 mA coil switching through a shared return trace is a nudge on a timing node |

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
2. **Stop the kicks** → `WD_OK` falls after ≈ 4.5 s (write the measured
   value on the schematic), relay A opens, contact opens, `FEEDBACK` high,
   with `RUN` still high.
3. Resume kicks → relay A closes again with no other action.
4. `RUN` low → both relays open at once, whatever the kicks do.
5. Pull CN9 → contact opens, `FEEDBACK` reads open at Board A.
6. Hold relay A closed by hand (a welded contact) → `RUN` low still opens the
   pair through relay B; hold relay B → stopping the kick still opens it
   through relay A. Both held is the case the lockout switch and the alarm
   exist for.
7. A brief reset of the controller (under 4.5 s) → the contact never opens.

Every one of these becomes a fault in the simulator before its fix, so the
bench proves a case the simulator already reproduces.

## Still open

- **The site's own input** — open-circuit voltage and short-circuit current on
  the GenStart 2-wire harness, a meter and a minute
  (the [controller design](https://docs.origin89.com/hardware/), "Still to confirm with GenStart").
  It confirms the relay choice for this site; the choice already covers the
  class.
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
