# Website renders

These scripts render the Controller media on the
[website](https://github.com/origin89hq/website)'s homepage: the hero film, the U7
and U8 chip views, the connection and integration stills, the Gerber artwork and
the 3D model. They read [`../origin89.blend`](../origin89.blend) and board A's
filed export in `boards/controller-a/build/2026-09-09/`, and never save over
either. Like the scene, the renders present the drawn design; they are not
evidence about a board.

The website packages the outputs with `apps/website/scripts/package-home-media.mjs`
and records this repository's commit and the SHA-256 of the scene, `gerber.zip`,
`pick-and-place.csv` and `bom.csv` beside them. The site miniatures on the same
page come from origin89hq/brand, `situations/scenes/site-miniatures/`.

| Script | Runs under | Writes |
| --- | --- | --- |
| `gerber_layers.mjs` | Node, through npx | `gerber-layers/`: `top-{copper,pads,silk,board}.png` masks at 64 px/mm and `top-layers.json` |
| `gerber_art.mjs` | Node, through npx | `gerber-art/`: `gerber-u7.webp`, `gerber-board-dim.webp`, `trace-mask-{u7,board}.webp` and `board-albedo.jpg` for the GLB |
| `build_detailed_board.py` | Blender | `controller-detailed.blend`, the scene the renders below use |
| `board_detail.py` | Blender, imported by the script above | parts and the board material |
| `render_film.py` | Blender, on the detailed scene | `film/frame-NNNN.png` (1920 × 1080) and `film/anchors.json` |
| `render_chips.py` | Blender, on the detailed scene | `chips/u7.png` and `chips/u8.png` (1000 × 1000, orthographic) |
| `render_studio.py` | Blender, on the detailed scene | `studio/connect-*.png` (1760 × 1210) and `studio/integrate-controller.png` (1600 × 1800) |
| `export_glb.py` | Blender | `controller-raw.glb`, compressed to `controller.glb` with gltf-transform |

Every Blender render has a transparent film. The detailed scene replaces the
STEP's box components with parts placed from pick-and-place, marked from the
BOM, and textures the board from the Gerber masks. Connectors keep the scene's
datasheet-envelope proxies. The ESP32 module's matrix code is a fixed
pseudo-random pattern. `render_chips.py` scales the laser marking and mattes
the finishes for the flat top view. `render_film.py` projects anchor points on
the board through each frame's camera into `anchors.json`; the website places
its callouts from that file, so change the shots, anchors and callouts together.

## Run

Requires Blender 5.2 on a Mac with a Metal GPU (the render scripts select Metal
devices), Node with network access for `npx`, the scene from Git LFS, and
Inter Tight 600 for the part markings: `fonts/InterTight-600.ttf` in
origin89hq/brand, also shipped in the `@origin89/brand` package. This
repository has no Node workspace; npx installs the pinned packages for each run.

From the repository root, on a clean checkout:

```sh
M=/tmp/home-media
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
FONT=/path/to/brand/fonts/InterTight-600.ttf
WEB=enclosure/blender/web

# 1. Gerber masks and artwork
unzip -o boards/controller-a/build/2026-09-09/gerber.zip -d "$M/gerber"
npx --yes --package sharp@0.35.3 --package pcb-stackup@4.2.8 -- \
  node "$WEB/gerber_layers.mjs" --gerbers "$M/gerber" --out "$M/gerber-layers"
npx --yes --package sharp@0.35.3 -- \
  node "$WEB/gerber_art.mjs" --layers "$M/gerber-layers" --out "$M/gerber-art"

# 2. Detailed board scene (keep $M/gerber-layers: the scene links those PNGs)
"$BLENDER" --background --python-exit-code 1 --python "$WEB/build_detailed_board.py" -- \
  --layers "$M/gerber-layers" --font "$FONT" --output "$M/controller-detailed.blend"

# 3. Film, chips and studio stills
"$BLENDER" --background --python-exit-code 1 "$M/controller-detailed.blend" \
  --python "$WEB/render_film.py" -- --out "$M/film"
for chip in U7 U8; do
  "$BLENDER" --background --python-exit-code 1 "$M/controller-detailed.blend" \
    --python "$WEB/render_chips.py" -- --out "$M/chips" --chip "$chip"
done
"$BLENDER" --background --python-exit-code 1 "$M/controller-detailed.blend" \
  --python "$WEB/render_studio.py" -- --out "$M/studio"

# 4. Web model
"$BLENDER" --background --python-exit-code 1 --python "$WEB/export_glb.py" -- \
  "$M/controller-detailed.blend" --board-albedo "$M/gerber-art/board-albedo.jpg" \
  --output "$M/controller-raw.glb"
npx --yes @gltf-transform/cli@4.5.0 webp "$M/controller-raw.glb" "$M/controller-webp.glb"
npx --yes @gltf-transform/cli@4.5.0 meshopt "$M/controller-webp.glb" "$M/controller.glb"
```

Hand `$M` and this checkout to the website packager. It reads `film/`, `chips/`,
`studio/`, `gerber-art/` and `controller.glb`, and `dioramas/` from the brand
script unless `--only` leaves the miniatures out. It refuses scene or fab inputs
that differ from the checked-out commit.

Run one Blender process at a time; the renders share the GPU. The film is 1176
frames at 40 samples, about 6.5 s per frame on an M2 Max, so a little over two
hours. It skips frames that already exist, so an interrupted render resumes;
`--frames 1-120` renders part of it and `--anchors-only` rewrites `anchors.json`
without rendering. The chips and stills (96 samples) take seconds each;
`render_studio.py --only` renders a subset. The Gerber masks take about a minute
of CPU.

With sharp 0.35.3, the two Gerber scripts reproduce the website's current Gerber
artwork byte for byte. New Cycles renders are not expected to match the published
hashes.

A new fabrication export changes the date in three places: `FAB_BUILD` in
`board_detail.py`, the `unzip` path above, and the packager's input paths.
`gerber_layers.mjs` stops if the board outline is no longer 100 × 125 mm, which
the board texture's UV mapping assumes.
