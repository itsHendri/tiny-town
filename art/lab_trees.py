"""Candidate tree crowns and ground shadows for the lab (art/lab.py, round "tree-look").

Crowns are drop-ins for iso_trees.crown (same arguments): every broadleaf kind, birch, poplar, willow and the scots
pine's needle clouds use it. Shadows are drop-ins for iso.place. Pixel-exact (no antialiasing), so JS can match.
"""
import math

from dualgrid import h


def _clumps(r, cx, cy, rx, ry, n, size):
    """n clumps in the crown's ellipse, back (top) to front (bottom); size: (min, max) radius as a share of R."""
    R = max(rx, ry)
    out = []
    for k in range(n):
        a = r.uniform(0, math.pi * 2)
        d = math.sqrt(r.uniform(0, 1)) * 0.72
        out.append((cx + math.cos(a) * d * rx, cy + math.sin(a) * d * ry, R * r.uniform(*size), r.uniform(0, 6.3)))
    # one big clump for the crown's top-left: the lit mass
    out.append((cx - rx * 0.18, cy - ry * 0.25, R * size[1] * 1.1, r.uniform(0, 6.3)))
    out.sort(key=lambda c: c[1])
    return out


def masses(scallop=0.0, rim=True, cel=False, dabs=False, count=3.2, grow=1.6):
    """A crown from a few big leaf masses.

    scallop: bumps on each mass's outline (leafy edge). rim: a dark line where a mass overlaps the one behind it.
    cel: tone from the crown's overall light only (flat bands), not per mass. dabs: the lit side broken into small
    leaf shapes instead of a smooth cap. count: how many fewer masses than today's clumps. grow: how much bigger."""
    def crown(s, r, cx, cy, rx, ry, n, cols, dark=0, clump=(0.22, 0.34), holes=0.0):
        size = (clump[0] * grow, clump[1] * grow)
        drawn = set()
        for (x, y, rr, ph) in _clumps(r, cx, cy, rx, ry, max(4, int(n / count)), size):
            if holes and r.random() < holes * 0.5:
                continue
            for j in range(int(y - rr) - 2, int(y + rr) + 3):
                for i in range(int(x - rr) - 2, int(x + rr) + 3):
                    dx, dy = i + 0.5 - x, j + 0.5 - y
                    d = math.hypot(dx, dy)
                    edge = rr * (1 + scallop * math.sin(math.atan2(dy, dx) * 5 + ph))
                    if d > edge:
                        continue
                    # the crown darkens to the bottom-right, mass by mass (tone edges follow the round masses,
                    # never a straight line across them)
                    whole = ((y - cy) / ry) + 0.55 * ((x - cx) / rx)
                    # this mass, lit top-left: a highlight disc pushed toward the light, a shadow crescent away
                    # from it (curved tone edges, no straight splits)
                    cap = math.hypot(dx + rr * 0.32, dy + rr * 0.38) < rr * 0.5
                    shade = math.hypot(dx + rr * 0.2, dy + rr * 0.26) > rr * 0.86
                    lit = 1.0 if cap else -1.0 if shade else 0.0
                    if cel:
                        k = 0 if whole < -0.35 else 1 if whole < 0.2 else 2 if whole < 0.6 else 3
                        if k > 0 and lit > 0.55:
                            k -= 1
                    else:
                        k = 0 if lit > 0.4 else 2 if lit < -0.35 else 1
                        if whole > 0.25:
                            k += 1
                        if whole > 0.75:
                            k += 1
                        if whole < -0.3 and k == 1 and lit > 0.0:
                            k = 0
                        k = min(3, k)
                    if dabs and k == 0 and h("dab", i // 2, j, 3) < 0.35:
                        k = 1                                                     # leaf-sized gaps in the light
                    if dabs and k == 1 and lit > 0.1 and h("dab2", i // 2, j) < 0.12:
                        k = 0                                                     # leaf-sized catches of light
                    if rim and (i, j) in drawn and d > edge - 1.2 and dy > -rr * 0.2:
                        k = min(3, max(k, 2) + 1)                                 # the line between masses
                    s.put(i, j, cols[min(5, k + dark)])
                    drawn.add((i, j))
    return crown


# ---------- ground shadows (for sprites without an anchor: trees, bushes, small things) ----------

def ellipse_rows(cx, cy, rx, ry):
    """Pixel rows of an ellipse: [(y, x0, x1)], x1 exclusive. Pixel centres inside, nothing antialiased."""
    rows = []
    for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
        t = 1 - ((y + 0.5 - cy) / ry) ** 2
        if t <= 0:
            continue
        half = rx * math.sqrt(t)
        x0, x1 = math.ceil(cx - half - 0.5), math.floor(cx + half - 0.5) + 1
        if x1 > x0:
            rows.append((y, x0, x1))
    return rows


def shadow_place(kind):
    """iso.place, with the shadow drawn as `kind`: contact (small, under the foot), cast (crown-sized, falling
    bottom-right, away from the light), pool (cast, with a darker core)."""
    def place(canvas, spr, X, Y):
        import iso
        from PIL import Image
        if getattr(spr, "anchor", None):
            return ORIGINAL(canvas, spr, X, Y)
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        px = sh.load()
        w = spr.w
        layers = {"contact": [(X, Y - 0.5, w * 0.3, 2.2, 90)],
                  "cast": [(X + w * 0.14, Y - 0.5, w * 0.46, 3.6, 80)],
                  "pool": [(X + w * 0.14, Y - 0.5, w * 0.48, 3.8, 55), (X + w * 0.06, Y - 0.5, w * 0.26, 2.2, 60)]}[kind]
        for (cx, cy, rx, ry, a) in layers:
            for (y, x0, x1) in ellipse_rows(cx, cy, rx, ry):
                for x in range(x0, x1):
                    if 0 <= x < sh.width and 0 <= y < sh.height:
                        r0, g0, b0, a0 = px[x, y]
                        px[x, y] = (34, 30, 52, min(255, a0 + a))
        canvas.alpha_composite(sh)
        canvas.alpha_composite(spr.im, (int(X - spr.w / 2), int(Y - spr.h)))
    return place


ORIGINAL = None
