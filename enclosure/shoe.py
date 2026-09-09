"""Origin 89 enclosure family: a plate and a shoe, for Board A and Board B.

The shape is the one every wall-hung DC controller has settled on (Victron's
SmartSolar and Cerbo are the references): a flat plate
carries the board on four bosses and hangs on the wall by four ears at its
sides, screws in the open the way a Cerbo GX hangs; the one-piece shoe
drops over it and is held by four M3 screws through its side walls into
tabs standing on the plate, the way a SmartSolar 100/50 sits on its bracket.
So the unit goes up and comes down assembled, and opens on the wall. The
connector edges are open under the shoe's rim, plugs go in from the side
and their cables leave downward, so there are no hoods and no lid seam.
Every insert (eight per box) sits in a flat face of the plate, which is
what an insert press wants.

Runs two ways, from the same file:
  - live, inside FreeCAD (through the MCP bridge or the Python console):
        exec(open("enclosure/shoe.py").read(), ns := {}); ns["build"](doc, ns["A"], "A_")
  - headless, to regenerate the fabrication artefacts:
        /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd enclosure/shoe.py

Frame: each board's own. Origin at board centre, X across, Y along, Z up,
z=0 the board's bottom surface. The connector heights come from datasheets,
not from the fab's STEP, which carries placeholder blocks.
"""

import os

import FreeCAD as App
import Part
from FreeCAD import Vector as V

# the rules both boxes share: JLC3DP's MJF floor (2.0 walls, 1.0 features),
# an insert press's flat faces, one screw kind per job
COMMON = dict(
    wall=2.0, top=2.5, plate_t=3.0,
    # board stands 4.5 mm off the plate: through-hole pins protrude ~2.5 mm
    standoff=4.5,
    # the shoe registers on a rim standing on the plate, 0.3 inside the wall.
    # 2.0 tall: through-hole pins reach 2.5 below the board and the rim must
    # stay under them where the board edge crosses it
    rim=2.0, rim_h=2.0, clear=0.3,
    # inserts: JLC3DP's DPLK-M3 (OD 4.5, 5.8 long), the one type on their
    # sheet with no mouth recess: hole 3.9 x 7.0. Bosses carry a 14 mm face
    # round it: 5 mm of wall, and the 14 mm flat their press asks for.
    # The face presses solder mask outside the copper-free radius, which
    # nothing on either board's bottom side minds. A 7.0 hole through a
    # 4.5 boss and a 3 mm plate leaves 0.5, so each boss has a 2 mm heel
    # under the plate; the box stands on feet, so the heel costs nothing
    boss_d=14.0, boss_base_d=16.0, insert_d=3.9, insert_depth=7.0, heel=2.0,
    # the cavity is the board plus `pad` on every side: room for the tabs
    # that hold the shoe, and the connectors end up set back under the rim
    # the way Victron's do. A 10 mm corner radius outside, 8 inside.
    # 14: the tab is 10.5 thick and stands 0.3 off the wall, which leaves the
    # board 3.2 mm. JLC's outline is +/-0.2, MJF +/-0.3 % over 100 mm, and
    # A bigger box beats reaching for a file
    pad=14.0, fillet_r=10.0, top_fillet_r=2.0,
    # the board itself, grown by this much all round, is an envelope too:
    # the gate refuses a plate or shoe that comes closer than this to it
    board_margin=2.0,
    # the shoe is held by M3 x 8 screws through its side walls into inserts
    # in tabs standing on the plate: the box must open on the wall.
    # A tab is 14 wide and 15 tall so an insert press has its flat 14 x 14
    # round the hole, 10.5 thick so the 3.9 hole keeps 3.3 mm of wall each
    # side and a 3.5 floor, and the screw axis sits 8 above the plate so
    # the press head clears it. The screw head stands on the wall: a
    # counterbore in a 2 mm wall would leave 0.8, which JLC3DP refuses
    tab_w=14.0, tab_t=10.5, tab_h=15.0, tab_screw_z=8.0, side_bore=3.4,
    # the plate hangs by four ears standing off its side walls on the
    # straight run past the corner radius, #8 screws through them in the
    # open (Cerbo GX). 14 x 14, 5 thick above the plate's underside, 2 mm
    # proud of its top, which the shoe never reaches, because a 3 mm ear
    # read as thin, and it is the one part of the box that carries
    # the box. Under each ear a 10 mm foot: the whole box stands off the
    # wall, so the wall is 17.5 mm from the antenna (A-15 asks 15 of any
    # material; it had been read as the box only) and the back vents
    # breathe. A #8 x 1 1/2" keeps 23 mm in the wall. Rounded ends
    ear=dict(len=14.0, w=14.0, t=5.0, foot=10.0, hole=4.5, r=4.0),
)

