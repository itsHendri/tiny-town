"""Trees for the isometric view, in many kinds, and no two alike.

Broadleaf crowns are built from many small leaf clumps, each lit from the top-left, inside an overall shape that
varies per tree (wider, taller, lopsided, a leaning trunk). Conifers are built from tiers. Every kind takes a seed,
so the same name always draws the same tree, and different names draw different trees.

    python art/iso_trees.py <out.png> [palette]      a sheet of every tree
"""
import math
import sys

from dualgrid import h
from sprites import Sprite, rng, tight

# leaf colours, light to dark (a "dark" tree starts further along)
LEAVES = {
    "green": ["t0", "t1", "t2", "t3", "t4", "t5"],
    "olive": ["moss", "moss2", "t2", "t3", "t4", "t5"],
    "deep": ["t1", "t2", "t3", "t4", "t5", "t5"],
    "autumn": ["y0", "fl_o", "y2", "r2", "r3", "r3"],
    "rust": ["r0", "r1", "r2", "r3", "trunk2", "trunk2"],
    "blossom": ["fl_w", "fl_p", "r0", "t2", "t3", "t4"],
    "birch": ["g0", "moss", "t1", "t2", "t3", "t4"],
    "fir": ["p0", "p1", "p2", "p3", "t5", "t5"],
    "fir_dark": ["p1", "p2", "p3", "t5", "t5", "t5"],
}


