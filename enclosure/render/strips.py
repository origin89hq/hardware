"""Per-band port-strip textures for the 3D preview, one PNG per strip,
sized exactly (length x 6 mm), transparent outside the die-cut band.
The cells come from artwork.py's STRIP_BANDS -- read from its source as a
pure literal, so the design lives in exactly one place and a retyped copy
cannot drift. Renaming or computing that constant breaks this loudly."""
import ast
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
os.makedirs(S, exist_ok=True)
FONT = {"family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "weight": "bold"}
MM = 1 / 25.4

def load_bands():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "artwork.py")
    tree = ast.parse(open(src).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(tg, ast.Name) and tg.id == "STRIP_BANDS" for tg in node.targets):
            table = ast.literal_eval(node.value)
            return {name: [(main, pos) for main, sub, pos in cells]
                    for name, (cells, title) in table.items()}
    raise SystemExit("STRIP_BANDS not found as a literal in artwork.py")

BANDS = load_bands()

meta = {}
for name, cells in BANDS.items():
    lo = min(p for _, p in cells) - 9.0
    hi = max(p for _, p in cells) + 9.0
    length = hi - lo
    fig = plt.figure(figsize=(length * MM, 6 * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-length / 2, length / 2); ax.set_ylim(-3, 3)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(FancyBboxPatch((-length / 2, -3), length, 6,
                 boxstyle="round,pad=0,rounding_size=1.2",
                 facecolor="#151619", edgecolor="none"))
    for label, pos in cells:
        x = pos - (lo + hi) / 2
        ax.text(x, 0, label, fontsize=2.6 / 0.7 / 0.3528, color="white",
                ha="center", va="center", **FONT)
    fig.savefig(os.path.join(S, "strip-%s.png" % name), transparent=True, dpi=600)
    plt.close(fig)
    meta[name] = dict(lo=lo, hi=hi, length=length, centre=(lo + hi) / 2)
    print(name, meta[name])

import json
json.dump(meta, open(os.path.join(S, "strips.json"), "w"))
