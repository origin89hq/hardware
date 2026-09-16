"""Export the Controller scene as the GLB behind the website's 3D viewer.

    blender --background --python-exit-code 1 --python enclosure/blender/web/export_glb.py -- \\
      /tmp/home-media/controller-detailed.blend \\
      --board-albedo /tmp/home-media/gerber-art/board-albedo.jpg \\
      --output /tmp/home-media/controller-raw.glb

SCENE is normally the file saved by build_detailed_board.py. --board-albedo
first swaps the board's Gerber node network, which glTF cannot carry, for one
colour texture baked from the same masks by gerber_art.mjs. The source file is
opened in memory and never saved. The raw export is then compressed with
gltf-transform (webp, then meshopt); see README.md beside this script.

The GLB has three top-level nodes that JavaScript can animate:

  cover  lid, light pipe, cover screws and the visible lid branding
  board  PCB slab, STEP components and the connector proxies
  plate  mounting plate

Inside each node, meshes are merged per material (one child mesh per material).
Output is Y-up metres; the board normal is +Y, so the cover lifts along +Y.
"""
import argparse
import re
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("scene", type=Path, help="Source .blend (never written)")
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--board-albedo", type=Path, help="Colour texture for the board top (UV map 'gerber')")
parser.add_argument("--max-mb", type=float, default=6.0, help="Decimate tiny passives if the GLB is larger")
args = parser.parse_args(argv)
if args.board_albedo is not None and not args.board_albedo.is_file():
    parser.error(f"missing board albedo: {args.board_albedo}")

COVER_EMPTY = "Cover | lift with O89 Controls"
EXCLUDED_COLLECTION_WORDS = ("cable", "studio", "camera", "control", "bus layout", "backdrop")
MM = 0.001


