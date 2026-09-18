"""Render isolated top views of U7 (STM32G0B1) and U8 (ESP32-C6 module) for the website.

Runs on the scene saved by build_detailed_board.py, once per chip, because it
deletes every other part from the open file before rendering:

    blender --background --python-exit-code 1 /tmp/home-media/controller-detailed.blend \\
      --python enclosure/blender/web/render_chips.py -- --out /tmp/home-media/chips --chip U7
    blender --background --python-exit-code 1 /tmp/home-media/controller-detailed.blend \\
      --python enclosure/blender/web/render_chips.py -- --out /tmp/home-media/chips --chip U8

Writes u7.png or u8.png: 1000 x 1000 transparent RGBA, orthographic, 96 samples.
The scene file is not saved.
"""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--chip', choices=('U7', 'U8'), required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
out = args.out
out.mkdir(parents=True, exist_ok=True)
which = args.chip

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
# Flat top views: a matte module PCB and antenna instead of the coated film finish.
for name, col in (('O89 detail | Module PCB', (.018, .022, .028, 1)), ('O89 detail | Module antenna', (.05, .06, .075, 1))):
    m = bpy.data.materials.get(name)
    if m:
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = col
        b.inputs['Coat Weight'].default_value = 0.
        b.inputs['Roughness'].default_value = .5
        b.inputs['Specular IOR Level'].default_value = .12
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        o.hide_render = True
MM = .001
ep = bpy.data.materials['O89 detail | IC epoxy'].node_tree.nodes['Principled BSDF']
ep.inputs['Roughness'].default_value = .78
ep.inputs['Specular IOR Level'].default_value = .18
cd = bpy.data.cameras.new('chip cam')
cd.type = 'ORTHO'
cd.clip_start = .001
cam = bpy.data.objects.new('chip cam', cd)
s.collection.objects.link(cam)
s.camera = cam
key = bpy.data.lights.new('chip key', 'AREA')
key.shape = 'DISK'
key.size = .12
key.energy = 2.2
kob = bpy.data.objects.new('chip key', key)
s.collection.objects.link(kob)
fill = bpy.data.lights.new('chip fill', 'AREA')
fill.shape = 'DISK'
fill.size = .3
fill.energy = .9
fob = bpy.data.objects.new('chip fill', fill)
s.collection.objects.link(fob)
for o in (kob, fob):
    o.visible_camera = False
if s.world and s.world.node_tree.nodes.get('Background'):
    s.world.node_tree.nodes['Background'].inputs['Strength'].default_value *= .04
bpy.data.objects['O89 Controls']['cover_lift_mm'] = 400.
bpy.data.objects['O89 Controls']['show_cables'] = False


def shot(prefix, center, scale, size):
    keep = [o for o in bpy.data.objects if o.name.startswith(prefix)]
    # Drivers re-show hidden scene parts, so move everything else out of the frame.
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE', 'FONT'):
            o.hide_render = o not in keep
            if o not in keep and o.parent is None:
                o.location.z -= 5.
    bpy.data.objects['Product | move or rotate the whole controller'].location.z = 0
    c = Vector((center[0] * MM, center[1] * MM, 0))
    cam.location = c + Vector((0, 0, .2))
    cam.rotation_euler = (0, 0, 0)
    cd.ortho_scale = scale * MM
    kob.location = c + Vector((-.09, .07, .14))
    kob.rotation_euler = (c - kob.location).to_track_quat('-Z', 'Y').to_euler()
    fob.location = c + Vector((.26, -.3, .16))
    fob.rotation_euler = (c - fob.location).to_track_quat('-Z', 'Y').to_euler()
    s.render.resolution_x, s.render.resolution_y = size
    s.render.filepath = str(out / f'{prefix.strip(" |").lower()}.png')
    bpy.ops.render.render(write_still=True)


# Package realism for flat top views: small laser marking, a moulded pin-1 dimple,
# a bright soft top light for the steel shield.
mark_scale = {'U7': .58, 'U8': .82}[which]
# Pick-and-place centres, mm.
centre = {'U7': Vector((17.736 * .001, .227 * .001, 0)), 'U8': Vector((-4.891 * .001, 45.62 * .001, 0))}[which]
for o in bpy.data.objects:
    if o.name.startswith(which + ' | marking'):
        mw = o.matrix_world.copy()
        loc = mw.translation.copy()
        off = Vector((loc.x - centre.x, loc.y - centre.y, 0))
        if which == 'U7':
            off = Vector((-1.2 * .001, 1.4 * .001, 0))
        o.matrix_world = Matrix.Translation(Vector((centre.x + off.x, centre.y + off.y, loc.z))) @ mw.to_3x3().to_4x4() @ Matrix.Scale(mark_scale, 4)
    if o.name == 'U7 | pin 1':
        dm = bpy.data.materials.new('dimple')
        dm.use_nodes = True
        b = dm.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (.004, .004, .005, 1)
        b.inputs['Roughness'].default_value = .18
        o.data.materials.clear()
        o.data.materials.append(dm)
mk = bpy.data.materials.get('O89 detail | Laser marking')
if mk:
    mk.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.24, .24, .245, 1)
if which == 'U8':
    sh = bpy.data.materials['O89 detail | Module shield'].node_tree.nodes['Principled BSDF']
    sh.inputs['Base Color'].default_value = (.42, .42, .41, 1)
    sh.inputs['Roughness'].default_value = .42
for o in [o for o in bpy.data.objects if o.type in ('MESH', 'CURVE', 'FONT') and not o.name.startswith(which + ' |')]:
    bpy.data.objects.remove(o, do_unlink=True)
if which == 'U7':
    shot('U7 |', (17.736, .227), 15.2, (1000, 1000))
else:
    shot('U8 |', (-4.891, 45.62), 31, (1000, 1000))
