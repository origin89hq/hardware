"""Render an existing edited .blend without rebuilding or saving over it."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--scene", type=Path, default=HERE / "origin89.blend")
parser.add_argument("--view", choices=("hero","front","left","right","pcb","exploded","cables","wiring","connectors","harness"), default="hero")
parser.add_argument("--label", choices=("clean","production"), default=None)
parser.add_argument("--output", type=Path, default=None)
parser.add_argument("--size", type=int, default=1600, help="Image width; height is 9/8 of width")
parser.add_argument("--samples", type=int, default=128)
parser.add_argument("--studio", action="store_true", help="Opaque charcoal backdrop instead of transparent alpha")
led_args = parser.add_mutually_exclusive_group()
led_args.add_argument("--led-off", action="store_true")
led_args.add_argument("--led-on", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
if args.size < 128 or args.samples < 1:
    raise SystemExit("Use size >=128 and samples >=1")

bpy.ops.wm.open_mainfile(filepath=str(args.scene.resolve()))
scene = bpy.context.scene
controls = bpy.data.objects["O89 Controls"]
if args.label is not None:
    controls["production_label"] = args.label == "production"
if args.led_off:
    controls["led_on"] = False
elif args.led_on:
    controls["led_on"] = True
views = {"hero":"Hero","front":"Front","left":"Left ports","right":"Right ports","pcb":"PCB","exploded":"Exploded","cables":"Cable detail","wiring":"Wiring","connectors":"Connector inspection","harness":"Harness"}
scene.camera = bpy.data.objects["Camera | " + views[args.view]]
if args.view == "pcb":
    controls["show_enclosure"] = False
    controls["show_cables"] = False
elif args.view == "exploded":
    controls["cover_lift_mm"] = 65.0
    controls["show_cables"] = False
elif args.view == "wiring":
    controls["show_bus_layout"] = True
    controls["show_cables"] = True
elif args.view == "connectors":
    controls["cover_lift_mm"] = 18.0
    controls["show_cables"] = True
controls.update_tag()
bpy.context.view_layer.update()
backdrop = bpy.data.objects["Backdrop | enable for opaque studio images"]
backdrop.hide_render = not args.studio
backdrop.hide_viewport = not args.studio
scene.render.film_transparent = not args.studio
scene.render.resolution_x = args.size
scene.render.resolution_y = round(args.size*9/8)
if args.view in ("wiring", "cables", "connectors", "harness"):
    scene.render.resolution_y = round(args.size*10/16)
scene.render.resolution_percentage = 100
scene.cycles.samples = args.samples

# Prefer the installed GPU where Blender reports one; CPU remains a valid fallback.
prefs = bpy.context.preferences.addons["cycles"].preferences
try:
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    gpu = [device for device in prefs.devices if device.type == "METAL"]
    if gpu:
        for device in prefs.devices:
            device.use = device.type == "METAL"
        scene.cycles.device = "GPU"
except (TypeError, RuntimeError):
    scene.cycles.device = "CPU"

output = args.output or HERE / "previews" / (args.view + ("-production" if controls["production_label"] else "") + ".png")
output = output.resolve()
output.parent.mkdir(parents=True,exist_ok=True)
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)

# Project the actual light pipe, so heartbeat packaging survives camera/resolution edits.
pipe = bpy.data.objects["pipe-a"]
bounds = [pipe.matrix_world @ Vector(c) for c in pipe.bound_box]
point = Vector((sum(p.x for p in bounds)/8,sum(p.y for p in bounds)/8,max(p.z for p in bounds)))
uv = world_to_camera_view(scene,scene.camera,point)
edge = world_to_camera_view(scene,scene.camera,point + Vector((0.0015,0,0)))
metadata = {"width":scene.render.resolution_x,"height":scene.render.resolution_y,
    "view":args.view,"production_label":bool(controls["production_label"]),
    "led_on":bool(controls["led_on"]), "transparent":not args.studio,
    "show_bus_layout":bool(controls.get("show_bus_layout",False)),
    "cover_lift_mm":float(controls["cover_lift_mm"]),
    "show_cable_sleeve":bool(controls.get("show_cable_sleeve",False)),
    "led_pixel":[uv.x*scene.render.resolution_x,(1-uv.y)*scene.render.resolution_y],
    "led_radius_px":abs(edge.x-uv.x)*scene.render.resolution_x,
    "camera":{"matrix_world":[list(row) for row in scene.camera.matrix_world],
        "type":scene.camera.data.type,"ortho_scale":scene.camera.data.ortho_scale,
        "lens":scene.camera.data.lens}}
output.with_suffix(".json").write_text(json.dumps(metadata,indent=2)+"\n")
print("RENDERED",output)
