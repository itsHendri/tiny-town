"""Build the isometric tile sheet and prop atlas (tiles/iso/), in one palette.

    python art/iso_tiles.py [earthy|deep|bright]

Every ground set has 15 shapes x 8 pattern phases (x 3 frames for water and tall grass). The browser picks the
phase from the grid corner, so patterns run on seamlessly. Cliff walls aren't tiles: the browser pushes each
level's outline down itself, using the colours listed in tileset.json.
"""
import json
import sys
from pathlib import Path

import palettes

ROOT = Path(__file__).resolve().parent.parent
PHASES = [(a, b) for a in range(4) for b in range(4) if (a + b) % 2 == 0]
WALL_COLOURS = ["out", "g3", "g4", "k1", "k2", "k3", "w0", "w1", "w2", "fl_w"]


def build(palette):
    palettes.use(palette)
    from iso import ANIMATED, CH, CW, HT, grass_cell, iso_tile
    from props import catalog
    from sprites import PAL
    from tiles import Sheet, build_props

    sh = Sheet()
    meta = {"version": 1, "projection": "iso", "palette": palette, "cell": [CW, CH], "levelHeight": HT,
            "frames": 3, "frameMs": 320, "image": "tileset.png"}
    meta["grass"] = {f"{a},{b}": sh.add(grass_cell((a, b))) for a, b in PHASES}
    sh.newline()
    meta["sets"] = {}
    for name in ("raised_fill", "raised_edge", "water", "soil", "path", "tallgrass"):
        frames = 3 if name in ANIMATED else 1
        tiles = {}
        for mask in range(1, 16):
            tiles[mask] = {f"{a},{b}": [sh.add(iso_tile(name, mask, f, (a, b))) for f in range(frames)] for a, b in PHASES}
        sh.newline()
        meta["sets"][name] = tiles
    meta["sets"]["cobbles"] = meta["sets"]["path"]
    meta["colors"] = {k: PAL[k] for k in WALL_COLOURS}
    out = ROOT / "tiles" / "iso"
    out.mkdir(parents=True, exist_ok=True)
    sh.image().save(out / "tileset.png")
    (out / "tileset.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n")
    im, pmeta = build_props()
    im.save(out / "props.png")
    (out / "props.json").write_text(json.dumps(pmeta, indent=1) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "earthy")
