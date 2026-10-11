"""Isometric buildings, drawn in code: timber-framed cottages with shingle or thatch roofs.

A house is a few flat faces in 3D (two walls, a gable, roof planes, a chimney). Each face is painted pixel by
pixel: every screen pixel is traced back to a point on the face, and the face's own pattern (plaster and beams,
windows, shingles, straw) decides its colour. So the patterns stay crisp at any angle.

Units: map pixels, 16 per cell. X runs along columns (down-right on screen), Y along rows (down-left), Z up.

    python art/iso_props.py <out.png> [rich|earthy|deep|bright]     a sheet of every building
"""
import math
import sys

from PIL import Image

from dualgrid import h
from sprites import OUTLINE, RGB, Sprite


def proj(X, Y, Z):
    return X - Y, (X + Y) / 2 - Z


class Canvas3D:
    """A sprite big enough for a building, with a 3D-to-screen origin."""

    def __init__(self, w, h, ox, oy):
        self.s = Sprite(w, h)
        self.ox, self.oy = ox, oy

    def face(self, o, a, b, colour, mask=None):
        """Paint the parallelogram o + s*a + t*b (s, t in [0, 1)); colour(s, t, su, tu) gets fractions and units."""
        (px, py), (ax, ay), (bx, by) = proj(*o), proj(*a), proj(*b)
        det = ax * by - ay * bx
        if abs(det) < 1e-6:
            return
        la, lb = math.sqrt(sum(v * v for v in a)), math.sqrt(sum(v * v for v in b))
        corners = [(px, py), (px + ax, py + ay), (px + bx, py + by), (px + ax + bx, py + ay + by)]
        x0, x1 = int(min(c[0] for c in corners)) - 1, int(max(c[0] for c in corners)) + 2
        y0, y1 = int(min(c[1] for c in corners)) - 1, int(max(c[1] for c in corners)) + 2
        for y in range(y0, y1):
            for x in range(x0, x1):
                dx, dy = x + 0.5 - px, y + 0.5 - py
                s = (dx * by - dy * bx) / det
                t = (ax * dy - ay * dx) / det
                if 0 <= s < 1 and 0 <= t < 1 and (mask is None or mask(s, t)):
                    c = colour(s, t, s * la, t * lb)
                    if c:
                        self.s.put(x + self.ox, y + self.oy, c)


# ---------- surface patterns ----------

BASE_LOOK = {"beam": "k3", "post_gap": 10, "braces": False, "stone_to": 3, "rise": 0.55, "dormer": False, "slate": False,
             "ground_shadow": False, "eave": 3, "windows": "today", "flower_box": True, "roof_steps": False}
LOOK = dict(BASE_LOOK)
# ground_shadow: a contact shadow along the wall feet and a short cast shadow off the shaded side (baked in, under the
# outline). eave: how far the shade under the roof reaches down the walls (map px). windows: "today" or "clean"
# (no glazing bars at this size: solid glass with a light streak in the top-left corner). flower_box: False puts a
# light sill under each window instead. roof_steps: shingles lighter near the ridge, darker to the eave, a lit
# ridge line, less moss.


