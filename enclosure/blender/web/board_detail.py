"""Replace the STEP board's box components with detailed parts built from the fab files.

Imported by build_detailed_board.py inside Blender; it has no CLI of its own.

Every part comes from board A's fabrication build (FAB_BUILD, relative to the
repository root): pick-and-place gives the centre and pin 1, the footprint name gives
the package, the BOM gives the marking. The board surface uses the top copper,
pad and silkscreen masks rendered from the Gerbers by gerber_layers.mjs.

Connectors (CN*) keep the scene's existing proxies. Footprints without a builder
are printed as "unhandled footprint" and left out.
"""
import csv
import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

MM = 0.001
TOP = 1.69  # board top surface, mm, as imported
FAB_BUILD = 'boards/controller-a/build/2026-09-09'

# 0805 resistor values to their 4-digit marking codes.
R_CODES = {
    '100kΩ': '1003', '52.3kΩ': '5232', '10kΩ': '1002', '330kΩ': '3303', '51.1kΩ': '5112',
    '120Ω': '1200', '1kΩ': '1001', '4.7kΩ': '4701', '31.6kΩ': '3162', '100Ω': '1000',
    '150Ω': '1500', '330Ω': '3300', '560Ω': '5600',
}
MARKINGS = {
    'STM32G0B1RET6': ('STM32G0B1', 'RET6'),
    'MAX13487EESA+T': ('MAX13487', 'EESA+'),
    'TJA1051T/3/1J': ('TJA1051T/3',),
    'TPS54331DR': ('54331',),
    'FM24W256-GTR': ('FM24W256', 'G'),
    'W25Q128JVSIQ': ('25Q128JVSQ',),
    'SPM6530T-150M-HZ': ('150',),
    'SMBJ18A': ('LE',),
    'SS34': ('SS34',),
}


# ---------------------------------------------------------------- materials

def principled(name, color, rough, metal=0., coat=0., coat_rough=.1, emission=None, strength=0., transmission=0.):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = coat_rough
    b.inputs['Transmission Weight'].default_value = transmission
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


def materials():
    return {
        'epoxy': principled('O89 detail | IC epoxy', (.008, .008, .009), .55),
        'mark': principled('O89 detail | Laser marking', (.55, .55, .54), .8),
        'tin': principled('O89 detail | Tin leads', (.8, .8, .78), .24, metal=1.),
        'mlcc': principled('O89 detail | MLCC ceramic', (.26, .19, .12), .45),
        'r_body': principled('O89 detail | Resistor ceramic', (.5, .5, .48), .5),
        'r_top': principled('O89 detail | Resistor coat', (.012, .012, .013), .4),
        'r_print': principled('O89 detail | Resistor print', (.82, .82, .8), .7),
        'shield': principled('O89 detail | Module shield', (.72, .72, .71), .3, metal=1.),
        'etch': principled('O89 detail | Shield etching', (.05, .05, .052), .55, metal=.3),
        'fuse_print': principled('O89 detail | Fuse print', (.8, .8, .78), .7),
        'copper_ring': principled('O89 detail | Inductor winding', (.32, .17, .08), .45, metal=.5),
        'module_pcb': principled('O89 detail | Module PCB', (.012, .02, .03), .3, coat=.6),
        'module_trace': principled('O89 detail | Module antenna', (.03, .05, .07), .28, coat=.6),
        'gold': principled('O89 detail | ENIG', (.95, .72, .42), .2, metal=1.),
        'lid': principled('O89 detail | Crystal lid', (.8, .8, .79), .22, metal=1.),
        'ceramic': principled('O89 detail | Crystal base', (.75, .68, .55), .5),
        'ferrite': principled('O89 detail | Inductor body', (.045, .045, .048), .72),
        'band': principled('O89 detail | Cathode band', (.55, .55, .56), .6),
        'polyfuse': principled('O89 detail | Polyfuse', (.06, .035, .022), .45),
        'header': principled('O89 detail | Header nylon', (.02, .02, .022), .55),
        'shunt': principled('O89 detail | Shunt', (.012, .012, .013), .35),
        'led_body': principled('O89 detail | LED body', (.86, .86, .84), .35),
        'led_lens': principled('O89 detail | LED lens', (.45, .85, .35), .12, emission=(.18, .62, .39), strength=0.),
    }


