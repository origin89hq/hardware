"""Board-frame geometry for the render chain: outer bounds, component and
plug envelopes, light pipes -- everything assembly_glb.py places by."""
import os, json, sys
from pathlib import Path
os.environ["O89_SHOE_LIB"] = "1"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import shoe
out = {}
for name, spec in (("a", shoe.A), ("b", shoe.B)):
    sh = shoe.Shoe(spec)
    d = {"ox0": sh.ox0, "ox1": sh.ox1, "oy0": sh.oy0, "oy1": sh.oy1}
    for k in ("board", "envelopes", "plugs", "led_pipes"):
        if k in spec:
            d[k] = spec[k]
    for k in ("plate_t", "standoff", "wall", "top"):
        d[k] = shoe.COMMON.get(k)
    out[name] = d
(HERE / "work").mkdir(exist_ok=True)
json.dump(out, open(HERE / "work" / "frames.json", "w"), indent=1, default=str)
print("frames dumped")
