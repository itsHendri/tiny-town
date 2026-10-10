"""The market village from the reference picture, built from tiny-town's parts. Writes maps/market-village.ldtk
and a picture of it, so it can be compared with the reference.

    python art/reference_town.py [palette] [house look]
"""
import sys
from pathlib import Path

import palettes

ROOT = Path(__file__).resolve().parent.parent
N = 28
PAD = 6          # cells of light wood round the town, part of the map (past it, the editor's grass runs on forever)


def layout():
    import preview
    m = preview.Map(N, N)
    P = lambda r0, c0, r1, c1, t="path": m.fill("terrain", r0, c0, r1, c1, t)
    # the cobbled road: in from the bottom-left, a bend at the market, out to the top-right, with branches
    P(16, 8, 28, 10)                 # entrance road (screen: from the bottom-left corner up to the middle)
    P(15, 8, 17, 21)                 # across the middle
    P(4, 19, 17, 21)                 # up to the top-right
    P(8, 8, 16, 10)                  # up to the houses on the left
    P(8, 3, 10, 10)                  # to the left houses' doors
    P(16, 14, 25, 16)                # down from the market to the bridge
    P(23, 14, 25, 27)                # over the stream and away
    P(4, 14, 6, 21)                  # to the thatched house
    m.fill("terrain", 17, 10, 23, 14, "cobbles")      # the market square
    # water: a pond at the top fed by a little waterfall, a stream on the right with a bridge
    m.fill("height", 0, 9, 3, 15, 1)
    P(0, 11, 3, 13, "water")
    for r in range(3, 8):                                     # a round pond under the waterfall
        for c in range(8, 16):
            if ((c - 12) / 3.6) ** 2 + ((r - 5) / 2.4) ** 2 <= 1.05:
                m.terrain[r][c] = "water"
    P(10, 22, 28, 24, "water")
    P(23, 22, 25, 24, "bridge")
    P(19, 17, 20, 18, "water")       # a little round pool in the flower garden
    # gardens: flower beds by the market and the houses, tall grass at the edges
    for (r0, c0, r1, c1) in ((17, 16, 22, 20), (11, 3, 13, 7), (6, 16, 8, 19), (24, 4, 26, 8), (12, 12, 14, 17)):
        for r in range(r0, r1):
            for c in range(c0, c1):
                if m.terrain[r][c] == "grass":
                    m.deco[r][c] = "flowers"
    for (r0, c0, r1, c1) in ((0, 0, 4, 6), (25, 0, 28, 6), (0, 24, 6, 28)):
        for r in range(r0, r1):
            for c in range(c0, c1):
                m.deco[r][c] = "tallgrass"
    # fenced yards: around the bottom-right house and along the left houses
    for c in range(23, 28):
        m.fence[11][c] = True
    for r in range(11, 18):
        m.fence[r][25] = True
    m.fence[14][25] = False; m.deco[14][25] = "gate"; P(14, 24, 15, 26)
    for r in range(17, 22):
        m.fence[r][2] = True
    for c in range(2, 7):
        m.fence[21][c] = True
    # trampled dirt under the market stalls and in front of the house doors
    for (r0, c0, r1, c1) in ((17, 6, 19, 8), (20, 6, 23, 8), (24, 9, 26, 11), (22, 15, 24, 17), (10, 4, 11, 6), (6, 17, 7, 19), (14, 26, 15, 28)):
        for r in range(r0, r1):
            for c in range(c0, c1):
                if m.terrain[r][c] == "grass":
                    m.terrain[r][c] = "dirt"
    return m


