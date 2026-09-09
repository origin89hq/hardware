# Origin89 — PCB layout requirements

For an external layout house. This document says what the boards must satisfy and
**why**, because a rule with no reason attached is the first thing a layout tool
optimises away.

The reasoning behind the circuits is in the [controller design](https://docs.origin89.com/hardware/).
This file does not repeat it; it extracts only what constrains placement and
routing.

Requirements are numbered `A-nn` for the controller; the generator board's
`B-nn` live in [GENERATOR-BOARD.md](../generator-b/GENERATOR-BOARD.md) (§4). Reply against
the numbers. **Any requirement that cannot be met must be
raised before routing starts, not reported afterwards.** Several trade against
each other, and we would rather choose than be told.

---

## 1. Two boards, and why the split exists

A controller that starts a generator at an unattended site four hours from a
road. It sits in a 3D-printed plastic enclosure in an electrical room, beside an inverter,
next to a running generator, through a Canadian winter. Nobody is watching it
fail.

| | Board | Carries |
|---|---|---|
| **A** | **Controller** | STM32G0B1, ESP32-C6 module, three RS-485 channels, CAN, two VE.Direct ports, 1-Wire, FRAM, NOR, power |
| **B** | **Generator** | Two series relays, the hardware run-enable watchdog, the field wiring to the genset |

**The split is a safety decision, not a packaging one.** The run-enable watchdog
lives on board B with the relays. The link between the boards carries only
"please run", so every way it can fail (connector backed out, cable pulled,
cold joint at −30 °C) stops the watchdog being fed and **opens the contact**. A
lost link is the safe state by construction. On one board the identical fault is
a cracked joint that is silent.

The second reason is surge. 60 ft of 18/2 runs to a generator in the garage and
is the dirtiest thing touching this design. On its own board that energy never
enters the board carrying the MCU, three RS-485 channels and CAN.

---

## 2. Deliverables, both boards

| | |
|---|---|
| Source document | EasyEDA Pro project, editable |
| Gerber | RS-274X, complete |
| BOM | With LCSC part numbers |
| Pick & place | Board A, top and bottom |
| Mechanical drawing | DXF: outline, mounting holes, connector positions |
| Fabrication drawing | PDF, with stackup and **achieved** impedance |
| 3D model | STEP |
| NC drill | Excellon, plated/non-plated separated |
| Assembly drawing | PDF, top and bottom, with designators |
| Netlist | IPC-D-356A, for bare-board electrical test |
| Revision block | Document revision and date on the fabrication drawing, matching the schematic and BOM revision delivered |

We want **all** of these, not the two ticked by default on the quote form. The
DXF and STEP are what let an enclosure be chosen without re-measuring, and the
fabrication PDF is the only place achieved impedance gets written down.

---

## 3. Board A — controller

### Mechanical and stackup

| ID | Requirement | Why |
|---|---|---|
| **A-01** | Outline **100 × 125 mm**, 1.6 mm FR-4 | **The board is the master dimension.** The enclosure is 3D printed around the finished board, so the board is sized for what the layout needs and the box follows. It was 100 × 100 (the cheapest fab tier) until the field band ran out of height: connectors at the edge, bus lamps pinned above them and the MCU keep-out above that left **~15 mm of usable band**, while each bus needs a TVS, a transceiver, a jumper and two bias resistors, about **13.4 mm of bodies before clearances**. Past that point every constraint added there only moved the violation somewhere else; one placement bought unambiguous termination jumpers by pushing the RS485-3 surge clamp **17.7 mm** from its own connector, which is a worse board. The extra 25 mm is all field band. One price tier, not a redesign |
| **A-02** | Four **M3** holes, 3.2 mm finished drill, **3.2 mm keep-out radius** measured from the hole centre and applying to **all copper layers and both silkscreens**, centres **4 mm** in from each board edge (**±46, ±58.5 mm** on the 100 × 125 outline) | Nylon standoffs, not brass. Brass under a board with 24 AWG field wiring nearby is a short waiting to happen |
| **A-03** | Mounting holes on **no net**: no plane, no stitching | The enclosure is **plastic**, so there is no chassis to bond to and nothing a standoff could usefully connect. Site earth exists (off-grid systems bond DC-negative to a rod) but that bond is made **once, elsewhere in the system**. A second bond here would create a ground loop through 60 ft of field wiring, which is an antenna for exactly the surge this board is protected against |
| **A-04** | **4 layer.** L1 signal, **L2 solid ground**, L3 power, L4 signal | L2 must be an uninterrupted reference under every differential pair |
| **A-05** | **Route every controlled-impedance pair on L1 only**, and allow **no split, slot or void in the Layer 2 ground plane beneath any differential pair or either crystal**. A pair routed on L4 references the *split power* plane L3 and is not controlled impedance | A return path that detours around a split radiates, and turns a working bench board into an intermittent field board. If unavoidable, ask. Do not route across it |
| **A-06** | All **field** wiring on one edge: 12 V in, the three RS-485 buses, CAN, 1-Wire, the selector. One gland plate, one loom, one direction of pull | Measured: 79.4 mm of connectors against 96 mm of usable edge, so it fits. It only fits because the six signal connectors are **3.5 mm pitch**; at 5.08 mm they need 103.4 mm and the requirement becomes unbuildable at this board size |
| **A-06b** | The short in-enclosure leads (VE.Direct `CN6`/`CN7`, the board-to-board plug `CN9` and the second 1-Wire landing `CN11`) go on the **right** edge, and must not cross the field edge | These are patch leads to gear in the same box, not part of the field loom. Putting them on the field edge would push it past 130 mm and force a larger board for no benefit |
| **A-06c** | The **left edge is the sense and control column**: selector (`CN10`), RTC backup cell (`CN14`), start-battery sense (`CN12`), SWD (`H1`), tank sender (`CN13`), top to bottom | **The bottom edge is full.** Six bus connectors use 79.4 mm of the 85.6 mm of clear edge between the corner mounting-hole keep-outs; a seventh does not fit. That number is measured. Splitting heavy comms/power one way and thin sense wiring the other is also how a panel gets wired |
| **A-07** | ENIG lead-free, green mask, white silkscreen | Flat pads for the LQFP-64 at 0.5 mm pitch; legible to somebody with a headlamp |

### Impedance

| ID | Net | Target |
|---|---|---|
| **A-08** | `CANH`/`CANL` | **120 Ω** differential ±10 %. ISO 11898 interconnect is a nominally 120 Ω cable terminated 120 Ω at each end, and `R13` on this board is 120 Ω; a 100 Ω trace target would contradict both |
| **A-09** | `RS485_1/2/3_A` / `_B` | **120 Ω** differential ±10 %, or as close as the stackup allows; **report the achieved figure** |
| **A-10** | Both pairs | Coupled the whole run, length-matched within 5 mm, no stubs, and on L1 only per `A-05` |

### Placement

| ID | Requirement | Why |
|---|---|---|
| **A-11** | **TVS at the connector**, before the signal reaches anything else | A TVS downstream of the part it protects protects nothing. The surge has already been through the transceiver |
| **A-11c** | **Verify every 3-pin SOT-23 protection device's land pattern against its datasheet before fabrication.** `D4`/`D5`/`D6` (SM712) and `D7` (PESD1CAN) all have the **common on pin 3**, not the middle pin | Neither library symbol names its pins, so a wrong assumption produces a netlist that passes every connectivity check and protects nothing. Both parts were initially wired with pin 2 to ground. Found by reading the electrical tables, which reference every parameter "pin 1 to 3 and 2 to 3" |
| **A-11b** | **Every field TVS returns to `CN1`'s ground pin by a short, wide, low-inductance path**: multiple stitching vias at each TVS ground pad, and the return must **not** traverse the Layer 2 ground beneath `U7`, either crystal, or any sense divider | "At the connector" alone does not say where the energy *goes*. The enclosure is plastic and there is no chassis, so surge leaves only via the 12 V negative to the bank, which is bonded to earth once elsewhere in the system. A TVS that clamps correctly but dumps its current through the plane under the MCU has moved the problem |
| **A-12** | Each of the **four** buses (RS-485 ×3 and CAN) is **one tight cluster**: connector + TVS + transceiver + termination resistor + termination jumper + activity LED. **≤ 14 mm pad to pad**, connector A-pin to transceiver A-pin. This one is stated pad-to-pad, not centre-to-centre like the rest of the document, because the number *is* the A/B trace length. **Do not pool parts by type** | A parts-bin layout is tidy and electrically wrong. **Delivered at ≤ 14 mm pad-to-pad on all four buses** (14.2–16.7 mm centre-to-centre, the spread being connector and SOIC body length). 11 mm was attempted to bring the centre-to-centre figure under 15 and the solver could not hold it. Four hard pairs came back at 11.2–13.8 mm, so the limit is set where it actually places. The surge clamp is the part that must be at the terminal: **`D4`–`D7` sit 5.4–8.7 mm from their connectors** |
| **A-13** | Each 120 Ω terminator (`R7`, `R9`, `R11`, `R13`) is in series with a **2-pin header and shunt** (`JP1`–`JP4`). Place each header at its own bus cluster, **reachable and readable with the board installed**, silkscreened with the bus name and which state is terminated. Default shipped state: **fitted** | Whether this board terminates depends on where it sits on the bus, and that is decided by whoever pulls the wire at install, not at assembly. A shunt is finger-operable and puts no sliding contact in the bus path, unlike a DIP switch, whose intermittent contact would make termination flicker. **Correction to an earlier draft:** a third 120 Ω terminator takes the parallel load from 60 Ω to 40 Ω. It does not "halve the swing", it loads the driver by half again |
| **A-13b** | Fail-safe bias `R49`/`R50`, `R51`/`R52`, `R53`/`R54` (560 Ω) placed **inside their own bus cluster**, close to the transceiver, not scattered to the power area | **The MAX13487E datasheet makes these mandatory:** *"The pullup and pulldown resistors on the A and B lines are required for proper operation of the device… they function to hold the bus in the high state (A−B > 200 mV) following a low-to-high transition."* The AutoDirection state machine takes the current A−B state as an input, so without bias its direction control runs on an undefined input. The receiver threshold is ±200 mV, so an unbiased idle bus is indeterminate. 560 Ω gives 254 mV idle with both ends terminated (60 Ω), 485 mV with one |
| **A-14** | `LED1`–`LED3` (RS-485) and `LED6` (CAN) visible from the connector edge, each labelled with its bus | They sit on the receiver output, so they show **RX activity**, which is the useful signal: it means something *else* on the bus is talking. Somebody at the panel learns the bus is alive without a laptop. Delivered aligned to within 0.1 mm of their own connector in x |
| **A-15** | **`ESP32-C6-WROOM-1-N8`** (Espressif, datasheet v1.x; confirm revision against the shipped part). **No copper on ANY layer** under the module's declared antenna keep-out, antenna at the board edge. Espressif additionally require **≥ 15 mm clearance from the antenna to any material inside the finished enclosure**, and end-product range testing; a copper void alone is not sufficient | A module antenna over a ground plane is a module that does not connect, discovered after fabrication. The 15 mm is an enclosure constraint, so it lands on the 3D-printed box as much as on the PCB |
| **A-16** | Keep the antenna end away from both switching regulators | |
| **A-17** | `X1` within **5 mm** of `U7` pins 10/11 (`OSC_IN`/`OSC_OUT`); `C29`/`C30` within 3 mm either side; **both cap grounds joined to each other first, then one short run to pin 9** (`VSS`, the adjacent pin); no track under `X1` on any layer, unbroken ground on L2 beneath; **≥ 10 mm from the switching inductors `L1`/`L2` and the switch nodes `SW_5V`/`SW_3V3`** | The link runs at 921600 and the clock is what makes that rate honest. **Met in the delivered placement, centre-to-centre: 16.6 mm from inductor `L1`, 49.6 mm from inductor `L2`.** All distances in this document are centre-to-centre unless stated. It took a placement keep-out over the MCU area to get there. Clearance rules alone lost three times to the `V3V3` ratsnest, which drags the 3.3 V buck centre-board because that rail fans out to the MCU, ESP32, FRAM and NOR. **A keep-out anchored at the board centre is not by itself enough, and believing it was cost two more respins of the placement.** The region is anchored at the centre but it does not *hold* the MCU there. The clock block is allowed anywhere inside it, including hard against its own boundary, with a converter legally sitting immediately on the other side. `L1` came to rest **4.49 mm** from `X1` with a 50 mm-wide exclusion nominally protecting it. The rule holds because `U7` is pinned to the board centre. The crystal is tied within 7 mm of `U7`, so it cannot travel more than ~12 mm out, and the 25 mm half-width then guarantees the separation no matter what else moves. **Do not undo it while routing.** Nothing in the netlist or the Gerbers records that this separation is deliberate, so moving `L2` inboard to shorten a trace kills the requirement silently. The victim is a high-impedance node swinging a few hundred mV; the aggressor slams 12 V in nanoseconds at 570 kHz a few cm away. The cost is a pulled clock rather than a dead board. A UART has no clock line, so at 921600 the two ends must agree within a couple of percent across a whole byte. It works on a bench at 20 °C and drops frames in January. If 10 mm from both inductors is ever impossible, prioritise distance from `L2`: it shares a rail with the MCU, so its noise has the shorter path into the ground the oscillator references |
| **A-18** | For **each** TPS54331 (`U1` with `C3`/`L1`/`D3`, `U2` with `C31`/`L2`/`D8`), per the TI datasheet layout section: (a) minimise the **input-capacitor → VIN → GND → catch-diode** loop area (the high di/dt loop); (b) place the catch diode and the inductor **immediately at the PH pin**; (c) keep **PH/switch-node copper as small as the current allows** (it is the dv/dt aggressor, not a heatsink); (d) route neither loop's return under a bus pair, either crystal, or any sense divider | "Input cap, inductor, diode in a tight loop" in an earlier draft was electrically imprecise. The inductor is not in the fast loop, the catch diode is |
| **A-19** | `C24`/`C25` within 5 mm of the ESP32 supply pin | It draws 382 mA in bursts |
| **A-26** | **1-Wire protection in order along the path**: `F2` upstream on `V3V3`; `D9` (ESD clamp) **at `CN8`**, ahead of anything else; `R41` (100 Ω) between the field node and `PC4` | Same rule as `A-11` and for the same reason. The clamp behind the series resistor protects the resistor, not the MCU. These probes hang outdoors and in a battery box on cable nobody will inspect again |
| **A-27** | `R46` (150 Ω, 4-20 mA sense) **at `CN13`**, its return short and not shared with the switching loops | That resistor *is* the measurement. Loop return current wandering through the board becomes a fuel reading that drifts with load |
| **A-28** | `X2` (32.768 kHz) and `C41`/`C42` tight to `U7` pins 4/5, guarded, unbroken ground beneath, **≥ 10 mm from the switching inductors `L1`/`L2` and the switch nodes `SW_5V`/`SW_3V3`** | Same aggressor as `A-17`, and an LSE is *more* fragile than the HSE: lower amplitude, higher impedance, and it has to keep time for years, not just clock a UART |
| **A-29** | `R44`/`R45` with `C39` at `CN12`, and `R42`/`R43` with `C38` beside them off `V12`, stay **in the left-edge sense column** with `R46`/`C40` (`A-27`); each divider's ground returns to the plane at the divider, and every `AIN_*` trace runs on L1 over unbroken L2 ground, **never through or over either switching loop**. `A-11b` and `A-18`(d) already keep aggressors away from the dividers, and this extends the same protection to the traces, which now cross the board | An earlier draft wanted these dividers at the ADC pins, and the placement that went to routing has them at the sense column instead. Accepted rather than reworked, for two reasons: the left edge is where the sense wiring lands (`A-06c`), and the divided node is not bare; 100 nF across the bottom resistor holds it low-impedance above ~175 Hz (9.1 kΩ Thevenin) while the channels are read at about 1 Hz. What that capacitor cannot do is shunt pickup collected along the trace *after* it, so the trace route is now the requirement: a divider is still a high-impedance node, noise on it is indistinguishable from a real change in battery voltage, and this board decides whether to start a generator on that number |
| **A-30** | The compensation network sits **on the COMP pin**: `R4`/`C9`/`C45` at `U1` pin 6, `R38`/`C37`/`C46` at `U2` pin 6, with `C45`/`C46` the closest of the three to the pin, and their ground returned to the IC's own ground pin rather than into the switching loop | `COMP` is the error amplifier's output and the highest-impedance node on either converter. `C45`/`C46` (100 pF) exist to shunt switching pickup to ground **at the pin**; on the far end of a 20 mm trace they filter nothing and the trace itself becomes the antenna. The values were recomputed against the real filter (see the compensation entry in the [controller design](https://docs.origin89.com/hardware/)), and a loop with 74° of phase margin on paper is still a ringing rail if this node picks up the switch node |
| **A-32** | Each termination jumper sits **unambiguously above its own connector** (`JP1`↔`CN2`, `JP2`↔`CN3`, `JP3`↔`CN4`, `JP4`↔`CN5`), closer to it than to any other connector by a clear margin, and **each is silkscreened with the bus name, not just its designator** (`TERM RS485-1`, not `JP1`) | The first placement put the whole jumper row about 7 mm left of where it belonged, which left each one roughly equidistant between two buses: `JP2` measured 11.1 mm to `CN2` and 11.8 mm to `CN3`, so three of the four were physically nearest a bus they do not terminate, and `JP1`'s nearest connector was `CN1`, the 12 V inlet. Somebody terminating the EPEver bus reaches for the jumper above `CN2`, fits `JP2`, and terminates the PZEM DC bus instead. **Nothing reports this.** Both buses still talk on a bench; the unterminated one starts throwing CRC errors over 60 ft on a cold night, which is a four-hour drive to diagnose. The LEDs were already immune because they are pinned to their connector's centreline (`A-14`); the jumpers were only softly attracted, and soft lost |
| **A-31** | `C44` (1 µF) within 3 mm of `U7` pin 7 (`VREF+`) | `VREF+` is the ADC's reference, and on this package it is a separate pin from `VDD/VDDA` (pin 8) even though both are on `V3V3`. Three of those ADC channels (house bank, start bank, tank level) are inputs to the decision to start a generator. Reference noise does not look like noise in the result; it looks like the battery moved |

### Power

| ID | Net | V | A | Note |
|---|---|---|---|---|
| **A-20** | `V_IN_RAW` / `V12` | 12 | 2.0 | Reverse-polarity protection and TVS **at** the input connector; trace ≥ 1.5 mm. A 12 V bank wired by hand in the field will be reversed once |
| **A-21** | `V5` | 5 | 1.5 | RS-485 and CAN transceivers |
| **A-22** | `V3V3` | 3.3 | 0.8 | Logic + ESP32. Size for burst, not average |
| **A-23** | `V3V3_ESP` | 3.3 | 0.5 | Switched sub-rail, gated by the MCU so a wedged comms processor is recoverable without a drive |
| **A-24** | `OW_VCC` | 3.3 | 0.1 | **Leaves the board on field cable** to DS18B20 probes outdoors and in the battery box. Fed through `F2`, a 100 mA PTC. Without it a chewed or water-ingressed probe cable shorts 3.3 V and takes the whole controller down: a $3 sensor killing the machine |
| **A-25** | `VBAT_RTC` | 3.3 | <1 mA | RTC backup, OR-ed from `V3V3` and an external cell (`CN14`) through `D11`. External to the *board*, not to the box: the cell and its holder live inside the enclosure, so `CN14` is not field wiring and carries no label on the port strips. Keeps the event log's timeline across a power loss |

---

## 4. Board B — generator

Drawn and routed in-house, so this brief never went out for it. Its rules are
numbered `B-nn` in [GENERATOR-BOARD.md](../generator-b/GENERATOR-BOARD.md), beside the
schematic they constrain and the bench proof they are checked by, and that
list is the only one. A second copy here would be two documents free to
disagree, which they had already begun to do. What this file keeps about
Board B is what a layout house would need: the split in §1, the deliverables
in §2, and items 5 and 6 of §5.

---

## 5. Open: ours to close, not yours

| | What | Status |
|---|---|---|
| 1 | ~~**Enclosure and board envelope**~~ | **Closed by reversing it.** The enclosure will be 3D printed around the finished board, so the board no longer waits on a box; the box waits on the board. This makes the **STEP and DXF deliverables in §2 load-bearing**: they are the model the enclosure is built from. Printed in **MJF PA12** (nylon, dyed black), not FDM: it sits in an electrical room beside an inverter and a generator, PLA softens around 60 °C and PETG creeps under load, and nylon does neither. The box is `enclosure/shoe.py`, one script for both boards, gated against these connector envelopes |
| 2 | ~~**MCU pin assignment**~~ | **Closed.** Every assignment checked against `stm32-metapac 21.0.0`, machine-extracted from ST's database by `stm32-data` and already a dependency of this firmware. USART1 CTS moved to **PB4/AF4**, so the ESP32 link sits entirely on PB6/PB7/PB4/PB3 and the PA11/PA12 dual-identity pads are untouched. FDCAN1 confirmed on PB9/PB8 at AF3. No two peripherals contend for a pin. See the [controller design](https://docs.origin89.com/hardware/), *Before any board is laid out* |
| 3 | ~~**5 V-tolerant RX pins**~~ | **Closed.** MAX13487E is a 5 V part, so `RO` drives 5 V logic into the three RS-485 RX pins. All three are `FT` per DS13560 §3.4: `PA3` **FT_ea**, `PB11` **FT_fa**, `PA1` **FT_ea**. **Note for anyone moving a pin later: `PA4` is `TT_a` and `PA5` is `TT_ea`, 3.3 V only.** They carry SPI to the NOR, which is a 3.3 V part, so they are safe here. Put a 5 V signal on either and the board is scrap |
| 4 | ~~**Relay contact material**~~ | **Closed for the class, still to confirm for the site.** A sweep of the remote-start section of every 2-wire generator controller's manual found each input is switched-to-negative at a few milliamps behind a pull-up (the dry-circuit range where plain silver contacts fail to make through their oxide film), so Board B carries the G5V-2's gold-clad bifurcated contacts, specified from 10 µA. A meter across the GenStart input (open-circuit V, short-circuit I) still confirms this site sits inside that class; it no longer decides the part |
| 5 | **How the 60 ft run is routed** | Buried, aerial or conduit. Aerial means surge protection sized for it; buried means rodents. Decides how hard GENERATOR-BOARD.md's `B-06` (the TVS at CN10) has to be |
| 6 | **Does the garage share the cabin's earthing system?** | Attached and on the same panel means one ground and nothing to do. A detached garage with its own rod means the pair bridges two earthing systems |
| 7 | ~~**RTC accuracy**~~ | **Closed.** `X2` (32.768 kHz, ±20 ppm, −40…+85 °C) is fitted with `C41`/`C42`, and `D11` ORs `V3V3` with an external cell on `CN14` into `VBAT`. ±20 ppm is ~1.7 s/day; the ESP32 can NTP-discipline it whenever Wi-Fi is up. A ±2 ppm TCXO RTC was considered and rejected at 35× the price for accuracy nothing here consumes |

**No isolated RS-485 channel is fitted, deliberately.** The criterion is two
separate earthing systems, not distance. At site A the generator's 120 V output
already runs to the cabin, so proof of running is measured at the panel and
**nothing but the dry contact pair crosses to the garage**. An ADM2582E and an
8 mm barrier would cost board area for a bus with no consumer. Item 6 above is
what would reopen this.

---

## 6. Acceptance

A layout is accepted when:

- Every `A-nn` and `B-nn` is met, or was raised and a decision recorded.
- DRC clean at the fab's stated capability, with the rule set delivered.
- The fabrication drawing shows **achieved** impedance for `A-08` and `A-09`, not target.
- A ground-plane view of L2 shows no split under any differential pair (`A-05`).
- The antenna keep-out of `A-15` is visible in the delivered Gerbers, checked
  layer by layer rather than asserted.

The last two are the ones to check by looking, not by trusting the report. Both
are failures that pass DRC.
