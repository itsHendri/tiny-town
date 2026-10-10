"""Shared art helpers: the palette, a small Sprite class, nature (tree, pine, bush, rock) and a cottage.

Everything is drawn at true pixel size from one palette, lit from the top-left, with navy outlines.
"""
import math
import random

from PIL import Image

# ---------- palette ----------

PAL = {
    "out": "#26303f",                                            # outlines: deep navy, never black
    "g0": "#d2e889", "g1": "#b4d566", "g2": "#93c050", "g3": "#6ea542", "g4": "#4f8a3c",   # grass
    "t0": "#a9dd62", "t1": "#7cc04f", "t2": "#4f9a48", "t3": "#2f7448",                   # round trees
    "p0": "#5fbf86", "p1": "#3a9c72", "p2": "#2a7a63", "p3": "#1f5a54",                   # pines
    "trunk": "#7a5040", "trunk2": "#5a3a32",
    "w0": "#e6fbfa", "w1": "#73dbe9", "w2": "#45bddd", "w3": "#2d97c6",                   # water
    "s0": "#a3abbd", "s1": "#7a8399", "s2": "#59617a", "s3": "#3e455c",                   # stone
    "d0": "#fff6b8", "d1": "#f4e48a", "d2": "#e2c96a",                                    # worn patches, dirt
    "r0": "#f59a63", "r1": "#e8673a", "r2": "#c4482c", "r3": "#94352a",                   # red roof
    "y0": "#fbd36e", "y1": "#f0aa45", "y2": "#cf8233", "y3": "#a1612b",                   # orange roof
    "c0": "#f6ecd2", "c1": "#e3d3ae", "c2": "#c4b28c", "c3": "#9c8b6e",                   # walls
    "t4": "#21573f", "t5": "#173f33",                                                     # deep forest shade
    "gh": "#c6e070", "gh2": "#a9cf58",                                                    # raised grass, a touch sunnier
    "k0": "#ecd29a", "k1": "#cfa765", "k2": "#a37a45", "k3": "#7a5733",                   # wood
    "door": "#d9493a", "door2": "#a8352d", "win": "#3d4d70", "win2": "#9fd3f2",
    "moss": "#a3c95c", "moss2": "#7fae4a",
    "fl_o": "#f39a3c", "fl_w": "#ffffff", "fl_y": "#ffe36b", "fl_p": "#f28fb0",
    "mail": "#d9493a",
    "jf0": "#e6ccff", "jf1": "#b86cd6", "jf2": "#7a6ae6", "jf3": "#22a8e0", "scr": "#1f2547",  # Jellyfin glow
    "sr0": "#d8ccff", "sr1": "#9d82f5", "sr2": "#6a4fd6", "sr3": "#3f2c99",                   # Seerr violet
    "m0": "#eef1f6", "m1": "#d3d8e2", "m2": "#aeb5c4", "m3": "#858da0",                       # laptop silver
    "steam": "#f4f7fb", "light": "#fff3a8", "car1": "#4f8fd9", "car2": "#e8b13c",
    "b0": "#8fbcf7", "b1": "#5b8fe3", "b2": "#3d6bc2", "b3": "#2b4c8f",                       # blue roof
    "sig": "#3a76f0", "sig2": "#2a59c4",                                                      # Signal blue
    "fx0": "#f08c4c", "fx1": "#d9622b", "fx2": "#a8431f", "fxw": "#fff4e6", "fxd": "#3a2a2a",   # fox
    "dg0": "#b88459", "dg1": "#8f5f3f", "dg2": "#6b4430", "dgc": "#ead2ad",                    # dog
    "ow0": "#d2ad84", "ow1": "#a3805b", "ow2": "#735a41", "owc": "#efe0c4",                    # owl
    "gold": "#f2c94c", "red": "#e2483d",
    "sk0": "#f6d2ac", "sk1": "#e2ad80",                                                       # skin
    "tc0": "#d8b77f", "tc1": "#b8935a", "tc2": "#8c6b3d",                                     # trench coat
    "vh0": "#4a4f5e", "vh1": "#30343f", "vh2": "#1f222b",                                     # VHS / rack black
    "led": "#7ee08a", "amber": "#ffb347",
    # the cat
    "c_o": "#e39a4c", "c_h": "#f2b86e", "c_O": "#c4743a", "c_c": "#f4e3c3", "c_C": "#dcc39b", "c_p": "#e9a3a0",
    "c_g": "#6a9a3c", "c_w": "#ffffff", "c_B": "#5a3320",
}
RGB = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) + (255,) for k, v in PAL.items()}
CLEAR = (0, 0, 0, 0)
OUTLINE = {"style": "solid", "double": True}      # Sprite.outline's style; double: buildings get a 2 px line
_DARK = {}