def dressing(m, taken, houses):
    """Small things along every road edge, and trees filling the quiet corners (the same every time)."""
    from dualgrid import h
    road = {"path", "cobbles", "bridge"}
    out = []
    near_road = lambda r, c, k: any(0 <= r + dr < N and 0 <= c + dc < N and m.terrain[r + dr][c + dc] in road
                                    for dr in range(-k, k + 1) for dc in range(-k, k + 1))
    for r in range(N):
        for c in range(N):
            if (c, r) in taken or m.terrain[r][c] != "grass" or m.fence[r][c] or m.deco[r][c] or m.height[r][c]:
                continue
            k = h("dress", c, r)
            if near_road(r, c, 1):
                if k < 0.32:
                    pick = ["detail-tuft-1", "detail-tuft-2", "detail-flowers-1", "detail-flowers-2", "detail-pebbles-1",
                            "detail-pebbles-2", "bush-1", "bush-3", "rock-1", "detail-mushrooms"][int(h("dk", c, r) * 10)]
                    out.append((pick, c, r))
            elif not near_road(r, c, 2) and k < 0.10 and not any((c + dc, r + dr) in houses for dr in range(-3, 3) for dc in range(-3, 3)):
                mix = ["tree-1", "birch-1", "tree-4", "pine-1", "oak-2", "tree-2", "pine-2", "maple-1", "poplar-1", "tree-5", "spruce-2", "birch-2", "tree-3", "pine-4", "oak-3", "willow-1"]
                out.append((mix[int(h("tk", c, r) * len(mix))], c, r))
            elif k > 0.93:
                out.append((["detail-flowers-1", "detail-tuft-2", "bush-2"][int(h("dk2", c, r) * 3)], c, r))
    return out


OBJECTS = [
    # houses (front cell)
    ("townhouse", 5, 9), ("cottage-red", 3, 15), ("thatch-house", 18, 3), ("townhouse", 27, 13), ("cottage-brown", 23, 6),
    # the market: stalls, crates, barrels, a chalkboard, lamps
    ("stall-red", 12, 18), ("stall-green", 12, 21), ("stall-purple", 7, 22), ("stall-orange", 10, 25), ("stall-red", 16, 23),
    ("crates", 13, 19), ("crate-tomatoes", 13, 22), ("crate-cabbages", 6, 23), ("barrel-iso", 5, 24), ("barrel-iso", 17, 24),
    ("chalkboard", 11, 16), ("flower-cart", 26, 15), ("bench-iso", 15, 14),
    ("lamp-sign", 7, 17), ("lamp-sign", 11, 14), ("lamp-iso", 18, 14), ("lamp-iso", 13, 24), ("lamp-sign", 21, 8), ("lamp-iso", 7, 11),
    # trees and bushes round the edges and between the houses
    ("pine-1", 1, 1), ("tree-2", 4, 1), ("pine-3", 7, 0), ("tree-5", 16, 0), ("pine-2", 22, 1), ("tree-1", 26, 2), ("pine-4", 27, 7),
    ("tree-4", 1, 7), ("pine-1", 0, 12), ("tree-6", 1, 19), ("pine-2", 0, 24), ("tree-3", 3, 27), ("pine-3", 8, 27), ("tree-1", 12, 27),
    ("pine-1", 18, 27), ("tree-5", 21, 26), ("pine-4", 27, 21), ("tree-2", 26, 25), ("tree-4", 17, 9), ("tree-1", 13, 9),
    ("tree-3", 10, 6), ("pine-2", 16, 6), ("bush-1", 9, 4), ("bush-2", 14, 7), ("bush-3", 6, 14), ("bush-1", 20, 12),
    ("bush-2", 4, 20), ("rock-1", 8, 2), ("rock-2", 15, 2), ("rock-1", 20, 21), ("rock-2", 24, 20), ("bush-3", 25, 9),
    ("tree-6", 21, 17), ("pine-3", 19, 25),
    ("rock-1", 8, 4), ("rock-2", 9, 7), ("rock-1", 15, 6), ("rock-2", 14, 8), ("detail-pebbles-1", 11, 8),
]