def board_material(gerber_dir: Path):
    m = bpy.data.materials.new('O89 detail | Board from Gerbers')
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N = nt.nodes.new
    L = nt.links.new
    out = N('ShaderNodeOutputMaterial')
    uv = N('ShaderNodeUVMap'); uv.uv_map = 'gerber'

    def img(layer):
        t = N('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(gerber_dir / f'top-{layer}.png'), check_existing=True)
        t.image.colorspace_settings.name = 'Non-Color'
        t.interpolation = 'Linear'
        t.extension = 'CLIP'
        L(uv.outputs['UV'], t.inputs['Vector'])
        return t.outputs['Color']

    copper, pads, silk, board = img('copper'), img('pads'), img('silk'), img('board')

    mask_col = N('ShaderNodeMix'); mask_col.data_type = 'RGBA'
    mask_col.inputs['A'].default_value = (.004, .026, .014, 1)  # mask over bare FR-4
    mask_col.inputs['B'].default_value = (.008, .052, .027, 1)  # mask over copper
    L(copper, mask_col.inputs['Factor'])
    mask = N('ShaderNodeBsdfPrincipled')
    L(mask_col.outputs['Result'], mask.inputs['Base Color'])
    mask.inputs['Roughness'].default_value = .5
    mask.inputs['Coat Weight'].default_value = .35
    mask.inputs['Coat Roughness'].default_value = .22
    gold = N('ShaderNodeBsdfPrincipled')
    gold.inputs['Base Color'].default_value = (.95, .72, .42, 1)
    gold.inputs['Metallic'].default_value = 1.
    gold.inputs['Roughness'].default_value = .22
    white = N('ShaderNodeBsdfPrincipled')
    white.inputs['Base Color'].default_value = (.86, .87, .85, 1)
    white.inputs['Roughness'].default_value = .62

    height = N('ShaderNodeMath'); height.operation = 'ADD'
    silk_h = N('ShaderNodeMath'); silk_h.operation = 'MULTIPLY'; silk_h.inputs[1].default_value = .8
    L(silk, silk_h.inputs[0])
    L(copper, height.inputs[0]); L(silk_h.outputs[0], height.inputs[1])
    bump = N('ShaderNodeBump'); bump.inputs['Distance'].default_value = .000035; bump.inputs['Strength'].default_value = 1.
    L(height.outputs[0], bump.inputs['Height'])
    for s in (mask, gold, white):
        L(bump.outputs['Normal'], s.inputs['Normal'])
    L(bump.outputs['Normal'], mask.inputs['Coat Normal'])

    m1 = N('ShaderNodeMixShader'); L(pads, m1.inputs['Fac']); L(mask.outputs[0], m1.inputs[1]); L(gold.outputs[0], m1.inputs[2])
    m2 = N('ShaderNodeMixShader'); L(silk, m2.inputs['Fac']); L(m1.outputs[0], m2.inputs[1]); L(white.outputs[0], m2.inputs[2])

    # Sides and bottom: plain mask; top: the Gerber stack; holes: transparent.
    geo = N('ShaderNodeNewGeometry')
    sep = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Normal'], sep.inputs[0])
    is_top = N('ShaderNodeMath'); is_top.operation = 'GREATER_THAN'; is_top.inputs[1].default_value = .5
    L(sep.outputs['Z'], is_top.inputs[0])
    side = N('ShaderNodeBsdfPrincipled'); side.inputs['Base Color'].default_value = (.012, .05, .026, 1); side.inputs['Roughness'].default_value = .45
    m3 = N('ShaderNodeMixShader'); L(is_top.outputs[0], m3.inputs['Fac']); L(side.outputs[0], m3.inputs[1]); L(m2.outputs[0], m3.inputs[2])
    hole = N('ShaderNodeBsdfTransparent')
    solid = N('ShaderNodeMath'); solid.operation = 'GREATER_THAN'; solid.inputs[1].default_value = .5
    L(board, solid.inputs[0])
    keep = N('ShaderNodeMath'); keep.operation = 'MAXIMUM'
    not_top = N('ShaderNodeMath'); not_top.operation = 'SUBTRACT'; not_top.inputs[0].default_value = 1.
    L(is_top.outputs[0], not_top.inputs[1])
    L(solid.outputs[0], keep.inputs[0]); L(not_top.outputs[0], keep.inputs[1])
    m4 = N('ShaderNodeMixShader'); L(keep.outputs[0], m4.inputs['Fac']); L(hole.outputs[0], m4.inputs[1]); L(m3.outputs[0], m4.inputs[2])
    L(m4.outputs[0], out.inputs['Surface'])
    return m


# ---------------------------------------------------------------- geometry

def new_object(name, bm, mats, parent, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    return ob


def add_box(bm, cx, cy, z0, sx, sy, sz, mat=0, bevel=0.):
    """Axis-aligned box in mm; bevel softens the top edges only."""
    x0, x1, y0, y1, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0 + sz
    b = min(bevel, sx / 3, sy / 3, sz / 2)
    ring_lo = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ring_hi = [(x0 + b, y0 + b), (x1 - b, y0 + b), (x1 - b, y1 - b), (x0 + b, y1 - b)]
    vs_lo = [bm.verts.new(Vector((x * MM, y * MM, z0 * MM))) for x, y in ring_lo]
    vs_mid = [bm.verts.new(Vector((x * MM, y * MM, (z1 - b) * MM))) for x, y in ring_lo]
    vs_hi = [bm.verts.new(Vector((x * MM, y * MM, z1 * MM))) for x, y in ring_hi]
    faces = [bm.faces.new(vs_hi)]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((vs_lo[i], vs_lo[j], vs_mid[j], vs_mid[i])))
        if b > 0:
            faces.append(bm.faces.new((vs_mid[i], vs_mid[j], vs_hi[j], vs_hi[i])))
    faces.append(bm.faces.new(list(reversed(vs_lo))))
    for f in faces:
        f.material_index = mat
    return faces


def add_profile(bm, pts, y0, y1, mat, axis_sign=1, along_x=True, cx=0., cy=0., row=0.):
    """Extrude a closed (d, z) profile across a lead's width; d runs outward from the body."""
    loops = []
    for y in (y0, y1):
        loop = []
        for d, z in pts:
            o = row + d
            x, yy = (cx + axis_sign * o, cy + y) if along_x else (cx + y, cy + axis_sign * o)
            loop.append(bm.verts.new(Vector((x * MM, yy * MM, z * MM))))
        loops.append(loop)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new((loops[0][i], loops[0][j], loops[1][j], loops[1][i]))
        f.material_index = mat
    for loop in loops:
        try:
            f = bm.faces.new(loop)
            f.material_index = mat
        except ValueError:
            pass


def gull_wing(z_exit, span_out, thick=.15):
    """Lead profile from the body wall (d=0) to the foot end (d=span_out)."""
    t = thick
    knee = .28
    foot = min(.6, span_out * .45)
    return [
        (-.05, z_exit), (knee, z_exit), (knee + .18, TOP + t + .02), (span_out, TOP + t + .02),
        (span_out, TOP + .02), (knee + .18 - t, TOP + .02), (knee - t * .6, z_exit - t), (-.05, z_exit - t),
    ]


# ---------------------------------------------------------------- parts

class Part:
    def __init__(self, row, bom):
        self.ref = row['Designator']
        self.fp = row['Footprint']
        self.x = float(row['Mid X'].rstrip('m'))
        self.y = float(row['Mid Y'].rstrip('m'))
        px, py = float(row['Pad X'].rstrip('m')), float(row['Pad Y'].rstrip('m'))
        self.dx, self.dy = px - self.x, py - self.y
        self.rot = float(row['Rotation'])
        self.value = bom.get(self.ref, ('', ''))
        # Row axis: the side the leads leave from (larger pin-1 offset).
        self.row_x = abs(self.dx) >= abs(self.dy)


def read_parts(pnp: Path, bom_path: Path):
    bom = {}
    with bom_path.open(encoding='utf-8', errors='replace') as f:
        for r in csv.DictReader(f):
            for ref in r['Designator'].split(','):
                bom[ref.strip()] = (r['Comment'], r['Manufacturer Part'])
    with pnp.open(encoding='utf-8', errors='replace') as f:
        return [Part(r, bom) for r in csv.DictReader(f) if r['Layer'] == 'T']


def text_mesh(lines, size, font, t_dir, pin1, cx, cy, z, mat, coll, parent, name, line_gap=1.25):
    """Flat laser-marked text centred at (cx, cy), baseline along t_dir, pin 1 at lower left."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = '\n'.join(lines)
    cu.font = font
    cu.size = size * MM
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.space_line = line_gap
    tmp = bpy.data.objects.new(name + ' tmp', cu)
    coll.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    ang = math.atan2(t_dir[1], t_dir[0])
    ob.matrix_world = Matrix.Translation(Vector((cx * MM, cy * MM, z * MM))) @ Matrix.Rotation(ang, 4, 'Z')
    return ob


def text_dir(p):
    """Baseline direction that puts pin 1 at the text's lower left."""
    for t in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        u = (-t[1], t[0])
        if t[0] * p.dx + t[1] * p.dy < 0 and u[0] * p.dx + u[1] * p.dy < 0:
            return t
    return (1, 0)


def build_ic(p, M, coll, parent, font, rows, pitch, n_side, body_row, body_pitch, h, span, lead_w, marks):
    """Gull-wing IC. rows: 2 (SOIC/SOT) or 4 (QFP). body_row is the body size across the lead rows."""
    bm = bmesh.new()
    standoff = .1 if rows == 4 else .12
    z0 = TOP + standoff
    sx, sy = (body_row, body_pitch) if p.row_x else (body_pitch, body_row)
    add_box(bm, p.x, p.y, z0, sx, sy, h, mat=0, bevel=.12)
    z_exit = z0 + h * .45
    out = (span - body_row) / 2
    sides = [(True, 1), (True, -1), (False, 1), (False, -1)] if rows == 4 else ([(p.row_x, 1), (p.row_x, -1)])
    for along_x, sign in sides:
        count = n_side if isinstance(n_side, int) else n_side[0 if sign > 0 else 1]
        half = (body_row if along_x == p.row_x or rows == 4 else body_pitch) / 2
        for k in range(count):
            off = (k - (count - 1) / 2) * pitch
            prof = gull_wing(z_exit, out)
            add_profile(bm, prof, off - lead_w / 2, off + lead_w / 2, 1, axis_sign=sign, along_x=along_x,
                        cx=p.x, cy=p.y, row=half)
    ob = new_object(f'{p.ref} | {p.value[1]}', bm, [M['epoxy'], M['tin']], parent, coll)
    top = z0 + h + .004
    t = text_dir(p)
    # Pin-1 dimple toward the pin-1 corner.
    if rows == 4 or body_row > 3:
        bm2 = bmesh.new()
        r = .45 if rows == 4 else .35
        cx = p.x + math.copysign(sx / 2 - r - .5, p.dx)
        cy = p.y + math.copysign(sy / 2 - r - .5, p.dy)
        bmesh.ops.create_circle(bm2, cap_ends=True, radius=r * MM, segments=24,
                                matrix=Matrix.Translation(Vector((cx * MM, cy * MM, (top - .002) * MM))))
        new_object(f'{p.ref} | pin 1', bm2, [M['mark']], parent, coll)
    if marks:
        width = max(len(s) for s in marks)
        along = sx if t[0] else sy
        size = min(along * .78 / max(width * .62, 1), (sy if t[0] else sx) * .5 / len(marks))
        text_mesh(marks, size, font, t, p, p.x, p.y, top, M['mark'], coll, parent, f'{p.ref} | marking')
    return ob


def build_two_terminal(p, M, coll, parent, font, L, W, H, kind):
    bm = bmesh.new()
    lx, wy = (L, W) if p.row_x else (W, L)
    cap = .45 if L < 2.5 else .55
    if kind in ('mlcc', 'res', 'fuse', 'led'):
        body_mat = {'mlcc': 0, 'res': 0, 'fuse': 0, 'led': 0}[kind]
        if p.row_x:
            add_box(bm, p.x, p.y, TOP + .02, L - 2 * cap, W, H, mat=body_mat, bevel=.05)
            for s in (-1, 1):
                add_box(bm, p.x + s * (L / 2 - cap / 2), p.y, TOP + .02, cap, W + .02, H + .02, mat=1, bevel=.06)
        else:
            add_box(bm, p.x, p.y, TOP + .02, W, L - 2 * cap, H, mat=body_mat, bevel=.05)
            for s in (-1, 1):
                add_box(bm, p.x, p.y + s * (L / 2 - cap / 2), TOP + .02, W + .02, cap, H + .02, mat=1, bevel=.06)
        mats = {'mlcc': [M['mlcc'], M['tin']], 'res': [M['r_body'], M['tin']],
                'fuse': [M['polyfuse'], M['tin']], 'led': [M['led_body'], M['tin']]}[kind]
        ob = new_object(f'{p.ref} | {p.value[1]}', bm, mats, parent, coll)
        if kind == 'res':
            bm2 = bmesh.new()
            add_box(bm2, p.x, p.y, TOP + .02 + H, (L - 2 * cap) if p.row_x else W - .1, W - .1 if p.row_x else (L - 2 * cap), .012)
            new_object(f'{p.ref} | coat', bm2, [M['r_top']], parent, coll)
            code = R_CODES.get(p.value[0])
            if code:
                t = (1, 0) if p.row_x else (0, 1)
                text_mesh([code], .62, font, t, p, p.x, p.y, TOP + .02 + H + .016, M['r_print'], coll, parent, f'{p.ref} | code')
        if kind == 'fuse' and L > 3:
            t = (1, 0) if p.row_x else (0, 1)
            text_mesh(['200'], 1.0, font, t, p, p.x, p.y, TOP + .02 + H + .004, M['fuse_print'], coll, parent, f'{p.ref} | code')
        if kind == 'led':
            bm2 = bmesh.new()
            add_box(bm2, p.x, p.y, TOP + .02 + H, (L - 2 * cap) * .9 if p.row_x else W * .8, W * .8 if p.row_x else (L - 2 * cap) * .9, .25, bevel=.1)
            new_object(f'{p.ref} | lens', bm2, [M['led_lens']], parent, coll)
        return ob
    # Molded diodes: body with a cathode band toward pin 1, flat tabs under the ends.
    add_box(bm, p.x, p.y, TOP + .05, lx, wy, H, mat=0, bevel=.18)
    tab = .9
    if p.row_x:
        for s in (-1, 1):
            add_box(bm, p.x + s * (L / 2 + .15), p.y, TOP, tab, W * .55, .12, mat=1)
    else:
        for s in (-1, 1):
            add_box(bm, p.x, p.y + s * (L / 2 + .15), TOP, W * .55, tab, .12, mat=1)
    ob = new_object(f'{p.ref} | {p.value[1]}', bm, [M['epoxy'], M['tin']], parent, coll)
    bm2 = bmesh.new()
    bx = p.x + (math.copysign(L / 2 - .45, p.dx) if p.row_x else 0)
    by = p.y + (0 if p.row_x else math.copysign(L / 2 - .45, p.dy))
    add_box(bm2, bx, by, TOP + .05 + H, .35 if p.row_x else W - .3, W - .3 if p.row_x else .35, .01)
    new_object(f'{p.ref} | band', bm2, [M['band']], parent, coll)
    return ob


def build_sot23(p, M, coll, parent, font):
    """SOT-23-3: two leads on the pin-1 side, one opposite."""
    bm = bmesh.new()
    body_row, body_pitch, h = 1.3, 2.9, 1.0
    sx, sy = (body_row, body_pitch) if p.row_x else (body_pitch, body_row)
    z0 = TOP + .08
    add_box(bm, p.x, p.y, z0, sx, sy, h, mat=0, bevel=.1)
    out = (2.4 - body_row) / 2 + .1
    s1 = 1 if (p.dx if p.row_x else p.dy) > 0 else -1
    for sign, offs in ((s1, (-.95, .95)), (-s1, (0.,))):
        for off in offs:
            add_profile(bm, gull_wing(z0 + h * .45, out, .12), off - .2, off + .2, 1, axis_sign=sign,
                        along_x=p.row_x, cx=p.x, cy=p.y, row=body_row / 2)
    return new_object(f'{p.ref} | {p.value[1]}', bm, [M['epoxy'], M['tin']], parent, coll)


def build_inductor(p, M, coll, parent, font):
    """Shielded power inductor: rounded square ferrite with the drum winding visible on top."""
    bm = bmesh.new()
    add_box(bm, p.x, p.y, TOP + .02, 7.1 if p.row_x else 6.5, 6.5 if p.row_x else 7.1, 2.6, mat=0, bevel=.9)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=2.9 * MM, radius2=2.9 * MM, depth=.3 * MM,
                          matrix=Matrix.Translation(Vector((p.x * MM, p.y * MM, (TOP + 2.62 + .15) * MM))))
    ob = new_object(f'{p.ref} | {p.value[1]}', bm, [M['ferrite']], parent, coll)
    bm2 = bmesh.new()
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=48, radius1=2.3 * MM, radius2=2.3 * MM, depth=.06 * MM,
                          matrix=Matrix.Translation(Vector((p.x * MM, p.y * MM, (TOP + 2.93) * MM))))
    new_object(f'{p.ref} | winding', bm2, [M['copper_ring']], parent, coll)
    bm3 = bmesh.new()
    bmesh.ops.create_cone(bm3, cap_ends=True, segments=36, radius1=1.35 * MM, radius2=1.35 * MM, depth=.08 * MM,
                          matrix=Matrix.Translation(Vector((p.x * MM, p.y * MM, (TOP + 2.95) * MM))))
    new_object(f'{p.ref} | core', bm3, [M['ferrite']], parent, coll)
    return ob