# datasheet bodies over the routed positions, drawn as translucent envelopes
# so a collision shows on screen: ((x0, x1), (y0, y1), height above board top)
A_ENVELOPES = {
    "CN1  KF2EDGR-5.08-2P": ((-39.1, -28.9), (-61.0, -48.8), 8.3),
    "CN2  KF2EDGR-3.5-3P": ((-26.8, -15.2), (-61.5, -52.3), 7.0),
    "CN3  KF2EDGR-3.5-3P": ((-13.8, -2.2), (-61.5, -52.3), 7.0),
    "CN4  KF2EDGR-3.5-3P": ((-0.8, 10.8), (-61.5, -52.3), 7.0),
    "CN5  KF2EDGR-3.5-3P": ((12.2, 23.8), (-61.5, -52.3), 7.0),
    "CN8  KF2EDGR-3.5-3P": ((25.2, 36.8), (-61.5, -52.3), 7.0),
    "CN10 KF2EDGR-3.5-3P": ((-49.0, -39.8), (8.2, 19.8), 7.0),
    "CN11 KF2EDGR-3.5-3P": ((39.8, 49.0), (8.2, 19.8), 7.0),
    "CN12 KF2EDGR-3.5-2P": ((-48.9, -39.7), (-18.5, -10.5), 7.0),
    "CN13 KF2EDGR-3.5-3P": ((-49.0, -39.8), (-33.8, -22.2), 7.0),
    "CN14 KF2EDGR-3.5-2P": ((-48.9, -39.7), (-4.0, 4.0), 7.0),
    "CN6  B4B-PH-K-S": ((44.4, 49.1), (-5.0, 5.0), 6.0),
    "CN7  B4B-PH-K-S": ((44.4, 49.1), (-46.5, -36.5), 6.0),
    "CN9  B5P-VH": ((40.4, 48.9), (-25.4, -5.6), 12.7),
    "H1   PZ254V-11-04P": ((-47.0, -36.8), (-21.8, -19.2), 8.6),
    "JP1  PZ254V-11-02P": ((-22.6, -17.6), (-44.9, -42.3), 8.6),
    "JP2  PZ254V-11-02P": ((-9.6, -4.6), (-44.9, -42.3), 8.6),
    "JP3  PZ254V-11-02P": ((3.3, 8.4), (-44.9, -42.3), 8.6),
    "JP4  PZ254V-11-02P": ((16.4, 21.4), (-47.5, -45.0), 8.6),
    "U8   ESP32-C6-WROOM-1": ((-13.9, 4.1), (29.8, 55.3), 3.2),
    # the mating plugs, wired and inserted: body beyond the board edge,
    # height above the board top. KF2EDGK-5.08 ~12.2 deep / 8.6 tall, -3.5 ~9.5 / 8.0
    "CN1  plug": ((-39.1, -28.9), (-74.7, -62.5), 8.6),
    "CN2  plug": ((-26.8, -15.2), (-72.0, -62.5), 8.0),
    "CN3  plug": ((-13.8, -2.2), (-72.0, -62.5), 8.0),
    "CN4  plug": ((-0.8, 10.8), (-72.0, -62.5), 8.0),
    "CN5  plug": ((12.2, 23.8), (-72.0, -62.5), 8.0),
    "CN8  plug": ((25.2, 36.8), (-72.0, -62.5), 8.0),
    "CN10 plug": ((-59.5, -50.0), (8.2, 19.8), 8.0),
    "CN14 plug": ((-59.5, -50.0), (-4.0, 4.0), 8.0),
    "CN12 plug": ((-59.5, -50.0), (-18.5, -10.5), 8.0),
    "CN13 plug": ((-59.5, -50.0), (-33.8, -22.2), 8.0),
    "CN11 plug": ((50.0, 59.5), (8.2, 19.8), 8.0),
}

