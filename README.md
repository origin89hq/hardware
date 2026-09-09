<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/origin89hq/brand/main/logos/origin89-horizontal-white.svg">
  <img src="https://raw.githubusercontent.com/origin89hq/brand/main/logos/origin89-horizontal-blue.svg" alt="Origin89" width="320">
</picture>

# Origin89 hardware

The boards and the enclosure of the Origin89 controller: a box that starts a
generator and manages a battery bank at a site four hours from a road, through
a Canadian winter, with nobody watching it fail. The reasoning behind the
circuits is in the [controller design](https://docs.origin89.com/hardware/);
this repository holds what was drawn from it and what a fab needs.

| Board | Stage | Files |
| --- | --- | --- |
| [Controller, board A](boards/controller-a/) | prototype: revision A fabricated, not measured | EasyEDA source, Gerbers, BOM, pick-and-place, STEP, DXF, fabrication drawing |
| [Generator, board B](boards/generator-b/) | prototype: five boards assembled, bench proof pending | EasyEDA source, Gerbers, BOM, pick-and-place, STEP, DXF |
| [Enclosure](enclosure/) | drawn, printing waits on a measured board | FreeCAD source |

Nothing here is a validated product. A board that has been fabricated has not
necessarily been measured, and one that has been measured has not been
through a winter.

## Layout

Each board has a README with its status and revisions, its design source
under `easyeda/`, and dated fabrication exports under `build/<date>/`. A file
that has been filed never changes: a changed export goes beside the old one
under a new date, so a board in someone's hands can still be matched to its
files. The STEP models are in Git LFS; install `git-lfs` before cloning or
they come down as pointer files.

EasyEDA names its exports after the board number and the date and puts them
in directories with parentheses. Do not file them by hand:

```sh
python tools/import_easyeda_export.py controller-a ~/Downloads/PCB1_2026-09-15
```

reads the date from the filenames, writes `build/2026-09-15/` with the same
names every export gets, `gerber.zip`, `bom.csv` and `bom.xlsx`,
`pick-and-place.csv`, `schematic.pdf`, `fabrication-layers.pdf`, `board.step`
and `board.dxf`, puts the `.eprj2` project under `easyeda/`, and refuses a
file it does not recognise or one that would change what is already filed.
Filing the 2026-09-09 exports through it reproduces the committed files byte
for byte, which is the check that the convention is the script and not a
memory.

## Checks

```sh
pip install gerbonara shapely
python tools/validate_gerbers.py boards/controller-a/gerber-rules.json boards/controller-a/build/2026-09-09/gerber.zip
```

It reads the copper layer by layer and reports each rule by number, so a
failure names the hole or the band. Which holes, which keep-out radius and
which voids come from the board's `gerber-rules.json`, so the same script
checks the [camera board](https://github.com/origin89hq/camera) against its
own rules. It runs in CI on every push against the newest controller export.

## Licence

The design files, drawings and CAD are under the CERN Open Hardware Licence
version 2, weakly reciprocal ([LICENSE](LICENSE)): change the board and share
the change; build a product around it and keep the rest of that product to
yourself. The Python tools are under MIT OR Apache-2.0 ([LICENSE-MIT](LICENSE-MIT),
[LICENSE-APACHE](LICENSE-APACHE)). The Origin89 name and marks are not covered
by either; see the [brand repository](https://github.com/origin89hq/brand).