def build_crystal(p, M, coll, parent, font, L, W, H):
    bm = bmesh.new()
    sx, sy = (L, W) if p.row_x else (W, L)
    add_box(bm, p.x, p.y, TOP + .02, sx, sy, H * .45, mat=0, bevel=.05)
    add_box(bm, p.x, p.y, TOP + .02 + H * .45, sx - .3, sy - .3, H * .55, mat=1, bevel=.12)
    return new_object(f'{p.ref} | {p.value[1]}', bm, [M['ceramic'], M['lid']], parent, coll)


def build_header(p, M, coll, parent, pins, shunt):
    """2.54 mm pin header; the termination jumpers carry a shunt (fitted by default)."""
    bm = bmesh.new()
    along_x = p.row_x
    L = pins * 2.54
    sx, sy = (L, 2.54) if along_x else (2.54, L)
    add_box(bm, p.x, p.y, TOP, sx, sy, 2.5, mat=0, bevel=.2)
    for k in range(pins):
        off = (k - (pins - 1) / 2) * 2.54
        cx, cy = (p.x + off, p.y) if along_x else (p.x, p.y + off)
        add_box(bm, cx, cy, TOP + 2.5, .64, .64, 6.0 if not shunt else 3.5, mat=1, bevel=.08)
    ob = new_object(f'{p.ref} | header', bm, [M['header'], M['gold']], parent, coll)
    if shunt:
        bm2 = bmesh.new()
        add_box(bm2, p.x, p.y, TOP + 2.5, (L - .1) if along_x else 2.4, 2.4 if along_x else (L - .1), 4.2, mat=0, bevel=.35)
        new_object(f'{p.ref} | shunt', bm2, [M['shunt']], parent, coll)
    return ob


