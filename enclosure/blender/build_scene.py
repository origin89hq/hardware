"""Build the editable Origin 89 studio from the CAD assembly, in metres.

blender --background --python-exit-code 1 --python enclosure/blender/build_scene.py
This is a rebuild. Use render_scene.py to render subsequent manual Blender edits.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
WORK = HERE.parent / "render/work"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=HERE / "origin89.blend")
parser.add_argument("--overwrite", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
if args.output.exists() and not args.overwrite:
    raise SystemExit("Output exists; use --overwrite to rebuild or render_scene.py to keep manual edits")

bpy.ops.wm.open_mainfile(filepath=str(WORK / "assembly.blend"))
scene = bpy.context.scene
scene.name = "Origin 89 | Satin black studio"
frames = json.loads((WORK / "frames.json").read_text())["a"]
provenance = json.loads((WORK / "board-a-source.json").read_text())

# Keep the native CAD meshes; remove the second enclosure and old render dressing.
for obj in list(bpy.data.objects):
    if obj.name.startswith(("plate-b", "shoe-b", "board-b", "b-", "cable-")):
        bpy.data.objects.remove(obj, do_unlink=True)

def collection(name):
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    return coll

groups = {key: collection(name) for key, name in {
    "case": "01 | Enclosure - CAD",
    "pcb": "02 | PCB - imported STEP",
    "connectors": "03 | Connectors - envelope-based proxies",
    "clean": "04 | Branding - clean editable text",
    "production": "05 | Branding - production transfers",
    "cables": "06 | Cables - editable Bezier curves",
    "studio": "07 | Studio lights and backdrop",
    "cameras": "08 | Cameras",
    "controls": "09 | Controls",
    "wiring": "10 | Bus layout - editable illustration",
    "management": "11 | Cable management - sleeve and straps",
}.items()}

def move(obj, group):
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    groups[group].objects.link(obj)
    return obj

def empty(name, group="controls"):
    obj = bpy.data.objects.new(name, None)
    groups[group].objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.012
    return obj

controls = empty("O89 Controls")
properties = {
    "production_label": (False, "Switch between clean branding and the original production transfers"),
    "cover_lift_mm": (0.0, "Lift the cover and its markings to reveal the real PCB"),
    "show_enclosure": (True, "Show the cover and mounting plate"),
    "show_cables": (True, "Show the editable cable harness"),
    "show_bus_layout": (False, "Show RS-485 and 1-Wire bus examples instead of the full harness"),
    "show_cable_sleeve": (True, "Show the common braided sleeve and cable retaining straps"),
    "led_on": (True, "Illuminate the single status light pipe"),
}
for name, (value, description) in properties.items():
    controls[name] = value
    controls.id_properties_ui(name).update(description=description)
controls.id_properties_ui("cover_lift_mm").update(min=0.0, max=150.0, soft_max=90.0)
root = empty("Product | move or rotate the whole controller")
cover = empty("Cover | lift with O89 Controls")
cover.parent = root

def driver(owner, prop, variables, expression, index=None):
    curve = owner.driver_add(prop) if index is None else owner.driver_add(prop, index)
    drv = curve.driver
    for name, control in variables.items():
        var = drv.variables.new()
        var.name = name
        var.type = "SINGLE_PROP"
        var.targets[0].id = controls
        var.targets[0].data_path = '["' + control + '"]'
    drv.expression = expression

driver(cover, "location", {"lift": "cover_lift_mm"}, "lift / 1000", 2)

def visibility(obj, variables, expression):
    for prop in ("hide_render", "hide_viewport"):
        driver(obj, prop, variables, expression)

def parent_to(obj, parent):
    bpy.context.view_layer.update()
    matrix = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = matrix

def material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

black = material("O89 | Charcoal nylon - fine grain", (0.006, 0.007, 0.008), 0.53)
black.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.3
nodes, links = black.node_tree.nodes, black.node_tree.links
tex = nodes.new("ShaderNodeTexNoise")
tex.name = "Nylon grain | scale in metres"
tex.inputs["Scale"].default_value = 7500
tex.inputs["Detail"].default_value = 2
coord = nodes.new("ShaderNodeTexCoord")
links.new(coord.outputs["Object"], tex.inputs["Vector"])
bump = nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.22
bump.inputs["Distance"].default_value = 0.000055
links.new(tex.outputs["Fac"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"])
roughness = nodes.new("ShaderNodeMapRange")
roughness.inputs["To Min"].default_value = 0.42
roughness.inputs["To Max"].default_value = 0.62
links.new(tex.outputs["Fac"], roughness.inputs["Value"])
links.new(roughness.outputs["Result"], nodes["Principled BSDF"].inputs["Roughness"])
base_black = material("O89 | Mounting plate - matte black", (0.006, 0.007, 0.008), 0.5)
rubber = material("O89 | Satin black cable jacket", (0.006, 0.007, 0.008), 0.43)
terminal = material("O89 | Terminal polymer - muted green", (0.038, 0.18, 0.071), 0.42)
socket = material("O89 | Socket shadow", (0.0015, 0.002, 0.002), 0.7)
steel = material("O89 | Nickel contacts", (0.35, 0.37, 0.39), 0.29, 0.85)
silver = material("O89 | Soft silver print", (0.58, 0.61, 0.62), 0.6)
mint = material("O89 | KM43 green print", (0.075, 0.57, 0.31), 0.52)
led = material("O89 | Status light pipe", (0.035, 0.35, 0.13), 0.26)
bsdf = led.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Emission Color"].default_value = (0.08, 1.0, 0.32, 1)
driver(bsdf.inputs["Emission Strength"], "default_value", {"on": "led_on"}, "1.8 if on else 0")

def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)

def bevel(obj, width=0.00015):
    mod = obj.modifiers.new("Small manufactured edge highlights", "BEVEL")
    mod.width = width
    mod.segments = 3
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(35)
    mod.harden_normals = True
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.set_sharp_from_angle(angle=math.radians(35))
    normal = obj.modifiers.new("Weighted surface normals", "WEIGHTED_NORMAL")
    normal.keep_sharp = True

pcb_objects = []
envelopes = []
for obj in list(bpy.data.objects):
    if obj.type != "MESH":
        continue
    if obj.name in ("shoe-a", "plate-a"):
        move(obj, "case")
        assign(obj, black if obj.name == "shoe-a" else base_black)
        bevel(obj, 0.00012)
        parent_to(obj, cover if obj.name == "shoe-a" else root)
        visibility(obj, {"show": "show_enclosure"}, "not show")
    elif obj.name == "pipe-a":
        move(obj, "case")
        assign(obj, led)
        parent_to(obj, cover)
        visibility(obj, {"show": "show_enclosure"}, "not show")
    elif obj.name.startswith(("shoe-a-decal", "strip-a-")):
        move(obj, "production")
        parent_to(obj, cover)
        visibility(obj, {"production": "production_label", "show": "show_enclosure"}, "not production or not show")
    elif obj.get("source_kind") == "PCB STEP":
        move(obj, "pcb")
        pcb_objects.append(obj)
        obj["source_file"] = provenance["source"]
        obj["source_sha256"] = provenance["sha256"]
        parent_to(obj, root)
    elif obj.get("source_kind") == "datasheet envelope":
        move(obj, "connectors")
        envelopes.append(obj)
        parent_to(obj, root)
        bevel(obj, 0.00018)
        if "KF2EDG" in obj["source_label"] or "plug" in obj["source_label"]:
            assign(obj, terminal)

# Envelopes preserve the measured footprint and height; render details remain proxies.
def box(name, centre, dimensions, mat, group="connectors", parent=root, edge=0.00012):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre)
    obj = bpy.context.object
    obj.name = name
    obj.scale = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    move(obj, group)
    parent_to(obj, parent)
    if edge:
        bevel(obj, edge)
    return obj

def cylinder(name, loc, radius, depth, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    move(obj, "connectors")
    assign(obj, mat)
    parent_to(obj, root)
    bevel(obj, 0.00006)
    obj["source_kind"] = "render detail - approximate"
    return obj

def subtract(body, cutter):
    bpy.context.view_layer.objects.active = body
    modifier = body.modifiers.new("Moulded connector recess", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def round_recess(body, location, radius, depth, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth,
        location=location, rotation=rotation)
    subtract(body, bpy.context.object)

for obj in envelopes:
    label = obj["source_label"]
    if "B4B-PH" in label or "B5P-VH" in label:
        xr, yr, height = frames["envelopes"][label]
        socket_top = 0.0016 + height/1000
        cx,cy = (xr[0]+xr[1])/2000,(yr[0]+yr[1])/2000
        depth = height/1000-0.0017
        recess = box("Temporary JST cavity", (cx,cy,socket_top-depth/2+0.0001),
            ((xr[1]-xr[0])/1000-0.0012,(yr[1]-yr[0])/1000-0.0012,depth+0.0002),socket,edge=0)
        subtract(obj,recess)
        count,pitch = (4,0.002) if "B4B-PH" in label else (5,0.00396)
        for pin in range(count):
            contact = box(label.split()[0]+" | JST pin "+str(pin+1),
                (cx,cy+(pin-(count-1)/2)*pitch,socket_top-depth/2),
                (0.0005,0.0005,depth-0.0007),steel,edge=0.00005)
            contact["source_kind"] = "render detail - approximate"
    if "plug" not in label:
        continue
    xr, yr, height = frames["envelopes"][label]
    x0, x1, y0, y1 = xr[0]/1000, xr[1]/1000, yr[0]/1000, yr[1]/1000
    top = 0.0016 + height/1000
    ref = label.split()[0]
    pins = 2 if ref in ("CN1", "CN12", "CN14") else 3
    # Small top screw wells and slots make the plugs read as screw terminals.
    for i in range(pins):
        if y1 < -0.062:
            x, y = x0 + (x1-x0)*(i+0.5)/pins, (y0+y1)/2
        else:
            x, y = (x0+x1)/2, y0 + (y1-y0)*(i+0.5)/pins
        round_recess(obj,(x,y,top-0.00045),0.00115,0.0012)
        cylinder(ref + " | contact screw " + str(i+1), (x,y,top-0.00082), 0.00086, 0.00020, steel)
        slot = box(ref + " | screw slot " + str(i+1), (x,y,top-0.000709), (0.00135,0.00023,0.000025), socket, edge=0)
        slot["source_kind"] = "render detail - approximate"
        if y1 < -0.062:
            round_recess(obj,(x,y0+0.0007,0.0055),0.00135 if pins == 2 else 0.0011,
                0.0020,(math.pi/2,0,0))
            # Shallow moulded dividers make individual terminal cells readable.
            if i < pins-1:
                divider_x = x0+(x1-x0)*(i+1)/pins
                cutter = box("Temporary terminal divider",(divider_x,y0+0.0001,0.0055),
                    (0.00035,0.0006,0.007),socket,edge=0)
                subtract(obj,cutter)
        else:
            side = -1 if x1 < 0 else 1
            face = x0 if side == -1 else x1
            round_recess(obj,(face-side*0.0007,y,0.0058),0.0011,0.0020,(0,math.pi/2,0))

# Four side screws at the axes defined in shoe.py; no invented front fasteners.
for side in (-1, 1):
    for y in (0.045, -0.058):
        screw = cylinder("Cover | M3 side screw", (side*0.0667,y,0.0035), 0.00265, 0.0014, base_black, (0,math.pi/2,0))
        parent_to(screw, cover)
        move(screw, "case")
        visibility(screw, {"show": "show_enclosure"}, "not show")

# Clean lettering remains editable FONT objects, with packed Michroma.
font = bpy.data.fonts.load(str(HERE.parent / "fonts/Michroma.ttf"))
top_z = max((bpy.data.objects["shoe-a"].matrix_world @ Vector(c)).z for c in bpy.data.objects["shoe-a"].bound_box)

def text(name, body, loc, size, width=None, align="LEFT", rotation=(0,0,0), display_font=False):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.space_character = 1.15
    curve.resolution_u = 10
    if display_font:
        curve.font = font
    obj = bpy.data.objects.new(name, curve)
    groups["clean"].objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rotation
    curve.materials.append(silver)
    bpy.context.view_layer.update()
    if width:
        obj.scale *= width / obj.dimensions.x
    parent_to(obj, cover)
    visibility(obj, {"production": "production_label", "show": "show_enclosure"}, "production or not show")
    return obj

z = top_z + 0.00008
text("Brand | ORIGIN 89", "ORIGIN 89", (0,0.045,z), 0.007, width=0.101, align="CENTER", display_font=True)
bar = box("Brand | KM43 green line", (-0.030,0.032,z), (0.040,0.0007,0.00003), mint, "clean", cover, edge=0)
visibility(bar, {"production": "production_label", "show": "show_enclosure"}, "production or not show")
text("Brand | Off-grid controller", "OFF-GRID CONTROLLER", (-0.050,0.024,z), 0.00215)
text("Brand | Built at km 43", "BUILT AT KM 43", (-0.050,-0.062,z), 0.0018)
px, py = frames["led_pipes"][0]
text("Brand | Status", "STATUS", ((px+6)/1000,py/1000,z), 0.0024)
for label, y in (("SEL",14), ("SNS",-14.5), ("TNK",-28)):
    text("Port | Left | " + label, label, (-0.061,y/1000,z), 0.0021, align="CENTER", rotation=(0,0,math.pi/2))
for label, y in (("1W",14), ("VED",0), ("LNK",-15.5), ("VED",-41.5)):
    text("Port | Right | " + label, label, (0.061,y/1000,z), 0.0021, align="CENTER", rotation=(0,0,math.pi/2))
for label, x in (("DC IN",-34), ("RS485 1",-21), ("RS485 2",-8), ("RS485 3",5), ("CAN",18), ("1-WIRE",31)):
    text("Port | Bottom | " + label, label, (x/1000,-0.07865,0.0175), 0.0017, align="CENTER", rotation=(math.pi/2,0,0))

# Curves, jacket materials, terminal breakouts and the optional bus illustration.
sys.path.insert(0, str(HERE))
from cabling import build_cabling
build_cabling(bpy=bpy, groups=groups, root=root, rubber=rubber, silver=silver,
    mint=mint, socket=socket, steel=steel, box=box, material=material,
    parent_to=parent_to, visibility=visibility)

scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.cycles.seed = 89
scene.cycles.max_bounces = 8
scene.render.resolution_x = 1600
scene.render.resolution_y = 1800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0
scene.render.filepath = "//previews/hero.png"
world = bpy.data.worlds.new("O89 | Quiet studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.12,0.14,0.18,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.07
scene.world = world

def point_at(obj, target):
    # The controller's upright direction is world Y, not world Z (it is wall-mounted).
    forward = (Vector(target)-obj.location).normalized()
    right = forward.cross(Vector((0,1,0))).normalized()
    up = right.cross(forward).normalized()
    obj.rotation_euler = Matrix((right,up,-forward)).transposed().to_euler()

def area(name, location, target, energy, size, size_y, color=(1,1,1)):
    data = bpy.data.lights.new(name,"AREA")
    data.energy = energy * 0.15
    data.shape = "RECTANGLE"
    data.size = size
    data.size_y = size_y
    data.color = color
    obj = bpy.data.objects.new(name,data)
    groups["studio"].objects.link(obj)
    obj.location = location
    point_at(obj,target)
    return obj

# Metre-scale product: small, low-power softboxes create dark faces and readable rims.
area("Light | Key softbox", (-0.19,0.17,0.33),(0,0,0), 4.5,0.18,0.30,(1.0,0.95,0.9))
area("Light | Cool right edge", (0.24,0.08,0.16),(0,0,0.01), 3.5,0.035,0.25,(0.8,0.89,1.0))
area("Light | Left connector fill", (-0.19,-0.015,0.012),(-0.055,-0.01,0.007), 3.3,0.06,0.16)
area("Light | Bottom connectors", (0,-0.30,0.075),(0,-0.066,0.005), 9.0,0.13,0.045)
area("Light | Right connector fill", (0.18,-0.02,0.016),(0.052,-0.015,0.01), 2.38,0.045,0.16)
area("Light | Front lettering", (0.04,-0.07,0.42),(0,0,0.01), 1.1,0.24,0.24)
layout_light = area("Light | Bus layout softbox", (0.34,-0.02,0.32),
    (0.29,-0.07,0), 5.0,0.45,0.40)
visibility(layout_light, {"layout":"show_bus_layout"}, "not layout")

def camera(name, loc, target, scale):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = scale
    data.lens = 70
    data.clip_start = 0.001
    data.clip_end = 20
    obj = bpy.data.objects.new(name,data)
    groups["cameras"].objects.link(obj)
    obj.location = loc
    point_at(obj,target)
    return obj

camera("Camera | Hero", (-0.24,-0.56,0.43),(0,-0.042,0),0.250)
camera("Camera | Front", (0,-0.62,0.47),(0,-0.042,0),0.250)
camera("Camera | Right ports", (0.64,-0.27,0.26),(0,-0.010,0.005),0.24)
camera("Camera | Left ports", (-0.64,-0.29,0.20),(0,-0.010,0.005),0.24)
camera("Camera | PCB", (-0.17,-0.22,0.62),(0,0,0.005),0.205)
camera("Camera | Exploded", (-0.33,-0.39,0.49),(0,0,0.042),0.295)
camera("Camera | Cable detail", (-0.022,-0.40,0.115),(0,-0.083,0.006),0.112)
camera("Camera | Connector inspection", (0.055,-0.20,0.15),(0,-0.065,0.008),0.150)
camera("Camera | Harness", (-0.025,-0.440,0.180),(0,-0.126,0.006),0.225)
camera("Camera | Wiring", (0.190,-0.26,0.95),(0.190,-0.030,0),0.620)
scene.camera = bpy.data.objects["Camera | Hero"]

# Optional backdrop is separate from the alpha-ready website product.
backdrop_mat = material("O89 | Studio charcoal backdrop",(0.002,0.0025,0.003),0.86)
backdrop = box("Backdrop | enable for opaque studio images", (0,-0.06,-0.022), (2,2,0.001), backdrop_mat, "studio", None, edge=0)
backdrop.hide_render = True
backdrop.hide_viewport = True

# Keep an in-file guide and STEP provenance with the portable, packed source.
readme = bpy.data.texts.new("START HERE - Origin 89")
readme.write("""ORIGIN 89 / EDITABLE PRODUCT STUDIO