def local_dark(rgba):
    """A darker, cooler shade of a colour, for outline pixels next to it (selective outlining)."""
    if rgba not in _DARK:
        from palettes import hexof, oklch
        L, C, H = oklch("#%02x%02x%02x" % rgba[:3])
        o = RGB["out"]
        oL = oklch("#%02x%02x%02x" % o[:3])[0]
        h = hexof(oL + (L - oL) * 0.38, C * 0.8, H + max(-14, min(14, (275 - H + 540) % 360 - 180)))
        _DARK[rgba] = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    return _DARK[rgba]


def rng(*seed):
    return random.Random("/".join(map(str, seed)))


# ---------- sprite helpers ----------

class Sprite:
    def __init__(self, w, h):
        self.im = Image.new("RGBA", (w, h), CLEAR)
        self.px = self.im.load()
        self.w, self.h = w, h

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[x, y] = RGB[c] if isinstance(c, str) else c

    def get(self, x, y):
        return self.px[x, y] if 0 <= x < self.w and 0 <= y < self.h else CLEAR

    def rect(self, x, y, w, h, c):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.put(i, j, c)

    def disc(self, cx, cy, r, c, squash=1.0):
        for j in range(int(cy - r) - 1, int(cy + r) + 2):
            for i in range(int(cx - r) - 1, int(cx + r) + 2):
                if (i - cx) ** 2 + ((j - cy) / squash) ** 2 <= r * r:
                    self.put(i, j, c)

    def outline(self, c="out"):
        """A 1-pixel outline around everything opaque, in the style OUTLINE["style"] says:
        solid: all `out` (the reference art's line). selout: lit sides (top, left) get a dark shade of the colour
        inside, shadow sides keep `out`. soft: a dark shade all round, `out` only along the bottom."""
        style = OUTLINE["style"]
        edge = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[x, y][3] == 0:
                    n = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if self.get(x + dx, y + dy)[3]]
                    if n:
                        edge.append((x, y, n))
        for x, y, n in edge:
            if style == "solid":
                self.put(x, y, c)
                continue
            shadow_side = any(d in n for d in ((0, -1), (-1, 0)))     # the shape is above or left of this pixel
            bottom = (0, -1) in n
            if (style == "selout" and shadow_side) or (style == "soft" and bottom):
                self.put(x, y, c)
            else:
                dx, dy = n[0]
                self.put(x, y, local_dark(self.get(x + dx, y + dy)))
        return self


def tight(sprite, pad=1):
    """Grow the canvas by `pad` on every side (room for the outline)."""
    s = Sprite(sprite.w + 2 * pad, sprite.h + 2 * pad)
    s.im.paste(sprite.im, (pad, pad))
    s.px = s.im.load()
    return s


# ---------- nature ----------

