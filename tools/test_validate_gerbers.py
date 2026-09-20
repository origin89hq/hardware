"""Behaviour tests for validate_gerbers.py's rule loading and silkscreen stroke check.

Needs gerbonara and shapely like the script itself (pip install -r requirements-dev.txt).
Run from the repository root: python3 -m unittest discover -s tools -p 'test_*.py'
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HAVE_DEPS = all(importlib.util.find_spec(m) for m in ("gerbonara", "shapely"))
if HAVE_DEPS:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import validate_gerbers as vg  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

# Two strokes in millimetres, 4.6 format: 0.100 mm wide along y=0, 0.150 mm wide along y=1.
SILK = """%FSLAX46Y46*%
%MOMM*%
%ADD10C,0.100*%
%ADD11C,0.150*%
D10*
X0Y0D02*
X1000000Y0D01*
D11*
X0Y1000000D02*
X1000000Y1000000D01*
M02*
"""

BASE = {
    "mounting_holes": {"rule": "A-02", "drill": 3.2, "keepout_radius": 3.2, "centres": [[0, 0]]},
    "copper_layers": [["L1 top", "Gerber_TopLayer.GTL"]],
    "silk_layers": [["top silk", "Gerber_TopSilkscreenLayer.GTO"]],
    "silk_min_stroke_mm": 0.15,
}


@unittest.skipUnless(HAVE_DEPS, "gerbonara and shapely are not installed")
class GerberRules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, payload):
        path = self.dir / "rules.json"
        path.write_text(json.dumps(payload))
        return path

    def test_stroke_under_the_minimum_is_found_and_one_at_it_is_not(self):
        silk = self.dir / "silk.gto"
        silk.write_text(SILK)
        thin = vg.thin_strokes(silk, 0.15)
        self.assertEqual(len(thin), 1, thin)
        x, y, width = thin[0]
        self.assertAlmostEqual(x, 0.5)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(width, 0.1)
        self.assertEqual(vg.thin_strokes(silk, 0.1), [])

    def test_silk_layers_need_a_positive_stroke_minimum(self):
        self.assertEqual(vg.load_rules(self.rules(BASE))["stroke"], 0.15)
        for bad in ({k: v for k, v in BASE.items() if k != "silk_min_stroke_mm"},
                    dict(BASE, silk_min_stroke_mm=0), dict(BASE, silk_min_stroke_mm="0.15"),
                    dict(BASE, silk_min_stroke_mm=True)):
            with self.assertRaises(ValueError, msg=bad):
                vg.load_rules(self.rules(bad))

    def test_no_silk_layers_needs_no_stroke_minimum(self):
        rules = {k: v for k, v in BASE.items() if k not in ("silk_layers", "silk_min_stroke_mm")}
        self.assertIsNone(vg.load_rules(self.rules(rules))["stroke"])

    def test_repository_rule_file_loads(self):
        rules = vg.load_rules(REPO / "boards/controller-a/gerber-rules.json")
        self.assertEqual(rules["stroke"], 0.15)
        self.assertEqual(len(rules["silk"]), 2)


if __name__ == "__main__":
    unittest.main()
