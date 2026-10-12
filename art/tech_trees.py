"""Tech trees for the neon city: not trees drawn in neon, but tech objects that read as trees. Straight lines,
light instead of leaves. Every concept covers all 12 tree kinds through their shape (round, wide, small, tall,
column, drooping, umbrella, cone, slim cone), so a dense wood keeps its variety.

    trees(concept) -> {name: Sprite}        concepts: data, circuit, wire, voxel, fibre

Concepts (from Hendri's references, 2026-10-12): data (a dark tree with glowing cubes in the crown and light
dropping from them, on a lit pedestal), circuit (an angular crown of neon traces, vias and a chip), wire (a
see-through wireframe hologram over a projector), voxel (a crown of little glowing cubes), fibre (straight fibre
strands fanning up, glowing tips).
"""
import math

from dualgrid import h
from sprites import RGB, Sprite, tight

# name -> (shape, size, accent): the 12 kept tree kinds
KINDS = {
    "tree-1": ("round", 1.0, "neon_b"), "tree-2-d2": ("wide", 1.0, "neon_a"), "oak-3": ("wide", 1.25, "neon_b"),
    "maple-1": ("round", 1.1, "neon_c"), "blossom-1": ("small", 0.85, "neon_a"), "tree-6": ("small", 0.9, "neon_c"),
    "birch-2": ("tall", 1.0, "neon_b"), "poplar-1": ("column", 1.0, "neon_a"), "willow-1": ("droop", 1.1, "neon_b"),
    "pine-2": ("umbrella", 1.0, "neon_c"), "pine-3": ("cone", 1.25, "neon_b"), "cypress-2": ("slim", 1.1, "neon_a"),
}


class Shape:
    """A crown's outline in sprite pixels and where the trunk runs."""

    def __init__(self, shape, size, w, hgt):
        self.kind = shape
        self.cx = w / 2
        self.base = hgt - 10                                 # feet row (room below for a pedestal)
        R = 14 * size
        if shape in ("cone", "slim"):
            half = R * (0.75 if shape == "cone" else 0.42)
            self.top, self.bottom, self.half = 3, self.base - 6, half
        elif shape == "umbrella":
            self.rx, self.ry, self.cy = R * 1.25, R * 0.45, R * 0.6 + 3
        else:
            rx, ry = {"round": (1.0, 0.9), "wide": (1.3, 0.8), "small": (0.85, 0.8), "tall": (0.7, 1.15),
                      "column": (0.5, 1.6), "droop": (1.3, 0.75)}[shape]
            self.rx, self.ry = R * rx, R * ry
            self.cy = self.ry + 3
        self.trunk_top = self.bottom if shape in ("cone", "slim") else self.cy + self.ry * 0.4

    def inside(self, x, y):
        if self.kind in ("cone", "slim"):
            if not self.top <= y <= self.bottom:
                return False
            f = (y - self.top) / (self.bottom - self.top)
            return abs(x + 0.5 - self.cx) <= self.half * f + 0.5
        dx, dy = (x + 0.5 - self.cx) / self.rx, (y + 0.5 - self.cy) / self.ry
        if self.kind in ("circuit-angular",):
            return max(abs(dx), abs(dy), (abs(dx) + abs(dy)) / 1.35) <= 1
        return dx * dx + dy * dy <= 1

    def angular(self, x, y):
        """An octagon in the crown's box: straight sides, cut corners (the circuit tree's outline)."""
        if self.kind in ("cone", "slim"):
            return self.inside(x, y)
        dx, dy = abs(x + 0.5 - self.cx) / self.rx, abs(y + 0.5 - self.cy) / self.ry
        return max(dx, dy, (dx + dy) / 1.38) <= 1


def canvas(shape, size):
    R = 14 * size
    w = int(R * 2.8 + 12)
    hgt = int(R * (3.6 if shape in ("cone", "slim", "column", "umbrella") else 3.0) + 14)
    return Sprite(w, hgt)


def trunk(s, sh, colours=("vh0", "vh1"), width=3, seam=None):
    """A straight trunk from the crown down to the feet; a glowing seam up its lit side if given."""
    x0 = int(sh.cx - width / 2)
    for y in range(int(sh.trunk_top), sh.base + 1):
        for i in range(width):
            s.put(x0 + i, y, colours[0] if i < width / 2 else colours[1])
        if seam:
            s.put(x0, y, seam)


def pedestal(s, sh, accent, w=16):
    """A low lit plate under the tree: a dark diamond with a neon rim on its front edges."""
    cx, cy = sh.cx, sh.base + 1
    for y in range(int(cy - w / 4) - 1, int(cy + w / 4) + 3):
        for x in range(int(cx - w / 2) - 1, int(cx + w / 2) + 2):
            d = abs(x + 0.5 - cx) / (w / 2) + abs(y + 0.5 - cy) / (w / 4)
            if d <= 1:
                s.put(x, y, accent if d > 0.8 and y + 0.5 > cy else "vh2")
            elif d <= 1.0 + 4 / (w / 4) and y + 0.5 > cy and abs(x + 0.5 - cx) < w / 2:
                s.put(x, y, "vh1" if x < cx else "vh2")                     # the plate's thickness


