# CAD to Blender

These scripts turn the enclosure CAD and a board STEP into the assembly that
[`../blender/build_scene.py`](../blender/build_scene.py) dresses into the
presentation scene. [`../blender/rebuild.py`](../blender/rebuild.py) runs the
whole chain; run the steps by hand only to debug one of them.

Two interpreters, because two ecosystems:

- **FreeCAD's Python** (`/Applications/FreeCAD.app/Contents/Resources/bin/python`)
  for anything that imports `shoe`/`artwork` or reads STEP. Put
  `/Applications/FreeCAD.app/Contents/Resources/lib` on `PYTHONPATH` when
  invoking it directly; the rebuild runner does this.
- **Blender** for assembly and the Cycles scene.

Intermediates land in `work/`, which is ignored and derived.

| # | Script | Runs under | Produces |
|---|---|---|---|
| 0 | `../shoe.py` | FreeCAD | `../out/board-{a,b}-{plate,shoe}.{step,stl}` |
| 1 | `../artwork.py` | FreeCAD | `../out/artwork-*.{svg,png}` |
| 2 | `frames.py` | FreeCAD Python | `work/frames.json`: envelopes, plugs and light pipes in the board frame |
| 3 | `board_glb.py --step <file>` | FreeCAD Python | `work/board-a.glb` and `board-a-source.json`, recording the STEP and its SHA-256 |
| 4 | `strips.py` | FreeCAD Python | `work/strip-*.png` and `strips.json`: one texture per port strip, read from `artwork.py`'s `STRIP_BANDS` |
| 5 | `textures.py` | FreeCAD Python | `work/tex-{a,b}.png`: the top transfers at texture size |
| 6 | `assembly_glb.py` | Blender | `work/assembly.blend` and `boxes-full.glb`: both boxes, boards, plugs, strips and cables |
| 7 | `../blender/build_scene.py` | Blender | `../blender/origin89.blend`: box A in the satin-black studio |

Step 6 still assembles box B, the generator board's enclosure, with an
envelope-only board. Step 7 removes it; `work/assembly.blend` is the place to
start a scene that shows both boxes.

Cycles is deterministic only on one machine with one seed. A re-render on
another machine differs in noise, not in content.

Gotchas that already cost time:

- The glTF exporter composes an unapplied object rotation about the world
  origin. Bake rotation into the mesh (`transform_apply`) before export.
- After a GLB round-trip, transforms are baked into vertices and every object
  origin is the world origin. Dress geometry by editing `v.co`, never
  `obj.scale` or `obj.location`.
- The EasyEDA STEP carries the board slab twice and has no bodies for THT
  connectors (0.8 mm outlines). `assembly_glb.py` keeps the lowest slab and
  stands in the datasheet envelopes from `frames.json`.
- `matrix_world` is stale after moving an object until
  `bpy.context.view_layer.update()`. Measure after the update, or a decal
  lands at the pre-move position.