def srgb(hex_colour):
    """Convert an sRGB hex colour to linear RGB, which is what Principled BSDF and glTF factors use."""
    value = hex_colour.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(value[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


# Export materials: plain Principled factors that survive glTF and read like the Cycles render.
SPECS = {
    "satin-black": dict(name="Satin black enclosure", base=srgb("#111214"), rough=0.45),
    "plate-black": dict(name="Matte black", base=srgb("#101113"), rough=0.55),
    "light-pipe": dict(name="Status light pipe", base=(0.035, 0.35, 0.13), rough=0.26, emission=(0.08, 1.0, 0.32), strength=1.8),
    "silver-print": dict(name="Silver print", base=(0.58, 0.61, 0.62), rough=0.6, double=True),
    "green-print": dict(name="KM43 green print", base=(0.075, 0.57, 0.31), rough=0.52, double=True),
    "solder-mask": dict(name="Solder mask green", base=(0.012, 0.085, 0.036), rough=0.42),
    "gold-pads": dict(name="ENIG gold pads", base=(0.94, 0.72, 0.36), rough=0.3, metal=1.0),
    "silkscreen": dict(name="Silkscreen white", base=(0.78, 0.79, 0.77), rough=0.6),
    "passive": dict(name="Passive ceramic", base=(0.30, 0.27, 0.23), rough=0.5),
    "ic-epoxy": dict(name="IC epoxy black", base=(0.035, 0.035, 0.04), rough=0.55),
    "terminal": dict(name="Terminal polymer green", base=(0.038, 0.18, 0.071), rough=0.42),
    "nylon": dict(name="Header nylon ivory", base=(0.85, 0.85, 0.78), rough=0.6),
    "nickel": dict(name="Nickel metal", base=(0.55, 0.56, 0.58), rough=0.32, metal=0.9),
    "led-lens": dict(name="LED lens", base=(0.8, 0.85, 0.8), rough=0.2),
    "socket-shadow": dict(name="Socket shadow", base=(0.004, 0.004, 0.004), rough=0.7),
}
EXACT = {
    "O89 | Charcoal nylon - fine grain": "satin-black",
    "O89 | Mounting plate - matte black": "plate-black",
    "O89 | Status light pipe": "light-pipe",
    "O89 | Soft silver print": "silver-print",
    "O89 | KM43 green print": "green-print",
    "O89 | Terminal polymer - muted green": "terminal",
    "O89 | Nickel contacts": "nickel",
    "O89 | Socket shadow": "socket-shadow",
    "pcb": "solder-mask",
    "chip": "passive",
    "epoxy": "ic-epoxy",
    "terminal": "terminal",
    "nylon": "nylon",
    "shield": "nickel",
    "led": "led-lens",
}
# Loose name rules for scenes that add materials (for example Gerber copper and silkscreen).
KEYWORDS = (
    (("gold", "enig", "copper", "pad"), "gold-pads"),
    (("silk",), "silkscreen"),
    (("mask", "solder", "fr4", "substrate", "pcb"), "solder-mask"),
    (("nickel", "tin", "shield", "steel", "metal", "lead"), "nickel"),
    (("epoxy", "mould", "mold", "package"), "ic-epoxy"),
    (("terminal",), "terminal"),
    (("print", "label", "text"), "silver-print"),
)


def principled(material):
    if material is None or material.node_tree is None:
        return None
    return next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def has_image_base(material):
    """True when an image texture drives the base colour; the glTF exporter can carry that."""
    bsdf = principled(material)
    if bsdf is None or not bsdf.inputs["Base Color"].is_linked:
        return False
    stack = [bsdf.inputs["Base Color"].links[0].from_node]
    seen = set()
    while stack:
        node = stack.pop()
        if node.name in seen:
            continue
        seen.add(node.name)
        if node.type == "TEX_IMAGE" and node.image is not None:
            return True
        stack.extend(link.from_node for sock in node.inputs for link in sock.links)
    return False


export_materials = {}


def make_material(key, spec):
    if key in export_materials:
        return export_materials[key]
    mat = bpy.data.materials.new("GLB | " + spec["name"])
    mat.use_nodes = True
    mat.use_backface_culling = not spec.get("double", False)
    bsdf = principled(mat)
    base = (*spec["base"], 1.0)
    bsdf.inputs["Base Color"].default_value = base
    mat.diffuse_color = base
    bsdf.inputs["Roughness"].default_value = spec.get("rough", 0.5)
    bsdf.inputs["Metallic"].default_value = spec.get("metal", 0.0)
    if spec.get("strength", 0.0) > 0:
        bsdf.inputs["Emission Color"].default_value = (*spec["emission"], 1.0)
        bsdf.inputs["Emission Strength"].default_value = spec["strength"]
    export_materials[key] = mat
    return mat


def generic_spec(material):
    bsdf = principled(material)
    if bsdf is None:
        colour = tuple(material.diffuse_color[:3])
        return dict(name=material.name, base=colour, rough=material.roughness, metal=material.metallic)

    def value(socket, fallback):
        s = bsdf.inputs[socket]
        return fallback if s.is_linked else s.default_value

    base = value("Base Color", material.diffuse_color)
    spec = dict(name=material.name, base=tuple(base[:3]), rough=float(value("Roughness", 0.5)),
                metal=float(value("Metallic", 0.0)))
    strength = float(value("Emission Strength", 0.0))
    if strength > 0:
        spec.update(emission=tuple(value("Emission Color", (1, 1, 1, 1))[:3]), strength=strength)
    return spec


def export_material_for(source, led_on):
    """Map a scene material to a glTF-safe material. Returns (material, needs_uv)."""
    if source is None:
        return make_material("socket-shadow", SPECS["socket-shadow"]), False
    if has_image_base(source):
        return source, True
    key = EXACT.get(source.name)
    if key is None:
        lowered = source.name.lower()
        key = next((k for words, k in KEYWORDS if any(w in lowered for w in words)), None)
    if key is None:
        return make_material("src:" + source.name, generic_spec(source)), False
    spec = dict(SPECS[key])
    if key == "light-pipe" and not led_on:
        spec["strength"] = 0.0
        key = "light-pipe-off"
    return make_material(key, spec), False


def ancestors(obj):
    while obj.parent is not None:
        obj = obj.parent
        yield obj


def world_bounds(obj):
    pts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def excluded_by_collection(obj):
    return any(any(word in coll.name.lower() for word in EXCLUDED_COLLECTION_WORDS) for coll in obj.users_collection)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def use_board_albedo(albedo):
    """Replace the Gerber node network on the board with one baked colour texture."""
    board = bpy.data.objects["Board~N0jj"]
    m = bpy.data.materials.new("O89 web | Board")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = .42
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(albedo))
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "gerber"
    nt.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    board.data.materials.clear()
    board.data.materials.append(m)
    for img in list(bpy.data.images):
        if img.filepath and "top-" in img.filepath:
            bpy.data.images.remove(img)


# ---------------------------------------------------------------- open and pose
bpy.ops.wm.open_mainfile(filepath=str(args.scene.resolve()))
if args.board_albedo is not None:
    use_board_albedo(args.board_albedo.resolve())
scene = bpy.context.scene
controls = bpy.data.objects.get("O89 Controls")
led_on = True
if controls is not None:
    for key, value in {"cover_lift_mm": 0.0, "show_enclosure": True, "show_cables": False,
                       "show_bus_layout": False, "show_cable_sleeve": False}.items():
        if key in controls.keys():
            controls[key] = value
    led_on = bool(controls.get("led_on", True))
    print("CONTROLS", {k: controls[k] for k in controls.keys()})
    controls.update_tag()
else:
    print("WARNING: no 'O89 Controls' object; exporting the scene as saved")
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
cover_root = bpy.data.objects.get(COVER_EMPTY)

# ---------------------------------------------------------------- choose objects
groups = {"cover": [], "board": [], "plate": []}
for obj in scene.objects:
    if obj.type not in {"MESH", "FONT", "CURVE", "SURFACE", "META"}:
        continue
    if excluded_by_collection(obj):
        continue
    if obj.evaluated_get(depsgraph).hide_render or obj.hide_render:
        continue
    if any(coll.hide_render for coll in obj.users_collection):
        continue
    if obj.type == "CURVE" and obj.data.bevel_depth == 0 and obj.data.extrude == 0 and obj.data.bevel_object is None:
        continue
    if cover_root is not None and cover_root in ancestors(obj):
        groups["cover"].append(obj)
    elif obj.name.lower().startswith("plate") or (
            any("enclosure" in c.name.lower() for c in obj.users_collection)):
        groups["plate"].append(obj)
    else:
        groups["board"].append(obj)

# The STEP import leaves a copy of every part model at the board origin, inside the slab,
# and two coincident copies at the placement. Drop geometry hidden inside the slab and
# exact duplicates; both are invisible and only cost bytes and z-fighting.
slabs = [o for o in groups["board"] if o.type == "MESH" and o.name.lower().startswith("board")]
slab = max(slabs, key=lambda o: (world_bounds(o)[1] - world_bounds(o)[0]).xy.length) if slabs else None
kept, dropped_inside, dropped_dupes, seen = [], 0, 0, set()
if slab is not None:
    s_lo, s_hi = world_bounds(slab)
for obj in groups["board"]:
    lo, hi = world_bounds(obj)
    if slab is not None and obj is not slab and obj.type == "MESH":
        inside_xy = lo.x >= s_lo.x - 1e-5 and hi.x <= s_hi.x + 1e-5 and lo.y >= s_lo.y - 1e-5 and hi.y <= s_hi.y + 1e-5
        # Real parts sit on the slab or pass through it; these copies start inside it and
        # do not rise above its top surface.
        small = (hi - lo).x * (hi - lo).y < 0.25 * (s_hi - s_lo).x * (s_hi - s_lo).y
        in_slab_z = lo.z < s_hi.z - 0.2 * MM and s_lo.z + 0.2 * MM < hi.z < s_hi.z + 0.2 * MM
        if inside_xy and small and "~" in obj.name and in_slab_z:
            dropped_inside += 1
            continue
    signature = (obj.type, tuple(round(v * 1e5) for v in (*lo, *hi)),
                 len(obj.data.vertices) if obj.type == "MESH" else obj.name,
                 tuple(s.material.name if s.material else "" for s in obj.material_slots))
    if signature in seen:
        dropped_dupes += 1
        continue
    seen.add(signature)
    kept.append(obj)
groups["board"] = kept
print("SELECTED", {k: len(v) for k, v in groups.items()}, "dropped inside slab:", dropped_inside,
      "duplicates:", dropped_dupes)
for name, objs in groups.items():
    print("  ", name, sorted(o.name for o in objs)[:12], "..." if len(objs) > 12 else "")

# ---------------------------------------------------------------- pivots (Blender Z-up coordinates)
def group_bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objs:
        a, b = world_bounds(obj)
        lo = Vector(map(min, lo, a))
        hi = Vector(map(max, hi, b))
    return lo, hi


bounds = {name: group_bounds(objs) for name, objs in groups.items() if objs}
pivots = {}
if "board" in bounds:
    lo, hi = world_bounds(slab) if slab is not None else bounds["board"]
    pivots["board"] = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))  # PCB centre, underside
