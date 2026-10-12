"""Landmarks: objects you place one at a time (not in crowds like trees), each with a twin in every theme.

    landmarks() -> {name: Sprite}      tank, pylon, station, street-pole, monument, mast

Cottage draws the twins picked in TWINS (two candidates each, from the twins builder); a theme can swap the whole
set (theme_cyber.apply sets OVERRIDE: tank -> storage tank, pylon -> power pylon, station -> transformer station,
street-pole -> LED street pole, monument -> ring monument, mast -> radio mast). Plain props: feet at the bottom
middle, a ground shadow.
"""
import math

from dualgrid import h
from sprites import Sprite, rng, tight

NAMES = ["tank", "pylon", "station", "street-pole", "monument", "mast"]
TWINS = {"tank": "water-tower", "pylon": "windmill", "station": "shed", "street-pole": "lantern-post",
         "monument": "standing-stone", "mast": "bell-tower"}
OVERRIDE = None          # a theme's {name: () -> Sprite}


def cylinder(s, cx, base, r, hgt, ramp, top=None):
    """An upright cylinder, feet at (cx, base): ramp (light, mid, dark) lit from the left; top colour pair."""
    ry = r / 2
    for y in range(int(base - hgt - ry) - 1, int(base + ry) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dx = x + 0.5 - cx
            if abs(dx) > r:
                continue
            yb = ry * math.sqrt(max(0, 1 - (dx / r) ** 2))
            if base - hgt - yb <= y + 0.5 <= base + yb:
                f = dx / r
                s.put(x, y, ramp[0] if f < -0.4 else ramp[2] if f > 0.45 else ramp[1])
    if top:
        for y in range(int(base - hgt - ry) - 1, int(base - hgt + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                dx, dy = x + 0.5 - cx, (y + 0.5 - (base - hgt)) / ry
                if (dx / r) ** 2 + dy ** 2 <= 1:
                    s.put(x, y, top[0] if dx < 0 else top[1])


def cone(s, cx, base, r, hgt, ramp):
    """A cone roof standing on (cx, base), lit from the left."""
    for y in range(int(base - hgt), int(base + r / 2) + 1):
        f = (y - (base - hgt)) / hgt
        half = r * min(1, f)
        for x in range(int(cx - half), int(cx + half) + 1):
            if y > base and abs(x + 0.5 - cx) / r > math.sqrt(max(0, 1 - ((y - base) / (r / 2)) ** 2)):
                continue
            d = (x + 0.5 - cx) / max(1, half)
            s.put(x, y, ramp[0] if d < -0.3 else ramp[2] if d > 0.4 else ramp[1])


def line(s, x0, y0, x1, y1, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for k in range(n):
        t = k / max(1, n - 1)
        s.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)


def box(w, d, hgt, wall, roof=None, rise=6, door=None, extra=None):
    """A small iso building with a pitched roof (ridge along X), using the house face painter."""
    from iso_props import Canvas3D, proj
    over = 1.5
    top = hgt + rise
    cv = Canvas3D(int(w + d + 12), int((w + d) / 2 + top + 14), int(d + over + 5), int(top + 8))
    cv.face((0, d, 0), (w, 0, 0), (0, 0, hgt), wall(True, w, door))
    cv.face((w, d, 0), (0, -d, 0), (0, 0, hgt), wall(False, d, None))
    mid = d / 2
    if roof:
        cv.face((w, d, hgt), (0, -d, 0), (0, 0, rise), lambda s, t, su, tu: "k2" if tu > 0.5 else "k3",
                mask=lambda s, t: t <= min(s, 1 - s) * 2)                 # the gable
        L = w + 2 * over
        slope = math.hypot(mid + over, rise)
        cv.face((-over, mid, top), (L, 0, 0), (0, mid + over, -rise), roof(L, slope, True))
        cv.face((-over, mid, top), (L, 0, 0), (0, -(mid + over), -rise), roof(L, slope, False), mask=lambda s, t: t < 0.1)
    if extra:
        extra(cv)
    s = cv.s
    x0, y0, x1, y1 = s.im.getbbox()
    out = Sprite(x1 - x0, y1 - y0)
    out.im.paste(s.im.crop((x0, y0, x1, y1)), (0, 0))
    out.px = out.im.load()
    return tight(out).outline()


def planks(lit, length, door):
    def col(s, t, su, tu):
        if door and door[0] <= su < door[0] + door[1] and tu < door[2]:
            return "k3" if su < door[0] + 0.8 or su > door[0] + door[1] - 0.8 or tu > door[2] - 0.8 else "door"
        k = ("k1", "k2") if lit else ("k2", "k3")
        return k[1] if int(su) % 3 == 0 else k[0]
    return col


# ---------- tank ----------

def water_tower():
    """A wooden tank with iron hoops on four legs, a pointed roof."""
    s = Sprite(32, 64)
    cx, base = 16, 60
    for dx in (-8, 8):                                               # legs, braced
        line(s, cx + dx, base, cx + dx * 0.75, base - 24, "k2" if dx < 0 else "k3")
    for dx in (-4, 4):
        line(s, cx + dx, base - 1, cx + dx * 0.8, base - 24, "k3")
    line(s, cx - 8, base - 6, cx + 6, base - 18, "k3"); line(s, cx + 8, base - 6, cx - 6, base - 18, "k3")
    cylinder(s, cx, base - 24, 9, 16, ("k1", "k2", "k3"), ("k0", "k1"))
    for k in (3, 9, 14):                                             # hoops
        for x in range(cx - 9, cx + 10):
            dx = x + 0.5 - cx
            s.put(x, int(base - 24 - k + 4.5 * math.sqrt(max(0, 1 - (dx / 9) ** 2))), "s2")
    cone(s, cx, base - 40, 11, 12, ("r0", "r1", "r2"))
    return tight(s).outline()


def grain_silo():
    """A tall stone silo with a domed roof and a little hatch."""
    s = Sprite(30, 64)
    cx, base = 15, 60
    cylinder(s, cx, base, 10, 38, ("c0", "c1", "c2"))
    for k in range(6, 38, 6):                                        # courses of stone
        for x in range(cx - 10, cx + 11):
            dx = x + 0.5 - cx
            if h("course", x, k) < 0.8:
                s.put(x, int(base - k + 5 * math.sqrt(max(0, 1 - (dx / 10) ** 2))), "c2" if dx < 4 else "c3")
    for j in range(7):                                               # the dome
        r = 10 * math.sqrt(1 - (j / 7) ** 2)
        for x in range(int(cx - r), int(cx + r) + 1):
            s.put(x, base - 38 - j, "r0" if x < cx - r / 3 else "r2" if x > cx + r / 3 else "r1")
    for y in range(base - 30, base - 24):
        for x in range(cx - 3, cx):
            s.put(x, y, "k3" if y == base - 30 else "k2")
    return tight(s).outline()


# ---------- pylon ----------

def windmill():
    """A plastered tower mill, a cap, four lattice sails."""
    s = Sprite(48, 70)
    cx, base = 24, 66
    for y in range(base - 34, base + 1):                             # the tapering tower
        f = (base - y) / 34
        half = 8 - f * 3
        for x in range(int(cx - half), int(cx + half) + 1):
            d = (x + 0.5 - cx) / half
            s.put(x, y, "c0" if d < -0.3 else "c2" if d > 0.45 else "c1")
    for y in range(base - 7, base + 1):                              # the door
        s.put(cx - 1, y, "k3"); s.put(cx, y, "door"); s.put(cx + 1, y, "door2")
    cone(s, cx, base - 34, 7, 7, ("r0", "r1", "r2"))
    hx, hy = cx - 2, base - 32                                       # the hub, sails crossing it
    for a in (0.6, 0.6 + math.pi / 2, 0.6 + math.pi, 0.6 + 3 * math.pi / 2):
        ex, ey = hx + math.cos(a) * 20, hy + math.sin(a) * 20
        line(s, hx, hy, ex, ey, "k3")
        for k in range(6, 20, 2):                                    # the lattice beside each arm
            px_, py_ = hx + math.cos(a) * k, hy + math.sin(a) * k
            qx, qy = px_ + math.cos(a + math.pi / 2) * 3.5, py_ + math.sin(a + math.pi / 2) * 3.5
            line(s, px_, py_, qx, qy, "c0" if k % 4 else "k2")
    s.put(hx, hy, "s2")
    return tight(s).outline()


def windpump():
    """A farm windpump: a slim lattice tower, a wheel of blades, a tail vane."""
    s = Sprite(36, 66)
    cx, base = 18, 62
    for side in (-1, 1):
        line(s, cx + side * 7, base, cx + side * 2, base - 40, "s2" if side < 0 else "s3")
    for k in range(4, 40, 6):
        f = k / 40
        half = 7 - f * 5
        line(s, cx - half, base - k, cx + half, base - k - 6, "s3")
    hx, hy = cx, base - 44
    for k in range(12):                                              # the wheel
        a = k / 12 * math.pi * 2
        line(s, hx + math.cos(a) * 2, hy + math.sin(a) * 2, hx + math.cos(a) * 9, hy + math.sin(a) * 9,
             "s0" if math.cos(a) < 0 else "s1")
    line(s, hx, hy, hx + 13, hy + 1, "s2")                           # the tail
    for j in range(-3, 4):
        s.put(hx + 13, hy + j, "r1"); s.put(hx + 14, hy + j, "r2")
    return tight(s).outline()


# ---------- station ----------

def shed():
    return box(14, 11, 11, lambda lit, L, door: planks(lit, L, door), roof=lambda L, S, lit: shingle_roof(L, S, lit),
               door=(4, 5, 9))


def woodshed():
    """An open-fronted woodshed, logs stacked inside."""
    def wall(lit, L, door):
        def col(s, t, su, tu):
            if lit and 1.5 < su < L - 1.5 and tu < 9:                  # the open front: stacked log ends
                r_ = int(tu / 2.2)
                cx_ = (su + (r_ % 2) * 1.1) % 2.2
                return "k0" if cx_ < 1.1 and (tu % 2.2) < 1.4 else "k3"
            return planks(lit, L, None)(s, t, su, tu)
        return col
    return box(16, 10, 10, wall, roof=lambda L, S, lit: shingle_roof(L, S, lit, "b"))


def shingle_roof(L, S, lit, colour="r"):
    from iso_props import shingles
    return shingles(L, S, lit, colour)


# ---------- street pole ----------

def lantern_post():
    """A wooden post with a lantern on top, glowing."""
    s = Sprite(12, 34)
    cx, base = 6, 32
    for y in range(base - 22, base + 1):
        s.put(cx - 1, y, "k1"); s.put(cx, y, "k2")
    for y in range(base - 28, base - 22):                           # the lantern
        for x in range(cx - 2, cx + 2):
            edge = x in (cx - 2, cx + 1) or y in (base - 28, base - 23)
            s.put(x, y, "out" if edge else "light")
    s.put(cx - 1, base - 29, "out"); s.put(cx, base - 29, "out")
    return tight(s).outline()


def hanging_lantern():
    """A post with an arm, a lantern hanging from it."""
    s = Sprite(18, 36)
    cx, base = 5, 34
    for y in range(base - 28, base + 1):
        s.put(cx - 1, y, "k1"); s.put(cx, y, "k2")
    for x in range(cx, cx + 9):
        s.put(x, base - 28, "k2")
    line(s, cx + 1, base - 24, cx + 4, base - 27, "k3")             # a brace
    s.put(cx + 7, base - 27, "out")
    for y in range(base - 26, base - 20):
        for x in range(cx + 5, cx + 10):
            edge = x in (cx + 5, cx + 9) or y in (base - 26, base - 21)
            s.put(x, y, "out" if edge else "light")
    return tight(s).outline()


# ---------- monument ----------

def standing_stone():
    """A tall standing stone, leaning a little, moss on its foot."""
    r = rng("stone", "standing")
    s = Sprite(20, 36)
    cx, base = 10, 33
    for y in range(base - 28, base + 1):
        f = (base - y) / 28
        half = 4.5 - f * 1.5 + (0.6 if y > base - 4 else 0)
        x0 = cx + f * 2
        for x in range(int(x0 - half), int(x0 + half) + 1):
            d = (x + 0.5 - x0) / half
            c = "s0" if d < -0.35 else "s2" if d > 0.4 else "s1"
            if y > base - 6 and h("moss", x, y) < 0.4:
                c = "moss" if d < 0.3 else "moss2"
            s.put(x, y, c)
    for _ in range(3):                                               # weathering
        s.put(int(cx + r.uniform(-2, 2)), int(base - r.uniform(8, 24)), "s3")
    return tight(s).outline()


def market_cross():
    """A stone cross on three steps, where a village meets."""
    s = Sprite(26, 40)
    cx, base = 13, 37
    for k, half in enumerate((11, 8, 5)):                            # the steps, seen at an angle
        y0 = base - k * 3
        for y in range(y0 - 3, y0 + 1):
            for x in range(cx - half, cx + half + 1):
                top = y == y0 - 3
                s.put(x, y, "s0" if top else ("s1" if x < cx else "s2"))
    for y in range(base - 27, base - 9):                             # the shaft
        s.put(cx - 1, y, "s0"); s.put(cx, y, "s1"); s.put(cx + 1, y, "s2")
    for x in range(cx - 4, cx + 5):                                  # the arms
        s.put(x, base - 23, "s1"); s.put(x, base - 22, "s2")
    return tight(s).outline()


# ---------- mast ----------

def bell_tower():
    """A little timber bell tower with a pointed roof and a bell."""
    def extra(cv):
        from iso_props import proj
        x, y = proj(4, 8, 19)
        for j in range(4):                                            # the bell, in the open top
            for i in range(-2 - j // 2, 3 + j // 2):
                cv.s.put(int(x + cv.ox + i), int(y + cv.oy + j), "y1" if i < 0 else "y2")

    def wall(lit, L, door):
        def col(s, t, su, tu):
            if tu > 16 and 1.2 < su < L - 1.2 and tu < 24:
                return None                                           # the open belfry
            return planks(lit, L, door)(s, t, su, tu)
        return col
    return box(9, 9, 26, wall, roof=lambda L, S, lit: shingle_roof(L, S, lit), rise=11, extra=extra)


def maypole():
    """A tall pole with a flower crown and ribbons."""
    s = Sprite(26, 56)
    cx, base = 13, 54
    for y in range(base - 46, base + 1):
        s.put(cx, y, "k1"); s.put(cx + 1, y, "k2")
    cols = ["fl_p", "fl_y", "b1", "fl_w", "r1"]
    for k in range(5):                                               # ribbons, out to the ground
        a = -1 + k * 0.5
        line(s, cx, base - 44, cx + a * 11, base - 2 - abs(a) * 3, cols[k])
    for i in range(-3, 4):                                           # the flower crown
        s.put(cx + i, base - 46, ("fl_p", "t1", "fl_y", "t1")[(i + 3) % 4])
    return tight(s).outline()


COTTAGE = {"water-tower": water_tower, "grain-silo": grain_silo, "windmill": windmill, "windpump": windpump,
           "shed": shed, "woodshed": woodshed, "lantern-post": lantern_post, "hanging-lantern": hanging_lantern,
           "standing-stone": standing_stone, "market-cross": market_cross, "bell-tower": bell_tower, "maypole": maypole}
CANDIDATES = {"tank": ["water-tower", "grain-silo"], "pylon": ["windmill", "windpump"], "station": ["shed", "woodshed"],
              "street-pole": ["lantern-post", "hanging-lantern"], "monument": ["standing-stone", "market-cross"],
              "mast": ["bell-tower", "maypole"]}


def landmarks():
    if OVERRIDE:
        return {n: make() for n, make in OVERRIDE.items()}
    import iso_props
    from iso_tiles import LOOK
    iso_props.use_look(LOOK)                                         # roofs as on the houses
    return {n: COTTAGE[TWINS[n]]() for n in NAMES}
