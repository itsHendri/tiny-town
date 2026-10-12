"""Isometric market things, drawn in code: stalls with striped awnings, produce crates, barrels, lamp posts with
hanging signs, a chalkboard and benches. Same 3D face painter as the houses (iso_props.Canvas3D).

    python art/iso_market.py <out.png> [palette]      a sheet of everything
"""
import math
import sys

from PIL import Image

from dualgrid import h
from iso_props import Canvas3D, proj
from sprites import Sprite

AWNINGS = {"red": ("r1", "c0"), "green": ("t2", "c0"), "purple": ("jf2", "c0"), "orange": ("y1", "c0")}
PRODUCE = {"tomatoes": ("red", "r2"), "cabbages": ("t1", "t3"), "carrots": ("fl_o", "y2"), "lemons": ("fl_y", "y1"),
           "apples": ("r1", "t2"), "plums": ("jf2", "sr3")}


def finish(cv, fw, fd):
    """Outline the drawing and work out its anchor (the centre of its front cell)."""
    spr = cv.s
    out = Sprite(spr.w + 2, spr.h + 2)
    out.im.paste(spr.im, (1, 1))
    out.px = out.im.load()
    out.outline()
    sx_, sy_ = proj(fw * 16, fd * 16, 0)
    out.anchor = (round(sx_ + cv.ox + 1), round(sy_ + cv.oy + 1 - 8))
    return out


def wood(lit, dark=False):
    def col(s, t, su, tu):
        plank = int(tu / 3) if tu > su * 0 else 0
        base = ("k2", "k3") if dark else ("k1", "k2") if lit else ("k2", "k3")
        return base[1] if tu % 3 < 0.7 else base[0]
    return col


def box(cv, x, y, z, w, d, hgt, top=None, lit=None, dark=False):
    """A wooden box: front-left face lit, front-right face shaded, a top."""
    cv.face((x, y + d, z), (w, 0, 0), (0, 0, hgt), wood(True, dark))
    cv.face((x + w, y + d, z), (0, -d, 0), (0, 0, hgt), wood(False, dark))
    cv.face((x, y, z + hgt), (w, 0, 0), (0, d, 0), top or (lambda s, t, su, tu: "k0" if not dark else "k1"))


def produce(kind):
    a, b = PRODUCE[kind]

    def col(s, t, su, tu):
        if su < 0.8 or tu < 0.8:
            return "k1"
        cx, cy = int(su / 2.2), int(tu / 2.2)
        fx, fy = su - (cx + 0.5) * 2.2, tu - (cy + 0.5) * 2.2
        if fx * fx + fy * fy > 1.4:
            return b
        return "fl_w" if fx < -0.4 and fy < -0.4 else a
    return col


def crate(kind="tomatoes"):
    cv = Canvas3D(28, 24, 14, 12)
    box(cv, 2, 3, 0, 9, 7, 5, produce(kind))
    return finish(cv, 1, 1)


def crate_stack(kinds=("apples", "cabbages")):
    cv = Canvas3D(30, 30, 15, 18)
    box(cv, 1, 3, 0, 9, 7, 5, produce(kinds[0]))
    box(cv, 3, 1, 5, 8, 6, 4, produce(kinds[1]))
    return finish(cv, 1, 1)


def barrel():
    s = Sprite(12, 15)
    for y in range(15):
        for x in range(12):
            nx = (x + 0.5 - 6) / 5.5
            if abs(nx) > 1:
                continue
            if y < 3 and ((x + 0.5 - 6) / 5.5) ** 2 + ((y + 0.5 - 2) / 2) ** 2 > 1:
                continue
            if y >= 3:
                bulge = 1 - 0.12 * ((y - 9) / 6) ** 2
                if abs(nx) > bulge:
                    continue
            if y < 3:
                c = "k3" if ((x + 0.5 - 6) / 4.5) ** 2 + ((y + 0.5 - 2) / 1.4) ** 2 < 1 else "k1"
            elif y in (5, 11):
                c = "s2" if nx < 0.3 else "s3"
            else:
                c = "k0" if nx < -0.4 else "k1" if nx < 0.35 else "k2"
            s.put(x, y, c)
    out = Sprite(14, 17)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (7, 13)
    return out