def trunk(s, cx, top, base, width=4.4, lean=0.0, birch=False, seed=0):
    """A trunk from `top` down to `base`, flared at the foot, leaning a little; lit on the left."""
    for y in range(int(top), base + 1):
        f = (base - y) / max(1, base - top)
        x0 = cx + lean * f
        half = width / 2 + max(0, (y - (base - 4)) * 0.6)
        for x in range(int(x0 - half), int(x0 + half) + 1):
            if birch:
                mark = h("bark", x, y // 2, seed) < 0.18 and (y % 3 == 0)
                c = "s3" if mark else ("c0" if x < x0 else "c1")
            else:
                c = "trunk2" if x > x0 + 0.5 else "trunk"
                if h("bark", x, y // 3, seed) < 0.12 and abs(x - x0) < half - 0.5:
                    c = "trunk2"                                     # bark furrows
            s.put(x, y, c)
    if not birch:                                                    # roots spreading at the foot
        for dx in (-1, 1):
            for k in range(int(width * 0.6)):
                s.put(int(cx + dx * (width / 2 + k + 1)), base - (0 if k > 1 else 1), "trunk2")


def crown(s, r, cx, cy, rx, ry, n, cols, dark=0, clump=(0.22, 0.34), holes=0.0):
    """A leafy crown: n clumps scattered in an ellipse, each with its own top-left light, the whole crown darker
    to the bottom-right."""
    R = max(rx, ry)
    clumps = []
    for _ in range(n):
        a = r.uniform(0, math.pi * 2)
        d = math.sqrt(r.uniform(0, 1)) * 0.8
        clumps.append((cx + math.cos(a) * d * rx, cy + math.sin(a) * d * ry, R * r.uniform(*clump)))
    clumps.sort(key=lambda c: c[1])
    for (x, y, rr) in clumps:
        if holes and r.random() < holes:
            continue
        for j in range(int(y - rr) - 1, int(y + rr) + 2):
            for i in range(int(x - rr) - 1, int(x + rr) + 2):
                dx, dy = i + 0.5 - x, j + 0.5 - y
                if dx * dx + dy * dy > rr * rr:
                    continue
                lit = -(dx * 0.8 + dy) / rr
                whole = ((j - cy) / ry) + 0.6 * ((i - cx) / rx)
                k = 1
                if lit > 0.55 and whole < 0.3:
                    k = 0
                elif lit < -0.45 or whole > 0.55:
                    k = 2 if whole < 0.85 else 3
                if whole > 1.0:
                    k = 3
                if k < 3 and h("leaf", i, j) < 0.13:
                    k += 1                                           # leaf texture, scattered
                elif k > 0 and h("leaf2", i, j) < 0.05:
                    k -= 1
                s.put(i, j, cols[min(5, k + dark)])
    for _ in range(int(n / 2.5)):                                  # glints on the lit side
        x, y = int(cx + r.uniform(-rx, rx * 0.3)), int(cy + r.uniform(-ry * 0.9, 0))
        if s.get(x, y)[3]:
            s.put(x, y, cols[dark])


def broadleaf(kind, seed, size=1.0, dark=0, leaves="green"):
    """oak (round), wide, tall, lopsided, small: one crown on one trunk, shaped by `kind`, varied by the seed."""
    r = rng(kind, seed)
    R = 17 * size
    shape = {"oak": (1.15, 0.95), "wide": (1.4, 0.8), "tall": (0.85, 1.25), "small": (0.9, 0.85), "lopsided": (1.2, 0.9)}[kind]
    rx = R * shape[0] * r.uniform(0.9, 1.1)
    ry = R * shape[1] * r.uniform(0.9, 1.1)
    w, hgt = int(rx * 2 + 12), int(ry * 2 + R * 0.55 + 10)
    s = Sprite(w, hgt)
    cx, cy = w / 2 + (r.uniform(-0.15, 0.15) * rx if kind == "lopsided" else 0), ry + 4
    lean = r.uniform(-2.5, 2.5)
    trunk(s, w / 2, cy + ry * 0.2, hgt - 3, 4.4 * size ** 0.5, lean, seed=seed)
    for dx in (-1, 1):                                             # two branches up into the crown
        for t in range(int(ry * 0.5)):
            s.put(int(w / 2 + lean * 0.3 + dx * t * 0.6), int(cy + ry * 0.35 - t), "trunk")
    crown(s, r, cx, cy, rx, ry, int(26 * size * shape[0]), LEAVES[leaves], dark)
    return tight(s).outline()


def fruit_tree(seed, size=0.95, fruit=("r1", "r0"), leaves="green", dark=0):
    s = broadleaf("small", seed, size, dark, leaves)
    r = rng("fruit", seed)
    for _ in range(int(22 * size)):                                # fruit hanging in the crown
        x, y = r.randint(4, s.w - 6), r.randint(4, int(s.h * 0.55))
        if s.get(x, y)[3] and s.get(x + 1, y + 1)[3]:
            s.put(x, y, fruit[0]); s.put(x + 1, y, fruit[0]); s.put(x, y + 1, fruit[0]); s.put(x + 1, y + 1, fruit[0]); s.put(x, y, fruit[1])
    return s


def birch(seed, size=1.0):
    r = rng("birch", seed)
    R = 13 * size
    rx, ry = R * r.uniform(0.8, 1.0), R * r.uniform(1.05, 1.3)
    w, hgt = int(rx * 2 + 10), int(ry * 2 + R * 1.3 + 10)
    s = Sprite(w, hgt)
    cx, cy = w / 2, ry + 4
    lean = r.uniform(-3, 3)
    crown(s, r, cx + lean * 0.4, cy, rx, ry, int(22 * size), LEAVES["birch"], clump=(0.18, 0.28), holes=0.12)
    trunk(s, cx, cy + ry * 0.55, hgt - 3, 3.2, lean, birch=True, seed=seed)       # the white trunk shows below
    return tight(s).outline()


def poplar(seed, size=1.0):
    r = rng("poplar", seed)
    R = 12 * size
    rx, ry = R * r.uniform(0.6, 0.72), R * r.uniform(1.8, 2.1)
    w, hgt = int(rx * 2 + 10), int(ry * 2 + 14)
    s = Sprite(w, hgt)
    cx, cy = w / 2, ry + 3
    trunk(s, cx, cy + ry * 0.6, hgt - 3, 3.4, seed=seed)
    crown(s, r, cx, cy, rx, ry, int(24 * size), LEAVES["deep"], clump=(0.2, 0.3))
    return tight(s).outline()


def willow(seed, size=1.0):
    r = rng("willow", seed)
    R = 17 * size
    rx, ry = R * 1.3, R * 0.75
    w, hgt = int(rx * 2 + 10), int(ry * 2 + R * 1.2 + 10)
    s = Sprite(w, hgt)
    cx, cy = w / 2, ry + 4
    trunk(s, cx, cy, hgt - 3, 5, r.uniform(-1.5, 1.5), seed=seed)
    crown(s, r, cx, cy, rx, ry, int(24 * size), LEAVES["olive"], clump=(0.2, 0.3))
    # falls of leaves hang from the crown in uneven, gently curving curtains
    cols = LEAVES["olive"]
    x = cx - rx * 0.95
    while x < cx + rx * 0.95:
        if r.random() < 0.7:
            y0 = cy + ry * 0.2 + r.uniform(0, ry * 0.45)
            length = r.uniform(7, 16) * size
            sway = r.uniform(-1.5, 1.5)
            for k in range(int(length)):
                xx, yy = int(x + sway * (k / length) ** 2), int(y0 + k)
                if 0 <= yy < hgt - 4:
                    c = cols[1] if k < length * 0.3 and x < cx else cols[2] if x < cx + rx * 0.3 else cols[3]
                    s.put(xx, yy, c)
                    if k < length * 0.6:
                        s.put(xx + 1, yy, cols[min(3, cols.index(c) + 1)])
        x += r.uniform(1.5, 3.0)
    return tight(s).outline()


def spruce(seed, size=1.0, dark=False):
    r = rng("spruce", seed)
    w, hgt = int(26 * size * r.uniform(0.9, 1.1)), int(50 * size * r.uniform(0.92, 1.1))
    s = Sprite(w, hgt)
    cx = w / 2
    s.rect(int(cx - 2), hgt - 7, 4, 7, "trunk2"); s.rect(int(cx - 2), hgt - 7, 2, 7, "trunk")
    cols = LEAVES["fir_dark" if dark else "fir"]
    tiers = r.randint(5, 7)
    for t in range(tiers):
        top = int(t * (hgt - 9) / (tiers + 0.3))
        bottom = int(top + (hgt - 9) / tiers * 1.65)
        half = (w / 2 - 1) * (0.3 + 0.7 * (t + 1) / tiers) * r.uniform(0.9, 1.05)
        skew = r.uniform(-1, 1)
        for j in range(top, min(bottom, hgt - 6)):
            f = (j - top) / max(1, bottom - top)
            span = half * f ** 0.85 + 1
            droop = (j == min(bottom, hgt - 6) - 1)
            for i in range(int(cx + skew * f - span), int(cx + skew * f + span) + 1):
                rel = (i - cx) / max(1, span)
                if droop and (i + t) % 3 == 0:
                    continue
                c = cols[3] if f > 0.86 else cols[2] if rel > 0.3 else cols[0] if rel < -0.45 and f < 0.75 else cols[1]
                if c == cols[1] and (i * 5 + j * 3) % 13 == 0:
                    c = cols[2]
                s.put(i, j, c)
    s.put(int(cx), 0, cols[0]); s.put(int(cx), 1, cols[1])
    return tight(s).outline()


def scots_pine(seed, size=1.0):
    """A tall orange-brown trunk and a flat, cloudy crown of needles."""
    r = rng("scots", seed)
    R = 13 * size
    w, hgt = int(R * 2.8 + 10), int(R * 3.6 + 10)
    s = Sprite(w, hgt)
    cx = w / 2
    lean = r.uniform(-4, 4)
    for y in range(int(R * 0.9), hgt - 2):                         # the trunk, rusty above, brown below
        f = (hgt - 2 - y) / (hgt - 2 - R * 0.9)
        x0 = cx + lean * f
        for x in range(int(x0 - 1.6), int(x0 + 1.6) + 1):
            s.put(x, y, ("y2" if x < x0 else "y3") if f > 0.45 else ("trunk" if x < x0 else "trunk2"))
    cols = LEAVES["fir"]
    for k in range(r.randint(2, 3)):                               # flat clouds of needles
        ccx = cx + lean + r.uniform(-R * 0.6, R * 0.6)
        ccy = R * 0.5 + k * R * 0.55
        crown(s, r, ccx, ccy + 4, R * r.uniform(0.75, 1.0), R * 0.38, 10, cols, clump=(0.25, 0.35))
    return tight(s).outline()


def cypress(seed, size=1.0):
    r = rng("cypress", seed)
    w, hgt = int(14 * size), int(46 * size * r.uniform(0.95, 1.1))
    s = Sprite(w, hgt)
    cx = w / 2
    s.rect(int(cx - 1), hgt - 4, 2, 4, "trunk2")
    cols = LEAVES["fir_dark"]
    for j in range(hgt - 4):
        f = j / (hgt - 4)
        span = (w / 2 - 0.5) * math.sin(min(1, f * 1.15) * math.pi * 0.62) ** 0.9
        for i in range(int(cx - span), int(cx + span) + 1):
            rel = (i - cx) / max(1, span)
            c = cols[0] if rel < -0.4 else cols[2] if rel > 0.35 else cols[1]
            if (j + i * 2) % 5 == 0:
                c = cols[min(3, cols.index(c) + 1)]
            s.put(i, j, c)
    return tight(s).outline()


# Trees kept 2026-10-11 (tree round: one per distinct shape). Every other old name points at the closest kept tree.
TREE_ALIASES = {
    "birch-1": "birch-2", "fruit-2": "tree-6", "maple-2": "maple-1", "oak-2": "oak-3", "pine-1": "pine-3",
    "pine-4": "cypress-2", "pine-5": "pine-2", "poplar-2": "poplar-1", "spruce-2": "pine-3",
    "tree-1-d1": "tree-1", "tree-1-d2": "tree-2-d2", "tree-2": "tree-1", "tree-2-d1": "tree-2-d2",
    "tree-3": "maple-1", "tree-3-d1": "maple-1", "tree-3-d2": "maple-1", "tree-4": "tree-1", "tree-4-d1": "oak-3",
    "tree-4-d2": "oak-3", "tree-5": "tree-1", "tree-5-d1": "tree-2-d2", "tree-5-d2": "oak-3",
    "tree-6-d1": "tree-6", "tree-6-d2": "tree-6",
}


def trees():
    """Every tree by its catalog name (old names: TREE_ALIASES)."""
    return {
        "tree-1": broadleaf("oak", "t0", 1.0, 0, "green"), "tree-2-d2": broadleaf("wide", "t1", 0.95, 2, "olive"),
        "tree-6": fruit_tree("t5", 0.95, dark=0), "oak-3": broadleaf("wide", "o3", 1.2, 1, "deep"),
        "maple-1": broadleaf("lopsided", "m1", 1.05, 0, "rust"), "blossom-1": broadleaf("small", "c1", 0.9, 0, "blossom"),
        "birch-2": birch("b2", 1.15), "poplar-1": poplar("q1", 1.0), "willow-1": willow("w1", 1.0),
        "pine-2": scots_pine("p2", 1.0), "pine-3": spruce("p3", 1.3, dark=True), "cypress-2": cypress("c2", 1.15),
    }

if __name__ == "__main__":
    import palettes
    from PIL import Image
    palettes.use(sys.argv[2] if len(sys.argv) > 2 else palettes.DEFAULT)
    ts = list(trees().items())
    W = sum(s.w for _, s in ts) + 6 * len(ts)
    H = max(s.h for _, s in ts)
    sheet = Image.new("RGBA", (W, H), (142, 164, 63, 255))
    x = 0
    for _, s in ts:
        sheet.alpha_composite(s.im, (x, H - s.h))
        x += s.w + 6
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(sys.argv[1])
    print("wrote", sys.argv[1], [n for n, _ in ts])