B_ENVELOPES = {
    "K1   G5V-2 (vertical)": ((-2.05, 8.05), (-4.25, 16.25), 11.5),
    "K2   G5V-2 (horizontal)": ((8.25, 28.75), (-14.55, -4.45), 11.5),
    "CN9  B5P-VH": ((-38.5, -30.5), (-10.8, 10.8), 10.6),
    "CN10 KF2EDGR-5.08-2P": ((24.7, 41.0), (7.0, 17.0), 8.6),
    "F1   BLX-A-B + fuse": ((11.5, 34.1), (-3.2, 5.8), 9.0),
    "D6   SMB": ((21.7, 26.3), (10.2, 13.8), 2.5),
    "U2   SOIC-16": ((-17.6, -7.6), (2.8, 6.8), 1.8),
    "U1   SOT-89": ((-7.1, -2.5), (-7.1, -4.5), 1.7),
    "CN9  VHR-5N plug + wire exit": ((-38.5, -30.5), (-11.0, 11.0), 22.0),
    "CN10 KF2EDGK plug, outside the wall": ((41.0, 53.0), (7.0, 17.0), 8.6),
}

A = dict(
    stems=("board-a-plate", "board-a-shoe"),
    board_x=100.0, board_y=125.0, board_t=1.6,
    # the mounting holes are the constants tools/validate_gerbers.py checks,
    # so the case and the copper agree by construction
    holes=[(-46.0, 58.5), (46.0, 58.5), (46.0, -58.5), (-46.0, -58.5)],
    # A-15: 15 mm of air past the antenna end (y=55.3) -> the cavity's back
    back_y=70.5,
    # interior height above the board bottom: the JST VH on CN9 is 12.7 mm
    # tall and its cable bends up; the antenna needs 15 mm of air above the
    # module (top at 4.9) -> 19.9; 20 satisfies both
    inner_z=20.0,
    # the open edges: plugs stand 8.6 above the board top (10.2), the rim of
    # the shoe passes 3.8 above them: room for the fingers that pull one
    mouths=[dict(edge="front", span=(-40.5, 38.5), z=14.0),
            dict(edge="left", span=(-35.25, 21.25), z=14.0),
            dict(edge="right", span=(-49.0, 21.25), z=14.0)],
    # top-entry JSTs on the right (CN9 VH, CN6/CN7 PH): their cables leave
    # upward, so the wall opens to the underside of the top over them
    notches=[dict(edge="right", span=(-28.0, 5.25), z0=8.0),
             dict(edge="right", span=(-49.0, -34.0), z0=8.0)],
    # shoe tabs on both side walls, where the wall is whole below the mouths;
    # the same two places left and right. -58, not -53: at -53 the right tab
    # sat 4.6 mm from CN7's PH plug; the straight wall runs to -66.5
    tabs=[dict(edge="left", pos=45.0), dict(edge="left", pos=-58.0),
          dict(edge="right", pos=45.0), dict(edge="right", pos=-58.0)],
    ears=[dict(edge="left", pos=-56.5), dict(edge="left", pos=56.5),
          dict(edge="right", pos=-56.5), dict(edge="right", pos=56.5)],
    # A-15: nothing under the antenna either, so a window in the plate
    antenna=dict(x=(-16.5, 6.5), y=46.0),
    # convection: the bucks dissipate well under a watt, slots on the back wall
    vents=dict(n=6, w=2.0, h=8.0, z=9.0, pitch=8.0),
    # one light pipe, over the status/fault pair: the heartbeat a person at
    # the panel reads. The four RX lamps are bench lamps (they show with the
    # shoe off, which is when somebody is looking at buses), and the top
    # carries no lettering at all: a plain shell, marked by a label.
    # Bivar PLP1-750: pipe 3.0, ring 3.1, hole 3.07 +0.08/-0.05, flange
    # 3.8 x 1.3 standing ON the shoe (a recess would put the tip on the LED);
    # the tip ends 19.0 below the top and the LED top is 19.7, so 0.7 of air
    led_pipes=[(-37.8, -7.5)], pipe=dict(hole_d=3.1, flange_d=0.0, flange_depth=0.0),
    envelopes=A_ENVELOPES,
)