def tree(seed, size=1.0, dark=0):
    """A round, clumpy tree: lit from the top-left, darker clumps at the bottom-right.
    dark=1 or 2 shifts every shade down (trees further back in the forest)."""
    r = rng("tree", seed)
    R = 15 * size
    w, h = int(R * 2 + 8), int(R * 2 + 14)
    s = Sprite(w, h)
    cx, cy = w / 2, R + 3
    s.rect(int(cx - 2), int(cy + R * 0.5), 5, int(h - cy - R * 0.5) - 1, "trunk")
    s.rect(int(cx + 1), int(cy + R * 0.5), 2, int(h - cy - R * 0.5) - 1, "trunk2")
    clumps = [(cx, cy, R * 0.82)]
    for k in range(9):
        a = math.pi * (0.9 + k * 1.2 / 8) + r.uniform(-0.15, 0.15)  # around the top and sides
        d = R * r.uniform(0.45, 0.62)
        clumps.append((cx + math.cos(a) * d * 1.1, cy + math.sin(a) * d, R * r.uniform(0.38, 0.5)))
    for k in range(4):
        clumps.append((cx + r.uniform(-R * 0.55, R * 0.55), cy + R * r.uniform(0.2, 0.5), R * r.uniform(0.35, 0.45)))
    clumps.sort(key=lambda c: c[1])
    for (x, y, rr) in clumps:
        for j in range(int(y - rr) - 1, int(y + rr) + 2):
            for i in range(int(x - rr) - 1, int(x + rr) + 2):
                dx, dy = i - x, j - y
                if dx * dx + dy * dy > rr * rr:
                    continue
                lit = -(dx + dy) / rr                    # +1 at the top-left edge, -1 at the bottom-right
                low = (j - cy) / R                       # lower part of the whole crown is in shade
                if lit > 0.75:
                    k = 0
                elif lit < -0.55 or low > 0.62:
                    k = 3 if low > 0.7 else 2
                else:
                    k = 1
                s.put(i, j, f"t{min(5, k + dark)}")
    # a few leaf glints
    for _ in range(6):
        x, y = int(cx + r.uniform(-R * 0.6, R * 0.2)), int(cy + r.uniform(-R * 0.7, 0))
        if s.get(x, y)[3]:
            s.put(x, y, f"t{dark}")
    return tight(s).outline()


def pine(seed, size=1.0):
    r = rng("pine", seed)
    w, h = int(22 * size), int(38 * size)
    s = Sprite(w, h)
    cx = w / 2
    s.rect(int(cx - 2), h - 7, 4, 6, "trunk")
    tiers = 4
    for t in range(tiers):
        top = int(t * (h - 8) / (tiers + 0.6))
        bottom = int(top + (h - 8) / tiers * 1.5)
        half = (w / 2 - 1) * (0.45 + 0.55 * (t + 1) / tiers)
        for j in range(top, min(bottom, h - 6)):
            f = (j - top) / max(1, bottom - top)
            span = half * f + 1
            for i in range(int(cx - span), int(cx + span) + 1):
                rel = (i - cx) / max(1, span)
                if f > 0.82:
                    c = "p3"
                elif rel > 0.35:
                    c = "p2"
                elif rel < -0.5 and f < 0.7:
                    c = "p0"
                else:
                    c = "p1"
                s.put(i, j, c)
    s.put(int(cx), 0, "p0")
    return tight(s).outline()


def bush(seed):
    r = rng("bush", seed)
    s = Sprite(16, 12)
    for (x, y, rr) in [(5, 6, 4.5), (11, 6, 4.5), (8, 4, 4.5)]:
        for j in range(12):
            for i in range(16):
                dx, dy = i - x, j - y
                if dx * dx + dy * dy <= rr * rr:
                    lit = -(dx + dy) / rr
                    s.put(i, j, "t0" if lit > 0.7 else "t2" if lit < -0.4 or j > 8 else "t1")
    if r.random() < 0.6:
        for _ in range(3):
            s.put(r.randint(3, 12), r.randint(2, 7), r.choice(["fl_o", "fl_w", "fl_p"]))
    return tight(s).outline()


