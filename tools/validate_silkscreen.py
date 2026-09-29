#!/usr/bin/env python3
"""Check an exported board DXF for the silkscreen text a rule requires.

Usage:

    tools/validate_silkscreen.py <gerber-rules.json> <board.dxf>

Exit 0 when every required label is present and every text is tall enough,
1 on any FAIL, 2 when the rule file is unreadable, has no usable `silk_text`
entry, or the DXF carries no text on the named layers. Standard library only.

The rule file's `silk_text` entry names the rule, the DXF layers to read, the
labels that must each appear at least once, regular expressions for text
whose exact wording is free (the board name, revision and date), and the
smallest text height the fab is asked to print. The three lists are required
and non-empty, and the height a positive number of millimetres:

    "silk_text": {
      "rule": "A-33",
      "dxf_layers": ["Top-Silkscreen-Layer", "Bottom-Silkscreen-Layer"],
      "required": ["BANK IN", "RS485-1", ...],
      "required_patterns": ["^ORIGIN ?89\\\\b", "\\\\bREV B\\\\b"],
      "min_text_height_mm": 0.7
    }

Every text on those layers, designators included, is held to the height. The
DXF records a TEXT's printed height, not EasyEDA's font size: size 1.0 is
0.70 mm there, and the 2026-09-19 controller Gerber prints it 0.71 mm tall.
JLCPCB's standard minimum is 1.0 mm printed (0.8 mm on its high-precision
process); the 0.70 mm in the controller's rule file is the height every
designator on the fabricated revision A boards was printed at. A text with no
recorded height fails, since nothing about it was checked. Stroke width is
not in the DXF; `validate_gerbers.py` checks it on the silkscreen Gerber.

A misspelt or missing key is a bad rule file and exits 2, not a check that
passes with nothing verified. Its sibling `validate_gerbers.py` fails the same
way on an empty centre list, and for the same reason.

Why the DXF and not the Gerber: the silkscreen Gerber holds text as strokes,
while EasyEDA's DXF export keeps each silkscreen string as a TEXT entity, so
the words are still words there. The 2026-09-09 controller export has 133 of
them on `Top-Silkscreen-Layer`, every one a designator, which is the finding
A-33 was written from.

Only the ENTITIES section counts: text inside a BLOCK definition is not on the
board unless the block is inserted, and this exporter inserts none. Matching
is exact after folding case, collapsing whitespace, decoding DXF escapes and
turning the minus sign U+2212 into a hyphen, so each label is one text object.
A required label is the minimum, not the whole silkscreen: the list grows as
the design settles. The check proves presence, not position: a label at the
wrong connector, or pins out of order, still passes, and the assembly drawing
is the check for that. It cannot see graphics either, so a pin-1 arrow or a
polarity mark drawn as lines is outside it.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

DESIGNATOR = re.compile(r"^[A-Z]{1,3}\d+$")
DXF_UNICODE = re.compile(r"\\U\+([0-9A-Fa-f]{4})")
MTEXT_TOGGLE = re.compile(r"\\[LlOoKk]")
MTEXT_FORMAT = re.compile(r"\\[A-Za-z][^;\\]*;")
TEXT_SYMBOLS = {"%%c": "\u00d8", "%%d": "\u00b0", "%%p": "\u00b1", "%%u": "", "%%o": ""}
SPEC_KEYS = {"rule", "dxf_layers", "required", "required_patterns", "min_text_height_mm"}


class RuleError(Exception):
    """The rule file cannot drive a check."""


def load_rules(path):
    """Return (rule, layers, required, patterns, min_height) from the rule file, or raise RuleError."""
    try:
        rules = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuleError(f"bad rule file {path}: {exc}") from exc
    spec = rules.get("silk_text") if isinstance(rules, dict) else None
    if not isinstance(spec, dict):
        raise RuleError(f"{path} has no silk_text entry; nothing to check")
    unknown = set(spec) - SPEC_KEYS
    if unknown:
        raise RuleError(f"{path}: silk_text has unknown keys {sorted(unknown)}")
    layers = spec.get("dxf_layers")
    required = spec.get("required")
    patterns = spec.get("required_patterns")
    for name, value in (("dxf_layers", layers), ("required", required), ("required_patterns", patterns)):
        if not isinstance(value, list) or not value or not all(isinstance(v, str) and v.strip() for v in value):
            raise RuleError(f"{path}: silk_text.{name} must be a non-empty list of strings")
    try:
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    except re.error as exc:
        raise RuleError(f"{path}: bad pattern: {exc}") from exc
    height = spec.get("min_text_height_mm")
    if isinstance(height, bool) or not isinstance(height, (int, float)) or height <= 0:
        raise RuleError(f"{path}: silk_text.min_text_height_mm must be a positive number of millimetres")
    return spec.get("rule", "silk"), layers, required, list(zip(patterns, compiled)), float(height)


def group_codes(path):
    """Yield (code, value) pairs from a DXF file, tolerating a stray last line."""
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    for i in range(0, len(lines) - 1, 2):
        yield lines[i].strip(), lines[i + 1]


def texts_on_layers(path, layers):
    """Return (decoded string, height in mm or None) for every TEXT and MTEXT entity on the given layers."""
    wanted = set(layers)
    found = []
    section = None
    entity = None
    layer = None
    height = None
    chunks = []

    def flush():
        if section == "ENTITIES" and entity in ("TEXT", "MTEXT") and layer in wanted and chunks:
            text = decode("".join(chunks))
            if text.strip():
                found.append((text, height))

    for code, value in group_codes(path):
        if code == "0":
            flush()
            entity, layer, height, chunks = value.strip(), None, None, []
            if entity == "ENDSEC":
                section = None
        elif code == "2" and entity == "SECTION":
            section = value.strip()
        elif code == "8":
            layer = value.strip()
        elif code == "40" and entity in ("TEXT", "MTEXT"):
            try:
                height = float(value)
            except ValueError:
                height = None
        elif entity in ("TEXT", "MTEXT") and code in ("1", "3"):
            chunks.append(value)
    flush()
    return found


def decode(raw):
    """Turn DXF text escapes and MTEXT formatting into the words the eye reads."""
    text = DXF_UNICODE.sub(lambda m: chr(int(m.group(1), 16)), raw)
    text = text.replace("\\P", " ").replace("\\~", " ")
    text = MTEXT_TOGGLE.sub("", text)
    text = MTEXT_FORMAT.sub("", text)
    for code, char in TEXT_SYMBOLS.items():
        text = text.replace(code, char)
    return text.replace("{", "").replace("}", "")


def normalise(text):
    return " ".join(text.replace("\u2212", "-").split()).casefold()


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0])
        print(f"usage: {argv[0]} <gerber-rules.json> <board.dxf>")
        return 2

    try:
        rule, layers, required, patterns, min_height = load_rules(argv[1])
    except RuleError as exc:
        print(exc)
        return 2

    dxf = Path(argv[2])
    if not dxf.is_file():
        print(f"{dxf} is not a file")
        return 2

    found = texts_on_layers(dxf, layers)
    if not found:
        print(f"{dxf} carries no TEXT or MTEXT on {layers}; wrong file or wrong layer names")
        return 2
    texts = [t for t, _ in found]

    seen = Counter(normalise(t) for t in texts)
    designators = sum(n for t, n in seen.items() if DESIGNATOR.match(t.upper()))
    labels = {t: n for t, n in seen.items() if not DESIGNATOR.match(t.upper())}
    print(f"{dxf}: {len(texts)} text items on {', '.join(layers)}, "
          f"{designators} designators, {sum(labels.values())} other")

    failures = 0
    for label in required:
        count = seen.get(normalise(label), 0)
        if count:
            print(f"PASS {rule}: {label!r} x{count}")
        else:
            print(f"FAIL {rule}: {label!r} missing")
            failures += 1

    for pattern, regex in patterns:
        matches = [t for t in seen if regex.search(t)]
        if matches:
            print(f"PASS {rule}: /{pattern}/ matched {matches[0]!r}")
        else:
            print(f"FAIL {rule}: /{pattern}/ matched nothing")
            failures += 1

    wanted = {normalise(label) for label in required}
    extras = sorted(t for t in labels if t not in wanted)
    if extras:
        print(f"INFO {rule}: text not in the required list: {', '.join(repr(t) for t in extras)}")

    # 1 um of slack: EasyEDA writes 0.7 mm as 0.7000017...
    small = Counter((normalise(t), h) for t, h in found if h is None or h < min_height - 0.001)
    for (text, height), count in sorted(small.items(), key=lambda item: (item[0][1] or 0, item[0][0])):
        size = "no height recorded" if height is None else f"{height:.2f} mm high"
        print(f"FAIL {rule}: {text!r} x{count} {size}, under {min_height:g} mm")
    short = sum(small.values())
    if not short:
        print(f"PASS {rule}: every text at least {min_height:g} mm high")

    failed = failures or short
    print(f"{'FAIL' if failed else 'PASS'} {rule}: {failures} missing, {short} under {min_height:g} mm")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