def cube(s, x, y, n, col, top="fl_w"):
    """A little iso cube with edge n, its top corner at (x, y): a light top, a lit left face, a dark right face."""
    for j in range(2 * n + 1):
        for i in range(-n, n + 1):
            low = n - abs(i) / 2                                     # the top diamond's lower edge at column i
            if abs(i) / n + abs(j - n / 2) / (n / 2) <= 1:
                s.put(x + i, y + j, top)
            elif low < j <= low + n:
                s.put(x + i, y + j, col if i < 0 else "out")


def finish(s, cx):
    """Crop to what's drawn, keeping the tree centred on cx, so the feet are the bottom middle."""
    x0, y0, x1, y1 = s.im.getbbox()
    half = int(max(cx - x0, x1 - cx)) + 1
    out = Sprite(2 * half + 1, y1 - y0)
    out.im.paste(s.im.crop((int(cx) - half, y0, int(cx) + half + 1, y1)), (0, 0))
    out.px = out.im.load()
    return out


def line(s, x0, y0, x1, y1, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for k in range(n):
        t = k / max(1, n - 1)
        s.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)


# ---------- the concepts ----------

def data_tree(name, shape, size, accent):
    """A dark tree with glowing cubes in its crown and light dropping from them, on a lit pedestal."""
    s = canvas(shape, size)
    sh = Shape(shape, size, s.w, s.h)
    for y in range(s.h):                                             # the dark canopy
        for x in range(s.w):
            if sh.inside(x, y):
                s.put(x, y, "lf2" if h("cano", name, x // 2, y // 2) < 0.3 else "lf3")
    trunk(s, sh, ("lf1", "lf2"), 3)
    for side in (-1, 1):                                             # angular branches: up, then out at 45 degrees
        x, y = sh.cx + side, sh.trunk_top
        line(s, x, y, x + side * 4, y - 4, "lf1")
        line(s, x + side * 4, y - 4, x + side * 4, y - 9, "lf1")
    drops = []
    for j in range(0, s.h, 8):                                       # cubes on a jittered grid in the crown
        for i in range(0, s.w, 9):
            x, y = i + int(h("cx", name, i, j) * 4), j + int(h("cy", name, i, j) * 3)
            if sh.inside(x, y + 3) and sh.inside(x, y - 1) and h("cube", name, i, j) < 0.75:
                cube(s, x, y, 3, accent)
                if h("drop", name, i, j) < 0.35:
                    drops.append((x, y + 5))
    for (x, y) in drops:                                             # light dropping from some cubes
        for k in range(int(4 + h("dl", name, x, y) * 8)):
            if y + k < sh.base:
                s.put(x, y + k, accent if k % 3 else "fl_w")
    s = tight(s, 2).outline()
    sh.cx += 2
    sh.base += 2
    pedestal(s, sh, accent)
    return finish(s, sh.cx)


def circuit_tree(name, shape, size, accent):
    """An angular crown: dark board, neon traces with 45-degree jogs from the trunk out, gold vias, a chip."""
    s = canvas(shape, size)
    sh = Shape(shape, size, s.w, s.h)
    for y in range(s.h):
        for x in range(s.w):
            if sh.angular(x, y):
                s.put(x, y, "vh2")
    trunk(s, sh, ("vh0", "vh1"), 3, seam=accent)
    cy = sh.cy if shape not in ("cone", "slim") else (sh.top + sh.bottom) * 0.6
    # traces fanning out from the chip: out sideways a little, a 45-degree jog to their row, then straight to the
    # edge, a via at the end; every other one dimmer
    rows = [cy + k * 3 for k in range(-8, 9)]
    for side in (-1, 1):
        for n_, ty in enumerate(rows):
            if not sh.angular(int(sh.cx + side * 5), int(ty)):
                continue
            x, y = sh.cx + side * 4, cy + (1 if ty > cy else -1 if ty < cy else 0)
            c = accent if n_ % 2 == 0 else "lf1"
            path = []
            while abs(y - ty) >= 1:                                   # the jog
                x += side; y += 1 if ty > y else -1
                path.append((x, y))
            if not all(sh.angular(int(px_ + side * 2), int(py_)) for px_, py_ in path):
                continue                                              # this trace wouldn't fit inside the crown
            for (px_, py_) in path:
                s.put(int(px_), int(py_), c)
            while sh.angular(int(x + side * 3), int(y)):              # straight out
                x += side
                s.put(int(x), int(y), c)
            if h("via", name, side, n_) < 0.75:
                for (i_, j_, vc) in ((0, -1, "cb1"), (side, -1, "cb1"), (0, 0, "cb1"), (side, 0, "cb2")):
                    s.put(int(x + side) + i_, int(y) + j_, vc)
    for j in range(-2, 3):                                            # the chip at the heart
        for i in range(-3, 4):
            edge = abs(i) == 3 or abs(j) == 2
            s.put(int(sh.cx) + i, int(cy) + j, "cb1" if edge and (i + j) % 2 else "vh1" if edge else "out")
    s = tight(s, 2)
    for y in range(s.h):                                              # a neon outline round the crown
        for x in range(s.w):
            if not s.px[x, y][3] and any(s.get(x + dx, y + dy)[:3] == RGB["vh2"][:3]
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                s.put(x, y, accent)
    s = s.outline()
    return finish(s, sh.cx + 2)


def wire_tree(name, shape, size, accent):
    """A wireframe hologram: a see-through crown, scanlines, bright edges and corners, over a projector base."""
    s = canvas(shape, size)
    sh = Shape(shape, size, s.w, s.h)
    col = RGB[accent][:3]
    for y in range(s.h):
        for x in range(s.w):
            if sh.angular(x, y):
                edge = any(not sh.angular(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge:
                    s.put(x, y, accent)
                elif y % 3 == 0:
                    s.put(x, y, col + (150,))                         # scanlines
                else:
                    s.put(x, y, col + (55,))                          # the see-through fill
    for (dx, dy) in ((-1, 0), (1, 0), (0, -1)):                       # bright corners
        x = int(sh.cx + dx * (getattr(sh, "rx", getattr(sh, "half", 6)) - 1))
        y = int((sh.cy if hasattr(sh, "cy") else sh.top + 2) + dy * (getattr(sh, "ry", 0) - 1))
        s.put(x, y, "fl_w")
    trunk(s, sh, (col + (120,), col + (90,)), 3)
    for k in range(-2, 3, 2):                                         # beams from the projector
        line(s, sh.cx + k * 0.5, sh.base, sh.cx + k * 2, sh.trunk_top + 2, col + (70,))
    s = tight(s, 2)
    sh.cx += 2
    sh.base += 2
    pedestal(s, sh, accent, 12)
    return finish(s, sh.cx)


def voxel_tree(name, shape, size, accent):
    """A crown of little glowing iso cubes, lighter to the top-left; a column of dark cubes for a trunk."""
    s = canvas(shape, size)
    sh = Shape(shape, size, s.w, s.h)
    ramp = {"neon_a": ("fl_p", "neon_a", "door2"), "neon_b": ("fl_w", "neon_b", "w2"), "neon_c": ("fl_y", "neon_c", "y2")}[accent]
    for y in range(int(sh.trunk_top), sh.base - 2, 3):
        cube(s, int(sh.cx), y, 2, "vh0", "vh1")
    cells = []
    for j in range(0, s.h, 3):
        for i in range(0, s.w, 4):
            x, y = i + (2 if (j // 3) % 2 else 0), j
            if sh.inside(x, y + 2):
                cells.append((x, y))
    for (x, y) in sorted(cells, key=lambda c: c[1]):
        f = (x - sh.cx) / s.w + (y - (getattr(sh, "cy", s.h / 3))) / s.h
        k = 0 if f < -0.15 else 1 if f < 0.2 else 2
        cube(s, x, y, 2, ramp[min(2, k)], ramp[max(0, k - 1)])
    return finish(tight(s).outline(), sh.cx + 1)


def fibre_tree(name, shape, size, accent):
    """A straight trunk fanning into straight fibre strands, each ending in a glowing tip."""
    s = canvas(shape, size)
    sh = Shape(shape, size, s.w, s.h)
    trunk(s, sh, ("vh0", "vh1"), 3, seam=accent)
    root = (sh.cx, sh.trunk_top)
    tips = []
    for j in range(0, s.h, 3):
        for i in range(0, s.w, 3):
            x, y = i + int(h("fx", name, i, j) * 2), j + int(h("fy", name, i, j) * 2)
            if sh.inside(x, y) and not sh.inside(x, y - 3) and h("tip", name, i, j) < 0.7:
                tips.append((x, y))                                  # the crown's upper edge
            elif sh.inside(x, y) and h("tip2", name, i, j) < 0.12:
                tips.append((x, y))
    for (x, y) in tips:
        line(s, root[0], root[1], x, y, "p3" if h("fc", name, x, y) < 0.5 else "lf1")
    for (x, y) in tips:
        s.put(x, y, "fl_w"); s.put(x + 1, y, accent); s.put(x, y + 1, accent)
    return finish(tight(s).outline(), sh.cx + 1)


CONCEPTS = {"data": data_tree, "circuit": circuit_tree, "wire": wire_tree, "voxel": voxel_tree, "fibre": fibre_tree}


def trees(concept):
    fn = CONCEPTS[concept]
    return {name: fn(name, shape, size, accent) for name, (shape, size, accent) in KINDS.items()}
