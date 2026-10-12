"""Neon city twins of the street and market things (art/iso_market.py): same names, footprints and anchors, so a
map places them the same way in either theme. theme_cyber.apply swaps them in per CYBER switch.

    kiosk (stalls), neon_lamp (lamp-iso, lamp-sign), steel_bench, drum (barrel-iso), cargo / cargo_stack (crates),
    screen (chalkboard), vending (flower-cart), vent (well), cargo_box (crate)
"""
import math

from dualgrid import h
from iso_market import box, finish, produce
from iso_props import Canvas3D, proj
from sprites import Sprite, tight

STALL_NEON = {"red": "neon_a", "green": "neon_b", "purple": "jf1", "orange": "neon_c"}


def metal(lit, dark=False):
    def col(s, t, su, tu):
        base = ("vh1", "vh2") if dark else ("s1", "s2") if lit else ("s2", "s3")
        return base[1] if int(su) % 4 == 0 else base[0]
    return col


def mbox(cv, x, y, z, w, d, hgt, top=None, strip=None, dark=False):
    """A metal box; strip: a neon line along the top of its lit face."""
    lit = metal(True, dark)
    face = (lambda s, t, su, tu: strip if tu > hgt - 1 else lit(s, t, su, tu)) if strip else lit
    cv.face((x, y + d, z), (w, 0, 0), (0, 0, hgt), face)
    cv.face((x + w, y + d, z), (0, -d, 0), (0, 0, hgt), metal(False, dark))
    cv.face((x, y, z + hgt), (w, 0, 0), (0, d, 0), top or (lambda s, t, su, tu: "s0"))


def kiosk(colour="red", goods=("tomatoes", "cabbages", "carrots")):
    """A neon kiosk on a 2x1 footprint: a metal counter with an LED strip, glowing goods, a flat canopy with a lit
    edge, a holo menu above."""
    neon = STALL_NEON[colour]
    cv = Canvas3D(64, 70, 22, 46)
    mbox(cv, 2, 4, 0, 26, 9, 8, strip=neon, dark=True)
    for k, kind in enumerate(goods):
        cv.face((3 + k * 8.4, 5, 8), (7.5, 0, 0), (0, 7, 0), produce(kind))
    for (px_, py_) in ((2, 4), (28, 4), (2, 13), (28, 13)):
        cv.face((px_, py_, 0), (1, 0, 0), (0, 0, 21), lambda *a: "s2")
    cv.face((0, 2, 22), (31, 0, 0), (0, 14, 0),                          # the canopy, its front and side edges lit
            lambda s, t, su, tu: neon if tu > 13 or su < 1 else "vh2")
    cv.face((0, 16, 22), (31, 0, 0), (0, 0, -1.5), lambda *a: neon)
    cv.face((8, 9, 23), (14, 0, 0), (0, 0, 8),                           # the holo menu
            lambda s, t, su, tu: neon if su < 1 or su > 13 or tu < 1 or tu > 7 else
            ("fl_w" if int(tu) % 2 == 0 and 2 < su < 12 and h("menu", colour, int(su / 2), int(tu)) < 0.75 else "vh2"))
    return finish(cv, 2, 1)


def neon_lamp(sign=True):
    """A slim LED street lamp; with a sign, a holo panel hangs from it."""
    s = Sprite(22, 40)
    s.rect(9, 6, 2, 33, "vh1"); s.rect(8, 37, 4, 2, "vh2")
    s.rect(9, 5, 8, 1, "vh1")                                            # the arm
    s.rect(13, 6, 5, 2, "neon_b"); s.rect(14, 6, 3, 1, "fl_w")          # the LED bar
    if sign:
        s.rect(11, 15, 7, 6, "jf1"); s.rect(12, 16, 5, 4, "vh2")
        s.rect(13, 17, 3, 1, "fl_w"); s.rect(13, 19, 2, 1, "neon_a")
    out = Sprite(24, 42)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (11, 40)
    return out


