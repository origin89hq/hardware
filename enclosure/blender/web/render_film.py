"""Render the website hero film: a 49 s loop (1176 frames at 24 fps) of the detailed Controller.

Runs on the scene saved by build_detailed_board.py, which Blender opens first:

    blender --background --python-exit-code 1 /tmp/home-media/controller-detailed.blend \\
      --python enclosure/blender/web/render_film.py -- --out /tmp/home-media/film

Shots: reveal, lift, trace sweep, STM32 orbit, ESP32 antenna, RS-485 track,
exploded turn, reassemble. The last frame matches the first, so the video loops
without a jump. Writes transparent RGBA frame-NNNN.png files and anchors.json
(per-frame callout positions as 0-1 fractions of the frame, from the render
camera). Existing frames are skipped, so an interrupted render resumes. The
scene file is not saved.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

MM = .001
FPS = 24

ANCHORS = {
    'cn': (-8., -53.6, 9.),
    'u7': (17.736, .227, 3.2),
    'antenna': (-6., 54.5, 2.6),
    'rs485': (-9.746, -38.258, 3.3),
    'board': (0., 0., 1.7),
}

# name: (start, end, keys[(frame, camera mm, aim mm, lens, f-stop)])
SHOTS = {
    'reveal': (1, 120, [(1, (-300, -560, 190), (-40, -6, 12), 60, 11), (120, (-250, -500, 215), (-36, -4, 14), 60, 11)]),
    'lift': (121, 264, [(121, (-190, -380, 300), (0, -4, 30), 52, 11), (200, (-130, -270, 330), (0, 0, 10), 50, 11), (264, (-95, -210, 330), (4, 0, 4), 48, 11)]),
    'sweep': (265, 408, [(265, (-30, -150, 120), (-6, -44, 2), 40, 16), (408, (10, 70, 150), (0, 30, 2), 40, 16)]),
    'u7': (409, 552, [(409, (70, -40, 52), (18.4, -.3, 3.1), 70, 18), (480, (58, -62, 50), (17.8, .2, 3.1), 70, 18), (552, (36, -74, 48), (17.2, .8, 3.1), 70, 18)]),
    'u8': (553, 696, [(553, (34, 4, 64), (-3.4, 42, 5), 58, 20), (696, (10, 26, 58), (-5.6, 51, 3.5), 58, 20)]),
    'rs485': (697, 840, [(697, (-60, -12, 56), (-22, -41, 3), 50, 18), (840, (0, -10, 58), (8, -44, 3), 50, 18)]),
    'explode': (841, 1032, [(841, (-300, -540, 300), (0, 0, 34), 44, 11), (1032, (-270, -500, 280), (0, 0, 30), 44, 11)]),
    'assemble': (1033, 1176, [(1033, (-270, -500, 280), (0, 0, 30), 44, 11), (1176, (-300, -560, 190), (-40, -6, 12), 60, 11)]),
}
LENGTH = 1176
KEY_LIGHT = {
    'reveal': (-.30, .26, .34), 'lift': (-.30, .26, .34), 'sweep': (-.10, -.30, .30), 'u7': (-.08, -.32, .30),
    'u8': (-.10, -.30, .30), 'rs485': (-.30, .26, .34), 'explode': (-.30, .26, .34), 'assemble': (-.30, .26, .34),
}
GRAZING = {'sweep': .08, 'u7': .08, 'u8': .5, 'rs485': .08}


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--frames', default=f'1-{LENGTH}', help='comma-separated frames or ranges, e.g. 1-120,400')
    p.add_argument('--samples', type=int, default=40)
    p.add_argument('--size', default='1920x1080')
    p.add_argument('--anchors-only', action='store_true', help='write anchors.json without rendering')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return p.parse_args(argv)


def curves(idb):
    ad = idb.animation_data
    out = []
    if ad and ad.action:
        for layer in getattr(ad.action, 'layers', []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    return out


def ease(idb, interp='BEZIER'):
    for fc in curves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            if interp == 'BEZIER':
                kp.easing = 'EASE_IN_OUT'
                kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def key_prop(owner, path, frames, interp='BEZIER'):
    for f, v in frames:
        if path.startswith('['):
            owner[path[2:-2]] = v
        else:
            setattr(owner, path, v)
        owner.keyframe_insert(data_path=path, frame=f)
    ease(owner, interp)


def trace_sweep(frames):
    """Blue light running along the real top copper, driven by a keyed band position."""
    m = bpy.data.materials['O89 detail | Board from Gerbers']
    nt = m.node_tree
    N, L = nt.nodes.new, nt.links.new
    out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    surface = out.inputs['Surface'].links[0].from_socket
    copper = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeTexImage' and 'copper' in n.image.filepath).outputs['Color']
    uv = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeUVMap')
    sep = N('ShaderNodeSeparateXYZ')
    L(uv.outputs['UV'], sep.inputs[0])
    pos = N('ShaderNodeValue')
    pos.name = 'sweep position'
    dist = N('ShaderNodeMath'); dist.operation = 'SUBTRACT'
    L(sep.outputs['Y'], dist.inputs[0]); L(pos.outputs[0], dist.inputs[1])
    absd = N('ShaderNodeMath'); absd.operation = 'ABSOLUTE'
    L(dist.outputs[0], absd.inputs[0])
    band = N('ShaderNodeMapRange')
    band.inputs['From Min'].default_value = 0.
    band.inputs['From Max'].default_value = .06
    band.inputs['To Min'].default_value = 1.
    band.inputs['To Max'].default_value = 0.
    band.clamp = True
    L(absd.outputs[0], band.inputs['Value'])
    glow = N('ShaderNodeMath'); glow.operation = 'MULTIPLY'
    L(band.outputs['Result'], glow.inputs[0]); L(copper, glow.inputs[1])
    level = N('ShaderNodeValue'); level.name = 'sweep level'
    amount = N('ShaderNodeMath'); amount.operation = 'MULTIPLY'
    L(glow.outputs[0], amount.inputs[0]); L(level.outputs[0], amount.inputs[1])
    em = N('ShaderNodeEmission')
    em.inputs['Color'].default_value = (.08, .26, 1., 1)
    L(amount.outputs[0], em.inputs['Strength'])
    add = N('ShaderNodeAddShader')
    L(surface, add.inputs[0]); L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs['Surface'])
    for node, keys in ((pos, frames['pos']), (level, frames['level'])):
        sock = node.outputs[0]
        for f, v in keys:
            sock.default_value = v
            sock.keyframe_insert('default_value', frame=f)
    ease(nt)


def antenna_glow(keys):
    m = bpy.data.materials['O89 detail | Module antenna']
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (.08, .28, 1., 1)
    sock = b.inputs['Emission Strength']
    for f, v in keys:
        sock.default_value = v
        sock.keyframe_insert('default_value', frame=f)
    ease(m.node_tree)


def main():
    a = parse()
    s = bpy.context.scene
    w, h = (int(v) for v in a.size.split('x'))
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, LENGTH
    s.render.film_transparent = True
    s.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    s.cycles.device = 'GPU'
    s.cycles.samples = a.samples
    s.cycles.adaptive_threshold = .03
    s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'
    s.cycles.max_bounces = 6
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA'

    controls = bpy.data.objects['O89 Controls']
    for k in ('show_cables', 'show_cable_sleeve', 'show_bus_layout'):
        controls[k] = False
    for n in ('06 | Cables - editable Bezier curves', '11 | Cable management - sleeve and straps'):
        for o in bpy.data.collections[n].all_objects:
            o.hide_render = True

    # Cover: closed, lifts to a readable 70 mm, clears the macro shots, drops to the exploded height, lands.
    key_prop(controls, '["cover_lift_mm"]', [(1, 0.), (140, 0.), (205, 70.), (230, 70.), (264, 300.), (840, 300.), (900, 95.), (1040, 95.), (1150, 0.), (LENGTH, 0.)])
    # Status light: 160 ms on every 1.3 s, as the firmware blinks it.
    blink = []
    f = 1
    while f <= LENGTH:
        blink += [(f, 1), (f + 4, 0)]
        f += 31
    key_prop(controls, '["led_on"]', blink, 'CONSTANT')

    # Exploded view: plate drops away, the whole product turns and returns.
    plate = bpy.data.objects['plate-a']
    z0 = plate.location.z
    for fr, dz in ((841, 0.), (905, -.042), (1040, -.042), (1140, 0.), (LENGTH, 0.)):
        plate.location.z = z0 + dz
        plate.keyframe_insert('location', index=2, frame=fr)
    ease(plate)
    product = bpy.data.objects['Product | move or rotate the whole controller']
    r0 = product.rotation_euler.z
    for fr, dr in ((841, 0.), (1032, math.radians(38)), (1160, 0.), (LENGTH, 0.)):
        product.rotation_euler.z = r0 + dr
        product.keyframe_insert('rotation_euler', index=2, frame=fr)
    ease(product)

    trace_sweep({'pos': [(265, -.08), (408, 1.08)], 'level': [(264, 0.), (280, 2.4), (395, 2.4), (408, 0.)]})
    antenna_glow([(560, 0.), (610, 0.), (650, 1.6), (690, 1.6), (696, 0.)])

    # Lights: one film key per shot, grazing studio lights dimmed on the macro shots.
    key = bpy.data.lights.new('Film key', 'AREA')
    key.shape, key.size, key.energy = 'DISK', .24, 7.
    kob = bpy.data.objects.new('Film key', key)
    s.collection.objects.link(kob)
    kob.visible_camera = False
    for name, (start, end, _) in SHOTS.items():
        kob.location = KEY_LIGHT[name]
        kob.rotation_euler = (Vector((0, 0, 0)) - kob.location).to_track_quat('-Z', 'Y').to_euler()
        for fr in (start, end):
            kob.keyframe_insert('location', frame=fr)
            kob.keyframe_insert('rotation_euler', frame=fr)
    ease(kob, 'CONSTANT')
    for name in ('Light | Key softbox', 'Light | Front lettering'):
        bpy.data.objects[name].data.energy *= .4
    for o in bpy.data.collections['07 | Studio lights and backdrop'].objects:
        if o.type != 'LIGHT':
            continue
        full = o.data.energy
        for name, (start, end, _) in SHOTS.items():
            o.data.energy = full * GRAZING.get(name, 1.)
            for fr in (start, end):
                o.data.keyframe_insert('energy', frame=fr)
        ease(o.data, 'CONSTANT')
    fill = bpy.data.lights.new('Film top fill', 'AREA')
    fill.shape, fill.size, fill.energy = 'DISK', .5, 2.5
    fob = bpy.data.objects.new('Film top fill', fill)
    s.collection.objects.link(fob)
    fob.visible_camera = False
    fob.location = (0., -.05, .55)
    if s.world and s.world.node_tree.nodes.get('Background'):
        s.world.node_tree.nodes['Background'].inputs['Strength'].default_value *= .5

    s.timeline_markers.clear()
    cams = {}
    for name, (start, end, keys) in SHOTS.items():
        data = bpy.data.cameras.new(f'Film {name}')
        data.clip_start = .002
        data.sensor_width = 36
        cam = bpy.data.objects.new(f'Camera | Film {name}', data)
        s.collection.objects.link(cam)
        aim = bpy.data.objects.new(f'Film aim {name}', None)
        s.collection.objects.link(aim)
        t = cam.constraints.new('TRACK_TO')
        t.target, t.track_axis, t.up_axis = aim, 'TRACK_NEGATIVE_Z', 'UP_Y'
        data.dof.use_dof = True
        data.dof.focus_object = aim
        for fr, cp, ap, lens, fstop in keys:
            cam.location = Vector(cp) * MM
            cam.keyframe_insert('location', frame=fr)
            aim.location = Vector(ap) * MM
            aim.keyframe_insert('location', frame=fr)
            data.lens = lens
            data.keyframe_insert('lens', frame=fr)
            data.dof.aperture_fstop = fstop
            data.dof.keyframe_insert('aperture_fstop', frame=fr)
        for idb in (cam, aim, data):
            ease(idb)
        s.timeline_markers.new(name, frame=start).camera = cam
        cams[name] = (start, end, cam)

    def camera_at(fr):
        return next(c for st, en, c in cams.values() if st <= fr <= en)

    track = {k: [] for k in ANCHORS}
    for fr in range(1, LENGTH + 1):
        s.frame_set(fr)
        cam = camera_at(fr)
        s.camera = cam
        for k, p in ANCHORS.items():
            co = world_to_camera_view(s, cam, product.matrix_world @ (Vector(p) * MM))
            track[k].append([round(co.x, 4), round(1 - co.y, 4)])
    a.out.mkdir(parents=True, exist_ok=True)
    shots = [{'name': n, 'start': st, 'end': en} for n, (st, en, _) in cams.items()]
    (a.out / 'anchors.json').write_text(json.dumps({'fps': FPS, 'frames': LENGTH, 'shots': shots, 'anchors': track}))
    if a.anchors_only:
        return

    frames = []
    for part in a.frames.split(','):
        lo, _, hi = part.partition('-')
        frames.extend(range(int(lo), int(hi or lo) + 1))
    for fr in frames:
        out = a.out / f'frame-{fr:04d}.png'
        if out.exists():
            continue
        s.frame_set(fr)
        s.camera = camera_at(fr)
        s.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)


main()