Select O89 Controls > Object Properties > Custom Properties:
  production_label: clean editable typography / original printed transfers
  cover_lift_mm: lift the cover and its artwork to inspect the PCB
  show_enclosure / show_cables: visibility controls
  show_bus_layout: RS-485 daisy chain and 1-Wire short sensor taps
  show_cable_sleeve: common braided wrap and side retaining straps
  led_on: the single status light

Collections separate the enclosure, STEP PCB, connector proxies, label
options, Bezier cables, lights and cameras. Text stays editable, cable
handles stay editable, and all textures and the display font are packed.
Units display millimetres; internal coordinates are metres.

The enclosure is a tessellated CAD mesh. Edit shoe.py for manufacturing
geometry; use Blender for presentation. The PCB is imported from STEP.
Some components in the vendor STEP are placeholders. Connector bodies
use the existing datasheet envelopes; screw wells are render-only detail.
Clean branding is a presentation option, not a fabrication artwork update.
Cat5e jackets and coloured pair breakouts illustrate RS-485 and 1-Wire.
12 V, CAN and side harnesses retain separate cable types. Colour assignments
are a proposed convention, not an Ethernet pinout. Wiring camera objects are
conceptual bus examples; their distances are not installation dimensions.

Render the saved file with render_scene.py; this preserves manual edits.
Rebuilding with build_scene.py --overwrite REPLACES manual scene edits.
Use Save As for design variants before rebuilding.
""")
source_text = bpy.data.texts.new("PCB STEP provenance.json")
source_text.write(json.dumps(provenance,indent=2))
scene["pcb_source"] = provenance["source"]
scene["pcb_sha256"] = provenance["sha256"]
scene["pcb_mesh_count"] = len(pcb_objects)
scene["enclosure_source"] = "enclosure/shoe.py"
scene["design_direction"] = "Satin black; clean branding; physical side ports retained"

# Fail on an unexpected board scale or coordinate-frame change.
slabs = [obj for obj in pcb_objects if obj.name.startswith("Board")]
assert len(slabs) == 1, "Expected exactly one PCB slab"
bpy.context.view_layer.update()
slab = slabs[0]
bounds = [slab.matrix_world @ Vector(c) for c in slab.bound_box]
dimensions = [max(p[i] for p in bounds)-min(p[i] for p in bounds) for i in range(3)]
assert abs(dimensions[0]-0.100) < 0.001 and abs(dimensions[1]-0.125) < 0.001, dimensions
assert abs(min(p.z for p in bounds)) < 0.0001, "PCB bottom must be z=0"

for coll in list(bpy.data.collections):
    if not coll.objects and not coll.children:
        bpy.data.collections.remove(coll)
bpy.ops.object.select_all(action="DESELECT")
controls.select_set(True)
bpy.context.view_layer.objects.active = controls
for screen in bpy.data.screens:
    for area_ui in screen.areas:
        if area_ui.type == "VIEW_3D":
            space = area_ui.spaces.active
            space.region_3d.view_perspective = "CAMERA"
            space.clip_start = 0.001
            space.overlay.show_floor = False
            space.shading.type = "MATERIAL"
            space.shading.use_scene_world = True
            space.shading.use_scene_lights = True

bpy.ops.file.pack_all()
args.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
print("STUDIO SAVED", args.output, "PCB meshes:",len(pcb_objects), "PCB dimensions:",dimensions)