B = dict(
    stems=("board-b-plate", "board-b-shoe"),
    board_x=80.0, board_y=55.0, board_t=1.6,
    holes=[(-36.5, 24.0), (36.5, 24.0), (36.5, -24.0), (-36.5, -24.0)],
    back_y=None,
    # the VH plug on CN9 stands ~12 mm over a 10.6 mm header and its cable
    # bends up: 28 is what that needs
    inner_z=28.0,
    # CN10's plug sits outside the right wall (KF2EDGK, 8.6 tall)
    mouths=[dict(edge="right", span=(4.0, 20.0), z=14.0)],
    # CN9's cable leaves the VH plug upward and out through the left wall
    notches=[dict(edge="left", span=(-6.0, 6.0), z0=8.0)],
    # the side walls carry the openings, so the tabs go on front and back
    tabs=[dict(edge="front", pos=-20.0), dict(edge="front", pos=20.0),
          dict(edge="back", pos=-20.0), dict(edge="back", pos=20.0)],
    ears=[dict(edge="left", pos=-21.5), dict(edge="left", pos=21.5),
          dict(edge="right", pos=-21.5), dict(edge="right", pos=21.5)],
    antenna=None, vents=None,
    # LED1/LED2 show what each relay coil got: bench lamps, seen with the
    # shoe off. No pipes
    led_pipes=[], pipe=dict(hole_d=3.0, flange_d=3.5, flange_depth=0.8),
    envelopes=B_ENVELOPES,
)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(d, z0, z1, x, y):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


def fillet_vertical(shape, r):
    edges = [e for e in shape.Edges
             if e.Curve.__class__.__name__ == "Line"
             and abs(e.tangentAt(e.FirstParameter).z) > 0.99]
    return shape.makeFillet(r, edges)


def fillet_at_z(shape, r, z):
    edges = [e for e in shape.Edges
             if abs(e.BoundBox.ZMin - z) < 1e-6 and abs(e.BoundBox.ZMax - z) < 1e-6]
    return shape.makeFillet(r, edges)


