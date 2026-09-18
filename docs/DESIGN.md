# Circuit design

Why the circuits are what they are: the generator interface, the power path,
the buses, the parts, and what was checked before any board was laid out. The
rules a layout has to keep are elsewhere and own the values:
[`LAYOUT-REQUIREMENTS.md`](../boards/controller-a/LAYOUT-REQUIREMENTS.md)
(`A-nn`) for board A and
[`GENERATOR-BOARD.md`](../boards/generator-b/GENERATOR-BOARD.md) (`B-nn`) for
board B, each stating what revision A was built with beside a rule revision B
changed. Where a value here has moved since revision A, the rule wins and this
document says so. The system side, what the controller decides and why the
comms processor may not, is the firmware's
[`ARCHITECTURE.md`](https://github.com/origin89hq/firmware/blob/main/docs/ARCHITECTURE.md);
this document does not repeat it.

It grew out of origin89's `CONTROLLER-V1.md` (2026-08-03), split three ways on
[origin89hq/origin89#16](https://github.com/origin89hq/origin89/issues/16): the
circuit reasoning came here (#50), the system design went to the firmware, and
the plan became origin89hq/firmware#3 and its milestones.

## Two boards, and why the split exists

The run-enable watchdog lives on board B with the relays it drops. That is what
makes the split a safety decision rather than a packaging one: the plug between
the boards carries only *please run*, so every way it can fail, a connector
backed out, a cable pulled, a cold joint at −30 °C, stops the kick arriving and
opens the contact. A lost link is the safe state by construction. Put the
watchdog on the controller instead and the same fault is a cracked joint that
nothing announces.

The second reason is dirt. The 60 ft pair to the generator is the filthiest
thing touching this design, and on its own board that energy never reaches the
one carrying the MCU, three RS-485 channels and CAN. `LAYOUT-REQUIREMENTS.md`
§1 states the same split for a layout house.

## The generator interface

### A maintained contact, and a kit that owns the engine

Site A's generator carries a wireless and 2-wire remote-start kit. The kit
maker's own answer, when asked:

> "You can touch the 2 terminals in that connector together with a screwdriver.
> When connection is made between these 2 terminals the generator should crank
> and start. When you release the connection the generator will shut off."

**A maintained contact, not a pulse. Closed is running, open is stopped.** The
kit owns the engine switch, the fuel valve, the choke, the crank sequence and
the retries; the controller owns deciding. So the generator interface is one
dry contact out and one AC meter in, not six inputs and four outputs, and there
is no generator module in V1: a dry contact over 60 ft has no voltage drop and
no comms link to lose. A module becomes a product feature when a run is long
enough that pulling twelve conductors beats pulling one shielded pair, or when
a site has a genset without a start kit. A genset with a controller panel of
its own changes that site from *drive a contact* to *talk to a controller over
Modbus*, which the buses below already carry.

### The electrical design

```text
   board A, controller          │          board B, generator
                                │
STM32 ── RUN ───────────────────┼──► relay B    rev A: RUN drives the coil
      ── KICK ──────────────────┼──► monostable ──► relay A
      ◄─ FEEDBACK ──────────────┤◄── the relays' second poles, in series
         12 V · 0 V ────────────┤
                       CN9, JST VH
                                    relay A ── relay B ── F1 ── CN10 ── 18/2 ── [lockout] ── 2-wire input
```

**Two relays in series, independently driven.** A maintained contact means a
welded relay runs the generator until the tank is empty. One weld no longer
does that. Both welding is still possible, which is what the alarm and the
lockout switch are for. The two-in-series claim holds only if nothing common
can hold both, so the two coils have two drivers from two sources and never a
shared gate net (B-01), and the relays are rotated to each other so a surge
through the pair they share does not find them the same way (B-14).

**A run-enable watchdog in hardware.** The contact stays closed only while
firmware keeps kicking a retriggerable monostable, a 74HC123 whose Q is the
level the relay wants. Firmware that dies stops kicking, the contact opens
after the window, and the generator stops: dead controller means stopped
engine, guaranteed by a part that runs no code. The kick line never reaches a
coil directly, because a `KICK` stuck high is exactly the failure the
monostable exists to catch (B-02). On revision A the window is about 4.5 s by
design and 4.3 s on the bench, inside the 3.0–6.5 s the contract allows and
drifting with board temperature, so the firmware measures what it sees and
never assumes (#22, and the
[bench log of 2026-09-17](../boards/generator-b/bench/2026-09-17.md)).

**The claim the first design made, and revision A did not keep.** The design
said a brief controller reset, a watchdog or a brown-out, would re-kick before
the window expired and the running generator would never notice. Revision A
does the opposite: `RUN` drives relay B's coil directly and holds the
monostable in reset while low, so the moment the controller's pin stops
driving, board B's pull-down reads *stop*, relay B opens and the monostable
clears, and every controller reset opened the contact at once (#18). Revision
B keeps the promise with a latch rather than a delay: relay B follows `RUN`
*sampled on each `KICK` edge*, so a deliberate stop lands within one kick and
only a silent controller rides through, bounded by a window widened to 15 s
(B-19, B-20). The window is budgeted: the controller's 8 s
watchdog at the LSI's worst case, 8.8 s, plus 3 s for reset-to-first-kick,
which the firmware owes as a requirement, plus margin (#51). Revision B is
drawn and not yet proven; B-21 is the table the bench runs against.

**A lockout switch at the generator end.** Open means the software is
physically disconnected regardless of what it believes. It is the service
lockout: cut it before touching the engine and nothing remote can crank it
while your hands are in there. The kit manual's own wiring diagram puts
an emergency stop switch in series in the junction box, which is this switch.
It is a different thing from the auto/off/manual selector at the controller,
which is an operator override; the firmware's `ARCHITECTURE.md` has both.

**Contacts for a dry circuit.** Nobody had measured the 2-wire input's
open-circuit voltage or short-circuit current when the first design was
written, and a low-level dry-circuit load is exactly where ordinary silver
contacts fail to make, because there is not enough energy to break through the
oxide film. A sweep of the remote-start section of every 2-wire generator
controller's manual found each input switched to negative at a few milliamps
behind a pull-up, one maker's at 12 V and 6 mA, another's at 5 V and
current-limited, so
board B carries the G5V-2's gold-clad bifurcated crossbar contacts, specified
from 10 µA to 2 A. That closes the question for the class; the site's own
figures still confirm it, and on revision B they size the clamp (below).

**The fuse and the clamp.** The kit's internal contacts are fused with its own
5 A main fuse and its manual says additional protection may be required, so
the run contact carries its own fuse sized below it: a 2 A 5 × 20 in a holder,
replaceable without a tool, because a soldered fuse four hours from a road is
a dead site and a fuse above the kit's makes the kit's blow inside a box
nobody opens (B-05). Across the pair at the terminal sits a bidirectional TVS,
bidirectional because the input's polarity is never guaranteed. On revision A
it is one part, and a single shorted TVS joins the pair with no relay involved
and the fuse not in the path, the one part outside the interlock that can
start the engine; revision B fits two in series, each blocking the site's
start-input voltage alone (B-06, #19). The 60 ft pair is the surge path, so
its copper is 1.0 mm and nothing else comes within 1.5 mm of it (B-04, B-13).

**The link between the boxes.** Five conductors, `CN9` to `CN9`, a locking
JST VH at both ends, under 3 m, indoors, unshielded: nothing on it carries
more than the two coils. The pin order is board A's and is written on both
silkscreens, because two boards that disagree on a locking connector's pin
order is 12 V on a logic pin with a connector that cannot be plugged the
other way to fix it (B-09). On revision A the three logic lines run straight
from the STM32's pins to the cable, and two of them are the pins ST's system
bootloader drives as FDCAN1 on an empty flash, which every board has before
programming and after an interrupted update: the bootloader pulls `RUN` above
board B's gate threshold and can pulse `KICK`, so the start contact can close
with no firmware running. The monostable guards against a stuck controller,
not against a bootloader that looks like one (#30). Revision B moves the three
nets to pins the bootloader does not configure, behind a series resistor, a
TVS and a pull-down at board A's end (A-34), and the firmware never leaves an
empty-flash window; the firmware's `ARCHITECTURE.md` carries that half.

### Proof of running is measured at the panel

A contact closing is not an engine catching. The `starting` to `running`
transition needs AC the controller can read itself, and the earlier answer, a
smart plug on Wi-Fi, breaks the one rule on the machine where not knowing the
state is most dangerous; the firmware's `ARCHITECTURE.md` makes that argument.
The choices for sensing:

| | | |
|---|---|---|
| **An RS-485 AC meter** at the panel, on the charger's supply | ~$25 | Voltage *and* frequency. "120 V at 60 Hz" is far better evidence an engine caught than "current is flowing" |
| **Optocoupled AC detect** into a GPIO | ~$5 | Simplest and most direct. What the smart plug plan replaced |
| **Charge current on the bank**, via the DC meter already there | free | Indirect, and solar charges too; it cannot tell the two sources apart |

The AC meter is the choice: frequency is the discriminator current alone
cannot provide. Its framing differs from the DC meters', so it cannot share
their bus; which port it takes is in the bus map below. At site
A the generator's 120 V output already runs to the cabin and lands on the
charger outlet, so proof of running is measured there and nothing but the dry
contact pair crosses to the garage.

### What the kit's manual says, and which lines change a design

From the kit's 2-wire installation manual:

> The manufacturer temperature range specification for the choke actuator is
> **−20 °C to +60 °C**. It is not recommended to start the generator with the
> remote start outside this range. **Choke actuator failure may result.**

The coldest night is exactly when the generator is most needed and least able
to be started; that is the central tension of the product stated by the
vendor. It is a behaviour decision, made deliberately and logged with the
outdoor temperature, and it belongs to the firmware (`ARCHITECTURE.md`, the
generator). What it asks of the hardware is an outdoor probe, which the 1-Wire
port carries.

- **"The generator ignition switch MUST be left on for the 2-wire start to
  operate."** Somebody switching it off disables remote start with no
  indication at our end. Proof of running at the panel is what catches it.
- **"Start Module internal contacts are fused with the start module main
  fuse. Additional circuit protection may be required."** The kit ships a 5 A
  fuse; B-05 is the answer.
- The manual states neither the input's open-circuit voltage nor its
  short-circuit current, so the meter is still the only way to learn them.

### Still to confirm at the site

- **Whether opening the 2-wire contact stops a fob-started generator.**
  Release means shut off was described for the 2-wire path only. If the fob
  latches, the firmware's `stop not honoured` is routine rather than rare, and
  the selector's *Off* position is the only honest way to hand control back.
  One email to the kit's maker.
- **The 2-wire input's open-circuit voltage and short-circuit current.** A
  meter across the connector, a minute. It confirms the site sits inside the
  class the G5V-2 covers, and on revision B it sizes each of B-06's two series
  clamps. Still unmeasured.
- **How the cable runs and whether the garage shares the cabin's earth.**
  `LAYOUT-REQUIREMENTS.md` §5 items 5 and 6: aerial means surge protection
  sized for it, buried means rodents, and a detached garage with its own rod
  means the pair bridges two earthing systems.

## Power

### The supply is the bank

The controller runs from the battery bank through its own validated input and
protection path, with no inverter and no computer kept on to host it, because
continuous consumption takes energy from the bank through the season when it
is weakest. Revision A was built for a 12 V bank only, with the bank itself on
the `V12` net; revision B takes a 12 V or a 24 V bank and regulates a 12 V
rail from it for everything past the front end (A-20, A-20e). 48 V banks are
out of scope by decision: such a site already runs its 24 V loads from a
converter of its own, and the controller connects to that (§5 item 11). The
input range has to account for the charging voltage and its transients as
well as the nominal, which is why A-20 is written from the highest voltage a
24 V charger applies with equalisation included.

Measure total input power on the assembled controller for idle, normal
polling, active communications, energised outputs and peak demand, converters,
transceivers and powered peripherals included, and record the communications
state and duty cycle with any daily energy figure. Until those measurements
exist, public copy states the low-consumption goal without a numeric saving or
runtime promise. An MCU's idle current is not the whole device's consumption.

### The rails

Two TPS54331 bucks, 5 V for the transceivers and 3.3 V for everything else.
The 3.3 V converter runs from `V12` directly rather than from the 5 V rail, so
a fault in the transceiver supply cannot take the MCU down with it. On
revision B one 60 V-class buck sits ahead of both and makes the regulated 12 V
they run from; below 12 V it passes the bank through, about 10.2 V at a
discharged 12 V bank, which the TPS54331s regulate from and board B's coils
pull in at (A-20e). Putting that converter on board A rather than on board B
keeps the bank voltage out of the safety chain and board B a 12 V board on
any bank. Every rail that leaves the board, board B's coil supply, the 4-pin
RS-485 port's 5 V, the 1-Wire supply and the tank loop, goes through its own
current limit with a fault flag the MCU can read, so a pinched cable is a
diagnosis and not a blown inlet fuse (A-20b to A-20d, A-24, #47).

The comms processor's 3.3 V is a switched sub-rail, gated by the MCU so a
wedged radio is recoverable without a drive. Revision A's switch defaults off
through every controller reset, which nobody chose, and switching it on after
minutes off corrupted the MCU 22 times of 22 on the bench; revision B's switch
is slew-limited and defaults on, and the controller takes ownership once it
has booted (A-23, §5 item 8, #5). The policy that decides when the radio is
cut is the firmware's, in `ARCHITECTURE.md` under the safety architecture.

### The buck's under-voltage lockout is deliberately low

`EN` divider 330 kΩ / 51.1 kΩ on revision A: the converter starts at 8.99 V and
stops at 8.00 V, about 1 V of hysteresis. Low on purpose, and the reason is the
whole point of the box. The first values, 75 kΩ / 10 kΩ, put the stop
threshold at 10.32 V with only 225 mV of hysteresis: the controller would
power down while the bank still had usable charge, and the controller is the
thing that decides to start the generator that recharges it. It would switch
off at exactly the moment it was most needed and stay off until somebody drove
out. Protecting the bank from deep discharge is the charge controller's
low-voltage disconnect, not the buck's. The thin hysteresis was a second
problem: a bank hovering at the threshold chatters the whole controller.

Computed with TI's equations 1 and 2, which include the internal 1 µA and 3 µA
`EN` current sources; treating `EN` as a plain divider gives a materially
different and wrong answer. Revision B's front-end buck sees the bank instead,
and the same argument sizes its enable network; its values are not yet in the
rules, and the bench measures the brown-out recovery either way (§5 item 9).
The firmware's radio policy has to sit above whichever threshold the front end
stops at, or it never runs.

### The buck's compensation, recomputed

10 kΩ and 10 nF in series on `COMP`, 100 pF from `COMP` to ground, on both
rails. The original 3.09 kΩ / 3.3 nF put the compensation zero at 15.6 kHz
while the loop crossed over at 5.7–9.5 kHz. A zero above crossover boosts
nothing where it matters, and the worst-case phase margin was about 20° on
both rails across the plausible range of ceramic derating and load: a peaky,
ringing rail rather than an obviously dead one, the kind that survives a bench
test and browns out under the comms processor's transmit bursts. Recomputed
against the real 15 µH filter to at least 74°.

The model was checked against the datasheet's own worked example first: it
reproduces TI's 3.3 V design at 22 kHz and 74° against their stated roughly
25 kHz and better than 60°, because a loop model nobody has calibrated is an
opinion. 10 kΩ and 10 nF were already in the BOM and the parts they replaced
were used nowhere else, so the change removed a line rather than adding one.
A-30 puts the network on the `COMP` pin itself, with the 100 pF closest: a
loop with 74° on paper is still a ringing rail if the error amplifier's output
picks up the switch node over 20 mm of trace.

## The buses

### Transceivers go on the board, not on headers

Breakout modules are how the circuit was prototyped. They are not how it
ships. Every connector is a failure point, and a module on pin headers
through a few hundred thermal cycles beside a running generator is an
intermittent fault that presents as a flaky bus and costs a week. Layout
cannot be controlled through wires: the transceiver belongs near the
connector, the TVS at the connector rather than after the chip, the pair
spaced deliberately, the ground reference short. And the transceiver IC costs
a dollar or two against six for the module, before its board, its headers and
somebody plugging it in. What carries across from the bench modules onto the
layout:

| | Why |
|---|---|
| **MAX13487E / MAX13488E**, auto-direction | No DE pin, no turnaround timing to get wrong: one category of bug removed permanently for about $2 a channel. **It does not remove the bias resistors**; see below. The one thing the auto-direction part cannot do is stop driving while the MCU is in reset, so each `TX` net carries a pull-up (A-41, #28) |
| **TVS on A/B, at the connector** | SM712 class: asymmetric 7 V / 12 V, matching RS-485's −7 / +12 V common-mode range, which a symmetric SMAJ12CA does not. **Pin 3 is the common on both the SM712 and the PESD1CAN; the middle pin is a signal line.** Both were first wired with pin 2 to ground, which would have left the A line with no path to ground and a spurious clamp across the pair. Neither symbol names its pins, so the netlist looked plausible and was wrong (A-11c) |
| **Selectable termination**, a header and shunt | Whichever device sits mid-bus must stop terminating without a soldering iron. Shipped fitted, placed above its own connector and silkscreened with the bus name, because the first placement left three of four jumpers nearest a bus they do not terminate (A-13, A-32) |
| **Activity LEDs** | On the receiver output, so they show something *else* on the bus talking, which is what somebody with the cover off wants to know. Revision A's are far brighter than an electrical room needs; revision B drives them at 0.2–0.5 mA (A-14) |

**Slew rate is the one place the two parts differ meaningfully**, and the
intuition is backwards: the MAX13487E's slew limiting exists to reduce
reflections and EMI on long cable, so the *slower* part is the right one for a
long run. Both cover 115200 many times over, so speed decides nothing.

### Bias is mandatory, and 560 Ω was not enough

The MAX13487E datasheet calls the A/B pull-up and pull-down *required for
proper operation*, because the direction state machine reads the current A−B
state and the receiver threshold is ±200 mV, not fail-safe. An unbiased idle
bus is indeterminate and the state machine's own input is undefined. This was
nearly omitted on the belief that the part had a true fail-safe receiver; it
does not.

The first design put 560 Ω to +5 V and to 0 V at the master end, and revision
A was built with it. **Superseded by A-13c.** 560 Ω leaves 254 mV of idle
differential with two terminators and 172 mV with three, inside the undefined
band, and a mid-bus board with its jumper still fitted is the three-terminator
case; two terminators keep only 40–50 mV of margin against noise on a long
cable. Revision B sizes the bias to stay above 200 mV with three terminators,
about 390 Ω, settled on a real cable against the bias of the other devices on
the site's buses before the order (#26).

### The isolated bus is the exception, and none is fitted

The criterion is two separate earthing systems, not distance. A 30 m run
inside one building shares a ground and needs nothing; two buildings ten
metres apart do not, and do. An ADM2582E-class part, isolated transceiver and
isolated DC-DC in one package, has explicit DE and RE pins; there is no common
isolated auto-direction part. So a bus that leaves the building uses the
USART's hardware driver-enable, which the STM32 outputs on the RTS pin (below),
and the firmware supports both modes regardless.

No isolated channel is fitted, deliberately. At site A nothing but the dry
contact pair crosses to the garage, so the bus would have no consumer, and an
ADM2582E with an 8 mm barrier would cost board area for it. A detached garage
with its own rod is what would reopen this (`LAYOUT-REQUIREMENTS.md` §5).

### Bus map

The VE.Direct family is the trap here, and it costs a bench day: those
products do not speak Modbus RTU on RS-485.

| Device | Bus |
|---|---|
| Charge controllers speaking Modbus RTU | RS-485, 115200 8N1 |
| DC meters | RS-485, Modbus RTU, 9600 **8N2**; passive on the bus side and fed 5 V over the cable, so they take the 4-pin port (A-37) |
| The AC meter at the panel | RS-485, 9600 8N1, a third framing, so it cannot share the DC meters' bus |
| Origin89 modules (V2) | RS-485, Modbus RTU, 9600, plus an attention line |
| Most lithium BMSes | CAN, 500 k |
| VE.Can and BMS-Can devices | CAN, 500 k |
| VE.Direct devices: shunts, battery monitors, MPPTs | **VE.Direct**: TTL UART, point to point, one port each |
| VE.Bus inverter-chargers | Proprietary; read through their own gateway over Modbus TCP, a client's job |
| DS18B20 | 1-Wire |

Three RS-485 channels carry three framings, one each. Which connector carries
which is configuration in the firmware, with one constraint the board sets:
the DC meters need the 5 V pin, and only `CN4` has one. Revision A read a DC
meter on that port at 9600 8N2 as soon as it had 5 V from elsewhere, 119 of
120 polls (#34). When the V2 modules arrive they take a channel, and the AC
meter is the port that then gets forgotten until a respin, which is why the
serial budget below counts it.

**Modules speak Modbus, not a house protocol.** The same driver stack then
reads them and third-party gear, any twenty-dollar USB dongle debugs them, and
every Modbus tool becomes test equipment. Keep our own register map; do not
invent framing. Modbus cannot let a leak sensor interrupt, so a shared
open-drain attention line on the same cable does that: any module pulls it low
to mean *poll me now*. One wire, decades old.

### VE.Direct is point to point, and needs isolation

Two VE.Direct ports are where the shunt lives, and the first design priced
them as nearly free, a UART and a level shift. Revision A built them that way,
with 1 kΩ in series and no level shift, listening on pin 3, its own TX
position, so they work only with a straight cable and only with 3.3 V
products. **Superseded by A-38.** The maker's MPPTs drive 5 V, which exceeds
the STM32's pin limit whenever the internal pull-up is on or the board is off,
and its own FAQ asks for galvanic isolation because the product side has
little protection of its own. Revision B listens on pin 2, the producer's TX,
through a digital isolator per port powered from the port's pin 4 within the
port's documented 10 mA limit, working at both levels the products drive, and
defaulting high on the board side while the product side is unpowered so an
unplugged port reads idle by the part's own fail-safe (#27). No VE.Direct
device has been on the bench yet; that is §5 item 9.

### Seven serial ports against eight instances

An earlier draft said the part has six USARTs and treated the budget as
closing at zero margin. It has eight independent serial instances,
USART1/2/3 (FULL), USART4/5/6 (BASIC), LPUART1/2 (LP), per RM0444 Rev 5 Table
179, and the undercount is the only reason this looked tight.

| Port | Instance | Why that one |
|---|---|---|
| ESP32 link, 921600, CTS+RTS | **USART1/2/3** | Only the FULL set has a FIFO. A BASIC instance at 921600 is a byte-at-a-time interrupt storm |
| Isolated bus, hardware DE, if ever fitted | **USART1/2/3** | FULL, and DE needs an instance whose RTS pin is free (below) |
| Two RS-485 channels, auto-direction | USART4/5/6 | No DE and no flow control needed, so BASIC is enough at 9600 |
| **The AC meter, proof of running** | USART4/5/6 | **A seventh port.** 9600 8N1 cannot share the DC meters' 8N2, and once the V2 modules take a channel it cannot share theirs either |
| VE.Direct ×2, RX only | **LPUART1/2** | Needs neither DE nor flow control, and LPUART can run while the core is stopped |
| Console | not a UART | `defmt` over RTT on SWD |

Seven allocated, one spare. Two silicon facts constrain the schematic:

- **The driver-enable signal is output on the RTS pin** (RM0444 §33.7.5,
  `CR3.DEM`). There is no separate DE ball. An instance does hardware RTS *or*
  hardware DE, never both. That does not collide here: the ESP32 link needs
  RTS and CTS and drives no transceiver, and Modbus RTU has no flow control.
  But a schematic drawn with a separate DE output is wrong, and an RTS pin
  spent on DE is an RTS pin gone.
- **USART4/5/6 have no TX or RX FIFO** (Table 180), which is what forces the
  921600 link onto the FULL set.

## Part choices

| Decision | Choice | Reason |
|---|---|---|
| Controller | STM32G0B1 | 512 KB dual-bank flash for A/B updates, 144 KB RAM, eight serial instances, FDCAN. The M0+ has no FPU, which is fine for 1 Hz counting |
| Upgrade path | STM32H5 | If command authentication and secure boot ever need TrustZone and a ROM signature check. The firmware keeps its core HAL-agnostic so the swap stays cheap, and names its images by role for the same reason |
| Comms | Pre-certified ESP32-C6 **module** | Inherits ISED, FCC and CE. A bare chip costs roughly ten times more to certify. Its antenna wants a board cutout and 15 mm of clearance inside the box (A-15, #16) |
| Generator output | Two relays in series, independently driven, behind a hardware run-enable watchdog on their own board | A maintained contact means one welded relay runs the tank dry (above) |
| Relays | Omron G5V-2, DPDT | Gold-clad bifurcated crossbar contacts specified from 10 µA, for a dry-circuit load; the second pole is the feedback contact for free. Rated −25 to +65 °C, an accepted deviation on board B's industrial-grade rule (B-08) |
| Temperature range, board A | Commercial parts | The electrical room stays above 0 °C and is occupied. No −40 requirement and no conformal coating for V1 |
| Mains | **Never on the board** | Dry contacts only, driving contactors somebody else certified. Sidesteps CSA and UL as a category |
| Storage | FRAM **and** NOR | Different failure consequences, so different chips: FRAM for everything control-critical that must survive a cut mid-write, NOR for the log ring. What each holds is the firmware's |
| Override | Auto/off/manual selector at the controller; lockout switch at the genset | Two different needs, operator override and service lockout. Revision B adds a button the STM32 reads for the gestures the protocol needs (A-42) |
| Debug | SWD, 6-pin in ST-LINK order on revision B | Revision A's header carries no NRST, so a probe cannot connect under reset and the only recovery is a wire to a capacitor pad; the M0+ has no trace, so the SWO position is labelled NC (A-40, #29) |

## Before any board is laid out

Established against the datasheets: the part fits on LQFP64 with one spare
serial instance and spare I/O; revision A left 19 pins unused (§5 item 2).
LQFP48 does not fit, failing on raw pin count before alternate functions are
considered.

Five items were open before revision A, and four were called respin grade.
They were answered without opening CubeMX: `stm32-metapac`, which the firmware
already depends on through `embassy-stm32`, ships the pin and alternate-
function tables for every part, machine-extracted from ST's own database by
`stm32-data`. It is the same source CubeMX reads. If it were wrong the
firmware would not work either, which makes it a witness rather than a second
opinion.

| | What | Answer |
|---|---|---|
| 1 | **CTS pin availability** | **Not scarce.** USART1 CTS is on **PA11/AF1 and PB4/AF4**. The fear that there might be none was unfounded; nobody had looked |
| 2 | **FDCAN pin mapping** | **FDCAN1 TX** on PA12, PB9, PC5, PD1; **RX** on PA11, PB8, PC4, PD0, all AF3. The board uses PB9/PB8 |
| 3 | **PA11/PA12 remap** | **Moot.** With CTS on PB4 and RTS on PB3, the whole ESP32 link sits on PB6/PB7/PB4/PB3 and touches neither pad. Revision B keeps those link pins (A-39) |
| 4 | **Alternate-function numbers** | Superseded. Read from metapac 21.0.0, not from DS13560 Rev 1 of November 2020 |
| 5 | **DMA channel budget** | **12 channels**, DMA1 ×7 and DMA2 ×5, plus **DMAMUX1**, so any request routes to any channel and there is no mapping puzzle, only a count. Full demand would be 18, but nothing obliges a 9600-baud Modbus TX to use DMA. This one could never have forced a respin: it is a firmware allocation question, and it was ranked alongside four that were |

The lesson is about the ranking, not the pins. Four items sat at respin grade
for months on the strength of a contradiction in one datasheet table, and the
answer was sitting in a Cargo dependency the firmware already builds against.
Before declaring something blocked on a tool nobody has opened, check whether
the machine-readable form is already on the disk. CubeMX is still worth an
hour as confirmation before fabrication; it is no longer a gate.

The pin assignment is closed for revision A and reopened for revision B: `RUN`,
`KICK` and `FEEDBACK` leave the bootloader's FDCAN1 pins (A-34) and the button
arrives (A-42), each new pin checked against the metapac and against AN2606's
table of the pins ST's system bootloader configures. Two pins to remember when
moving anything: `PA4` and `PA5` are 3.3 V only, carry SPI to the NOR, and a 5 V
signal on either is a scrapped board (§5 item 3).

## Settled

Recorded so they are not re-litigated:

- **The generator interface** is a maintained dry contact, closed means run,
  and the start kit owns cranking, confirmed by its maker.
- **No generator module in V1.** A dry contact over 60 ft has no voltage drop
  and no comms link to lose.
- **The electrical room stays above 0 °C and is occupied**, so commercial-range
  parts on board A and no conformal coating for V1.
- **The generator run is 60 ft**, garage to panel, not the 100 ft an earlier
  draft carried. It changes nothing for a dry contact; it is recorded so
  nobody measures it a third time.
- **Nothing but the dry contact pair crosses to the garage.** Proof of running
  is measured at the panel, no RS-485 leaves the building at site A, and the
  isolated bus has no consumer there.
- **The 2-wire input's class is closed, the site's figures are not**, and on
  revision B they size B-06.

## What lives elsewhere

- The rules and their values, per revision: `A-nn` in
  [`LAYOUT-REQUIREMENTS.md`](../boards/controller-a/LAYOUT-REQUIREMENTS.md),
  `B-nn` in [`GENERATOR-BOARD.md`](../boards/generator-b/GENERATOR-BOARD.md),
  each naming the issue that argued for it. The open items are that file's
  §5.
- What each board is, its status, its filed exports and its bench sessions:
  [board A](../boards/controller-a/README.md) and
  [board B](../boards/generator-b/README.md).
- The system design, what decides, what persists, what fails safe and how:
  [`ARCHITECTURE.md`](https://github.com/origin89hq/firmware/blob/main/docs/ARCHITECTURE.md)
  in origin89hq/firmware.
- The wire between the two processors and to every client:
  [KM43](https://github.com/origin89hq/km43).
