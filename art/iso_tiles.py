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
LOOK = "storybook"                                         # house look, picked 2026-10-09 (tiles round 3)
WALL_COLOURS = ["out", "g3", "g4", "k1", "k2", "k3", "w0", "w1", "w2", "fl_w"]


def build(palette):
    palettes.use(palette)
    from iso import ANIMATED, CH, CW, HT, grass_cell, iso_tile
    from props import catalog
    from sprites import PAL
    from tiles import Sheet

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
    from iso_ground import flats
    sh.newline()
    meta["flats"] = {name: sh.add(im) for name, im in flats().items()}
    meta["colors"] = {k: PAL[k] for k in WALL_COLOURS}
    out = ROOT / "tiles" / "iso"
    out.mkdir(parents=True, exist_ok=True)
    sh.image().save(out / "tileset.png")
    (out / "tileset.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n")
    im, pmeta = build_iso_props()
    im.save(out / "props.png")
    (out / "props.json").write_text(json.dumps(pmeta, indent=1) + "\n")
    print("wrote", out)


# The top-down houses are replaced by isometric ones; their old names point at the closest new house.
HOUSE_ALIASES = {"red": "cottage-red", "yellow": "thatch-house", "blue": "longhouse"}


def build_iso_props():
    """Every prop, with isometric buildings instead of the top-down houses. Buildings carry an anchor (where their
    front cell's centre is in the picture) and a footprint in cells."""
    from iso_props import HOUSES, house, use_look
    use_look(LOOK)
    from props import catalog
    from iso_nature import nature
    items = {name: (spr, shadow, {}) for name, (spr, shadow) in catalog().items() if not name.startswith("house-")}
    for name, spr in nature().items():
        items[name] = (spr, not name.startswith("rock"), {})
    for name, kw in HOUSES.items():
        spr, (ax, ay), foot = house(**kw)
        items[name] = (spr, False, {"ax": ax, "ay": ay, "foot": list(foot)})
    from iso_ground import uprights
    for name, spr in uprights().items():
        items[name] = (spr, False, {"ax": spr.anchor[0], "ay": spr.anchor[1]})
    from iso_market import FOOTPRINTS, MARKET
    for name, make in MARKET.items():
        spr = make()
        extra = {"ax": spr.anchor[0], "ay": spr.anchor[1]}
        if name in FOOTPRINTS:
            extra["foot"] = FOOTPRINTS[name]
        items[name] = (spr, name in ("barrel-iso", "crates", "flower-cart"), extra)
    order = sorted(items.items(), key=lambda kv: -kv[1][0].h)
    W, x, y, shelf, placed = 512, 0, 0, 0, {}
    for name, (spr, shadow, extra) in order:
        if x + spr.w > W:
            x, y, shelf = 0, y + shelf + 1, 0
        placed[name] = {"x": x, "y": y, "w": spr.w, "h": spr.h, "shadow": shadow, **extra}
        x += spr.w + 1
        shelf = max(shelf, spr.h)
    from PIL import Image
    out = Image.new("RGBA", (W, y + shelf), (0, 0, 0, 0))
    for name, (spr, _, _) in items.items():
        out.alpha_composite(spr.im, (placed[name]["x"], placed[name]["y"]))
    for colour, target in HOUSE_ALIASES.items():
        for size in ("s", "m", "l"):
            placed[f"house-{colour}-{size}"] = {**placed[target], "alias": target}
    return out, {"version": 1, "image": "props.png", "props": dict(sorted(placed.items()))}


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "earthy")
