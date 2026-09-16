# Blender presentation scene

`origin89.blend` is the controller as the website and documentation show it:
the enclosure meshes from `shoe.py`, board A imported from its STEP, the
satin-black finish, both label options, editable cable curves, ten cameras
and a studio light rig. Textures and the Michroma font are packed into the
file. It is stored in Git LFS; install `git-lfs` before cloning.

It is a presentation of the drawn design, not evidence about a board. Change
dimensions in `shoe.py` and rebuild; use Blender for finish, cables, lights
and cameras.

## Controls

Select **O89 Controls** in the Outliner, then open **Object Properties → Custom
Properties**:

| Control | Use |
| --- | --- |
| `production_label` | Switch between the clean editable text and the production transfers from `artwork.py`, including their QR code and specification table. |
| `cover_lift_mm` | Lift the cover, its labels and its light pipe to expose the PCB. |
| `show_enclosure` | Hide the cover and mounting plate for a board-only view. |
| `show_cables` | Hide the harness. |
| `show_bus_layout` | Replace the harness with an illustrative RS-485 daisy chain and 1-Wire trunk with short sensor taps. Use the Wiring camera. |
| `show_cable_sleeve` | Hide or show the braided sleeve and side retaining straps. The jacketed cables inside stay editable. |
| `led_on` | Toggle the single status indicator. |

The numbered collections separate CAD, PCB, connector proxies, clean text,
production artwork, cables, lights and cameras. Move the whole product with
`Product | move or rotate the whole controller`. Units display millimetres;
one internal Blender unit is one metre.

The saved scene uses the Hero camera. The others show the front, left and
right ports, the PCB, the exploded assembly, cable detail, connector
inspection, harness and wiring. **Connector inspection** lifts the cover
18 mm, so from that camera the port labels appear one position left of their
plugs; the closed views line up. **Wiring** shows one RS-485 bus serving
three example devices and one 1-Wire bus serving three probes; the device
shapes and distances are illustrative.

## Render

These commands read the saved `.blend` and never save over it. Run them from
the repository root. Tested with Blender 5.2.1 LTS.

```sh
blender --background --python-exit-code 1 \
  --python enclosure/blender/render_scene.py -- --view hero --studio
```

`--view` is one of `hero`, `front`, `left`, `right`, `pcb`, `exploded`,
`cables`, `wiring`, `connectors` or `harness`. `--label clean|production`
overrides the saved label choice, `--led-on`/`--led-off` the status light.
Omitting `--studio` gives a transparent PNG. Use `--scene` for a saved
variant, `--size 960 --samples 32` for a draft and `--output` to choose the
destination; the default is the ignored `previews/` directory. Each render
writes a JSON file with its camera, controls and projected light-pipe
position. Cable detail, connector inspection, harness and wiring use a 16:10
frame.

The website renders its controller images from this file with its own scripts
in [origin89hq/website](https://github.com/origin89hq/website) and records the
file's SHA-256 beside them.

## Cable presentation

The three RS-485 leads and the bottom 1-Wire lead have graphite Cat5e jackets
(illustrative 5.2 mm diameter), an exposed twisted pair and a third conductor.
The 12 V lead has a separate power jacket with red/black conductors. CAN,
VE.Direct and the left-side leads keep their own cable types. LNK needs the
VH harness specified in `boards/generator-b/GENERATOR-BOARD.md`; Cat5e is
not a substitute for these leads.

Below the connector branches, the jacketed leads gather inside one charcoal
braided sleeve, about 25 mm outside diameter. Sleeve size, weave and strap
placement are presentation choices, not manufacturing CAD. The bus layout
view hides the sleeve so its routes stay readable.

The colour convention below is recorded inside the `.blend`. It is **not** an
Ethernet pinout or a published Origin89 wiring standard:

| Port | Pin 1 | Pin 2 | Pin 3 |
| --- | --- | --- | --- |
| RS-485 CN2/CN3/CN4 | Orange: A | White/orange: B | Green: GND |
| 1-Wire CN8 | Orange: OW_VCC | Blue: OW_DATA_F | White/blue: GND |
| CAN CN5, dedicated cable | Grey: CANH | White/grey: CANL | Green: GND |

Pin order and nets were checked against the `PAD_NET` records of the
2026-08-31 EasyEDA project. CN11 on the side and CN8 on the bottom share the
same 1-Wire nets; the layout uses CN8. Unused Cat5e cores stay insulated
inside the jacket.

RS-485 runs device to device with termination at the two bus ends; 1-Wire
uses one trunk with short taps. The scene does not specify distances or cable
suitability. Cat5e differs in impedance from typical 120-ohm RS-485 cable, so
termination and run length must suit the real design. See
[TI's RS-485 design guide](https://www.ti.com/lit/an/slla272d/slla272d.pdf) and
[Analog Devices' long-line 1-Wire guidelines](https://www.analog.com/en/resources/technical-articles/guidelines-for-reliable-long-line-1wire-networks.html).

## Rebuild from the CAD

**Rebuilding replaces the output file.** Save manual Blender edits under
another name first; rendering preserves them.

```sh
python3 enclosure/blender/rebuild.py --refresh-cad \
  --step boards/controller-a/build/<date>/board.step \
  --output enclosure/blender/origin89.blend --overwrite
```

`--refresh-cad` regenerates the enclosure STLs and production artwork from
`shoe.py` and `artwork.py` first; without it, `enclosure/out/` must already
hold them. The chain in [`../render/`](../render/) always refreshes the PCB
and textures. The runner uses the installed FreeCAD and Blender: on macOS the
applications in `/Applications`, overridden by `FREECAD_PYTHON`, `FREECAD_LIB`
and `BLENDER`. A restricted process sandbox can stop FreeCAD's CPU detection
and Blender's initialisation; run the applications normally in that case.

The 2026-08-31 STEP rebuilds in about a minute. The filed 2026-09-09 export
takes about seven and is not ready to replace it: its import leaves hundreds of
connector, header and inductor meshes stacked at the board centre, which the
debris filter in `assembly_glb.py` does not remove because they sit on the
board. Render the `pcb` view and check the centre before committing a rebuild.

## What the saved file was built from

The committed scene (SHA-256
`ba1af6a1d35ab9483d43a325ea3239f1ef33b9b08b4d51e17c7cd068e499e8b3`) was built before this
repository existed and records the paths of that earlier checkout:

- PCB: `3D_PCB1_2026-08-31.step`, SHA-256
  `36dd9b2bd17666da48dedbe704e6ce8f5d29558beba39459faf885ba20ff91f9`, 1,278
  shapes at 0.2 mm tessellation. This export predates the filed and fabricated
  `boards/controller-a/build/2026-09-09/board.step`, and the board's
  components differ between the two.
- Enclosure and artwork: `shoe.py` and `artwork.py` with the same geometry and
  label positions as `enclosure/` here.

A rebuild from `enclosure/` and the 2026-08-31 STEP renders the same as the
saved file, so the scene carries no manual edits beyond `build_scene.py`.

The connector bodies are datasheet envelopes from `shoe.py` with recessed
screw wells, wire-entry bores and hollow JST sockets for readability. They are
proxies; replace them with supplier CAD if exact connector detail matters.
The clean front text is a presentation variant; the fabrication artwork
remains the other label option.
