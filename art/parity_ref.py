"""Small test maps drawn by the Python renderer, for checking that the browser draws the same pixels.
Writes out/iso-ref.png and out/iso-ref.json (a map on level 0), and out/iso-ref-dig.png and out/iso-ref-dig.json
(a map whose ground is level 1, with a pit dug into it, drawn with a margin), plus each map top-down
(out/top-iso-ref*.png, by art/preview.py). The browser check is in CLAUDE.md.

    python art/parity_ref.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palettes

ROOT = Path(__file__).resolve().parent.parent

palettes.use(palettes.DEFAULT)
import iso
import preview

T = {"grass": 0, "path": 1, "cobbles": 2, "water": 3, "soil": 4, "bridge": 5, "dirt": 6}


def write(m, name, margin=0):
    iso.render(m, 1, objects=False, margin=margin).save(ROOT / "out" / f"{name}.png")
    preview.render(m, preview.DEFAULT, 1).save(ROOT / "out" / f"top-{name}.png")
    json.dump({"cols": m.cols, "rows": m.rows, "margin": margin, "H": sum(m.height, []), "T": [T[t] for t in sum(m.terrain, [])],
               "F": [1 if f == "stairs" else 0 for f in sum(m.feature, [])], "D": [3 if d == "tallgrass" else 0 for d in sum(m.deco, [])]},
              open(ROOT / "out" / f"{name}.json", "w"))
    print(f"wrote out/{name}.png, out/top-{name}.png and out/{name}.json")


(ROOT / "out").mkdir(exist_ok=True)

m = preview.Map(14, 12)
m.fill("height", 1, 8, 6, 13, 1); m.fill("height", 2, 10, 4, 13, 2)
m.fill("terrain", 6, 0, 8, 14, "path"); m.fill("terrain", 0, 4, 6, 6, "path")
m.fill("terrain", 8, 2, 11, 6, "water"); m.fill("terrain", 2, 9, 4, 10, "water"); m.fill("terrain", 1, 1, 4, 3, "soil")
m.fill("terrain", 3, 12, 6, 13, "water")   # water at the plateau's front edge: a waterfall
m.fill("terrain", 9, 7, 11, 9, "dirt")
for r in range(9, 12):
    for c in range(8, 13):
        m.deco[r][c] = "tallgrass"
write(m, "iso-ref")

# ground on level 1: a pit with a pond in it, a hill, a road leaving the map, stairs down into the pit
d = preview.Map(12, 10)
d.fill("height", 0, 0, 10, 12, 1)
d.fill("height", 2, 3, 6, 7, 0); d.fill("height", 1, 8, 4, 11, 2)       # rows first, ends not included
d.fill("terrain", 3, 4, 5, 6, "water"); d.fill("terrain", 8, 0, 9, 12, "path"); d.fill("terrain", 5, 8, 8, 11, "cobbles")
d.feature[2][4] = "stairs"                                            # at the foot of the pit's back wall
write(d, "iso-ref-dig", margin=2)