def with_woods(m, objects):
    """The town with PAD cells of thinning wood all round it, its roads and river running on out through the trees.
    The trees stand where the renderer's margin wood would (same hashes), so it looks as before, only lighter."""
    import preview
    from iso import MARGIN_TREES, ihash, margin_trees
    n = N + 2 * PAD
    big, trees = preview.Map(n, n), []
    for r in range(n):
        for c in range(n):
            r0, c0 = r - PAD, c - PAD
            if 0 <= r0 < N and 0 <= c0 < N:
                for layer in ("height", "terrain", "feature", "fence", "deco"):
                    getattr(big, layer)[r][c] = getattr(m, layer)[r0][c0]
                continue
            rc, cc = min(N - 1, max(0, r0)), min(N - 1, max(0, c0))
            ri, ci = rc + (2 if r0 < 0 else -2 if r0 >= N else 0), cc + (2 if c0 < 0 else -2 if c0 >= N else 0)
            t = m.terrain[rc][cc]
            if t in ("path", "cobbles", "water") and m.terrain[ri][ci] == t and m.height[rc][cc] == 0:
                big.terrain[r][c] = t                        # a road or the river leaving the town runs on
            elif ihash(c0 & 0xffff, r0 & 0xffff, 11) < margin_trees(c0, r0, N, N):
                trees.append((MARGIN_TREES[int(ihash(c0 & 0xffff, r0 & 0xffff, 13) * len(MARGIN_TREES))], c, r))
    return big, [(name, c + PAD, r + PAD) for name, c, r in objects] + trees


def sprites():
    """Every prop by name, drawn in the current palette."""
    import iso_ground
    import iso_market
    import iso_props
    from props import catalog
    out = {name: spr for name, (spr, _) in catalog().items() if not name.startswith("house-")}
    from iso_nature import nature
    out.update(nature())
    out.update({name: iso_props.house(**kw)[0] for name, kw in iso_props.HOUSES.items()})
    out.update({name: make() for name, make in iso_market.MARKET.items()})
    return out


def build(palette="earthy", look="storybook"):
    palettes.use(palette)
    import iso
    import iso_props
    import ldtk
    iso_props.use_look(look)
    m = layout()
    spr = sprites()
    taken, houses = set(), set()
    for name, c, r in OBJECTS:
        foot = iso_props.HOUSES.get(name, {})
        fw, fd = foot.get("fw", 1), foot.get("fd", 1)
        if name.startswith("stall"):
            fw, fd = 2, 1
        for rr in range(r - fd + 1, r + 1):
            for cc in range(c - fw + 1, c + 1):
                taken.add((cc, rr))
                if name in iso_props.HOUSES:
                    houses.add((cc, rr))
    m, objects = with_woods(m, OBJECTS + dressing(m, taken, houses))
    n = N + 2 * PAD
    for name, c, r in objects:
        m.objects.append((spr[name], c * 16 + 8, (r + 1) * 16))
    # the map file
    p = ldtk.Project(n, n)
    T_ = {"grass": 0, "path": 1, "cobbles": 2, "water": 3, "soil": 4, "bridge": 5, "dirt": 6}
    D_ = {"flowers": 2, "tallgrass": 3, "gate": 4}
    flat = lambda g: [v for row in g for v in row]
    p.set_intgrid("Height", flat(m.height))
    p.set_intgrid("Terrain", [T_[t] for t in flat(m.terrain)])
    p.set_intgrid("Features", [1 if f == "stairs" else 0 for f in flat(m.feature)])
    p.set_intgrid("Deco", [1 if f else D_.get(d, 0) for f, d in zip(flat(m.fence), flat(m.deco))])
    for name, c, r in objects:
        p.add_entity("Prop", c * 16 + 8, (r + 1) * 16, {"sprite": name})
    p.add_entity("Region", (8 + PAD) * 16, (27 + PAD) * 16, {"name": "start"}, w=16, h=16)
    p.save(ROOT / "maps" / "market-village.ldtk")
    return iso.render(m, 0, margin=6, woods=False)


def full_bleed(im):
    """The middle of the picture: everything inside the forest's diamond, no plain background showing."""
    W, H = im.size
    return im.crop((int(W * 0.27), int(H * 0.25), int(W * 0.73), int(H * 0.76)))


if __name__ == "__main__":
    im = build(sys.argv[1] if len(sys.argv) > 1 else "earthy", sys.argv[2] if len(sys.argv) > 2 else "storybook")
    im.save(ROOT / "out" / "market-village.png")
    full_bleed(im).save(ROOT / "out" / "market-village-scene.png")
    print("wrote maps/market-village.ldtk and out/market-village.png", im.size)