def stall(colour="red", goods=("tomatoes", "cabbages", "carrots")):
    """A market stall on a 2x1 footprint: a wooden counter of produce, four posts, a striped awning with a
    scalloped edge."""
    stripe, plain = AWNINGS[colour]
    cv = Canvas3D(64, 64, 22, 40)
    # counter
    box(cv, 2, 4, 0, 26, 9, 8, None)
    for k, kind in enumerate(goods):
        cv.face((3 + k * 8.4, 5, 8), (7.5, 0, 0), (0, 7, 0), produce(kind))
    # posts
    for (px_, py_) in ((2, 4), (28, 4), (2, 13), (28, 13)):
        cv.face((px_, py_, 0), (1.2, 0, 0), (0, 0, 22), lambda s, t, su, tu: "k2")
    # awning: sloping down to the front-left, stripes along it, a scalloped valance
    def awning(s, t, su, tu):
        band = int(su / 4) % 2
        c = stripe if band == 0 else plain
        if tu > 14.5:
            return "out" if tu > 15.4 else c
        return c
    cv.face((-1, 1, 25), (32, 0, 0), (0, 15, -5), awning)
    cv.face((-1, 16, 20), (32, 0, 0), (0, 0, -3), lambda s, t, su, tu: (stripe if int(su / 4) % 2 == 0 else plain)
            if tu > 3 - 2.4 * abs(math.sin(su / 4 * math.pi)) else None)
    return finish(cv, 2, 1)


def lamp(sign=True):
    """A lamp post: a dark post, a lantern with a warm glow, and a little hanging sign."""
    s = Sprite(22, 40)
    s.rect(9, 8, 2, 31, "vh1"); s.rect(8, 37, 4, 2, "vh2")
    s.rect(7, 3, 6, 7, "vh1"); s.rect(8, 4, 4, 5, "light"); s.rect(8, 4, 2, 2, "fl_w"); s.rect(6, 2, 8, 1, "vh2"); s.put(10, 1, "vh2")
    if sign:
        s.rect(11, 14, 6, 1, "vh1"); s.put(13, 15, "vh1"); s.put(16, 15, "vh1")
        s.rect(12, 16, 6, 5, "k1"); s.rect(12, 16, 6, 1, "k0"); s.rect(13, 18, 4, 1, "k3")
    out = Sprite(24, 42)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (11, 40)
    return out


