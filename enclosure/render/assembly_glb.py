"""Both boxes assembled: plates, shoes with transfer decals, the real
board A from the STEP, envelope stand-ins for the THT parts, plugs in
the mouths, port strips on the lid margins, cable dressing."""
import bpy, os, math, re, json, mathutils
HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.join(HERE, "..", "out")
S = os.path.join(HERE, "work")
FR = json.load(open(S + "/frames.json"))
DXB = 0.130   # board B assembly shifted +x, metres
bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, rgb, rough, metal=0.0, blend=None):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if blend and hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    elif blend:
        m.blend_method = blend
    return m

plastic = mat("plastic", (0.045, 0.045, 0.05), 0.55)
pcb     = mat("pcb", (0.010, 0.070, 0.032), 0.45)
white   = mat("nylon", (0.85, 0.85, 0.78), 0.6)
tgreen  = mat("terminal", (0.035, 0.22, 0.09), 0.5)
dark    = mat("epoxy", (0.04, 0.04, 0.045), 0.5)
chip    = mat("chip", (0.30, 0.27, 0.23), 0.5)
metal   = mat("shield", (0.55, 0.55, 0.58), 0.35, metal=0.9)
ledm    = mat("led", (0.8, 0.85, 0.8), 0.2)

RULES = [(r"^Board", pcb), (r"VH|B4B-PH|PH2", white),
         (r"CONN-TH_(2P|3P|P3)", tgreen), (r"WROOM|ESP32|CRYSTAL|SMA_|IND", metal),
         (r"LED", ledm), (r"C0805|C1206|R0805|F0805|F1812", chip), (r"HDR|SO|LQFP|SMB", dark)]

def wbb(objs):
    lo = [1e9]*3; hi = [-1e9]*3
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi

def import_stl(stem, name, dx=0.0):
    bpy.ops.wm.stl_import(filepath=os.path.join(O, stem + ".stl"))
    o = bpy.context.selected_objects[0]; o.name = name
    o.scale = (0.001,) * 3
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(scale=True)
    d = o.modifiers.new("dec", "DECIMATE"); d.decimate_type = "DISSOLVE"; d.angle_limit = math.radians(2.0)
    bpy.ops.object.modifier_apply(modifier="dec")
    o.data.materials.clear(); o.data.materials.append(plastic)
    o.location.x = dx
    o["source_kind"] = "enclosure CAD"
    o["source_file"] = "enclosure/out/" + stem + ".step"
    return o

def decal(shoe_obj, tex, name):
    # location.x set moments ago is not in matrix_world until the deps
    # graph updates -- without this, B's decal lands at B's PRE-move bbox,
    # which is a grey sheet floating over box A
    bpy.context.view_layer.update()
    lo, hi = wbb([shoe_obj])
    w, h = hi[0]-lo[0], hi[1]-lo[1]
    bpy.ops.mesh.primitive_plane_add(size=1, location=((lo[0]+hi[0])/2, (lo[1]+hi[1])/2, hi[2] + 0.0003))
    pl = bpy.context.active_object; pl.name = name
    pl.scale = (w, h, 1)
    bpy.ops.object.transform_apply(scale=True)
    m = mat(name + "-m", (1,1,1), 0.45, blend="BLEND")
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    pl.data.materials.append(m)

# --- box A: plate, shoe+decal, real board ---------------------------------
plate_a = import_stl("board-a-plate", "plate-a")
shoe_a  = import_stl("board-a-shoe", "shoe-a")
decal(shoe_a, S + "/tex-a.png", "shoe-a-decal")
plate_top_a = wbb([plate_a])[1][2]

before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=S + "/board-a.glb")
brd = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
# EasyEDA's STEP carries the board slab twice, the copy floating high --
# keep the lowest Board* and drop the rest
boards = sorted([o for o in brd if o.name.startswith("Board")], key=lambda o: wbb([o])[0][2])
if not boards:
    raise RuntimeError("PCB import contains no Board slab; inspect the STEP coordinate frame")
for o in boards[1:]:
    brd.remove(o)
    bpy.data.objects.remove(o, do_unlink=True)
slab = boards[0]
slab_bot = wbb([slab])[0][2]
dz = 0.0 - slab_bot
for o in brd:
    o["source_kind"] = "PCB STEP"
    o["source_label"] = o.name
    o.location.z += dz
