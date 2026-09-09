"""Insert drawings for the print order: one PNG per plate, a plan with every
insert numbered, a table giving each one's type, position, axis and entry
face, and a schematic section. Read from the same tables the parts are built
from. JLC3DP: "specify the insert types and their locations in the diagram"."""
import os, sys
os.environ["O89_SHOE_LIB"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrow
import shoe

INSERT = "DPLK-M3"
FACE = {"left": "from -x wall", "right": "from +x wall", "front": "from -y wall", "back": "from +y wall"}

for spec in (shoe.A, shoe.B):
    sh = shoe.Shoe(spec)
    c = shoe.COMMON
    stem = spec["stems"][0]
    zp, z0 = sh.zp, sh.zp - c["plate_t"]
    W, H = sh.ox1 - sh.ox0 + 40, sh.oy1 - sh.oy0 + 20
    edges = []
    for t in spec["tabs"]:
        if t["edge"] not in edges:
            edges.append(t["edge"])
    fig = plt.figure(figsize=(11, 11 * H / W + 2.6 + 2.8 * len(edges)))
    gs = fig.add_gridspec(2 + len(edges), 1, height_ratios=[11 * H / W] + [2.6] * len(edges) + [2.6], hspace=0.45)
    ax = fig.add_subplot(gs[0])
    elev = [fig.add_subplot(gs[1 + i]) for i in range(len(edges))]
    tab_ax = fig.add_subplot(gs[1 + len(edges)])

    # plan
    ax.add_patch(FancyBboxPatch((sh.ox0, sh.oy0), sh.ox1 - sh.ox0, sh.oy1 - sh.oy0,
                                boxstyle="round,pad=0,rounding_size=%g" % c["fillet_r"], fill=False, lw=1.6))
    ax.add_patch(Rectangle((-spec["board_x"] / 2, -spec["board_y"] / 2), spec["board_x"], spec["board_y"],
                           fill=False, lw=0.7, ls=":", color="grey"))
    ax.text(0, -spec["board_y"] / 2 + 3, "PCB outline (reference)", ha="center", fontsize=7, color="grey")
    rows = []
    n = 0
    for hx, hy in spec["holes"]:
        n += 1
        ax.add_patch(Circle((hx, hy), c["boss_d"] / 2, fill=False, lw=0.9, color="tab:red"))
        ax.add_patch(Circle((hx, hy), c["insert_d"] / 2, color="tab:red"))
        ax.text(hx, hy + c["boss_d"] / 2 + 1.5, str(n), ha="center", va="bottom", fontsize=11, weight="bold", color="tab:red")
        rows.append([n, INSERT, "vertical, from above", "boss top, z = 0", "%+.1f" % hx, "%+.1f" % hy, "0.0", "%.1f x %.1f" % (c["insert_d"], c["insert_depth"])])
    for t in spec["tabs"]:
        n += 1
        axis, outer, inner, sign = sh.wall_frame(t["edge"])
        tb = sh.tab_box(t["edge"], t["pos"]).BoundBox
        ax.add_patch(Rectangle((tb.XMin, tb.YMin), tb.XLength, tb.YLength, facecolor="#cfe2f3", edgecolor="tab:blue", lw=0.9))
        near = inner - sign * c["clear"]
        hx, hy = (near, t["pos"]) if axis == "x" else (t["pos"], near)
        ax.add_patch(Circle((hx, hy), c["insert_d"] / 2, color="tab:blue"))
        dx, dy = (-sign * 9, 0) if axis == "x" else (0, -sign * 9)   # arrow: from the wall side into the tab
        ax.add_patch(FancyArrow(hx - dx * 1.6, hy - dy * 1.6, dx, dy, width=1.2, head_width=3.5, head_length=3, color="tab:blue", length_includes_head=True))
        lx, ly = (tb.Center.x, tb.Center.y)
        ax.text(lx, ly, str(n), ha="center", va="center", fontsize=11, weight="bold", color="tab:blue")
        rows.append([n, INSERT, "horizontal, " + FACE[t["edge"]], "tab face, wall side", "%+.1f" % hx, "%+.1f" % hy,
                     "%+.1f" % (zp + c["tab_screw_z"]), "%.1f x %.1f" % (c["insert_d"], c["insert_depth"])])
    e = c["ear"]
    for ear in spec["ears"]:
        axis, outer, inner, sign = sh.wall_frame(ear["edge"])
        if axis == "x":
            x0 = min(outer, outer + sign * e["len"]); ax.add_patch(Rectangle((x0, ear["pos"] - e["w"] / 2), e["len"], e["w"], fill=False, lw=0.7, color="grey"))
            hx, hy = outer + sign * (e["len"] - e["w"] / 2), ear["pos"]
        else:
            y0 = min(outer, outer + sign * e["len"]); ax.add_patch(Rectangle((ear["pos"] - e["w"] / 2, y0), e["w"], e["len"], fill=False, lw=0.7, color="grey"))
            hx, hy = ear["pos"], outer + sign * (e["len"] - e["w"] / 2)
        ax.add_patch(Circle((hx, hy), e["hole"] / 2, fill=False, lw=0.7, color="grey"))
    ax.text(sh.ox1 + 8, sh.oy1 - 8, "grey ears: wall-screw\nclearance holes, NO insert", fontsize=7, color="grey", ha="left")
    ax.set_aspect("equal"); ax.set_xlim(sh.ox0 - 22, sh.ox1 + 22); ax.set_ylim(sh.oy0 - 10, sh.oy1 + 10)
    ax.set_xlabel("x, mm  (origin = PCB centre)"); ax.set_ylabel("y, mm")
    ax.set_title("%s -- %d x M3 threaded insert, type %s -- plan view from above (+z)\n"
                 "red: in the bosses, axis vertical, pressed from above.   blue: in the tabs, axis HORIZONTAL (in this plane), pressed from the wall side -- see the wall views below" % (stem, n, INSERT), fontsize=9)

    # elevations: one per wall with tabs, seen from OUTSIDE that wall. The
    # hole is in a vertical face, and this is the view that says so
    for i, edge in enumerate(edges):
        ev = elev[i]
        axis, outer, inner, sign = sh.wall_frame(edge)
        lo, hi = (sh.oy0, sh.oy1) if axis == "x" else (sh.ox0, sh.ox1)
        ev.add_patch(Rectangle((lo, z0), hi - lo, c["plate_t"], facecolor="#eeeeee", edgecolor="black", lw=1.0))
        ev.add_patch(Rectangle((lo, zp), hi - lo, c["tab_h"] + 3, fill=False, lw=0.5, ls=":", color="grey"))
        k = 0
        for t in spec["tabs"]:
            k_n = 4 + 1 + spec["tabs"].index(t)
            if t["edge"] != edge:
                continue
            ev.add_patch(Rectangle((t["pos"] - c["tab_w"] / 2, zp), c["tab_w"], c["tab_h"], facecolor="#cfe2f3", edgecolor="tab:blue", lw=1.0))
            ev.add_patch(Circle((t["pos"], zp + c["tab_screw_z"]), c["insert_d"] / 2, color="tab:blue"))
            ev.text(t["pos"], zp + c["tab_h"] + 1, str(k_n), ha="center", va="bottom", fontsize=10, weight="bold", color="tab:blue")
        for ear in spec["ears"]:
            if ear["edge"] == edge:
                ev.add_patch(Rectangle((ear["pos"] - e["w"] / 2, z0 - e["foot"]), e["w"], e["foot"] + e["t"], fill=False, lw=0.6, color="grey"))
        along = "y" if axis == "x" else "x"
        ev.set_xlim(lo - 5, hi + 5); ev.set_ylim(z0 - e["foot"] - 2, zp + c["tab_h"] + 6); ev.set_aspect("equal", adjustable="datalim")
        ev.set_yticks([zp, zp + c["tab_screw_z"]]); ev.set_yticklabels(["plate top", "hole axis"], fontsize=7)
        ev.set_xlabel("%s, mm" % along, fontsize=7)
        ev.set_title("%s seen from outside: the tab faces, holes Ø%.1f x %.1f deep, axis %.0f mm above the plate top, HORIZONTAL"
                     % (FACE[edge].replace("from ", ""), c["insert_d"], c["insert_depth"], c["tab_screw_z"]), fontsize=8)
        if sign > 0 and axis == "x" or sign < 0 and axis == "y":
            ev.invert_xaxis()      # seen from outside, the along-wall axis runs the other way
    # table
    tab_ax.axis("off")
    tbl = tab_ax.table(cellText=[[str(v) for v in r] for r in rows],
                       colLabels=["#", "type", "axis / pressed", "entry face", "x", "y", "z of axis", "hole Ø x depth"],
                       colWidths=[0.04, 0.10, 0.22, 0.18, 0.09, 0.09, 0.10, 0.14], loc="center", cellLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 1.25)
    tab_ax.text(0.5, -0.30, "z = 0 is the PCB underside; plate top is z = %.1f, plate bottom z = %.1f. Hole depth may be deeper, never shallower." % (zp, z0),
                transform=tab_ax.transAxes, ha="center", fontsize=8)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", stem + "-insert-drawing.png")
    fig.savefig(out, dpi=150, bbox_inches="tight"); print(out, n, "inserts")