class Shoe:
    """One board's plate and shoe, from COMMON and its own table."""

    def __init__(self, spec):
        self.s, self.c = spec, COMMON
        s, c = spec, COMMON
        d, w = c["pad"], c["wall"]
        self.ix0, self.ix1 = -s["board_x"] / 2 - d, s["board_x"] / 2 + d
        self.iy0 = -s["board_y"] / 2 - d
        self.iy1 = max(s["back_y"] or 0.0, s["board_y"] / 2 + d)
        self.ox0, self.ox1 = self.ix0 - w, self.ix1 + w
        self.oy0, self.oy1 = self.iy0 - w, self.iy1 + w
        self.zp = -c["standoff"]                       # plate top
        self.zt = s["inner_z"] + c["top"]              # shoe top

    def edge_cut(self, edge, span, z0, z1):
        """A box through one wall over `span` along it, between z0 and z1."""
        if edge == "front":
            return box(span[0], span[1], self.oy0 - 1, self.iy0 + 1, z0, z1)
        if edge == "back":
            return box(span[0], span[1], self.iy1 - 1, self.oy1 + 1, z0, z1)
        if edge == "left":
            return box(self.ox0 - 1, self.ix0 + 1, span[0], span[1], z0, z1)
        return box(self.ix1 - 1, self.ox1 + 1, span[0], span[1], z0, z1)

    def wall_frame(self, edge):
        """For one wall: its outer face, its inner face, and the unit normal
        pointing OUT, as (axis, outer, inner, sign)."""
        return {"left": ("x", self.ox0, self.ix0, -1), "right": ("x", self.ox1, self.ix1, 1),
                "front": ("y", self.oy0, self.iy0, -1), "back": ("y", self.oy1, self.iy1, 1)}[edge]

    def hcyl(self, d, edge, pos, z, a, b):
        """A cylinder of diameter d along the wall's normal, from a to b
        (coordinates on the normal axis), centred at `pos` along the wall."""
        axis, outer, inner, sign = self.wall_frame(edge)
        lo, hi = min(a, b), max(a, b)
        if axis == "x":
            return Part.makeCylinder(d / 2, hi - lo, V(lo, pos, z), V(1, 0, 0))
        return Part.makeCylinder(d / 2, hi - lo, V(pos, lo, z), V(0, 1, 0))

    def tab_box(self, edge, pos, extra=0.0):
        """The tab's solid on the plate: against the wall (0.3 inside it),
        tab_t thick, tab_w wide, tab_h tall. `extra` widens it for clearance."""
        c = self.c
        axis, outer, inner, sign = self.wall_frame(edge)
        near = inner - sign * c["clear"]                 # face toward the wall
        far = near - sign * c["tab_t"]
        w2 = c["tab_w"] / 2 + extra
        if axis == "x":
            return box(min(near, far), max(near, far), pos - w2, pos + w2, self.zp, self.zp + c["tab_h"])
        return box(pos - w2, pos + w2, min(near, far), max(near, far), self.zp, self.zp + c["tab_h"])

    def shoe(self):
        s, c = self.s, self.c
        body = box(self.ox0, self.ox1, self.oy0, self.oy1, self.zp, self.zt)
        body = fillet_vertical(body, c["fillet_r"])
        body = fillet_at_z(body, c["top_fillet_r"], self.zt)
        inner = box(self.ix0, self.ix1, self.iy0, self.iy1, self.zp - 1, s["inner_z"])
        inner = fillet_vertical(inner, c["fillet_r"] - c["wall"])
        body = body.cut(inner)
        for m in s["mouths"]:
            body = body.cut(self.edge_cut(m["edge"], m["span"], self.zp - 1, m["z"]))
        for n in s["notches"]:
            body = body.cut(self.edge_cut(n["edge"], n["span"], n["z0"], s["inner_z"] + 0.01))
        zs = self.zp + c["tab_screw_z"]
        for t in s["tabs"]:
            axis, outer, inner_face, sign = self.wall_frame(t["edge"])
            body = body.cut(self.hcyl(c["side_bore"], t["edge"], t["pos"], zs, outer + sign, inner_face - sign))
        if s["vents"]:
            v = s["vents"]
            x = -(v["n"] - 1) * v["pitch"] / 2
            for i in range(v["n"]):
                body = body.cut(self.edge_cut("back", (x - v["w"] / 2, x + v["w"] / 2), v["z"], v["z"] + v["h"]))
                x += v["pitch"]
        pp = s["pipe"]
        for lx, ly in s["led_pipes"]:
            body = body.cut(cyl(pp["hole_d"], s["inner_z"] - 1, self.zt + 1, lx, ly))
            if pp["flange_depth"] > 0:
                body = body.cut(cyl(pp["flange_d"], self.zt - pp["flange_depth"], self.zt + 1, lx, ly))
        return body.removeSplitter()

    def plate(self):
        s, c = self.s, self.c
        z0 = self.zp - c["plate_t"]
        plate = box(self.ox0, self.ox1, self.oy0, self.oy1, z0, self.zp)
        plate = fillet_vertical(plate, c["fillet_r"])
        e, k = c["ear"], c["clear"]
        for ear in s["ears"]:
            axis, outer, inner, sign = self.wall_frame(ear["edge"])
            far = outer + sign * e["len"]
            # rooted 1 mm into the plate below the wall line; above the plate
            # it starts 0.3 outside the wall, where the shoe's skirt will be
            root, free = outer - sign, outer + sign * k
            zf = z0 - e["foot"]
            if axis == "x":
                lug = box(min(root, far), max(root, far), ear["pos"] - e["w"] / 2, ear["pos"] + e["w"] / 2, zf, self.zp)
                lug = lug.fuse(box(min(free, far), max(free, far), ear["pos"] - e["w"] / 2, ear["pos"] + e["w"] / 2, self.zp - 0.01, z0 + e["t"]))
                hx, hy = outer + sign * (e["len"] - e["w"] / 2), ear["pos"]
            else:
                lug = box(ear["pos"] - e["w"] / 2, ear["pos"] + e["w"] / 2, min(root, far), max(root, far), zf, self.zp)
                lug = lug.fuse(box(ear["pos"] - e["w"] / 2, ear["pos"] + e["w"] / 2, min(free, far), max(free, far), self.zp - 0.01, z0 + e["t"]))
                hx, hy = ear["pos"], outer + sign * (e["len"] - e["w"] / 2)
            outer_edges = [ed for ed in lug.Edges if abs(ed.tangentAt(ed.FirstParameter).z) > 0.99
                           and abs((ed.BoundBox.XMin if axis == "x" else ed.BoundBox.YMin) - far) < 1e-6]
            lug = lug.makeFillet(e["r"], outer_edges)
            plate = plate.fuse(lug).cut(cyl(e["hole"], zf - 1, z0 + e["t"] + 1, hx, hy))
        rim = box(self.ix0 + k, self.ix1 - k, self.iy0 + k, self.iy1 - k, self.zp, self.zp + c["rim_h"])
        rim = fillet_vertical(rim, c["fillet_r"] - c["wall"] - k)
        rim = rim.cut(box(self.ix0 + k + c["rim"], self.ix1 - k - c["rim"], self.iy0 + k + c["rim"],
                          self.iy1 - k - c["rim"], self.zp - 1, self.zp + c["rim_h"] + 1))
        for m in s["mouths"]:            # a flat floor under the plugs and their cables
            rim = rim.cut(self.edge_cut(m["edge"], m["span"], self.zp - 1, self.zp + c["rim_h"] + 1))
        plate = plate.fuse(rim)
        zs = self.zp + c["tab_screw_z"]
        for t in s["tabs"]:
            axis, outer, inner_face, sign = self.wall_frame(t["edge"])
            tab = self.tab_box(t["edge"], t["pos"])
            near = inner_face - sign * k
            tab = tab.cut(self.hcyl(c["insert_d"], t["edge"], t["pos"], zs, near + sign, near - sign * c["insert_depth"]))
            plate = plate.fuse(tab)
        # bosses clipped to the cavity outline, which with 14 mm of pad never bites
        inside = box(self.ix0 + k, self.ix1 - k, self.iy0 + k, self.iy1 - k, self.zp - 1, 1)
        inside = fillet_vertical(inside, c["fillet_r"] - c["wall"] - k)  # the cavity's own rounded corners
        for hx, hy in s["holes"]:
            boss = cyl(c["boss_base_d"], self.zp, self.zp + 1.5, hx, hy).fuse(cyl(c["boss_d"], self.zp, 0.0, hx, hy))
            plate = plate.fuse(boss.common(inside))
            plate = plate.fuse(cyl(c["boss_base_d"], z0 - c["heel"], z0 + 0.01, hx, hy))
            plate = plate.cut(cyl(c["insert_d"], -c["insert_depth"], 0.1, hx, hy))
        if s["antenna"]:
            ax, ay = s["antenna"]["x"], s["antenna"]["y"]
            plate = plate.cut(box(ax[0], ax[1], ay, self.iy1 + 1, z0 - 1, self.zp + 1))
        return plate.removeSplitter()

    def envelopes(self):
        """The board's datasheet bodies and inserted plugs, each plug also
        swept 20 mm outward (a mouth that clears a seated plug but not its
        travel is a box nobody can wire), and the board itself grown by
        board_margin all round."""
        s, m = self.s, self.c["board_margin"]
        out = [(name, box(x0, x1, y0, y1, s["board_t"], s["board_t"] + h))
               for name, ((x0, x1), (y0, y1), h) in s["envelopes"].items()]
        out.append(("board + %.1f mm" % m, box(-s["board_x"] / 2 - m, s["board_x"] / 2 + m,
                                              -s["board_y"] / 2 - m, s["board_y"] / 2 + m, 0.0, s["board_t"])))
        bx, by = s["board_x"] / 2, s["board_y"] / 2
        for name, ((x0, x1), (y0, y1), h) in s["envelopes"].items():
            if "plug" not in name:
                continue
            if y1 <= -by + 0.5: y0 -= 20.0            # front edge: travel is -y
            elif x0 >= bx - 0.5: x1 += 20.0           # right edge
            elif x1 <= -bx + 0.5: x0 -= 20.0          # left edge
            out.append((name + " travel", box(x0, x1, y0, y1, s["board_t"], s["board_t"] + h)))
        return out