if "cover" in bounds:
    lo, hi = bounds["cover"]
    pivots["cover"] = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))  # lid centre on its seating rim
if "plate" in bounds:
    lo, hi = bounds["plate"]
    pivots["plate"] = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))  # plate centre on the wall face


def decimate_tiny_passives(objs, ratio):
    """Only passives and small packages; never the enclosure, slab or connectors."""
    count = 0
    for obj in objs:
        if obj.type != "MESH" or obj is slab or len(obj.data.polygons) < 64:
            continue
        name = obj.name.upper()
        if name.startswith(("A-", "CN")) or "CONN" in name or "HDR" in name or "|" in name:
            continue
        lo, hi = world_bounds(obj)
        if max(hi - lo) > 4 * MM:
            continue
        mod = obj.modifiers.new("GLB size decimate", "DECIMATE")
        mod.ratio = ratio
        count += 1
    return count


# ---------------------------------------------------------------- build merged export meshes
export_coll = bpy.data.collections.new("GLB export")
scene.collection.children.link(export_coll)


def build_group(name, objs):
    copies, needs_uv = [], False
    local_depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objs:
        evaluated = obj.evaluated_get(local_depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=local_depsgraph)
        if len(mesh.polygons) == 0:
            bpy.data.meshes.remove(mesh)
            continue
        mesh.transform(Matrix.Translation(-pivots[name]) @ obj.matrix_world)
        if obj.matrix_world.determinant() < 0:
            mesh.flip_normals()
        slots = [slot.material for slot in evaluated.material_slots] or [None]
        mesh.materials.clear()
        for source in slots:
            mat, uv = export_material_for(source, led_on)
            needs_uv |= uv
            mesh.materials.append(mat)
        copy = bpy.data.objects.new(name + " | " + obj.name, mesh)
        export_coll.objects.link(copy)
        copies.append(copy)

    root = bpy.data.objects.new(name, None)
    export_coll.objects.link(root)
    root.location = pivots[name]
    if not copies:
        return root, [], needs_uv

    # Join everything, then split per material: one draw call per material per group.
    target = copies[0]
    view_layer = bpy.context.view_layer
    if len(copies) > 1:
        with bpy.context.temp_override(active_object=target, object=target, selected_objects=copies,
                                       selected_editable_objects=copies):
            bpy.ops.object.join()
    for o in view_layer.objects:
        o.select_set(False)
    view_layer.objects.active = target
    target.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = [o for o in view_layer.objects if o.select_get()]

    merged = {}
    for part in parts:
        mesh = part.data
        used = {p.material_index for p in mesh.polygons}
        if not used:
            bpy.data.objects.remove(part)
            continue
        material = mesh.materials[used.pop()]
        mesh.polygons.foreach_set("material_index", [0] * len(mesh.polygons))
        mesh.materials.clear()
        mesh.materials.append(material)
        label = name + "-" + slug(material.name.replace("GLB | ", ""))
        if label in merged:  # separate() can leave two parts with the same material; join them
            with bpy.context.temp_override(active_object=merged[label], object=merged[label],
                                           selected_objects=[merged[label], part],
                                           selected_editable_objects=[merged[label], part]):
                bpy.ops.object.join()
            continue
        part.name = label
        mesh.name = label
        part.parent = root
        part.matrix_parent_inverse = Matrix.Identity(4)
        part.location = (0, 0, 0)
        merged[label] = part
    return root, list(merged.values()), needs_uv


