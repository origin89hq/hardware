"""Behaviour tests for validate_silkscreen.py, on synthetic DXF files.

Run from the repository root: python3 -m unittest discover -s tools -p 'test_*.py'
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_silkscreen as vs  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TOP = "Top-Silkscreen-Layer"
BOTTOM = "Bottom-Silkscreen-Layer"


def dxf(entities, blocks=()):
    """Build a minimal DXF: (kind, layer, chunks[, height]) tuples, height 0.7 mm unless
    given and omitted when None; blocks go in BLOCKS."""
    out = []

    def emit(kind, layer, chunks, height=0.7):
        out.extend(["  0", kind, "  8", layer])
        if height is not None:
            out.extend([" 40", repr(height)])
        if kind == "MTEXT":
            for c in chunks[:-1]:
                out.extend(["  3", c])
        out.extend(["  1", chunks[-1]])

    out += ["  0", "SECTION", "  2", "HEADER", "  9", "$ACADVER", "  1", "AC1015", "  0", "ENDSEC"]
    if blocks:
        out += ["  0", "SECTION", "  2", "BLOCKS", "  0", "BLOCK", "  2", "title"]
        for e in blocks:
            emit(*e)
        out += ["  0", "ENDBLK", "  0", "ENDSEC"]
    out += ["  0", "SECTION", "  2", "ENTITIES"]
    for e in entities:
        emit(*e)
    out += ["  0", "ENDSEC", "  0", "EOF"]
    return "\r\n".join(out) + "\r\n"


class SilkscreenCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.spec = {
            "rule": "T-1",
            "dxf_layers": [TOP, BOTTOM],
            "required": ["BANK IN", "TERM CAN", "RS485-1 RX", "NRST"],
            "required_patterns": ["^ORIGIN ?89\\b", "\\bREV B\\b"],
            "min_text_height_mm": 0.7,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, spec=None, raw=None):
        path = self.dir / "rules.json"
        path.write_text(raw if raw is not None else json.dumps({"silk_text": spec or self.spec}))
        return str(path)

    def board(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def run_check(self, rules, board):
        out = io.StringIO()
        with redirect_stdout(out):
            code = vs.main(["validate_silkscreen.py", rules, board])
        return code, out.getvalue().splitlines()

    def test_full_set_passes_with_escapes_chunks_and_split_title(self):
        board = self.board("full.dxf", dxf([
            ("MTEXT", TOP, ["{\\fArial|b0;BANK", "\\P IN}"]),
            ("TEXT", BOTTOM, ["term\\~can%%u"]),
            ("TEXT", TOP, ["rs485\\U+2212" + "1  rx"]),
            ("TEXT", TOP, ["\\LNRST\\l"]),
            ("TEXT", TOP, ["ORIGIN 89 CONTROLLER"]),
            ("TEXT", TOP, ["rev B 2026-10"]),
            ("TEXT", TOP, ["CN4"]),
            ("TEXT", TOP, ["   "]),
        ]))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 0, out)
        self.assertIn("PASS T-1: 0 missing, 0 under 0.7 mm", out[-1])
        self.assertTrue(any("7 text items" in line and "1 designators" in line for line in out), out[0])
        self.assertTrue(any("'BANK IN' x1" in line for line in out))
        self.assertTrue(any("'TERM CAN' x1" in line for line in out))

    def test_missing_label_and_wrong_revision_fail(self):
        board = self.board("partial.dxf", dxf([
            ("TEXT", TOP, ["BANK IN"]), ("TEXT", TOP, ["TERM CAN"]), ("TEXT", TOP, ["RS485-1 RX"]),
            ("TEXT", TOP, ["ORIGIN 89 CONTROLLER rev A"]),
        ]))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 1)
        fails = [line for line in out if line.startswith("FAIL T-1: ")]
        self.assertEqual(len(fails), 3, fails)
        self.assertIn("FAIL T-1: 'NRST' missing", fails)
        self.assertTrue(any("REV B" in line for line in fails))

    def test_text_in_block_definition_does_not_count(self):
        board = self.board("blocks.dxf", dxf(
            [("TEXT", TOP, ["TERM CAN"])],
            blocks=[("TEXT", TOP, ["BANK IN"]), ("TEXT", TOP, ["NRST"])],
        ))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 1)
        self.assertIn("FAIL T-1: 'BANK IN' missing", out)
        self.assertTrue(any("1 text items" in line for line in out), out[0])

    def test_wrong_layer_exits_2(self):
        board = self.board("layer.dxf", dxf([("TEXT", "Top-Layer", ["BANK IN"])]))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 2)
        self.assertIn("carries no TEXT or MTEXT", out[-1])

    def test_bad_rule_files_exit_2_instead_of_passing(self):
        board = self.board("ok.dxf", dxf([("TEXT", TOP, ["BANK IN"])]))
        typo = dict(self.spec)
        typo["require"] = typo.pop("required")
        no_patterns = {k: v for k, v in self.spec.items() if k != "required_patterns"}
        payloads = (
            json.dumps({"silk_text": typo}),
            json.dumps({"silk_text": dict(self.spec, required=[])}),
            json.dumps({"silk_text": dict(self.spec, required_patterns=["("])}),
            json.dumps({"silk_text": no_patterns}),
            json.dumps({"silk_text": dict(self.spec, required_patterns=[])}),
            json.dumps({"silk_text": dict(self.spec, required_patterns=[" "])}),
            json.dumps({"silk_text": dict(self.spec, dxf_layers="Top-Silkscreen-Layer")}),
            json.dumps({"silk_text": dict(self.spec, required=["BANK IN", 7])}),
            json.dumps({"silk_text": {k: v for k, v in self.spec.items() if k != "min_text_height_mm"}}),
            json.dumps({"silk_text": dict(self.spec, min_text_height_mm=0)}),
            json.dumps({"silk_text": dict(self.spec, min_text_height_mm="0.7")}),
            json.dumps({"silk_text": dict(self.spec, min_text_height_mm=True)}),
            "[]",
            "{",
            json.dumps({"mounting_holes": {}}),
        )
        for raw in payloads:
            rules = self.rules(raw=raw)
            code, out = self.run_check(rules, board)
            self.assertEqual(code, 2, (raw, out))
            self.assertFalse(any(line.startswith("PASS") for line in out), (raw, out))
        self.assertEqual(len(payloads), 15)

    def test_text_under_the_minimum_height_fails_with_its_height(self):
        board = self.board("small.dxf", dxf([
            ("TEXT", TOP, ["BANK IN"]), ("TEXT", TOP, ["TERM CAN"]), ("TEXT", TOP, ["RS485-1 RX"]),
            ("TEXT", BOTTOM, ["NRST"], 0.56), ("TEXT", BOTTOM, ["GND"], 0.56), ("TEXT", BOTTOM, ["GND"], 0.56),
            ("TEXT", TOP, ["R45"], 0.69), ("TEXT", TOP, ["U7"], 0.7000017780035),
            ("TEXT", TOP, ["ORIGIN 89 CTRL REV B 2026-09"], 0.84),
        ]))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 1)
        self.assertIn("PASS T-1: 'NRST' x1", out)
        self.assertIn("FAIL T-1: 'gnd' x2 0.56 mm high, under 0.7 mm", out)
        self.assertIn("FAIL T-1: 'nrst' x1 0.56 mm high, under 0.7 mm", out)
        self.assertIn("FAIL T-1: 'r45' x1 0.69 mm high, under 0.7 mm", out)
        self.assertFalse(any("'u7'" in line for line in out), out)
        self.assertIn("FAIL T-1: 0 missing, 4 under 0.7 mm", out[-1])

    def test_text_with_no_recorded_height_fails(self):
        board = self.board("noheight.dxf", dxf([
            ("TEXT", TOP, ["BANK IN"]), ("TEXT", TOP, ["TERM CAN"]), ("TEXT", TOP, ["RS485-1 RX"]),
            ("TEXT", TOP, ["NRST"]), ("MTEXT", TOP, ["ORIGIN 89 REV B"], None),
        ]))
        code, out = self.run_check(self.rules(), board)
        self.assertEqual(code, 1)
        self.assertIn("FAIL T-1: 'origin 89 rev b' x1 no height recorded, under 0.7 mm", out)
        self.assertIn("FAIL T-1: 0 missing, 1 under 0.7 mm", out[-1])

    def test_usage_exits_2(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(vs.main(["validate_silkscreen.py"]), 2)

    def test_repository_rule_file_loads(self):
        rule, layers, required, patterns, min_height = vs.load_rules(REPO / "boards/controller-a/gerber-rules.json")
        self.assertEqual(rule, "A-33")
        self.assertEqual(min_height, 0.7)
        self.assertEqual(layers, [TOP, BOTTOM])
        self.assertGreater(len(required), 40)
        self.assertEqual(len(patterns), 3)


if __name__ == "__main__":
    unittest.main()