def build(doc, spec, prefix):
    for o in list(doc.Objects):
        if o.Name.startswith(prefix):
            doc.removeObject(o.Name)
    sh = Shoe(spec)
    plate = doc.addObject("Part::Feature", prefix + "Plate")
    plate.Shape = sh.plate()
    shoe = doc.addObject("Part::Feature", prefix + "Shoe")
    shoe.Shape = sh.shoe()
    grp = doc.addObject("App::DocumentObjectGroup", prefix + "Envelopes")
    for name, shape in sh.envelopes():
        o = doc.addObject("Part::Feature", prefix + "env_" + name.split()[0])
        o.Label = prefix + "env " + name
        o.Shape = shape
        grp.addObject(o)
    doc.recompute()
    if App.GuiUp:
        plate.ViewObject.ShapeColor = (0.16, 0.16, 0.18)
        shoe.ViewObject.ShapeColor = (0.16, 0.16, 0.18)
        for o in grp.Group:
            o.ViewObject.ShapeColor = (1.0, 0.55, 0.1)
            o.ViewObject.Transparency = 50
    return (plate, shoe), sh


def check_clearances(parts, envelopes):
    """The two gates every printed box must pass. Datasheet envelopes must
    clear every part (a collision here is a case that will not close over
    the connectors it was drawn around), and the printed parts must not
    intersect each other, or they print as a fit that cannot be assembled."""
    for name, env in envelopes:
        for obj in parts:
            v = env.common(obj.Shape).Volume
            if v > 0.01:
                print("GATE: %s collides with %s (%.1f mm^3)" % (name, obj.Name, v), flush=True)
                raise SystemExit(1)
    print("envelopes clear of all parts")
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            v = a.Shape.common(b.Shape).Volume
            if v > 0.01:
                print("GATE: %s intersects %s (%.1f mm^3)" % (a.Name, b.Name, v), flush=True)
                raise SystemExit(1)
    print("parts clear of each other")


