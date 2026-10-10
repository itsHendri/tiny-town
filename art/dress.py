"""Dress a map: small things along every road edge (tufts, flowers, pebbles, bushes, rocks), trees in the quiet
corners away from roads and houses. The same map always gets the same dressing.

    python art/dress.py <in.ldtk> <out.ldtk>
"""
import sys

import ldtk
from dualgrid import h

ROAD = {1, 2, 5}                 # path, cobbles, bridge
EDGE = ["detail-tuft-1", "detail-tuft-2", "detail-flowers-1", "detail-flowers-2", "detail-pebbles-1", "detail-pebbles-2",
        "bush-1", "bush-3", "rock-1", "detail-mushrooms"]
TREES = ["tree-1", "birch-1", "tree-4", "pine-1", "oak-2", "tree-2", "pine-2", "maple-1", "poplar-1", "tree-5", "spruce-2", "birch-2", "tree-3", "pine-4", "oak-3", "willow-1"]
FOOT = {"house-red": (2, 2), "house-yellow": (3, 2), "house-blue": (3, 2), "cottage": (2, 2), "townhouse": (2, 2),
        "thatch": (3, 2), "longhouse": (3, 2), "stall": (2, 1)}


def footprint(name):
    for prefix, f in FOOT.items():
        if name.startswith(prefix):
            return f
    return (1, 1)


def dress(p, edge=0.32, trees=0.10):
    cols, rows = p.cols, p.rows
    T, D, H = p.grids["Terrain"], p.grids["Deco"], p.grids["Height"]
    at = lambda r, c: r * cols + c
    taken, houses = set(), set()
    for e in p.entities:
        c, r = int(e["px"][0] // 16), int((e["px"][1] - 1) // 16)
        name = next((f["__value"] for f in e["fieldInstances"] if f["__identifier"] == "sprite"), "") or ""
        fw, fd = footprint(name)
        for rr in range(r - fd + 1, r + 1):
            for cc in range(c - fw + 1, c + 1):
                taken.add((cc, rr))
                if fw > 1 and not name.startswith("stall"):
                    houses.add((cc, rr))
    road_near = lambda r, c, k: any(0 <= r + dr < rows and 0 <= c + dc < cols and T[at(r + dr, c + dc)] in ROAD
                                    for dr in range(-k, k + 1) for dc in range(-k, k + 1))
    added = 0
    for r in range(rows):
        for c in range(cols):
            i = at(r, c)
            if (c, r) in taken or T[i] or D[i] or H[i]:
                continue
            k = h("dress", c, r)
            name = None
            if road_near(r, c, 1):
                if k < edge:
                    name = EDGE[int(h("dk", c, r) * len(EDGE))]
            elif not road_near(r, c, 2) and k < trees and not any((c + dc, r + dr) in houses for dr in range(-3, 3) for dc in range(-3, 3)):
                name = TREES[int(h("tk", c, r) * len(TREES))]
            elif k > 0.93:
                name = ["detail-flowers-1", "detail-tuft-2", "bush-2"][int(h("dk2", c, r) * 3)]
            if name:
                p.add_entity("Prop", c * 16 + 8, (r + 1) * 16, {"sprite": name})
                added += 1
    return added


if __name__ == "__main__":
    p = ldtk.load(sys.argv[1])
    n = dress(p)
    p.save(sys.argv[2])
    print(f"added {n} things; wrote {sys.argv[2]}")