def rock(seed):
    r = rng("rock", seed)
    w = r.choice([8, 10])
    s = Sprite(w, 7)
    s.disc(w / 2 - 0.5, 4, w / 2, "s1", squash=0.7)
    for i in range(1, w - 2):
        s.put(i, 2, "s0")
    s.rect(w // 2, 5, w // 2 - 1, 1, "s2")
    return tight(s).outline()


def mailbox():
    s = Sprite(8, 14)
    s.rect(3, 6, 2, 8, "k3")
    s.rect(0, 0, 8, 6, "mail")
    s.rect(0, 0, 8, 1, "r0")
    s.rect(6, 1, 2, 5, "door2")
    s.put(6, 2, "fl_w")
    return tight(s).outline()


# ---------- buildings ----------

def house(seed, w=56, wall_h=24, roof="r", sign=None, chimney=True, moss=0.15, gable=False, plants=True):
    """A cottage in 3/4 view: a shingled roof with ridge, verge boards and overhang, cream walls in a timber
    frame, a stone footing, a red door with a step, windows with flower boxes. gable=True adds a front gable."""
    r = rng("house", seed)
    over = 4
    roof_h = int(w * 0.52)
    W = w + over * 2
    H = roof_h + wall_h + 1
    s = Sprite(W, H)
    x0, yw = over, roof_h - 1
    # walls
    s.rect(x0, yw, w, wall_h, "c0")
    s.rect(x0 + w - 3, yw, 3, wall_h, "c1")
    for k, c in enumerate(("c3", "c2", "c1")):            # shadow under the eaves
        s.rect(x0, yw + k, w, 1, c)
    beams = [x0, x0 + w - 1] + ([x0 + w // 2] if w > 60 else [])
    for bx in beams:
        s.rect(bx, yw, 1, wall_h - 4, "k2")
    s.rect(x0, yw + wall_h - 5, w, 1, "k2")
    for k in range(wall_h - 4):                           # a little ivy on the left corner
        if r.random() < 0.5 and k > 2:
            s.put(x0 + 1 + (k % 3 == 0), yw + k, "t2" if k % 2 else "t1")
    s.rect(x0, yw + wall_h - 4, w, 4, "s1")                # stone footing
    s.rect(x0, yw + wall_h - 4, w, 1, "s0")
    for i in range(x0, x0 + w, 6):
        s.rect(i, yw + wall_h - 3, 1, 3, "s2")
    s.rect(x0, yw + wall_h - 1, w, 1, "s2")
    # door with a frame and a step
    dx = x0 + (w // 2 - 5 if gable else (w * 2) // 3 - 5)
    dy = yw + wall_h - 16
    s.rect(dx - 1, dy - 1, 12, 13, "k3")
    s.rect(dx, dy, 10, 12, "door")
    s.rect(dx + 7, dy, 3, 12, "door2")
    for i in (dx + 3, dx + 6):
        s.rect(i, dy + 1, 1, 11, "door2")
    s.rect(dx, dy, 10, 1, "door2")
    s.put(dx + 2, dy + 6, "fl_y")
    s.rect(dx - 1, yw + wall_h - 1, 12, 1, "s0")
    # windows with flower boxes
    spots = [x for x in (x0 + 5, x0 + 21, x0 + w - 17, x0 + w - 33) if x0 + 3 <= x <= x0 + w - 14 and abs(x - dx) > 12]
    taken = []
    for wx in spots:
        if any(abs(wx - t) < 14 for t in taken):
            continue
        taken.append(wx)
        wy = yw + 6
        s.rect(wx - 1, wy - 1, 12, 10, "k3")
        s.rect(wx, wy, 10, 8, "win")
        s.rect(wx, wy, 4, 3, "win2")
        s.rect(wx + 5, wy, 1, 8, "k2"); s.rect(wx, wy + 4, 10, 1, "k2")
        if plants:
            s.rect(wx - 1, wy + 8, 12, 2, "k2")
            for i in range(wx, wx + 10):
                s.put(i, wy + 7, r.choice(["t1", "t2", "fl_o", "fl_p", "t1", "fl_w"]))
    # roof: shingles in rows, lit on the left, a ridge cap on top, dark eaves below
    c = [f"{roof}{i}" for i in range(4)]
    inset = int(w * 0.22)
    for j in range(roof_h):
        f = j / max(1, roof_h - 1)
        left = int(inset * (1 - f))
        right = W - left
        for i in range(left, right):
            row = j // 5
            tx = (i + (row % 2) * 4) % 8
            ty = j % 5
            k = 1
            if ty == 4 or tx == 0:
                k = 2
            elif ty == 0 and i < W * 0.6:
                k = 0
            if i > W * 0.62:
                k = min(3, k + 1)                          # the shaded side
            if i < left + 2 or i >= right - 2:
                k = 3                                      # verge boards
            if j >= roof_h - 2:
                k = 3 if j == roof_h - 1 else 2            # the eave edge
            s.put(i, j, c[k])
    s.rect(inset, 0, W - 2 * inset, 1, c[0])
    s.rect(inset, 1, W - 2 * inset, 1, c[2])
    if gable:  # a front gable: a little wall triangle with a round window, roofed on both sides
        gw = int(w * 0.46)
        gx = x0 + w // 2 - gw // 2
        top = int(roof_h * 0.12)
        for j in range(top, roof_h):
            f = (j - top) / max(1, roof_h - top)
            half = int(gw / 2 * f) + 1
            cx = gx + gw // 2
            for i in range(cx - half - 3, cx + half + 3):
                edge = abs(i - cx) >= half
                s.put(i, j, (c[2] if i > cx else c[1]) if edge else ("c1" if i > cx + half - 3 else "c0"))
            if j >= roof_h - 2:
                for i in range(cx - half - 3, cx + half + 3):
                    s.put(i, j, c[3])
        cy = top + int((roof_h - top) * 0.6)
        s.disc(gx + gw // 2, cy, 3.2, "k3"); s.disc(gx + gw // 2, cy, 2.2, "win"); s.put(gx + gw // 2 - 1, cy - 1, "win2")
    if moss:
        for _ in range(int(w * moss * 2)):
            x, y = r.randint(inset + 3, W - inset - 4), r.randint(3, roof_h - 5)
            if s.get(x, y)[3]:
                for dx_, dy_ in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0)):
                    if r.random() < 0.8:
                        s.put(x + dx_, y + dy_, "moss" if dy_ == 0 else "moss2")
    if chimney:
        cx = int(W * 0.7)
        s.rect(cx, 0, 8, roof_h // 2, "s1")
        s.rect(cx + 6, 0, 2, roof_h // 2, "s2")
        s.rect(cx, 0, 8, 1, "s0")
        s.rect(cx - 1, 1, 10, 2, "s3")
        s.rect(cx + 1, 1, 6, 1, "out")
    if sign:
        sign(s, x0, yw, w, wall_h)
    if plants:
        for (bx, by) in ((x0 + 1, yw + wall_h - 6), (dx + 11, yw + wall_h - 6)):
            for k in range(14):
                i, j = bx + r.randint(0, 5), by + r.randint(0, 4)
                s.put(i, j, r.choice(["t1", "t2", "t2", "t0"]))
    return tight(s).outline()


def place(canvas, sprite, x, y, shadow=True):
    """Paste a sprite with its feet at (x, y) bottom-centre, with a soft ground shadow."""
    left, top = int(x - sprite.w / 2), int(y - sprite.h)
    if shadow:
        for j in range(-2, 3):
            for i in range(int(-sprite.w * 0.42), int(sprite.w * 0.5)):
                if (i / (sprite.w * 0.46)) ** 2 + (j / 2.6) ** 2 <= 1:
                    xx, yy = int(x + i + 2), int(y + j - 1)
                    cur = canvas.get(xx, yy)
                    if cur[3] and cur[:3] in (RGB["g1"][:3], RGB["g2"][:3], RGB["g0"][:3], RGB["d0"][:3], RGB["d1"][:3]):
                        canvas.put(xx, yy, "g4" if cur[:3] in (RGB["g1"][:3], RGB["g2"][:3], RGB["g0"][:3]) else "d2")
    canvas.im.alpha_composite(sprite.im, (left, top))
