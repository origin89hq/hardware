"""Rebuild the Blender source from CAD, artwork and an explicitly chosen PCB STEP.

Run with any Python 3. Override FREECAD_PYTHON, FREECAD_LIB and BLENDER if needed.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RENDER = HERE.parent / "render"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--step", type=Path, required=True)
parser.add_argument("--output", type=Path, default=HERE / "origin89.blend")
parser.add_argument("--overwrite", action="store_true", help="Replace the output, including manual Blender edits")
parser.add_argument("--refresh-cad", action="store_true", help="Regenerate enclosure meshes and production artwork too")
args = parser.parse_args()
if not args.step.is_file():
    raise SystemExit("STEP not found: " + str(args.step))
if args.output.exists() and not args.overwrite:
    raise SystemExit("Output already exists. Save a variant or pass --overwrite to rebuild it.")
freecad = os.environ.get("FREECAD_PYTHON", "/Applications/FreeCAD.app/Contents/Resources/bin/python")
blender = os.environ.get("BLENDER", shutil.which("blender") or "/Applications/Blender.app/Contents/MacOS/Blender")
env = os.environ.copy()
lib = os.environ.get("FREECAD_LIB", "/Applications/FreeCAD.app/Contents/Resources/lib")
env["PYTHONPATH"] = lib + os.pathsep + env.get("PYTHONPATH", "")
env["MPLCONFIGDIR"] = str(RENDER / "work/matplotlib")

def cad(script, *arguments):
    subprocess.run([freecad, str(script), *map(str,arguments)], cwd=ROOT, env=env, check=True)

if args.refresh_cad:
    cad(HERE.parent / "shoe.py")
    cad(HERE.parent / "artwork.py")
for required in ("board-a-plate.stl", "board-a-shoe.stl", "board-b-plate.stl", "board-b-shoe.stl", "artwork-a-top-transfer.png", "artwork-b-top-transfer.png"):
    if not (HERE.parent / "out" / required).is_file():
        raise SystemExit("Missing " + required + "; rerun with --refresh-cad")
cad(RENDER / "frames.py")
cad(RENDER / "board_glb.py", "--step", args.step.resolve())
cad(RENDER / "strips.py")
cad(RENDER / "textures.py")
subprocess.run([blender,"--background","--python-exit-code","1","--python",str(RENDER / "assembly_glb.py")],cwd=ROOT,check=True)
cmd = [blender,"--background","--python-exit-code","1","--python",str(HERE / "build_scene.py"),"--","--output",str(args.output.resolve())]
if args.overwrite:
    cmd.append("--overwrite")
subprocess.run(cmd,cwd=ROOT,check=True)