def plaster_wall(width, height, windows, door=None, lit=True, storeys=1):
    """Cream plaster in a dark timber frame: corner posts, a sill beam, a beam per storey, braces, windows."""
    beam = LOOK["beam"]
    plaster, shade = ("c0", "c1") if lit else ("c1", "c2")
    stone, stone2 = ("s1", "s2") if lit else ("s2", "s3")
    stone_to = LOOK["stone_to"] if LOOK["stone_to"] > 3 else 3

    def col(s, t, su, tu):
        x, z = su, tu
        if z < stone_to and not any(wx - 1 <= x < wx + ww + 1 and wz - 1 <= z < wz + wh + 1 for (wx, wz, ww, wh) in windows) \
                and not (door and door[0] - 1 <= x < door[0] + door[1] + 1 and z < 3 + door[2] + 1):
            row = int(z / 3)
            bx = (x + (row % 2) * 2.5) % 5
            return "s3" if (z % 3 < 0.7 or bx < 0.7) and stone_to > 3 else stone if (int(x) // 4 + int(z)) % 2 else stone2   # stone footing
        clean = LOOK["windows"] == "clean"
        for (wx, wz, ww, wh) in windows:
            if wx - 1 <= x < wx + ww + 1 and wz - 1 <= z < wz + wh + 1:
                if not (wx <= x < wx + ww and wz <= z < wz + wh):
                    return "k3"                                                       # window frame
                if clean:                                                             # solid glass, a light streak
                    return "win2" if (x - wx) + (wz + wh - z) < 2.2 else "win"
                if abs(x - (wx + ww / 2)) < 0.6 or abs(z - (wz + wh / 2)) < 0.6:
                    return "k2"                                                       # glazing bars
                return "win2" if (x - wx) < ww * 0.45 and (z - wz) > wh * 0.5 else "win"
            if LOOK["flower_box"] and wz - 3 <= z < wz - 1 and wx - 1 <= x < wx + ww + 1:     # a flower box under it
                return "k1" if z < wz - 2 else ("fl_p" if int(x) % 3 == 0 else "fl_y" if int(x) % 3 == 1 else "t1")
            if clean and not LOOK["flower_box"] and wz - 2 <= z < wz - 1 and wx - 1.5 <= x < wx + ww + 1.5:
                return "c0" if lit else "c1"                                          # a light sill
        if door:
            dx_, dw, dh = door
            if dx_ - 1 <= x < dx_ + dw + 1 and 3 <= z < 3 + dh + 1:
                inner = dx_ <= x < dx_ + dw and z < 3 + dh - max(0, abs(x - dx_ - dw / 2) - dw / 2 + 1.5)
                if not inner:
                    return "k3"
                return "door2" if int(x - dx_) % 3 == 0 else "door"
        if x < 1.2 or x > width - 1.2:
            return beam                                                               # corner posts
        storey_h = (height - 3) / storeys
        for k in range(storeys + 1):
            if abs(z - (3 + k * storey_h)) < 0.8 or z > height - 1.2:
                return beam                                                           # sill and storey beams
        gap = LOOK["post_gap"]
        for bx in range(gap, int(width) - 4, gap):
            if abs(x - bx) < 0.7:
                return beam                                                           # posts
            if LOOK["braces"] and z > stone_to and bx - gap < x < bx:
                zz = (z - 3) % storey_h
                if abs((x - (bx - gap)) / gap * storey_h - zz) < 0.9:
                    return beam                                                       # diagonal braces
        if z > height - LOOK["eave"]:                                             # shade under the roof
            return ("c2" if lit else "c3") if LOOK["eave"] > 3 and z > height - LOOK["eave"] / 2 else shade
        return plaster
    return col


def shingles(length, slope, lit=True, roof="r"):
    """Roof shingles in staggered rows, lit along their top edge, a dark eave and verge."""
    c = [f"{roof}{i}" for i in range(4)]

    def col(s, t, su, tu):
        x, d = su, tu                       # x along the ridge, d down the slope from the ridge
        if d > slope - 1.5:
            return c[3]                                                               # eave edge
        if x < 1 or x > length - 1:
            return c[3]                                                               # verges
        row = int(d / 3)
        tx = (x + (row % 2) * 2.5) % 5
        ty = d % 3
        k = 1 if lit else 2
        if ty < 0.8:
            k = 0 if lit else 1
        if tx < 0.7 or ty > 2.2:
            k = min(3, k + 1)
        if LOOK["roof_steps"]:
            if d < 1.2:
                return c[0] if lit else c[1]                                          # the lit ridge line
            if d > slope * 0.62 and k < 3:
                k += 1                                                                # darker toward the eave
            if h("moss", int(x) // 2, row) < 0.008:
                return "moss" if lit else "moss2"
            return c[k]
        if h("moss", int(x) // 2, row) < 0.025:
            return "moss" if lit else "moss2"
        return c[k]
    return col


def thatch(length, slope, lit=True):
    """Straw: streaks down the slope, a thick rounded eave."""
    def col(s, t, su, tu):
        x, d = su, tu
        if d > slope - 2.5:
            return "y2" if lit else "y3"
        streak = h("straw", int(x), int(d / 2))
        base = ("y1", "y0", "y2") if lit else ("y2", "y1", "y3")
        return base[1] if streak < 0.25 else base[2] if streak > 0.85 else base[0]
    return col


def stone_block(lit):
    def col(s, t, su, tu):
        row = int(tu / 3)
        bx = (su + (row % 2) * 2) % 4
        return ("s3" if bx < 0.7 or tu % 3 < 0.7 else ("s0" if lit else "s1")) if tu < 999 else None
    return col


# ---------- a house ----------

def house(fw=2, fd=2, wall=22, roof="shingle", ridge="x", colour="r", chimney=True, storeys=1, seed=0):
    """A timber-framed house on a fw x fd cell footprint. ridge 'x': the roof ridge runs down-right, so the gable
    faces right; 'y': it runs down-left and the gable faces left. Returns (sprite, anchor, footprint)."""
    X1, Y1 = fw * 16, fd * 16
    over = 3                                             # roof overhang
    span = (Y1 if ridge == "x" else X1) + 2 * over
    rise = span * (0.62 if roof == "thatch" else LOOK["rise"])
    top = wall + rise
    W = X1 + Y1 + 2 * over + 8
    H = int((X1 + Y1) / 2 + top + 14)
    cv = Canvas3D(W, H, Y1 + over + 4, int(top) + 8)

    # walls: front-left (+Y face, lit) and front-right (+X face, shaded)
    win = lambda length: [(x, 8 + (wall - 3) * 0.15, 5, 6) for x in range(5, int(length) - 6, 11)]
    door_on_left = ridge == "x"
    left_len, right_len = X1, Y1
    left_windows = win(left_len)
    door = None
    if door_on_left:
        door = (left_len / 2 - 3, 6, 11)
        left_windows = [w for w in left_windows if abs(w[0] + 2.5 - left_len / 2) > 6]
    right_windows = win(right_len)
    if storeys > 1:
        left_windows += [(x, wall * 0.62, 5, 6) for x in range(5, int(left_len) - 6, 11)]
        right_windows += [(x, wall * 0.62, 5, 6) for x in range(5, int(right_len) - 6, 11)]
    right_door = None if door_on_left else (right_len / 2 - 3, 6, 11)
    if right_door:
        right_windows = [w for w in right_windows if abs(w[0] + 2.5 - right_len / 2) > 6]
    cv.face((0, Y1, 0), (X1, 0, 0), (0, 0, wall), plaster_wall(left_len, wall, left_windows, door, True, storeys))
    cv.face((X1, Y1, 0), (0, -Y1, 0), (0, 0, wall), plaster_wall(right_len, wall, right_windows, right_door, False, storeys))

    colour = "b" if LOOK["slate"] and roof != "thatch" else colour
    pattern = (lambda L, S, lit: thatch(L, S, lit)) if roof == "thatch" else (lambda L, S, lit: shingles(L, S, lit, colour))
    if ridge == "x":
        # gable on the right wall: a triangle of plaster with a beam along the roof line
        mid = Y1 / 2
        cv.face((X1, Y1, wall), (0, -Y1, 0), (0, 0, rise - 1),
                lambda s, t, su, tu: ("k3" if abs(su - (Y1 - su)) < 1.2 or tu < 1 else "c2"),
                mask=lambda s, t: t * (rise - 1) <= min(s, 1 - s) * 2 * (rise - 1) * (Y1 / 2) / (Y1 / 2))
        L = X1 + 2 * over
        slope_len = math.hypot(mid + over, rise)
        # the front-left roof plane (+Y side), from the ridge down to the eave
        cv.face((-over, mid, top), (L, 0, 0), (0, mid + over, -rise), pattern(L, slope_len, True))
        if LOOK["dormer"]:
            zb = wall + rise * 0.3
            yb = mid + (top - zb) / rise * (mid + over)
            for xd in [X1 * 0.3] + ([X1 * 0.68] if X1 > 40 else []):
                cv.face((xd, yb, zb), (8, 0, 0), (0, 0, 8), lambda s, t, su, tu: "k3" if su < 1 or su > 7 or tu < 1 else
                        ("win2" if su < 4 and tu > 4 else "win") if 2 < su < 6 and 2 < tu < 7 else "c1")
                cv.face((xd - 1, yb + 2, zb + 8), (10, 0, 0), (0, -6, 4), pattern(10, 7, True))
        # a sliver of the back plane shows above the ridge line on the right
        cv.face((-over, mid, top), (L, 0, 0), (0, -(mid + over), -rise), pattern(L, slope_len, False),
                mask=lambda s, t: t < 0.08)
    else:
        mid = X1 / 2
        cv.face((0, Y1, wall), (X1, 0, 0), (0, 0, rise - 1),
                lambda s, t, su, tu: ("k3" if tu < 1 else "c1"),
                mask=lambda s, t: t <= min(s, 1 - s) * 2)
        L = Y1 + 2 * over
        slope_len = math.hypot(mid + over, rise)
        cv.face((mid, Y1 + over, top), (0, -L, 0), (mid + over, 0, -rise), pattern(L, slope_len, False))
        cv.face((mid, Y1 + over, top), (0, -L, 0), (-(mid + over), 0, -rise), pattern(L, slope_len, True), mask=lambda s, t: t < 0.08)

    if chimney:
        cx, cy = (X1 * 0.72, Y1 * 0.35) if ridge == "x" else (X1 * 0.35, Y1 * 0.72)
        cz0, cz1 = wall + rise * 0.45, top + 6
        cw = 5
        cv.face((cx, cy + cw, cz0), (cw, 0, 0), (0, 0, cz1 - cz0), stone_block(True))
        cv.face((cx + cw, cy + cw, cz0), (0, -cw, 0), (0, 0, cz1 - cz0), stone_block(False))
        cv.face((cx, cy, cz1), (cw, 0, 0), (0, cw, 0), lambda s, t, su, tu: "out" if 0.2 < s < 0.8 and 0.2 < t < 0.8 else "s2")

    smoke = None
    if chimney:
        tx, ty = proj(cx + cw / 2, cy + cw / 2, cz1)
        smoke = (tx + cv.ox + 2, ty + cv.oy + 2)
    spr = cv.s
    spr.outline()
    # where the footprint's front (south) corner lands in the sprite; props stand at their front cell's centre
    sx_, sy_ = proj(X1, Y1, 0)
    ax, ay = sx_ + cv.ox + 1, sy_ + cv.oy + 1 - 8
    out = Sprite(spr.w + 2, spr.h + 2)
    out.im.paste(spr.im, (1, 1))
    out.px = out.im.load()
    if OUTLINE["double"]:
        out.outline()
    if LOOK["ground_shadow"]:
        out = with_ground_shadow(out, X1, Y1, cv.ox + 1, cv.oy + 1)
    out.anchor = (round(ax), round(ay))
    out.smoke = (round(smoke[0]), round(smoke[1])) if smoke else None
    return out, out.anchor, (fw, fd)


def with_ground_shadow(spr, X1, Y1, ox, oy):
    """The house over its ground shadow: a 2 px contact band along both front walls' feet and a 4 px cast shadow
    off the shaded (+X) side, away from the light. Pixel-exact, in `shade`."""
    sh = Image.new("RGBA", (spr.w, spr.h), (0, 0, 0, 0))
    px, col = sh.load(), RGB["shade"][:3]
    parts = [((X1, 0, 0), (4, 0, 0), (0, Y1 + 2, 0), 70),        # cast, off the right wall
             ((0, Y1, 0), (X1 + 2, 0, 0), (0, 2, 0), 60)]          # contact, in front of the left wall
    for (o, a, b, alpha) in parts:
        (pxo, pyo), (ax, ay), (bx, by) = proj(*o), proj(*a), proj(*b)
        det = ax * by - ay * bx
        for y in range(spr.h):
            for x in range(spr.w):
                dx, dy = x - ox + 0.5 - pxo, y - oy + 0.5 - pyo
                s, t = (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det
                if 0 <= s < 1 and 0 <= t < 1:
                    px[x, y] = col + (max(alpha, px[x, y][3]),)
    sh.alpha_composite(spr.im)
    out = Sprite(spr.w, spr.h)
    out.im, out.px = sh, sh.load()
    return out


HOUSES = {
    "cottage-red": dict(fw=2, fd=2, roof="shingle", ridge="x", colour="r"),
    "cottage-brown": dict(fw=2, fd=2, roof="shingle", ridge="y", colour="r", chimney=False),
    "thatch-house": dict(fw=3, fd=2, roof="thatch", ridge="x"),
    "townhouse": dict(fw=2, fd=2, wall=34, roof="shingle", ridge="y", colour="r", storeys=2),
    "longhouse": dict(fw=3, fd=2, roof="shingle", ridge="x", colour="b"),
}


LOOKS = {
    "cosy": {},
    "storybook": {"beam": "out", "post_gap": 7, "braces": True, "rise": 0.78, "dormer": True},
    "stone": {"stone_to": 12, "post_gap": 8, "slate": True, "rise": 0.6},
}


def use_look(name):
    LOOK.clear()
    LOOK.update(BASE_LOOK, **LOOKS[name])


if __name__ == "__main__":
    import palettes
    palettes.use(sys.argv[2] if len(sys.argv) > 2 else palettes.DEFAULT)
    use_look(sys.argv[3] if len(sys.argv) > 3 else "cosy")
    sprites = [house(**kw)[0] for kw in HOUSES.values()]
    W = sum(s.w for s in sprites) + 12 * len(sprites)
    H = max(s.h for s in sprites)
    sheet = Image.new("RGBA", (W, H), (142, 164, 63, 255))
    x = 0
    for s in sprites:
        sheet.alpha_composite(s.im, (x, H - s.h))
        x += s.w + 12
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(sys.argv[1])
    print("wrote", sys.argv[1])
