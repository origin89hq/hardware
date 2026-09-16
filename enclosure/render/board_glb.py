"""EasyEDA STEP -> GLB. Tessellate every shape first: RWGltf silently
skips anything without triangulation and hands back an empty file."""
import argparse, hashlib, json, time
from pathlib import Path
import FreeCAD as App, Import
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--step", type=Path, required=True, help="Filed PCB STEP, such as boards/controller-a/build/<date>/board.step")
args = parser.parse_args()
step = args.step.resolve()
if not step.is_file():
    raise SystemExit("STEP does not exist: " + str(step))
t0 = time.time()
doc = App.newDocument("brd")
Import.insert(str(step), "brd")
objs = [o for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()]
n = 0
for o in objs:
    try:
        o.Shape.tessellate(0.2)
        n += 1
    except Exception as error:
        raise RuntimeError("Could not tessellate " + o.Label) from error
if not n:
    raise RuntimeError("STEP contains no tessellatable shapes")
print("tessellated", n, "of", len(objs), "in %.0fs" % (time.time() - t0))
(HERE / "work").mkdir(exist_ok=True)
Import.export(objs, str(HERE / "work" / "board-a.glb"))
try:
    source = str(step.relative_to(ROOT))
except ValueError:
    source = str(step)
(HERE / "work" / "board-a-source.json").write_text(json.dumps({
    "source": source,
    "sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
    "tessellation_mm": 0.2,
    "shapes": n,
    "labels": [o.Label for o in objs],
}, indent=2) + "\n")
print("glb exported in %.0fs total" % (time.time() - t0))