def build_all():
    roots, parts, needs_uv = [], [], False
    for name in ("cover", "board", "plate"):
        if not groups[name]:
            print("WARNING: group", name, "is empty")
            continue
        root, group_parts, uv = build_group(name, groups[name])
        roots.append(root)
        parts.extend(group_parts)
        needs_uv |= uv
    return roots, parts, needs_uv


def export(roots, parts, needs_uv):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in roots + parts:
        o.select_set(True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.resolve()), export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_texcoords=needs_uv, export_normals=True,
        export_tangents=False, export_vertex_color="NONE", export_attributes=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False, export_extras=False,
        export_animations=False, export_draco_mesh_compression_enable=False,
        export_meshopt_compression_enable=False)
    return args.output.stat().st_size / 1e6


roots, parts, needs_uv = build_all()
size_mb = export(roots, parts, needs_uv)
if size_mb > args.max_mb:
    print(f"GLB is {size_mb:.2f} MB; decimating tiny passives and exporting again")
    for o in roots + parts:
        bpy.data.objects.remove(o)
    n = decimate_tiny_passives(groups["board"], 0.35)
    print("decimated", n, "tiny parts")
    roots, parts, needs_uv = build_all()
    size_mb = export(roots, parts, needs_uv)
    if size_mb > args.max_mb:
        print(f"WARNING: GLB is still {size_mb:.2f} MB (> {args.max_mb} MB); the heavy geometry is not tiny passives")

print(f"GLB WRITTEN {args.output} {size_mb:.2f} MB")
for root in roots:
    p = root.location
    tris = sum(sum(len(poly.vertices) - 2 for poly in child.data.polygons) for child in root.children)
    print(f"NODE {root.name}: pivot blender(mm)=({p.x / MM:.2f}, {p.y / MM:.2f}, {p.z / MM:.2f}) "
          f"gltf(m)=({p.x:.4f}, {p.z:.4f}, {-p.y:.4f}) triangles={tris}")
    for child in sorted(root.children, key=lambda o: o.name):
        print("   ", child.name, sum(len(poly.vertices) - 2 for poly in child.data.polygons), "tris")