def build_wroom(p, M, coll, parent, font):
    """ESP32-C6-WROOM-1: 18 x 25.5 x 3.2 mm, shield over the RF section, PCB antenna toward +Y."""
    W, L, pcb_t = 18., 25.5, .8
    # The pick-and-place centre is the pad centroid; the silkscreen body outline spans y 32.8-58.4 mm.
    y0 = p.y + 3.07 - L / 2
    bm = bmesh.new()
    add_box(bm, p.x, y0 + L / 2, TOP + .05, W, L, pcb_t, mat=0)
    shield_len = 17.6
    add_box(bm, p.x, y0 + .45 + shield_len / 2, TOP + .05 + pcb_t, W - .9, shield_len, 2.35, mat=1, bevel=.35)
    # Castellations: gold half-pads along both long sides and the bottom edge.
    for s in (-1, 1):
        for k in range(14):
            yy = y0 + 1.5 + k * 1.27
            add_box(bm, p.x + s * (W / 2 - .15), yy, TOP + .05, .32, .9, pcb_t + .01, mat=2)
    for k in range(9):
        add_box(bm, p.x + (k - 4) * 1.27, y0 + .15, TOP + .05, .9, .32, pcb_t + .01, mat=2)
    ob = new_object(f'{p.ref} | ESP32-C6-WROOM-1-N8', bm, [M['module_pcb'], M['shield'], M['gold']], parent, coll)
    # Meander antenna under the mask.
    bm2 = bmesh.new()
    ay0, ay1 = y0 + shield_len + 1.4, y0 + L - .9
    xs = [p.x - 7.2, p.x - 4.6, p.x - 2.0, p.x + .6, p.x + 3.2]
    z = TOP + .05 + pcb_t + .004
    add_box(bm2, p.x - 7.8, (ay0 + ay1) / 2, z - .004, .5, ay1 - ay0, .012)
    for i, x in enumerate(xs):
        add_box(bm2, x, (ay0 + ay1) / 2, z - .004, .5, ay1 - ay0, .012)
        yy = ay1 if i % 2 == 0 else ay0
        if i + 1 < len(xs):
            add_box(bm2, x + 1.3, yy, z - .004, 3.1, .5, .012)
    new_object('U8 | antenna', bm2, [M['module_trace']], parent, coll)
    top = TOP + .05 + pcb_t + 2.35 + .003
    sy0 = y0 + .45
    text_mesh(['ESP32-C6-WROOM-1'], 1.25, font, (1, 0), p, p.x, sy0 + shield_len * .78, top, M['etch'], coll, parent, 'U8 | marking')
    text_mesh(['N8'], .9, font, (1, 0), p, p.x, sy0 + shield_len * .66, top, M['etch'], coll, parent, 'U8 | marking 2')
    # Matrix code: a fixed pseudo-random 21 x 21 pattern with finder squares, etched.
    rnd = random.Random(8913)
    n, cell = 21, .22
    ox, oy = p.x + 3.2, sy0 + 3.2
    bmq = bmesh.new()
    def finder(ix, iy):
        return (ix < 7 and iy < 7) or (ix >= n - 7 and iy < 7) or (ix < 7 and iy >= n - 7)
    def finder_on(ix, iy):
        for fx, fy in ((0, 0), (n - 7, 0), (0, n - 7)):
            if fx <= ix < fx + 7 and fy <= iy < fy + 7:
                dx, dy = ix - fx, iy - fy
                ring = max(abs(dx - 3), abs(dy - 3))
                return ring != 2
        return False
    for ix in range(n):
        for iy in range(n):
            on = finder_on(ix, iy) if finder(ix, iy) else rnd.random() < .48
            if on:
                add_box(bmq, ox + ix * cell, oy + iy * cell, top - .002, cell, cell, .004)
    new_object('U8 | matrix code', bmq, [M['etch']], parent, coll)
    return ob


