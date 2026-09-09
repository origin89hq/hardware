#!/usr/bin/env python3
"""Check an exported Gerber set against the copper rules that only the
artwork can witness: the mounting-hole keep-outs and the antenna voids,
layer by layer. Which holes, which radius and which voids come from a rule
file beside the board, so the same script serves every board.

Usage:

    tools/validate_gerbers.py <gerber-rules.json> <gerber-dir-or-zip>

Exit 0 when every check passes, 1 on any FAIL, 2 when the input is not a
Gerber set this script recognises. Needs `gerbonara` and `shapely`
(pip install gerbonara shapely).

The rule file names the board's mounting holes (centres, finished drill,
keep-out radius, the rule number), its voids (rectangles that must be bare
on every copper layer, each with its rule number) and the layer files:

    {
      "mounting_holes": {"rule": "A-02", "drill": 3.2, "keepout_radius": 3.2,
                         "centres": [[-46, 58.5], [46, 58.5], [46, -58.5], [-46, -58.5]]},
      "voids": [{"rule": "A-15", "label": "antenna band above y=52.5",
                 "rect": [-50, 52.5, 50, 62.5]}],
      "copper_layers": [["L1 top", "Gerber_TopLayer.GTL"], ...],
      "silk_layers": [["top silk", "Gerber_TopSilkscreenLayer.GTO"], ...]
    }

Why this exists: the placement checker cannot see pads, copper or routing,
and DRC is silent about both failures this script names. JLCPCB's delivered
package for the controller (2026-08-31) carried a 6.4 mm copper pad flashed
at all four mounting holes on all four copper layers, copper filling
exactly the 3.2 mm-radius zone A-02 declares keep-out, and every DRC run
had been clean, because a pad at a hole is normal to DRC. This script went
red on that delivery before it was fixed; that is its birth certificate.

A missing expected layer is a FAIL, not a skip: a check that silently
compares nothing reports success about nothing.

The check measures the FINISHED board, not the raw artwork: every non-plated
drill is subtracted from every copper layer first, because copper strictly
inside an NPTH drill cannot exist after fabrication. EasyEDA flashes a pad
even at pad == hole size, and that flash is exactly what the drill consumes;
without the subtraction the check cannot distinguish it from real copper.
Everything outside a drill still fails, which is how this check caught the
pour flooding to r=1.85 around the controller's two bottom holes after the
6.4 mm pads that had been holding the pour back were shrunk.

Only holes of the mounting drill size are held to the centre list; a board
may have other non-plated holes (connector pegs) and those are reported,
subtracted from the copper, and otherwise left alone.

Geometry notes: dark/clear polarity is honoured in file order. Curved
region edges are approximated by chords between their endpoints; the sag
is far below the millimetre-scale margins checked here.
"""

import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from gerbonara import GerberFile
    from gerbonara import graphic_primitives as gp
    from shapely import affinity
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import unary_union
except ImportError as e:
    print(f"missing dependency: {e.name} (pip install gerbonara shapely)")
    sys.exit(2)

NPTH_DRILL = "Drill_NPTH_Through.DRL"


def prim_to_shapely(p):
    if isinstance(p, gp.Circle):
        return Point(p.x, p.y).buffer(p.r, quad_segs=32)
    if isinstance(p, gp.Rectangle):
        b = box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)
        if p.rotation:
            b = affinity.rotate(b, math.degrees(p.rotation), origin=(p.x, p.y))
        return b
    if isinstance(p, gp.Line):
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, quad_segs=16)
    if isinstance(p, gp.Arc):
        # cx/cy are absolute per gerbonara graphic_primitives.Arc.
        r = math.dist((p.x1, p.y1), (p.cx, p.cy))
        a1 = math.atan2(p.y1 - p.cy, p.x1 - p.cx)
        if p.is_circle:
            a2 = a1 - 2 * math.pi if p.clockwise else a1 + 2 * math.pi
        else:
            a2 = math.atan2(p.y2 - p.cy, p.x2 - p.cx)
            if p.clockwise:
                while a2 > a1:
                    a2 -= 2 * math.pi
            else:
                while a2 < a1:
                    a2 += 2 * math.pi
        n = max(8, int(abs(a2 - a1) * r / 0.05))
        pts = [(p.cx + r * math.cos(a1 + (a2 - a1) * i / n),
                p.cy + r * math.sin(a1 + (a2 - a1) * i / n)) for i in range(n + 1)]
        return LineString(pts).buffer(p.width / 2, quad_segs=16)
    if isinstance(p, gp.ArcPoly):
        pts = list(p.outline)
        if len(pts) < 3:
            return None
        poly = Polygon(pts)
        return poly if poly.is_valid else poly.buffer(0)
    raise TypeError(f"unhandled primitive {type(p).__name__}")


def layer_dark(path):
    """Final dark geometry of one Gerber file, polarity honoured in order."""
    dark_parts, geom = [], None
    for obj in GerberFile.open(path).objects:
        for p in obj.to_primitives(unit="mm"):
            s = prim_to_shapely(p)
            if s is None or s.is_empty:
                continue
            if p.polarity_dark:
                dark_parts.append(s)
            else:
                if dark_parts:
                    merged = unary_union(dark_parts)
                    geom = merged if geom is None else unary_union([geom, merged])
                    dark_parts = []
                if geom is not None:
                    geom = geom.difference(s)
    if dark_parts:
        merged = unary_union(dark_parts)
        geom = merged if geom is None else unary_union([geom, merged])
    return geom