bpy.context.view_layer.update()
# whatever still floats above the tallest real body (VH plug tops out at
# 14.3) is export debris -- name it as it dies, so we know what it was
for o in list(brd):
    lo, hi = wbb([o])
    if lo[2] > 0.016:
        print("DEBRIS", o.name, [round(v * 1000, 1) for v in (hi[0]-lo[0], hi[1]-lo[1], lo[2], hi[2])])
        brd.remove(o)
        bpy.data.objects.remove(o, do_unlink=True)
for o in brd:
    m = dark
    for rx, mm in RULES:
        if re.search(rx, o.name): m = mm; break
    o.data.materials.clear(); o.data.materials.append(m)
def env_mat(name):
    if "VH" in name or "B4B-PH" in name or "PH2" in name: return white
    if "KF2EDG" in name or "plug" in name: return tgreen
    if "ESP32" in name: return metal
    return dark
for name, (xr, yr, h) in FR["a"]["envelopes"].items():
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=((xr[0]+xr[1])/2000, (yr[0]+yr[1])/2000, 0.0016 + h/2000))
    o = bpy.context.active_object; o.name = "a-" + name.split()[0]
    o["source_kind"] = "datasheet envelope"
    o["source_label"] = name
    o.scale = ((xr[1]-xr[0])/1000, (yr[1]-yr[0])/1000, h/1000)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(env_mat(name))

# port strips: the die-cut side stickers from artwork.py, as textured
# planes. Front and left sit on the 6 mm wall band above their mouths
# (z 14..20). The RIGHT band does not exist -- the top-exit notches for
# CN6/7/9 open that wall to the underside of the top over three of the
# four label positions -- so the right strip lies on the top margin along
# the right edge, rotated so each label still sits beside its port.
STRIPS = json.load(open(S + "/strips.json"))
def strip_plane(band, name, loc, euler, rot_u=False):
    m = STRIPS[band]
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    pl = bpy.context.active_object; pl.name = name
    pl.scale = (m["length"]/1000, 0.006, 1)
    pl.rotation_euler = euler
    # bake rotation+scale into the mesh: the glTF exporter composes an
    # unapplied object rotation about the world origin, not the pivot
    bpy.ops.object.transform_apply(rotation=True, scale=True)
    mm = mat(name + "-m", (1, 1, 1), 0.5, blend="BLEND")
    nt = mm.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(S + "/strip-%s.png" % band)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    pl.data.materials.append(mm)
shoe_top_a = wbb([shoe_a])[1][2]
strip_plane("front", "strip-a-front",
            (STRIPS["front"]["centre"]/1000, -0.0788, 0.017), (math.pi/2, 0, 0))
strip_plane("left", "strip-a-left",
            (-0.061, STRIPS["left"]["centre"]/1000, shoe_top_a + 0.0006), (0, 0, math.pi/2))
strip_plane("right", "strip-a-right",
            (0.061, STRIPS["right"]["centre"]/1000, shoe_top_a + 0.0006), (0, 0, math.pi/2))

# cables: one round jacket per plugged port, drooping down-wall (-y is
# gravity on a wall mount). Bezier -> mesh, since glTF drops raw curves.
def cable(name, pts, radius, rgb):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
    cu.bevel_depth = radius; cu.bevel_resolution = 4; cu.resolution_u = 24
    sp = cu.splines.new("BEZIER"); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o)
    o.data.materials.append(mat(name + "-m", rgb, 0.7))
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return o

RUBBER = {"12V": (0.06, 0.06, 0.065), "RS1": (0.05, 0.28, 0.30), "RS2": (0.16, 0.16, 0.17),
          "RS3": (0.30, 0.30, 0.32), "CAN": (0.55, 0.42, 0.05), "1W": (0.75, 0.75, 0.72)}
for i, (lbl, x0) in enumerate([("12V", -34.0), ("RS1", -21.0), ("RS2", -8.0),
                               ("RS3", 5.0), ("CAN", 18.0), ("1W", 31.0)]):
    x = x0 / 1000; sway = (i - 2.5) * 0.004
    cable("cable-a-" + lbl,
          [(x, -0.066, 0.007), (x, -0.084, 0.006), (x + sway * 0.4, -0.102, 0.0045),
           (x + sway, -0.125, 0.0035), (x + sway * 1.3, -0.150, 0.003)],
          0.0016 if lbl == "12V" else 0.0012, RUBBER[lbl])