def build(product, hardware: Path, gerber_png: Path, font_path: Path, hide_step=True):
    """Add the detailed parts under `product` and texture the board from the Gerber masks.

    hardware is the repository root, gerber_png the directory holding
    top-{copper,pads,silk,board}.png, font_path the marking font. With hide_step the
    STEP part meshes are deleted from the open file. Returns (parts by designator, materials).
    """
    coll = bpy.data.collections.new('12 | Board detail - from fab files')
    bpy.context.scene.collection.children.link(coll)
    M = materials()
    font = bpy.data.fonts.load(str(font_path), check_existing=True)
    build_dir = hardware / FAB_BUILD
    parts = read_parts(build_dir / 'pick-and-place.csv', build_dir / 'bom.csv')

    board = bpy.data.objects['Board~N0jj']
    me = board.data
    uv = me.uv_layers.get('gerber') or me.uv_layers.new(name='gerber')
    me.uv_layers.active = uv
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            # The Gerber masks span the 100 x 125 mm board outline, centred on the origin.
            uv.data[li].uv = ((co.x / MM + 50) / 100, (co.y / MM + 62.5) / 125)
    me.materials.clear()
    me.materials.append(board_material(gerber_png))

    if hide_step:
        # Drivers on the STEP parts re-show them, so the working copy drops them outright.
        doomed = [o for o in bpy.data.collections['02 | PCB - imported STEP'].all_objects
                  if o.type == 'MESH' and o is not board]
        doomed += [o for o in bpy.data.objects if o.name in ('a-U8', 'a-H1', 'a-JP1', 'a-JP2', 'a-JP3', 'a-JP4')]
        for o in doomed:
            bpy.data.objects.remove(o, do_unlink=True)

    made = {}
    for p in parts:
        fp = p.fp
        if p.ref.startswith('CN'):
            continue
        if p.ref.startswith(('JP', 'H')):
            made[p.ref] = build_header(p, M, coll, product, 4 if p.ref == 'H1' else 2, shunt=p.ref.startswith('JP'))
            continue
        if fp.startswith('LQFP-64'):
            made[p.ref] = build_ic(p, M, coll, product, font, 4, .5, 16, 10., 10., 1.4, 12., .22, MARKINGS.get(p.value[1]))
        elif fp.startswith('SOIC-8_L5.3'):
            made[p.ref] = build_ic(p, M, coll, product, font, 2, 1.27, 4, 5.3, 5.3, 1.8, 8., .42, MARKINGS.get(p.value[1]))
        elif fp.startswith('SOIC-8_L5.0'):
            made[p.ref] = build_ic(p, M, coll, product, font, 2, 1.27, 4, 4.0, 5.0, 1.5, 6., .42, MARKINGS.get(p.value[1]))
        elif fp.startswith('SOIC-8'):
            made[p.ref] = build_ic(p, M, coll, product, font, 2, 1.27, 4, 3.9, 4.9, 1.5, 6., .42, MARKINGS.get(p.value[1]))
        elif fp.startswith('SOT-23'):
            made[p.ref] = build_sot23(p, M, coll, product, font)
        elif fp.startswith('WIRELM-SMD_ESP32-C6'):
            made[p.ref] = build_wroom(p, M, coll, product, font)
        elif fp == 'C0805':
            h = 1.25 if p.value[0] in ('22uF', '10uF') else .85
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 2., 1.25, h, 'mlcc')
        elif fp == 'C1206':
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 3.2, 1.6, 1.6, 'mlcc')
        elif fp == 'R0805':
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 2., 1.25, .5, 'res')
        elif fp == 'F0805':
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 2., 1.25, .85, 'fuse')
        elif fp == 'F1812':
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 4.5, 3.2, 1.1, 'fuse')
        elif fp.startswith('LED0805'):
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 2., 1.25, .55, 'led')
        elif fp.startswith('SMB'):
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 4.6, 3.6, 2.1, 'diode')
        elif fp.startswith('SMA'):
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 4.3, 2.6, 2.0, 'diode')
        elif fp.startswith('SOD-123'):
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 2.7, 1.6, 1.1, 'diode')
        elif fp.startswith('SOD-323'):
            made[p.ref] = build_two_terminal(p, M, coll, product, font, 1.7, 1.3, .9, 'diode')
        elif fp.startswith('IND-SMD'):
            made[p.ref] = build_inductor(p, M, coll, product, font)
        elif fp.startswith('CRYSTAL-SMD_4P'):
            made[p.ref] = build_crystal(p, M, coll, product, font, 3.2, 2.5, .8)
        elif fp.startswith('CRYSTAL-SMD_L3.2-W1.5'):
            made[p.ref] = build_crystal(p, M, coll, product, font, 3.2, 1.5, .9)
        else:
            print('unhandled footprint', p.ref, fp)
    print('board detail parts', len(made))
    return made, M