def npth_holes(path):
    """(x, y, diameter) of every hole in an Excellon NPTH file."""
    tools, holes, current = {}, [], None
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("T") and "C" in line and not line.startswith("T0C"):
            name, _, dia = line.partition("C")
            try:
                tools[name] = float(dia)
            except ValueError:
                continue
        elif line.startswith("T") and line[1:].isdigit():
            current = tools.get(line)
        elif line.startswith("X") and "Y" in line and current is not None:
            x, _, y = line[1:].partition("Y")
            holes.append((float(x), float(y), current))
    return holes


def load_rules(path):
    """The board's rule file, checked for shape so a typo fails here and not
    as a check that silently compares nothing."""
    rules = json.loads(Path(path).read_text())
    mh = rules["mounting_holes"]
    centres = [(float(x), float(y)) for x, y in mh["centres"]]
    if not centres:
        raise ValueError("mounting_holes.centres is empty")
    voids = []
    for v in rules.get("voids", []):
        x1, y1, x2, y2 = (float(c) for c in v["rect"])
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"void {v.get('rule')} rect is not (xmin, ymin, xmax, ymax)")
        voids.append((str(v["rule"]), str(v["label"]), box(x1, y1, x2, y2)))
    copper = [(str(n), str(f)) for n, f in rules["copper_layers"]]
    silk = [(str(n), str(f)) for n, f in rules.get("silk_layers", [])]
    if not copper:
        raise ValueError("copper_layers is empty")
    return {
        "rule": str(mh["rule"]),
        "centres": centres,
        "drill": float(mh["drill"]),
        "keepout": float(mh["keepout_radius"]),
        "voids": voids,
        "copper": copper,
        "silk": silk,
    }


def unpack(src):
    """A directory as given, or a zip unpacked flat into a temporary one."""
    if src.is_file() and src.suffix.lower() == ".zip":
        tmp = tempfile.mkdtemp(prefix="gerber-check-")
        with zipfile.ZipFile(src) as z:
            for info in z.infolist():
                name = info.filename
                if not info.flag_bits & 0x800:
                    # JLC zips carry cp437-mangled GBK names; the layer
                    # files themselves are plain ASCII either way.
                    try:
                        name = name.encode("cp437").decode("gbk")
                    except UnicodeError:
                        pass
                if info.is_dir():
                    continue
                out = Path(tmp) / Path(name).name
                out.write_bytes(z.read(info))
        return Path(tmp)
    return src


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    try:
        rules = load_rules(sys.argv[1])
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"bad rule file {sys.argv[1]}: {e}")
        return 2
    src = unpack(Path(sys.argv[2]))
    if not src.is_dir():
        print(f"not a directory or zip: {src}")
        return 2

    failed = False

    def check(ok, label, detail=""):
        nonlocal failed
        failed |= not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {label}{': ' + detail if detail else ''}")

    hole_rule, centres, drill, keepout = rules["rule"], rules["centres"], rules["drill"], rules["keepout"]
    where = ", ".join(f"({x:+g},{y:+g})" for x, y in centres)
    print(f"== {hole_rule} non-plated mounting holes ==")
    drl = src / NPTH_DRILL
    drilled = []
    if not drl.exists():
        check(False, f"{NPTH_DRILL} missing")
    else:
        holes = npth_holes(drl)
        mounting = [(x, y, d) for x, y, d in holes if abs(d - drill) < 0.01]
        others = [(x, y, d) for x, y, d in holes if abs(d - drill) >= 0.01]
        expected = {(x, y) for x, y in centres}
        got = {(x, y) for x, y, _ in mounting}
        check(got == expected, f"{drill} mm NPTH holes at {where} and nowhere else",
              f"found {sorted(got)}")
        if others:
            print(f"  note {len(others)} other non-plated holes, not mounting holes: "
                  + ", ".join(f"{d} mm at ({x:+.2f},{y:+.2f})" for x, y, d in others))
        drilled = [Point(x, y).buffer(d / 2, quad_segs=64) for x, y, d in holes]

    for name, fname in rules["copper"] + rules["silk"]:
        path = src / fname
        is_silk = (name, fname) in rules["silk"]
        print(f"== {name} ({fname}) ==")
        if not path.exists():
            check(False, "layer file missing")
            continue
        geom = layer_dark(path)
        if geom is None or geom.is_empty:
            # An empty silkscreen is legitimate; an empty copper layer is not.
            check(is_silk, "layer has no dark geometry")
            continue
        # finished board: the non-plated drills remove whatever they cover
        for disc in drilled:
            geom = geom.difference(disc)
        for hx, hy in centres:
            inter = geom.intersection(Point(hx, hy).buffer(keepout, quad_segs=64))
            check(inter.is_empty, f"{hole_rule} keep-out at ({hx:+g},{hy:+g})",
                  "" if inter.is_empty else f"{inter.area:.2f} mm^2 inside r={keepout}")
        if is_silk:
            continue
        for rule, label, rect in rules["voids"]:
            # A mounting hole inside a void is the hole rule's finding and is
            # reported there; counting it again here read as "copper under the
            # antenna", which is a different failure.
            band = rect
            for hx, hy in centres:
                band = band.difference(Point(hx, hy).buffer(keepout, quad_segs=64))
            inter = geom.intersection(band)
            # A shared edge with the subtracted discs is a zero-area line, not copper.
            clean = inter.is_empty or inter.area < 1e-6
            check(clean, f"{rule} {label}",
                  "" if clean else f"{inter.area:.2f} mm^2 of copper in the void")

    print("\nall clear" if not failed else "\nVIOLATIONS FOUND")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
