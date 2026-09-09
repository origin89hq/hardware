#!/usr/bin/env python3
"""File an EasyEDA Pro fabrication export under boards/<board>/build/<date>/
with fixed names, so every export looks the same whoever made it.

    tools/import_easyeda_export.py controller-a ~/Downloads/PCB1_2026-08-31 [--date 2026-08-31]

EasyEDA writes `Gerber_PCB1_2026-08-31.zip`, `BOM_Board1_PCB1_2026-08-31.xlsx`,
`fabrication_layer(PDF)/PCB_PCB1_2026-08-31.pdf` and so on, each name carrying
the board number and the date and the directory names carrying parentheses.
None of that survives here: the date becomes the directory, the board is the
directory above it, and each file gets the name its kind always gets. The
project archive (`.epro2` or `.eprj2`) is the design source and goes to
`easyeda/` under its own name. Spreadsheets are copied as they came and also
written as CSV, which a diff can read.

Never changes a file already filed: a dated export can be completed later
with the outputs that were missing (a STEP, a schematic PDF), but a file that
is already there must come back byte-identical, so a board in someone's hands
still matches its files. Anything else goes beside it under a new date. Exit
0 when filed, 1 on refusal or an unrecognised file, 2 on usage.
"""
import csv
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (regex on the path relative to the export, canonical name). Order matters only for readability.
KINDS = [
    (r"(^|/)Gerber_[^/]*\.zip$", "gerber.zip"),
    (r"(^|/)BOM_[^/]*\.xlsx$", "bom.xlsx"),
    (r"(^|/)PickAndPlace_[^/]*\.xlsx$", "pick-and-place.xlsx"),
    (r"(^|/)Schematic_[^/]*\.pdf$", "schematic.pdf"),
    (r"(^|/)SCH_[^/]*\.pdf$", "schematic.pdf"),
    (r"(^|/)PCB_[^/]*\.pdf$", "fabrication-layers.pdf"),
    (r"(^|/)3D_[^/]*\.step$", "board.step"),
    (r"(^|/)TOP/DXF_[^/]*\.dxf$", "outline-top.dxf"),
    (r"(^|/)BOT/DXF_[^/]*\.dxf$", "outline-bottom.dxf"),
    (r"(^|/)DXF_[^/]*\.dxf$", "board.dxf"),
    (r"(^|/)PCB production instructions\.xls$", "production-instructions.xls"),
    (r"(^|/)PCB Layout-Generated files illustration\.txt$", "files-illustration.txt"),
]
SOURCE = r"(^|/)[^/]*\.(epro2|eprj2)$"
DATE = re.compile(r"(\d{4})[-_](\d{2})[-_](\d{2})")


def csv_of(xlsx: Path, out: Path) -> None:
    try:
        import openpyxl  # type: ignore
    except ImportError:
        print(f"  {out.name}: skipped, openpyxl is not installed (pip install openpyxl)")
        return
    sheet = openpyxl.load_workbook(xlsx, read_only=True).worksheets[0]
    with out.open("w", newline="") as handle:
        writer = csv.writer(handle)
        for row in sheet.iter_rows(values_only=True):
            writer.writerow(["" if cell is None else cell for cell in row])
    print(f"  {out.name}")


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    flags = dict(a[2:].split("=", 1) for a in argv if a.startswith("--") and "=" in a)
    if len(args) != 2:
        print(__doc__)
        return 2
    board, export = args[0], Path(args[1]).expanduser()
    board_dir = ROOT / "boards" / board
    if not board_dir.is_dir():
        print(f"no such board: boards/{board}")
        return 2
    if not export.is_dir():
        print(f"not a directory: {export}")
        return 2
    files = [p for p in export.rglob("*") if p.is_file() and p.name != ".DS_Store"]
    dates = {m.group(0).replace("_", "-") for p in files for m in [DATE.search(p.name)] if m}
    date = flags.get("date") or (dates.pop() if len(dates) == 1 else None)
    if not date:
        print(f"could not settle on one export date from the filenames ({sorted(dates) or 'none'}); pass --date=YYYY-MM-DD")
        return 1
    build = board_dir / "build" / date
    filed, unknown = [], []
    plan = []
    for path in files:
        rel = path.relative_to(export).as_posix()
        if re.search(SOURCE, rel):
            plan.append((path, board_dir / "easyeda" / path.name))
            continue
        for pattern, name in KINDS:
            if re.search(pattern, rel):
                plan.append((path, build / name))
                break
        else:
            unknown.append(rel)
    if unknown:
        print("unrecognised files, nothing filed:\n  " + "\n  ".join(unknown))
        return 1
    names = [dst.name for _, dst in plan if dst.parent == build]
    if len(names) != len(set(names)):
        print(f"two files map to the same name: {sorted(n for n in names if names.count(n) > 1)}")
        return 1
    same = [dst for src, dst in plan if dst.parent == build and dst.exists() and dst.read_bytes() == src.read_bytes()]
    differs = [dst for src, dst in plan if dst.parent == build and dst.exists() and dst.read_bytes() != src.read_bytes()]
    if differs:
        print(f"{build.relative_to(ROOT)} already holds a different " + ", ".join(d.name for d in differs)
              + "; a changed export goes beside the old one under a new date, not over it")
        return 1
    build.mkdir(parents=True, exist_ok=True)
    (board_dir / "easyeda").mkdir(exist_ok=True)
    print(f"{board_dir.relative_to(ROOT).as_posix()}/build/{date}/")
    for src, dst in sorted(plan, key=lambda p: p[1].name):
        if dst in same:
            print(f"  {dst.relative_to(board_dir).as_posix()}  (already filed, identical)")
            continue
        shutil.copyfile(src, dst)
        filed.append(dst)
        print(f"  {dst.relative_to(board_dir).as_posix()}")
        if dst.suffix == ".xlsx":
            csv_of(dst, dst.with_suffix(".csv"))
    gerber = build / "gerber.zip"
    if gerber.exists():
        print(f"\nnext: python tools/validate_gerbers.py {gerber.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
