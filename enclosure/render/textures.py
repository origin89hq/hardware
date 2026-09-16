"""Top-transfer textures for the 3D assembly: artwork.py's 600 dpi sheets
are far larger than a texture needs; 1600 px wide is plenty."""
from pathlib import Path
from PIL import Image
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
(HERE / "work").mkdir(exist_ok=True)
for stem, tex in (("artwork-a-top-transfer", "tex-a"), ("artwork-b-top-transfer", "tex-b")):
    img = Image.open(OUT / (stem + ".png"))
    img.thumbnail((1600, 1600))
    img.save(HERE / "work" / (tex + ".png"))
    print(tex, img.size)
