"""Render the website hero film: a 48 s loop (1440 frames at 30 fps) of the detailed Controller.

Runs on the scene saved by build_detailed_board.py, which Blender opens first:

    blender --background --python-exit-code 1 /tmp/home-media/controller-detailed.blend \\
      --python enclosure/blender/web/render_film.py -- --out /tmp/home-media/film

One camera moves without cuts along periodic curves through STATIONS: the
closed Controller, the cover lifting, the ESP32-C6 antenna, a light sweep along
the top copper, the STM32G0B1, the RS-485 transceivers, the exploded view
turning a full circle, reassembly and a forward flip that lands on the first
frame, so the video loops without a seam. The cover, plate, product and lights
move along monotone curves between their states instead of switching, and the
render uses motion blur. Writes transparent RGBA frame-NNNN.png files and
anchors.json (per-frame callout positions as 0-1 fractions of the frame, from
the render camera, and the window in which each callout is shown). Existing
frames are skipped, so an interrupted render resumes. The scene file is not
saved.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Quaternion, Vector

MM = .001
FPS = 30
SECONDS = 48
LENGTH = FPS * SECONDS

ANCHORS = {
    'cn': (-8., -53.6, 9.),
    'u7': (17.736, .227, 3.2),
    'antenna': (-6., 54.5, 2.6),
    'rs485': (-9.746, -38.258, 3.3),
    'board': (0., 0., 1.7),
}

# Camera stations: (seconds, aim mm, azimuth deg, elevation deg, distance mm, lens mm, f-stop).
# Periodic curves pass through every station, so the camera never cuts or stops and the last
# frame leads into the first. Azimuth is measured from +X; the terminal edge
# faces -Y.
STATIONS = [
    (0.0, (-40, -6, 12), -118, 16, 650, 60, 11),      # closed Controller, right of the hero copy
    (3.5, (-26, -6, 18), -114, 22, 560, 57, 11),
    (7.5, (-6, -8, 30), -108, 31, 460, 52, 11),       # cover lifting, terminals in view
    (10.5, (-4, 14, 14), -96, 44, 300, 48, 12),       # over the board as the cover leaves the frame
    (13.5, (-3.5, 43, 4.5), -64, 50, 95, 56, 19),     # ESP32-C6 antenna
    (16.5, (-5.6, 51, 3.5), -46, 58, 68, 58, 20),
    (18.5, (-2, 30, 2), -70, 55, 190, 42, 15),        # light sweep along the top copper
    (22.0, (2, -14, 2), -92, 50, 180, 42, 15),
    (24.5, (18.2, -.4, 3.1), -98, 40, 92, 64, 18),    # STM32G0B1, orbiting away from the white headers
    (28.0, (17.4, .6, 3.1), -128, 37, 86, 68, 18),
    (29.5, (0, -20, 3), -120, 58, 150, 52, 17),
    (31.0, (-24, -35, 3), -102, 68, 84, 50, 18),      # RS-485 transceivers, from above the terminal row
    (34.5, (6, -37, 3), -84, 66, 78, 50, 18),
    (39.5, (0, 0, 36), -118, 26, 660, 44, 11),        # exploded view turning
    (44.0, (0, 0, 26), -124, 22, 640, 48, 11),        # reassembly and flip
]

# Callout windows in seconds. HeroFilm.tsx shows a callout only inside its window.
WINDOWS = {
    'reveal': (0, 5), 'lift': (5.8, 10.2), 'u8': (13.6, 17.2), 'sweep': (18.4, 22.4),
    'u7': (24.6, 28.8), 'rs485': (30.9, 34.8), 'explode': (35.5, 43), 'assemble': (43, 48),
}
CALLOUT_ANCHORS = {'lift': 'cn', 'u8': 'antenna', 'sweep': 'board', 'u7': 'u7', 'rs485': 'rs485'}

# Object states as (seconds, value) keys, joined by monotone curves: they rest on repeated
# values and pass through the others without stopping.
COVER_MM = [(0, 0), (5, 0), (9.5, 80), (13, 300), (37, 300), (40.5, 95), (43.8, 95), (45.6, 0), (48, 0)]
PLATE_MM = [(0, 0), (38, 0), (40.5, -42), (44, -42), (45.6, 0), (48, 0)]
SPIN_DEG = [(0, 0), (38.5, 0), (44, 360), (48, 360)]
FLIP_DEG = [(0, 0), (45.5, 0), (48, 360)]
FLIP_RISE_MM = [(0, 0), (45.5, 0), (46.75, 45), (48, 0)]
# The flip turns about a level axis across the opening camera's view, through the product's centre.
FLIP_AXIS = Vector((math.cos(math.radians(-28)), math.sin(math.radians(-28)), 0))
PRODUCT_CENTRE_MM = (0, 0, 2.5)
SWEEP_POSITION = [(0, 1.08), (17.5, 1.08), (22.5, -.08), (48, -.08)]
SWEEP_LEVEL = [(0, 0), (17.2, 0), (18, 2.4), (22, 2.4), (22.8, 0), (48, 0)]
ANTENNA_GLOW = [(0, 0), (12.5, 0), (14.5, 1.6), (16.5, 1.6), (18, 0), (48, 0)]

WIDE_KEY = (-.30, .26, .34)
MACRO_KEY = (-.10, -.30, .30)
CHIP_KEY = (-.08, -.32, .30)
KEY_LIGHT = [(0, WIDE_KEY), (9.5, WIDE_KEY), (13, MACRO_KEY), (22, MACRO_KEY), (24.5, CHIP_KEY),
             (28.5, CHIP_KEY), (31, WIDE_KEY), (48, WIDE_KEY)]
# Grazing studio lights, as a fraction of their scene energy.
GRAZING = [(0, 1), (10, 1), (13, .5), (17.2, .5), (18.6, .08), (34.8, .08), (37.5, 1), (48, 1)]


def parse():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--frames', default=f'1-{LENGTH}', help='comma-separated frames or ranges, e.g. 1-120,400')
    p.add_argument('--samples', type=int, default=40)
    p.add_argument('--size', default='1920x1080')
    p.add_argument('--anchors-only', action='store_true', help='write anchors.json without rendering')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    return p.parse_args(argv)


def seconds(fr):
    return (fr - 1) / FPS


def monotone(keys):
    """Piecewise cubic through (seconds, value) keys that never overshoots (Fritsch-Carlson)."""
    t = [float(k[0]) for k in keys]
    v = [float(k[1]) for k in keys]
    n = len(t)
    h = [t[i + 1] - t[i] for i in range(n - 1)]
    d = [(v[i + 1] - v[i]) / h[i] for i in range(n - 1)]
    m = [0.] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def at(x):
        if x <= t[0]:
            return v[0]
        if x >= t[-1]:
            return v[-1]
        i = next(j for j in range(n - 1) if x < t[j + 1])
        s = (x - t[i]) / h[i]
        return ((2 * s ** 3 - 3 * s ** 2 + 1) * v[i] + (s ** 3 - 2 * s ** 2 + s) * h[i] * m[i]
                + (-2 * s ** 3 + 3 * s ** 2) * v[i + 1] + (s ** 3 - s ** 2) * h[i] * m[i + 1])
    return at


def periodic_monotone(times, values, period):
    """Periodic Fritsch-Carlson cubic: holds still where neighbouring stations repeat a value, never overshoots."""
    n = len(times)
    t = [times[-1] - period] + list(times) + [times[0] + period, times[1] + period]
    y = [values[-1]] + list(values) + [values[0], values[1]]
    h = [t[i + 1] - t[i] for i in range(len(t) - 1)]
    d = [(y[i + 1] - y[i]) / h[i] for i in range(len(t) - 1)]
    m = [0.] * len(t)
    for i in range(1, len(t) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def at(x):
        x %= period
        i = max(j for j in range(1, n + 1) if t[j] <= x)
        u = (x - t[i]) / h[i]
        return ((2 * u ** 3 - 3 * u ** 2 + 1) * y[i] + (u ** 3 - 2 * u ** 2 + u) * h[i] * m[i]
                + (-2 * u ** 3 + 3 * u ** 2) * y[i + 1] + (u ** 3 - u ** 2) * h[i] * m[i + 1])
    return at


def periodic_hermite(times, values, period):
    """Periodic cubic with centred-difference slopes: continuous velocity through every station."""
    n = len(times)
    t = list(times) + [times[0] + period]
    y = list(values) + [values[0]]

    def slope(i):
        prev_t, prev_y = (times[i - 1], values[i - 1]) if i > 0 else (times[-1] - period, values[-1])
        next_t, next_y = (t[i + 1], y[i + 1])
        return (next_y - prev_y) / (next_t - prev_t)
    m = [slope(i) for i in range(n)] + [slope(0)]

    def at(x):
        x %= period
        i = max(j for j in range(n) if t[j] <= x)
        h = t[i + 1] - t[i]
        u = (x - t[i]) / h
        return ((2 * u ** 3 - 3 * u ** 2 + 1) * y[i] + (u ** 3 - 2 * u ** 2 + u) * h * m[i]
                + (-2 * u ** 3 + 3 * u ** 2) * y[i + 1] + (u ** 3 - u ** 2) * h * m[i + 1])
    return at


def curves(idb):
    ad = idb.animation_data
    out = []
    if ad and ad.action:
        for layer in getattr(ad.action, 'layers', []):
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    return out


def interpolate(idb, interp):
    for fc in curves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = interp


def bake(owner, path, value_at, index=-1):
    """Key a property on every frame, linearly between frames, so motion blur follows the curve."""
    for fr in range(1, LENGTH + 1):
        value = value_at(seconds(fr))
        if path.startswith('['):
            owner[path[2:-2]] = value
        else:
            prop = getattr(owner, path)
            if index >= 0:
                prop[index] = value
            elif hasattr(prop, '__len__'):
                prop[:] = value
            else:
                setattr(owner, path, value)
        owner.keyframe_insert(data_path=path, frame=fr, index=index)
    interpolate(owner.id_data, 'LINEAR')


def trace_sweep():
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
    bake(pos.outputs[0], 'default_value', monotone(SWEEP_POSITION))
    bake(level.outputs[0], 'default_value', monotone(SWEEP_LEVEL))


def antenna_glow():
    m = bpy.data.materials['O89 detail | Module antenna']
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (.08, .28, 1., 1)
    bake(b.inputs['Emission Strength'], 'default_value', monotone(ANTENNA_GLOW))


def camera_path():
    """Per-frame camera position and aim in metres, lens and f-stop, from the periodic spline."""
    times = [s[0] for s in STATIONS]
    # The aim holds on each subject between its stations and never overshoots, so a chip stays
    # centred while the camera orbits it. The camera's angles, distance and optics keep moving
    # through every station. Distance is interpolated in log space so dollies read at an even pace.
    channels = [periodic_monotone(times, [s[1][k] for s in STATIONS], SECONDS) for k in range(3)]
    az = periodic_hermite(times, [s[2] for s in STATIONS], SECONDS)
    el = periodic_hermite(times, [s[3] for s in STATIONS], SECONDS)
    dist = periodic_hermite(times, [math.log(s[4]) for s in STATIONS], SECONDS)
    lens = periodic_hermite(times, [s[5] for s in STATIONS], SECONDS)
    fstop = periodic_hermite(times, [s[6] for s in STATIONS], SECONDS)

    def at(x):
        aim = Vector([c(x) for c in channels]) * MM
        a, e, d = math.radians(az(x)), math.radians(el(x)), math.exp(dist(x)) * MM
        eye = aim + Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * d
        return eye, aim, lens(x), fstop(x)
    return at


def main():
    a = parse()
    s = bpy.context.scene
    w, h = (int(v) for v in a.size.split('x'))
    s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = w, h, 100
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, LENGTH
    s.render.film_transparent = True
    s.render.use_motion_blur = True
    s.render.motion_blur_shutter = .5
    s.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'METAL'
    s.cycles.device = 'GPU'
    s.cycles.samples = a.samples
    s.cycles.adaptive_threshold = .03
    s.cycles.use_animated_seed = True
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

    bake(controls, '["cover_lift_mm"]', monotone(COVER_MM))
    # Status light: on for 5 frames every 40 (167 ms every 1.33 s), which repeats exactly over the loop.
    for fr in range(1, LENGTH + 1, 40):
        for f, v in ((fr, 1), (fr + 5, 0)):
            controls['led_on'] = v
            controls.keyframe_insert(data_path='["led_on"]', frame=f)
    for fc in curves(controls):
        if fc.data_path == '["led_on"]':
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'

    plate = bpy.data.objects['plate-a']
    z0 = plate.location.z
    plate_mm = monotone(PLATE_MM)
    bake(plate, 'location', lambda x: z0 + plate_mm(x) * MM, index=2)

    product = bpy.data.objects['Product | move or rotate the whole controller']
    # The spin and flip are relative to the product's saved placement. STATIONS and ANCHORS
    # frame the scene's default placement at the origin.
    base_location = product.location.copy()
    base_rotation = product.rotation_euler.to_quaternion()
    product.rotation_mode = 'QUATERNION'
    spin, flip, rise = monotone(SPIN_DEG), monotone(FLIP_DEG), monotone(FLIP_RISE_MM)
    centre = Vector(PRODUCT_CENTRE_MM) * MM

    def turn(x):
        return Quaternion((0, 0, 1), math.radians(spin(x))) @ Quaternion(FLIP_AXIS, math.radians(flip(x)))
    bake(product, 'rotation_quaternion', lambda x: base_rotation @ turn(x))
    bake(product, 'location', lambda x: base_location + base_rotation @ (centre + Vector((0, 0, rise(x) * MM)) - turn(x) @ centre))

    trace_sweep()
    antenna_glow()

    key = bpy.data.lights.new('Film key', 'AREA')
    key.shape, key.size, key.energy = 'DISK', .24, 7.
    kob = bpy.data.objects.new('Film key', key)
    s.collection.objects.link(kob)
    kob.visible_camera = False
    key_axes = [monotone([(t, p[k]) for t, p in KEY_LIGHT]) for k in range(3)]

    def key_at(x):
        return Vector([c(x) for c in key_axes])
    bake(kob, 'location', key_at)
    bake(kob, 'rotation_euler', lambda x: (-key_at(x)).to_track_quat('-Z', 'Y').to_euler())
    for name in ('Light | Key softbox', 'Light | Front lettering'):
        bpy.data.objects[name].data.energy *= .4
    grazing = monotone(GRAZING)
    for o in bpy.data.collections['07 | Studio lights and backdrop'].objects:
        if o.type == 'LIGHT':
            full = o.data.energy
            bake(o.data, 'energy', lambda x, full=full: full * grazing(x))
    fill = bpy.data.lights.new('Film top fill', 'AREA')
    fill.shape, fill.size, fill.energy = 'DISK', .5, 2.5
    fob = bpy.data.objects.new('Film top fill', fill)
    s.collection.objects.link(fob)
    fob.visible_camera = False
    fob.location = (0., -.05, .55)
    if s.world and s.world.node_tree.nodes.get('Background'):
        s.world.node_tree.nodes['Background'].inputs['Strength'].default_value *= .5

    s.timeline_markers.clear()
    data = bpy.data.cameras.new('Film')
    data.clip_start = .002
    data.sensor_width = 36
    cam = bpy.data.objects.new('Camera | Film', data)
    s.collection.objects.link(cam)
    aim = bpy.data.objects.new('Film aim', None)
    s.collection.objects.link(aim)
    t = cam.constraints.new('TRACK_TO')
    t.target, t.track_axis, t.up_axis = aim, 'TRACK_NEGATIVE_Z', 'UP_Y'
    data.dof.use_dof = True
    data.dof.focus_object = aim
    path = camera_path()
    bake(cam, 'location', lambda x: path(x)[0])
    bake(aim, 'location', lambda x: path(x)[1])
    bake(data, 'lens', lambda x: path(x)[2])
    bake(data.dof, 'aperture_fstop', lambda x: path(x)[3])
    s.camera = cam

    track = {k: [] for k in ANCHORS}
    for fr in range(1, LENGTH + 1):
        s.frame_set(fr)
        for k, p in ANCHORS.items():
            co = world_to_camera_view(s, cam, product.matrix_world @ (Vector(p) * MM))
            track[k].append([round(co.x, 4), round(1 - co.y, 4)])
    shots = [{'name': n, 'start': round(st * FPS) + 1, 'end': round(en * FPS)} for n, (st, en) in WINDOWS.items()]
    for shot in shots:
        anchor = CALLOUT_ANCHORS.get(shot['name'])
        if anchor:
            points = track[anchor][shot['start'] - 1:shot['end']]
            inside = sum(.05 < x < .95 and .05 < y < .95 for x, y in points) / len(points)
            print(f"callout {shot['name']}: anchor in frame for {inside:.0%} of its window")
    a.out.mkdir(parents=True, exist_ok=True)
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
        s.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)


main()