def report_solids(parts):
    for obj in parts:
        n = len(obj.Shape.Solids)
        print("%-11s valid=%s solids=%d volume=%.0f mm^3" % (obj.Name, obj.Shape.isValid(), n, obj.Shape.Volume))
        if n != 1:
            print("GATE: %s is %d solids: a cut severed it" % (obj.Name, n), flush=True)
            raise SystemExit(1)


def export(parts, outdir, stems):
    os.makedirs(outdir, exist_ok=True)
    for obj, stem in zip(parts, stems):
        Part.export([obj], os.path.join(outdir, stem + ".step"))
        obj.Shape.exportStl(os.path.join(outdir, stem + ".stl"))
    return outdir


def main():
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    doc = App.ActiveDocument if App.GuiUp and App.ActiveDocument else App.newDocument("shoe")
    for spec, prefix in ((A, "A_"), (B, "B_")):
        parts, sh = build(doc, spec, prefix)
        if not App.GuiUp:
            check_clearances(parts, sh.envelopes())
            export(parts, os.path.join(here, "out"), spec["stems"])
            report_solids(parts)
    if not App.GuiUp:
        print("exported to", os.path.join(here, "out"))


# FreeCAD's script runner does not set __name__ to "__main__"; headless
# execution is the signal that this file was invoked to regenerate artefacts.
# insert_drawing.py imports this file and sets O89_SHOE_LIB so the import
# does not rebuild.
if __name__ == "__main__" or (not App.GuiUp and not os.environ.get("O89_SHOE_LIB")):
    main()
