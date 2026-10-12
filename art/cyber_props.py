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