def steel_bench():
    cv = Canvas3D(36, 24, 16, 14)
    mbox(cv, 1, 6, 4, 18, 4, 1.5, top=lambda s, t, su, tu: "s0" if int(su) % 3 else "s1")
    for x in (2, 16):
        cv.face((x, 10, 0), (1.5, 0, 0), (0, 0, 4), lambda *a: "vh1")
    cv.face((3, 10, 3.5), (14, 0, 0), (0, 0, 0.6), lambda *a: "neon_b")  # the LED strip under the seat
    cv.face((1, 6, 5.5), (18, 0, 0), (0, 0, 5), lambda s, t, su, tu: "s1" if 1 < tu < 4 else None)
    return finish(cv, 1, 1)


def drum():
    """A chemical drum: steel, a hazard band, a glowing cap."""
    from landmarks import cylinder
    s = Sprite(12, 15)
    cylinder(s, 6, 13, 5, 10, ("s0", "s1", "s2"), ("s1", "s2"))
    for x in range(1, 11):                                               # the hazard band
        for y in (7, 8):
            s.put(x, y + (1 if abs(x - 6) < 3 else 0), "neon_c" if (x + y) // 2 % 2 else "out")
    s.put(7, 2, "neon_b"); s.put(8, 2, "neon_b")
    out = Sprite(14, 17)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (7, 13)
    return out


def ribbed(colour):
    def col(s, t, su, tu):
        return colour[1] if int(su) % 2 == 0 else colour[0]
    return col


def cargo(kind="tomatoes"):
    """A plastic cargo crate of glowing goods."""
    cv = Canvas3D(28, 24, 14, 12)
    cv.face((2, 10, 0), (9, 0, 0), (0, 0, 5), ribbed(("b1", "b2")))
    cv.face((11, 10, 0), (0, -7, 0), (0, 0, 5), ribbed(("b2", "b3")))
    cv.face((2, 3, 5), (9, 0, 0), (0, 7, 0), produce(kind))
    return finish(cv, 1, 1)


def cargo_stack(kinds=("apples", "cabbages")):
    cv = Canvas3D(30, 30, 15, 18)
    for (x, y, z, w, d, hh, kind, c) in ((1, 3, 0, 9, 7, 5, kinds[0], ("b1", "b2")), (3, 1, 5, 8, 6, 4, kinds[1], ("r1", "r2"))):
        cv.face((x, y + d, z), (w, 0, 0), (0, 0, hh), ribbed(c))
        cv.face((x + w, y + d, z), (0, -d, 0), (0, 0, hh), ribbed((c[1], c[1])))
        cv.face((x, y, z + hh), (w, 0, 0), (0, d, 0), produce(kind))
    return finish(cv, 1, 1)


def cargo_box():
    """An empty cargo crate (the plain `crate`)."""
    cv = Canvas3D(24, 22, 12, 12)
    cv.face((1, 9, 0), (9, 0, 0), (0, 0, 7), ribbed(("b1", "b2")))
    cv.face((10, 9, 0), (0, -8, 0), (0, 0, 7), ribbed(("b2", "b3")))
    cv.face((1, 1, 7), (9, 0, 0), (0, 8, 0), lambda s, t, su, tu: "b0" if 1 < su < 8 and 1 < tu < 7 else "b1")
    s = cv.s
    x0, y0, x1, y1 = s.im.getbbox()
    out = Sprite(x1 - x0, y1 - y0)
    out.im.paste(s.im.crop((x0, y0, x1, y1)), (0, 0)); out.px = out.im.load()
    return tight(out).outline()


def screen():
    """A digital screen on a stand: neon text on black."""
    s = Sprite(14, 18)
    s.rect(1, 1, 12, 10, "vh1"); s.rect(2, 2, 10, 8, "vh2")
    for (x, y, w, c) in ((3, 3, 6, "neon_b"), (3, 5, 4, "neon_a"), (3, 7, 7, "fl_w")):
        s.rect(x, y, w, 1, c)
    s.rect(6, 11, 2, 6, "vh1"); s.rect(4, 16, 6, 1, "vh2")
    out = Sprite(16, 20)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (8, 18)
    return out


def vending():
    """A vending machine: a lit front of glowing rows, a dark side."""
    cv = Canvas3D(34, 44, 16, 32)

    def front(s, t, su, tu):
        if su < 1 or su > 9 or tu < 1.5 or tu > 18:
            return "vh1"
        if su > 7:
            return "neon_a" if 10 < tu < 13 else "vh2"                  # the coin panel
        row = int((tu - 2) / 3.2)
        return ("neon_b", "fl_p", "neon_c", "fl_w")[row % 4] if (tu - 2) % 3.2 < 1.6 and int(su) % 2 else "w2"
    cv.face((2, 10, 0), (10, 0, 0), (0, 0, 20), front)
    cv.face((12, 10, 0), (0, -7, 0), (0, 0, 20), lambda *a: "vh2")
    cv.face((2, 3, 20), (10, 0, 0), (0, 7, 0), lambda *a: "vh0")
    return finish(cv, 1, 1)


def vent():
    """A steam vent: a round grate with a glowing rim, steam rising (a plain prop, like the well)."""
    from PIL import Image
    s = Sprite(24, 30)
    cx, cy = 12, 25
    for y in range(s.h):
        for x in range(s.w):
            d = ((x + 0.5 - cx) / 9) ** 2 + ((y + 0.5 - cy) / 4.5) ** 2
            if d <= 1:
                rim = d > 0.72
                s.put(x, y, ("neon_c" if y + 0.5 > cy else "s1") if rim else ("vh2" if (x + y) % 2 else "s3"))
    s = tight(s).outline()
    steam = Image.new("RGBA", s.im.size, (0, 0, 0, 0))
    sp = steam.load()
    for k, (ox, oy, r) in enumerate(((13, 18, 4.5), (11, 12, 4), (14, 6, 3.2))):   # puffs, fading upward
        for y in range(s.h):
            for x in range(s.w):
                if (x + 0.5 - ox) ** 2 + (y + 0.5 - oy) ** 2 <= r * r and not s.px[x, y][3]:
                    sp[x, y] = (226, 232, 240, 120 - k * 30)
    s.im.alpha_composite(steam)
    s.px = s.im.load()
    return s


def market(switch):
    """The overrides for iso_market.MARKET / PLAIN, per CYBER switch (each "neon" or "recolour")."""
    m, plain = {}, {}
    if switch.get("stalls") == "neon":
        m.update({"stall-red": lambda: kiosk("red", ("tomatoes", "apples", "lemons")),
                  "stall-green": lambda: kiosk("green", ("cabbages", "carrots", "lemons")),
                  "stall-purple": lambda: kiosk("purple", ("plums", "apples", "cabbages")),
                  "stall-orange": lambda: kiosk("orange", ("carrots", "lemons", "tomatoes"))})
    if switch.get("lamps") == "neon":
        m.update({"lamp-sign": neon_lamp, "lamp-iso": lambda: neon_lamp(False)})
    if switch.get("bench") == "neon":
        m["bench-iso"] = steel_bench
    if switch.get("barrel") == "neon":
        m["barrel-iso"] = drum
    if switch.get("crates") == "neon":
        m.update({"crate-tomatoes": lambda: cargo("tomatoes"), "crate-cabbages": lambda: cargo("cabbages"),
                  "crate-carrots": lambda: cargo("carrots"), "crates": cargo_stack})
        plain["crate"] = cargo_box
    if switch.get("board") == "neon":
        m["chalkboard"] = screen
    if switch.get("cart") == "neon":
        m["flower-cart"] = vending
    if switch.get("well") == "neon":
        plain["well"] = vent
    return m, plain


# ---------- ground pieces (art/iso_ground.py): fences, gates, bridge rails, stairs, the deck, flower beds, crops ----------

def fence_neon(conn, style="rail"):
    """Metal posts; toward each joined neighbour a glowing top rail and a plain lower one (style "rail"), or a glass
    panel with a neon top edge (style "glass")."""
    from iso_ground import E_, N_, S_, W_, finish_cell
    cv = Canvas3D(40, 34, 20, 22)
    c = 8
    glass = style == "glass"
    for bit, (dx, dy) in ((N_, (0, -1)), (W_, (-1, 0)), (E_, (1, 0)), (S_, (0, 1))):
        if not conn & bit:
            continue
        a = (dx * 8.5, 0, 0) if dx else (0, dy * 8.5, 0)
        if glass:
            cv.face((c, c, 1), a, (0, 0, 7.5), lambda s, t, su, tu: "neon_b" if tu > 6.6 else (120, 220, 235, 90))
        else:
            cv.face((c, c, 3.5), a, (0, 0, 1.4), lambda *a_: "s1")
            cv.face((c, c, 7.5), a, (0, 0, 1.4), lambda *a_: "neon_b")
    cv.face((c - 1, c + 1, 0), (2, 0, 0), (0, 0, 10), lambda *a: "s1")
    cv.face((c + 1, c + 1, 0), (0, -2, 0), (0, 0, 10), lambda *a: "s2")
    cv.face((c - 1, c - 1, 10), (2, 0, 0), (0, 2, 0), lambda *a: "neon_b")
    return finish_cell(cv)


def gate_neon(axis):
    """A barrier between two posts: a hazard-striped bar."""
    from iso_ground import finish_cell
    cv = Canvas3D(40, 34, 20, 22)
    bar = lambda s, t, su, tu: ("neon_c" if int(su / 2) % 2 else "out") if 0.6 < tu < 2.2 else None
    if axis == "x":
        for x in (0.5, 14):
            cv.face((x, 9, 0), (1.6, 0, 0), (0, 0, 9), lambda *a: "s1")
        cv.face((2, 8.6, 5), (12, 0, 0), (0, 0, 2.8), bar)
    else:
        for y in (0.5, 14):
            cv.face((9, y, 0), (0, 1.6, 0), (0, 0, 9), lambda *a: "s2")
        cv.face((8.6, 2, 5), (0, 12, 0), (0, 0, 2.8), bar)
    return finish_cell(cv)


def rail_neon(axis, sides):
    """Bridge rails: a glass panel with a neon top along each open side."""
    from iso_ground import finish_cell
    cv = Canvas3D(40, 34, 20, 22)
    panel = lambda s, t, su, tu: "neon_b" if tu > 5.6 else (120, 220, 235, 90)
    for side in sides:
        if axis == "x":
            y = 0.5 if side == "a" else 15
            cv.face((0, y, 0), (16, 0, 0), (0, 0, 6.5), panel)
        else:
            x = 0.5 if side == "a" else 15
            cv.face((x, 0, 0), (0, 16, 0), (0, 0, 6.5), panel)
    return finish_cell(cv)


def stairs_neon(direction, lit=True):
    """Metal steps with an LED strip along every lip."""
    from iso_ground import HT, finish_cell
    cv = Canvas3D(44, 44, 22, 30)
    for k in reversed(range(4)):
        z = (k + 1) * HT / 4
        if direction == "n":
            y0 = 16 - (k + 1) * 4
            cv.face((1, y0 + 4, 0), (14, 0, 0), (0, 0, z), lambda s, t, su, tu, z=z: "neon_b" if tu > z - 0.8 else "s2")
            cv.face((1, y0, z), (14, 0, 0), (0, 4, 0), lambda s, t, su, tu: "s0" if int(su) % 3 else "s1")
            cv.face((15, y0 + 4, 0), (0, -4, 0), (0, 0, z), lambda *a: "s3")
        else:
            x0 = 16 - (k + 1) * 4
            cv.face((x0 + 4, 15, 0), (0, -14, 0), (0, 0, z), lambda s, t, su, tu, z=z: "neon_b" if tu > z - 0.8 else "s3")
            cv.face((x0, 1, z), (4, 0, 0), (0, 14, 0), lambda s, t, su, tu: "s0" if int(tu) % 3 else "s1")
            cv.face((x0, 15, 0), (4, 0, 0), (0, 0, z), lambda *a: "s2")
    return finish_cell(cv)


def deck_neon(axis):
    """Steel grating across the bridge, a glowing line down the middle."""
    from iso_ground import diamond

    def fn(x, y):
        dx, dy = x + 0.5 - 16, y + 0.5 - 8
        u, v = (dx + 2 * dy) / 2 + 8, (2 * dy - dx) / 2 + 8
        across, along = (u, v) if axis == "x" else (v, u)
        if 7.2 < across < 8.8:
            return "neon_b"
        return "vh2" if int(along) % 3 == 0 or int(across) % 3 == 0 else "s2"
    return diamond(fn)


def flowers_led(variant):
    """An LED bed: dark soil, a grid of tiny lights in two colours."""
    from iso_ground import diamond
    cols = [("neon_a", "neon_b"), ("neon_c", "fl_p"), ("neon_b", "fl_w"), ("fl_p", "neon_c")][variant % 4]

    def fn(x, y):
        if (x + 2 * y) % 6 == 0 and y % 2 == 0:
            return cols[int(h("led", variant, x, y) * 2)]
        return "lf3" if (x + y) % 3 else "g4"
    return diamond(fn)


def flowers_shroom(variant):
    """A bed of glowing mushrooms: small caps lit from below."""
    from iso_ground import diamond
    col = ("neon_b", "fl_p", "neon_c", "neon_a")[variant % 4]
    spots = [(3 + i * 5.2 + (2.5 if j % 2 else 0) + h("mx", variant, i, j) * 2, 3 + j * 3.4) for j in range(4) for i in range(6)]

    def fn(x, y):
        for (sx, sy) in spots:
            if abs(x + 0.5 - sx) < 1.6 and -1.2 < y + 0.5 - sy < 0.2:
                return col if y + 0.5 - sy > -0.6 else "fl_w"         # a cap, lit on top
            if abs(x + 0.5 - sx) < 0.5 and 0.2 <= y + 0.5 - sy < 1.6:
                return "lf1"                                           # its stem
        return "lf3"
    return diamond(fn)


def crops_hydro():
    """Hydroponic trays: rows of glowing sprouts along metal channels."""
    from iso_ground import diamond

    def fn(x, y):
        k = (x + 2 * y) % 8
        if k in (0, 1):
            return "s2"                                                # the channel
        if k == 2 and (x // 2 + y) % 3 == 0:
            return "neon_b" if (x + y) % 2 else "p0"                   # sprouts
        if k == 3 and (x // 2 + y) % 3 == 0:
            return "p1"
        return None
    return diamond(fn)


def ground(switch):
    """Patches for art/iso_ground.py per CYBER switch."""
    import iso_ground
    if switch.get("fences") in ("rail", "glass"):
        style = switch["fences"]
        iso_ground.fence_iso = lambda conn, style_=style, **_: fence_neon(conn, style_)
        iso_ground.gate_iso = gate_neon
    if switch.get("rails") == "neon":
        iso_ground.bridge_iso = rail_neon
    if switch.get("stairs") == "neon":
        iso_ground.stairs_iso = stairs_neon
    if switch.get("deck") == "neon":
        iso_ground.deck_iso = deck_neon
    if switch.get("beds") == "led":
        iso_ground.flowers_iso = flowers_led
    elif switch.get("beds") == "shrooms":
        iso_ground.flowers_iso = flowers_shroom
    if switch.get("crops") == "neon":
        iso_ground.crops_iso = crops_hydro


# ---------- nature bits (art/iso_nature.py): bushes, rocks, the small details ----------

def _line(s, x0, y0, x1, y1, c):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for k in range(n):
        t = k / max(1, n - 1)
        s.put(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)


def fibre_bush(seed):
    """A small fibre tuft: straight strands fanning up from one root, glowing tips (the fibre trees' cousin)."""
    from sprites import rng
    r = rng("fibush", seed)
    s = Sprite(20, 15)
    rx, ry = 10, 13
    tip = ("neon_b", "fl_p", "neon_c")[int(h("fbt", seed) * 3)]
    for k in range(9):
        a = math.pi * (0.12 + 0.76 * k / 8) + r.uniform(-0.08, 0.08)
        ln = r.uniform(7, 11)
        x, y = rx - math.cos(a) * ln * 0.95, ry - math.sin(a) * ln
        _line(s, rx, ry, x, y, "p3" if k % 2 else "lf1")
        s.put(round(x), round(y), "fl_w"); s.put(round(x) + 1, round(y), tip)
    return tight(s).outline()


def led_shrub(seed):
    """A dark rounded shrub, dotted with little lights."""
    from sprites import rng
    r = rng("ledsh", seed)
    s = Sprite(20, 15)
    for (x, y, rr) in [(6, 8, 5.5), (13, 8, 5.5), (9.5, 5, 5.5)]:
        for j in range(15):
            for i in range(20):
                dx, dy = i + 0.5 - x, j + 0.5 - y
                if dx * dx + dy * dy <= rr * rr:
                    lit = -(dx + dy) / rr
                    s.put(i, j, "lf1" if lit > 0.7 else "lf3" if lit < -0.4 or j > 11 else "lf2")
    col = r.choice(["neon_a", "neon_b", "neon_c"])
    for _ in range(10):
        x, y = r.randint(3, 16), r.randint(2, 11)
        if s.get(x, y)[3]:
            s.put(x, y, col if r.random() < 0.7 else "fl_w")
    return tight(s).outline()


def _small_box(w, d, hgt, lit, dark, top):
    cv = Canvas3D(int(w + d + 8), int((w + d) / 2 + hgt + 8), int(d + 4), int(hgt + 4))
    cv.face((0, d, 0), (w, 0, 0), (0, 0, hgt), lit)
    cv.face((w, d, 0), (0, -d, 0), (0, 0, hgt), dark)
    cv.face((0, 0, hgt), (w, 0, 0), (0, d, 0), top)
    return cv


def _crop(cv):
    s = cv.s
    x0, y0, x1, y1 = s.im.getbbox()
    out = Sprite(x1 - x0, y1 - y0)
    out.im.paste(s.im.crop((x0, y0, x1, y1)), (0, 0)); out.px = out.im.load()
    return tight(out).outline()


def concrete_block(seed):
    """A broken concrete block, rebar sticking out of its top."""
    from iso_props import proj
    w = 9 if h("cbw", seed) < 0.5 else 11
    cv = _small_box(w, 6, 5, lambda s, t, su, tu: "c2" if (su + tu * 2) % 7 < 0.8 else "c1",
                    lambda *a: "c3", lambda s, t, su, tu: "c1" if su < w - 2 or tu > 2 else None)
    for k in range(2):                                                # rebar
        x, y = proj(2 + k * 4, 3, 5)
        for j in range(4 + k):
            cv.s.put(int(x + cv.ox + j * 0.4), int(y + cv.oy - j), "s2" if j < 3 + k else "cb2")
    return _crop(cv)


def scrap(seed):
    """A small pile of scrap: plates, a pipe, one glowing part."""
    from sprites import rng
    r = rng("scrap", seed)
    s = Sprite(16, 10)
    for k in range(4):
        x, y = r.randint(1, 10), r.randint(4, 7)
        w, hh = r.randint(3, 5), r.randint(2, 3)
        s.rect(x, y, w, hh, ("s1", "s2", "vh1", "b2")[k])
        s.rect(x, y, w, 1, ("s0", "s1", "vh0", "b1")[k])
    s.rect(4, 3, 7, 2, "s1"); s.rect(4, 3, 7, 1, "s0")                # the pipe
    s.put(r.randint(3, 11), r.randint(5, 7), "neon_b")
    return tight(s).outline()


def connector(seed):
    """Rocks as connector chips: rock-1 a pin header (a black block, a row of gold pins standing up), rock-2 a small
    chip (a black square, silver legs, a pin-one dot)."""
    from iso_props import proj
    header = str(seed).endswith("0")
    if header:
        w, d, hgt = 12, 4, 3
        cv = _small_box(w, d, hgt, lambda *a: "vh1", lambda *a: "vh2", lambda *a: "vh0")
        for k in range(5):                                            # the pins
            x, y = proj(1.5 + k * 2.2, d / 2, hgt)
            for j in range(4):
                cv.s.put(int(x + cv.ox), int(y + cv.oy - j), "cb0" if j == 3 else "cb1")
        return _crop(cv)
    w = d = 8
    cv = _small_box(w, d, 2, lambda *a: "vh1", lambda *a: "vh2",
                    lambda s, t, su, tu: "fl_w" if (su - 1.6) ** 2 + (tu - 1.6) ** 2 < 0.7 else "vh0")
    for k in range(3):                                                # legs on the two front sides
        cv.face((1.5 + k * 2.5, d, 0), (0.9, 0, 0), (0, 1.6, 0), lambda *a: "s0")
        cv.face((w, 1.5 + k * 2.5, 0), (1.6, 0, 0), (0, 0.9, 0), lambda *a: "s1")
    return _crop(cv)


def bolts(seed):
    """Nuts and bolts on the ground."""
    from sprites import rng
    r = rng("bolts", seed)
    s = Sprite(14, 7)
    for _ in range(4):
        x, y = r.randint(2, 11), r.randint(2, 5)
        s.rect(x, y, 2, 2, "s1"); s.put(x, y, "s0"); s.put(x + 1, y + 1, "s2")
    return tight(s).outline()


def cables(seed):
    """Cables poking up out of the ground, glowing at the ends."""
    from sprites import rng
    r = rng("cables", seed)
    s = Sprite(12, 10)
    for k in range(4):
        x0 = 2 + k * 2.4
        hgt = r.randint(4, 8)
        lean = r.uniform(-2, 2)
        for j in range(hgt):
            s.put(int(x0 + lean * (j / hgt) ** 2), 9 - j, "vh1" if k % 2 else "vh0")
        s.put(int(x0 + lean), 9 - hgt, ("neon_b", "fl_p", "neon_c", "neon_a")[k])
    return tight(s)


def led_flowers(seed):
    """Little stems with neon heads."""
    from sprites import rng
    r = rng("ledfl", seed)
    s = Sprite(12, 10)
    col = r.choice(["neon_a", "neon_b", "neon_c"])
    for k in range(5):
        x, y = r.randint(2, 9), r.randint(2, 6)
        s.put(x, y + 1, "vh1"); s.put(x, y + 2, "vh1"); s.put(x, y + 3, "vh1")
        s.put(x, y, col); s.put(x, y - 1, "fl_w")
    return tight(s).outline()


def glow_shrooms(seed):
    """Glowing mushrooms."""
    from sprites import rng
    r = rng("gshroom", seed)
    s = Sprite(12, 9)
    for k in range(r.randint(2, 3)):
        x = 2 + k * 4 + r.randint(0, 1)
        s.rect(x, 5, 1, 3, "lf1")
        s.rect(x - 2, 3, 5, 2, "neon_b"); s.rect(x - 1, 2, 3, 1, "neon_b"); s.put(x - 1, 2, "fl_w")
    return tight(s).outline()


def nature(switch):
    """Patches for art/iso_nature.py per CYBER switch: bushes recolour / fibre / led, rocks recolour / concrete /
    scrap, details recolour / neon."""
    import iso_nature
    if switch.get("bushes") == "fibre":
        iso_nature.flower_bush = fibre_bush
    elif switch.get("bushes") == "led":
        iso_nature.flower_bush = led_shrub
    if switch.get("rocks") == "concrete":
        iso_nature.mossy_rock = concrete_block
    elif switch.get("rocks") == "scrap":
        iso_nature.mossy_rock = scrap
    elif switch.get("rocks") == "connector":
        iso_nature.mossy_rock = connector
    if switch.get("details") == "neon":
        iso_nature.pebbles, iso_nature.tuft = bolts, cables
        iso_nature.flower_clump, iso_nature.mushrooms = led_flowers, glow_shrooms
