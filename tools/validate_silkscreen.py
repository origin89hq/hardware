#!/usr/bin/env python3
"""Check an exported board DXF for the silkscreen text a rule requires.

Usage:

    tools/validate_silkscreen.py <gerber-rules.json> <board.dxf>

Exit 0 when every required label is present, 1 on any FAIL, 2 when the rule
file has no `silk_text` entry or the DXF carries no text on the named layers.
Standard library only.

The rule file's `silk_text` entry names the rule, the DXF layers to read, the
labels that must appear at least once, and regular expressions for text whose
exact wording is free (the board name and revision):

    "silk_text": {
      "rule": "A-33",
      "dxf_layers": ["Top-Silkscreen-Layer", "Bottom-Silkscreen-Layer"],
      "required": ["12V IN", "RS485-1", ...],
      "required_patterns": ["^ORIGIN ?89\\\\b.*\\\\bREV B\\\\b"]
    }

Why the DXF and not the Gerber: the silkscreen Gerber holds text as strokes,
while EasyEDA's DXF export keeps each silkscreen string as a TEXT entity, so
the words are still words there. The 2026-09-09 controller export has 133 of
them on `Top-Silkscreen-Layer`, every one a designator, which is the finding
A-33 was written from.

Matching is exact after folding case, collapsing whitespace and turning the
minus sign U+2212 into a hyphen. A required label is the minimum, not the
whole silkscreen: the list grows as the design settles. The check cannot see
graphics, so a pin-1 arrow or a polarity mark drawn as lines is outside it.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

DESIGNATOR = re.compile(r"^[A-Z]{1,3}\d+$")
DXF_UNICODE = re.compile(r"\\U\+([0-9A-Fa-f]{4})")
MTEXT_FORMAT = re.compile(r"\\[A-Za-z][^;\\]*;")


def group_codes(path):
    """Yield (code, value) pairs from a DXF file, tolerating a stray last line."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i in range(0, len(lines) - 1, 2):
        yield lines[i].strip(), lines[i + 1]


def texts_on_layers(path, layers):
    """Return the decoded string of every TEXT and MTEXT entity on the given layers."""
    wanted = set(layers)
    found = []
    entity = None
    layer = None
    chunks = []

    def flush():
        if entity in ("TEXT", "MTEXT") and layer in wanted and chunks:
            found.append(decode("".join(chunks)))

    for code, value in group_codes(path):
        if code == "0":
            flush()
            entity, layer, chunks = value.strip(), None, []
        elif code == "8":
            layer = value.strip()
        elif entity in ("TEXT", "MTEXT") and code in ("1", "3"):
            chunks.append(value)
    flush()
    return found


def decode(raw):
    """Turn DXF text escapes and MTEXT formatting into the words the eye reads."""
    text = DXF_UNICODE.sub(lambda m: chr(int(m.group(1), 16)), raw)
    text = text.replace("\\P", " ")
    text = MTEXT_FORMAT.sub("", text)
    return text.replace("{", "").replace("}", "")


def normalise(text):
    return " ".join(text.replace("\u2212", "-").split()).casefold()


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0])
        print(f"usage: {argv[0]} <gerber-rules.json> <board.dxf>")
        return 2

    rules = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    spec = rules.get("silk_text")
    if not spec:
        print(f"{argv[1]} has no silk_text entry; nothing to check")
        return 2

    dxf = Path(argv[2])
    if not dxf.is_file():
        print(f"{dxf} is not a file")
        return 2

    rule = spec.get("rule", "silk")
    layers = spec.get("dxf_layers", [])
    texts = texts_on_layers(dxf, layers)
    if not texts:
        print(f"{dxf} carries no TEXT or MTEXT on {layers}; wrong file or wrong layer names")
        return 2

    seen = Counter(normalise(t) for t in texts)
    designators = sum(n for t, n in seen.items() if DESIGNATOR.match(t.upper()))
    labels = {t: n for t, n in seen.items() if not DESIGNATOR.match(t.upper())}
    print(f"{dxf}: {len(texts)} text items on {', '.join(layers)}, "
          f"{designators} designators, {sum(labels.values())} other")

    failures = 0
    for label in spec.get("required", []):
        key = normalise(label)
        count = seen.get(key, 0)
        if count:
            print(f"PASS {rule}: {label!r} x{count}")
        else:
            print(f"FAIL {rule}: {label!r} missing")
            failures += 1

    for pattern in spec.get("required_patterns", []):
        regex = re.compile(pattern, re.IGNORECASE)
        matches = [t for t in seen if regex.search(t)]
        if matches:
            print(f"PASS {rule}: /{pattern}/ matched {matches[0]!r}")
        else:
            print(f"FAIL {rule}: /{pattern}/ matched nothing")
            failures += 1

    required = {normalise(l) for l in spec.get("required", [])}
    extras = sorted(t for t in labels if t not in required)
    if extras:
        print(f"INFO {rule}: text not in the required list: {', '.join(repr(t) for t in extras)}")

    print(f"{'FAIL' if failures else 'PASS'} {rule}: {failures} missing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
