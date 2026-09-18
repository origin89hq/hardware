"""Render the dark studio stills of the Controller for the website's connection and integration sections.

Runs on the scene saved by build_detailed_board.py, using the cameras saved in
the presentation scene:

    blender --background --python-exit-code 1 /tmp/home-media/controller-detailed.blend \\
      --python enclosure/blender/web/render_studio.py -- --out /tmp/home-media/studio

Writes transparent RGBA PNGs at 96 samples: connect-{bottom,cable,right,left,harness}.png
(1760 x 1210, cover closed, cables and sleeve shown) and integrate-controller.png
(1600 x 1800 from the Hero camera, no cables). --only renders a subset. The scene
file is not saved.
"""
import argparse
import sys
from pathlib import Path

import bpy

CABLE_COLLECTIONS = ('06 | Cables - editable Bezier curves', '11 | Cable management - sleeve and straps')
# name: (camera, resolution)
SHOTS = {
    'connect-bottom': ('Camera | Connector inspection', (1760, 1210)),
    'connect-cable': ('Camera | Cable detail', (1760, 1210)),
    'connect-right': ('Camera | Right ports', (1760, 1210)),
    'connect-left': ('Camera | Left ports', (1760, 1210)),
    'connect-harness': ('Camera | Harness', (1760, 1210)),
    'integrate-controller': ('Camera | Hero', (1600, 1800)),
}

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--only', nargs='+', choices=tuple(SHOTS), default=())
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
out = args.out
out.mkdir(parents=True, exist_ok=True)
only = set(args.only)

s = bpy.context.scene
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == 'METAL'
s.render.engine = 'CYCLES'
s.cycles.device = 'GPU'
s.cycles.samples = 96
s.cycles.use_denoising = True
s.render.film_transparent = True
s.render.image_settings.file_format = 'PNG'
s.render.image_settings.color_mode = 'RGBA'
c = bpy.data.objects['O89 Controls']
c['cover_lift_mm'] = 0.
c['show_cables'] = True
c['show_cable_sleeve'] = True
c['led_on'] = True
for n in CABLE_COLLECTIONS:
    for o in bpy.data.collections[n].all_objects:
        o.hide_render = False

for name, (cam, (w, h)) in SHOTS.items():
    if only and name not in only:
        continue
    c['show_bus_layout'] = False
    bare = name == 'integrate-controller'
    c['show_cables'] = not bare
    c['show_cable_sleeve'] = not bare
    for n in CABLE_COLLECTIONS:
        for o in bpy.data.collections[n].all_objects:
            o.hide_render = bare
    for o in bpy.data.collections['10 | Bus layout - editable illustration'].all_objects:
        o.hide_render = True
    s.camera = bpy.data.objects[cam]
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.filepath = str(out / f'{name}.png')
    bpy.ops.render.render(write_still=True)
