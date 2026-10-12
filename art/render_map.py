"""Draw a .ldtk map in isometric, in Python (the same pixels as the browser for the ground).

    python art/render_map.py <map.ldtk> <out.png> [--margin N] [--sprites DIR] [--crop]

Characters are looked up as DIR/<sprite>.png (default: the repo's sprites/ folder).
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

import palettes

ROOT = Path(__file__).resolve().parent.parent
TERRAIN = {0: "grass", 1: "path", 2: "cobbles", 3: "water", 4: "soil", 5: "bridge", 6: "dirt"}
DECO = {2: "flowers", 3: "tallgrass", 4: "gate"}
ALIASES = {"lamp": "lamp-iso", "bench": "bench-iso", "barrel": "barrel-iso",
           **{f"house-{c}-{s}": t for c, t in (("red", "cottage-red"), ("yellow", "thatch-house"), ("blue", "longhouse")) for s in "sml"}}


class Picture:
    """A plain image with a feet-at-bottom-centre anchor, for character PNGs."""

    def __init__(self, im):
        self.im, self.w, self.h = im, im.width, im.height


def props():
    import iso_market
    import iso_props
    from iso_nature import nature
    from props import catalog
    iso_props.use_look("storybook")
    out = {name: spr for name, (spr, _) in catalog().items() if not name.startswith("house-")}
    for name, (spr, shadow) in catalog().items():
        spr.shadow = shadow
    out.update(nature())
    out.update({name: iso_props.house(**kw)[0] for name, kw in iso_props.HOUSES.items()})
    out.update({name: iso_market.make(name) for name in iso_market.MARKET})
    for name, draw in iso_market.PLAIN.items():
        out[name] = draw()
        out[name].shadow = name == "well"
    from landmarks import landmarks
    out.update(landmarks())
    return out


def load_map(path, sprite_dir):
    import ldtk
    import preview
    p = ldtk.load(path)
    m = preview.Map(p.cols, p.rows)
    for i in range(p.cols * p.rows):
        r, c = divmod(i, p.cols)
        m.height[r][c] = p.grids["Height"][i]
        m.terrain[r][c] = TERRAIN.get(p.grids["Terrain"][i], "grass")
        m.feature[r][c] = "stairs" if p.grids["Features"][i] else None
        d = p.grids["Deco"][i]
        m.fence[r][c] = d == 1
        m.deco[r][c] = DECO.get(d)
    P = props()
    chars = []
    for e in p.entities:
        f = {x["__identifier"]: x["__value"] for x in e["fieldInstances"]}
        x, y = e["px"]
        if e["__identifier"] == "Prop":
            from iso_trees import TREE_ALIASES
            name = ALIASES.get(f.get("sprite"), f.get("sprite"))
            name = TREE_ALIASES.get(name, name)
            if name in P:
                m.objects.append((P[name], x, y))
        elif e["__identifier"] == "Character":
            png = Path(sprite_dir) / f"{f.get('sprite')}.png"
            if png.exists():
                chars.append((Picture(Image.open(png).convert("RGBA")), x, y))
    return m, chars


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("out")
    ap.add_argument("--margin", type=int, default=6)
    ap.add_argument("--sprites", default=str(ROOT / "sprites"))
    ap.add_argument("--crop", action="store_true")
    ap.add_argument("--palette", default=palettes.DEFAULT)
    a = ap.parse_args()
    palettes.use(a.palette)
    import iso
    m, chars = load_map(a.map, a.sprites)
    m.objects += chars
    im = iso.render(m, 0, margin=a.margin)
    if a.crop:
        W, H = im.size
        im = im.crop((int(W * 0.27), int(H * 0.25), int(W * 0.73), int(H * 0.76)))
    im.save(a.out)
    print("wrote", a.out, im.size)


if __name__ == "__main__":
    sys.exit(main())