for j, y0 in enumerate([14.0, -14.5, -28.0]):
    y = y0 / 1000; g = 0.10 + j * 0.05
    cable("cable-a-left%d" % j,
          [(-0.058, y, 0.006), (-0.073, y, 0.0055), (-0.082, y - 0.014, 0.0045),
           (-0.086, y - 0.05, 0.0035), (-0.087, y - 0.10, 0.003)],
          0.0011, (g, g, g * 1.05))
for j, y0 in enumerate([0.0, -41.5]):
    y = y0 / 1000
    cable("cable-a-ved%d" % j,
          [(0.047, y, 0.014), (0.070, y, 0.017), (0.079, y - 0.012, 0.012),
           (0.083, y - 0.05, 0.006), (0.084, y - 0.10, 0.004)],
          0.0010, (0.22, 0.22, 0.24))

# the one light pipe, from the board up through the shoe top
px, py = FR["a"]["led_pipes"][0]
shoe_top_a = wbb([shoe_a])[1][2]
bpy.ops.mesh.primitive_cylinder_add(radius=0.0015, depth=shoe_top_a - 0.002,
    location=(px/1000, py/1000, (0.002 + shoe_top_a)/2), vertices=24)
pipe = bpy.context.active_object; pipe.name = "pipe-a"; pipe.data.materials.append(ledm)

# --- box B: plate, shoe+decal, slab + envelope bodies ---------------------
plate_b = import_stl("board-b-plate", "plate-b", dx=DXB)
shoe_b  = import_stl("board-b-shoe", "shoe-b", dx=DXB)
decal(shoe_b, S + "/tex-b.png", "shoe-b-decal")
plate_top_b = wbb([plate_b])[1][2]
bz = 0.0
bpy.ops.mesh.primitive_cube_add(size=1, location=(DXB, 0, bz + 0.0008))
sb = bpy.context.active_object; sb.name = "board-b-pcb"
sb.scale = (0.080, 0.055, 0.0016)
bpy.ops.object.transform_apply(scale=True)
sb.data.materials.append(pcb)
BMAT = {"K1": dark, "K2": dark, "CN9  B5P-VH": white, "CN10 KF2EDGR": tgreen,
        "F1": dark, "D6": dark, "U2": dark, "U1": dark}
for name, (xr, yr, h) in FR["b"]["envelopes"].items():
    m = dark
    for k, mm in BMAT.items():
        if name.startswith(k.split()[0]): m = mm; break
    if "VH" in name: m = white
    if "KF2EDG" in name: m = tgreen
    w, d = (xr[1]-xr[0])/1000, (yr[1]-yr[0])/1000
    cx, cy = (xr[0]+xr[1])/2000 + DXB, (yr[0]+yr[1])/2000
    top = bz + 0.0016
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, top + h/2000))
    o = bpy.context.active_object; o.name = "b-" + name.split()[0]
    o.scale = (w, d, h/1000)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(m)

# B's own cables: the generator contact pair out the right mouth and
# down, the VH loom up through the left notch and over
cable("cable-b-gen",
      [(DXB + 0.048, 0.012, 0.012), (DXB + 0.062, 0.012, 0.010),
       (DXB + 0.070, 0.004, 0.007), (DXB + 0.074, -0.030, 0.004), (DXB + 0.075, -0.080, 0.003)],
      0.0016, (0.06, 0.06, 0.065))
cable("cable-b-vh",
      [(DXB - 0.0345, 0.0, 0.020), (DXB - 0.050, 0.0, 0.024), (DXB - 0.062, -0.006, 0.016),
       (DXB - 0.066, -0.040, 0.006), (DXB - 0.067, -0.090, 0.004)],
      0.0014, (0.75, 0.75, 0.72))

tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
print("ASSEMBLY tris:", tris, "plate_top_a mm:", round(plate_top_a*1000,1), "shoe_top_a mm:", round(shoe_top_a*1000,1))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=S + "/assembly.blend", compress=True)
bpy.ops.export_scene.gltf(filepath=S + "/boxes-full.glb", export_format="GLB", export_apply=True, export_yup=True)
print("GLB DONE")
