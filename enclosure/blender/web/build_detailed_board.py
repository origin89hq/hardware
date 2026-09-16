"""Build the detailed Controller scene that the website film, chip and studio renders use.

Opens the presentation scene (enclosure/blender/origin89.blend), hides the cables
and sleeve, replaces the STEP box parts with board_detail's parts from board A's
pick-and-place and BOM, textures the board from the Gerber layer masks and saves
a copy. The source scene is never written. From the repository root:

    blender --background --python-exit-code 1 \\
      --python enclosure/blender/web/build_detailed_board.py -- \\
      --layers /tmp/home-media/gerber-layers --font /path/to/brand/fonts/InterTight-600.ttf \\
      --output /tmp/home-media/controller-detailed.blend

--font is the part marking font, Inter Tight 600 from origin89hq/brand
(fonts/InterTight-600.ttf, also shipped in @origin89/brand). The saved copy links
the layer PNGs by absolute path; keep --layers in place while rendering from it.
"""
import argparse
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import board_detail  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--hardware', type=Path, default=ROOT, help='hardware checkout with the scene and fab files (default: this one)')
parser.add_argument('--scene', type=Path, help='defaults to enclosure/blender/origin89.blend in --hardware')
parser.add_argument('--layers', type=Path, required=True, help='top-*.png from gerber_layers.mjs')
parser.add_argument('--output', type=Path, required=True, help='detailed .blend to write')
parser.add_argument('--font', type=Path, required=True, help='part marking font: InterTight-600.ttf from origin89hq/brand')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])

scene_path = args.scene or args.hardware / 'enclosure/blender/origin89.blend'
fab = args.hardware / board_detail.FAB_BUILD
required = [scene_path, fab / 'pick-and-place.csv', fab / 'bom.csv', args.font]
required += [args.layers / f'top-{layer}.png' for layer in ('copper', 'pads', 'silk', 'board')]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    parser.error('missing input: ' + ', '.join(missing))
if args.output.resolve() == scene_path.resolve():
    parser.error('--output must not overwrite the source scene')

bpy.ops.wm.open_mainfile(filepath=str(scene_path.resolve()))
controls = bpy.data.objects['O89 Controls']
controls['show_cables'] = False
controls['show_cable_sleeve'] = False
product = bpy.data.objects['Product | move or rotate the whole controller']
board_detail.build(product, args.hardware.resolve(), args.layers.resolve(), args.font.resolve())
args.output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), copy=True)
print('DETAILED SCENE', args.output)
