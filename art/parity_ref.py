"""A small test map drawn by the Python renderer, for checking that the browser draws the same pixels.
Writes out/iso-ref.png (the picture) and out/iso-ref.json (the map). The browser check is in CLAUDE.md.

    python art/parity_ref.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palettes

ROOT = Path(__file__).resolve().parent.parent

palettes.use("earthy")
import iso
import preview

m = preview.Map(14, 12)
m.fill("height", 1, 8, 6, 13, 1); m.fill("height", 2, 10, 4, 13, 2)
m.fill("terrain", 6, 0, 8, 14, "path"); m.fill("terrain", 0, 4, 6, 6, "path")
m.fill("terrain", 8, 2, 11, 6, "water"); m.fill("terrain", 2, 9, 4, 10, "water"); m.fill("terrain", 1, 1, 4, 3, "soil")
m.fill("terrain", 3, 12, 6, 13, "water")   # water at the plateau's front edge: a waterfall
for r in range(9, 12):
    for c in range(8, 13):
        m.deco[r][c] = "tallgrass"
(ROOT / "out").mkdir(exist_ok=True)
iso.render(m, 1, objects=False).save(ROOT / "out" / "iso-ref.png")
T = {"grass": 0, "path": 1, "cobbles": 2, "water": 3, "soil": 4, "bridge": 5, "dirt": 6}
json.dump({"cols": 14, "rows": 12, "H": sum(m.height, []), "T": [T[t] for t in sum(m.terrain, [])],
           "F": [0] * 168, "D": [3 if d == "tallgrass" else 0 for d in sum(m.deco, [])]},
          open(ROOT / "out" / "iso-ref.json", "w"))
print("wrote out/iso-ref.png and out/iso-ref.json")