def chalkboard():
    s = Sprite(14, 16)
    s.rect(2, 1, 10, 10, "k2"); s.rect(3, 2, 8, 8, "vh2")
    for (x, y, w) in ((4, 3, 5), (4, 5, 4), (5, 7, 4)):
        s.rect(x, y, w, 1, "fl_w")
    for k in range(5):
        s.put(3 + k // 2, 11 + k, "k2"); s.put(10 - k // 2, 11 + k, "k3")
    out = Sprite(16, 18)
    out.im.paste(s.im, (1, 1)); out.px = out.im.load(); out.outline()
    out.anchor = (8, 16)
    return out


def bench():
    cv = Canvas3D(36, 24, 16, 14)
    box(cv, 1, 6, 4, 18, 4, 1.5, lambda s, t, su, tu: "k0" if int(su) % 4 else "k1")
    for x in (2, 16):
        cv.face((x, 10, 0), (1.5, 0, 0), (0, 0, 4), lambda s, t, su, tu: "k3")
    cv.face((1, 6, 5.5), (18, 0, 0), (0, 0, 5), lambda s, t, su, tu: "k1" if 1 < tu < 4 else None)
    return finish(cv, 1, 1)


def flower_cart():
    cv = Canvas3D(44, 34, 18, 20)
    box(cv, 2, 3, 4, 18, 9, 6, lambda s, t, su, tu: ("fl_p", "fl_y", "fl_w", "fl_o")[int(su / 2 + tu / 2) % 4] if (int(su) + int(tu)) % 2 else "t2")
    s = cv.s
    for (cx, cy) in ((proj(4, 12, 2)), (proj(18, 12, 2))):
        for y in range(-3, 4):
            for x in range(-3, 4):
                if x * x + y * y <= 10:
                    s.put(int(cx + x + cv.ox), int(cy + y + cv.oy), "k3" if x * x + y * y > 5 else "k1")
    return finish(cv, 1, 1)


def well_iso():
    """A stone well with a little shingle roof on two posts and a bucket, drawn for the angle (a plain prop)."""
    from landmarks import cylinder
    from sprites import tight
    s = Sprite(26, 36)
    cx, base = 13, 32
    cylinder(s, cx, base, 9, 7, ("s0", "s1", "s2"), ("s1", "s2"))
    for y in range(int(base - 7 - 2), int(base - 7 + 3)):          # the water inside the ring
        for x in range(cx - 7, cx + 8):
            if ((x + 0.5 - cx) / 6.5) ** 2 + ((y + 0.5 - (base - 7)) / 2.6) ** 2 <= 1:
                s.put(x, y, "w3" if x < cx else "w2")
    for k in (3, 6):                                               # courses on the ring
        for x in range(cx - 9, cx + 10):
            dx = x + 0.5 - cx
            if h("wc", x, k) < 0.7:
                s.put(x, int(base - k + 4.5 * math.sqrt(max(0, 1 - (dx / 9) ** 2))), "s2" if dx < 3 else "s3")
    for px_ in (cx - 8, cx + 7):                                   # posts, a roller, the roof
        s.rect(px_, base - 22, 2, 15, "k2" if px_ < cx else "k3")
    s.rect(cx - 7, base - 18, 15, 1, "k1")
    for j in range(5):
        for x in range(cx - 10 + j, cx + 11 - j):
            s.put(x, base - 23 - j, "r1" if x < cx else "r2")
    s.rect(cx + 1, base - 16, 3, 3, "k1"); s.put(cx + 2, base - 17, "k3")       # the bucket on its rope
    return tight(s).outline()


def crate_iso():
    """An empty wooden crate, drawn for the angle (a plain prop)."""
    from sprites import tight
    cv = Canvas3D(24, 22, 12, 12)
    box(cv, 1, 1, 0, 9, 8, 7, lambda s, t, su, tu: "k1" if 0.8 < su < 8.2 and 0.8 < tu < 7.2 else "k0")
    s = cv.s
    x0, y0, x1, y1 = s.im.getbbox()
    out = Sprite(x1 - x0, y1 - y0)
    out.im.paste(s.im.crop((x0, y0, x1, y1)), (0, 0)); out.px = out.im.load()
    return tight(out).outline()


# Plain props (feet at the bottom middle) drawn here instead of the top-down catalog's flat ones; same names.
PLAIN = {"well": well_iso, "crate": crate_iso}
SHADOWED = ("barrel-iso", "crates", "flower-cart")    # market things that cast a ground shadow


MARKET = {
    "stall-red": lambda: stall("red", ("tomatoes", "apples", "lemons")),
    "stall-green": lambda: stall("green", ("cabbages", "carrots", "lemons")),
    "stall-purple": lambda: stall("purple", ("plums", "apples", "cabbages")),
    "stall-orange": lambda: stall("orange", ("carrots", "lemons", "tomatoes")),
    "crate-tomatoes": lambda: crate("tomatoes"),
    "crate-cabbages": lambda: crate("cabbages"),
    "crate-carrots": lambda: crate("carrots"),
    "crates": lambda: crate_stack(),
    "barrel-iso": barrel,
    "lamp-sign": lamp,
    "lamp-iso": lambda: lamp(False),
    "chalkboard": chalkboard,
    "bench-iso": bench,
    "flower-cart": flower_cart,
}
FOOTPRINTS = {name: [2, 1] for name in MARKET if name.startswith("stall")}


def make(name):
    """A market thing by name, marked if it casts a ground shadow (iso.place and js/render.js draw it)."""
    spr = MARKET[name]()
    spr.ground_shadow = name in SHADOWED
    return spr


if __name__ == "__main__":
    import palettes
    palettes.use(sys.argv[2] if len(sys.argv) > 2 else palettes.DEFAULT)
    sprites = [f() for f in MARKET.values()]
    W = sum(s.w for s in sprites) + 8 * len(sprites)
    H = max(s.h for s in sprites)
    sheet = Image.new("RGBA", (W, H), (142, 164, 63, 255))
    x = 0
    for s in sprites:
        sheet.alpha_composite(s.im, (x, H - s.h))
        x += s.w + 8
    sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(sys.argv[1])
    print("wrote", sys.argv[1])
