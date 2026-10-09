"""Every tile, drawn in code. Each look is a small function that colours one pixel at a time, so a new style is
one more function in a registry.

    TERRAIN[name][style](shape, x, y, frame, variant)  -> a colour for one pixel of a dual-grid tile, or None
    CLIFF[style]                                        -> how a cliff face, a waterfall and stairs are coloured
    FENCE[style](conn)                                  -> a 16x16 fence tile for its 4 neighbours (N1 E2 S4 W8)

Colours are palette names from sprites.PAL, or RGBA tuples (for soft shadows).
"""
import math
from functools import lru_cache

from PIL import Image

from dualgrid import T, Shape, h, shape_canvas
from sprites import RGB, Sprite

SHADOW = [(38, 48, 63, 95), (38, 48, 63, 62), (38, 48, 63, 30)]
FACE = 16                                   # cliff height in pixels: one cell


def gxy(x, y):
    """Map-aligned coordinates inside a display tile (display tiles start half a cell off the cell grid)."""
    return (x + 8) % T, (y + 8) % T


# ---------- grass (the base under everything, one tile per cell) ----------

@lru_cache(maxsize=None)
def grass_tile(variant, raised=False):
    s = Sprite(T, T)
    base, tufts = ("gh", ("gh2", "gh2", "g2")) if raised else ("g1", ("g2", "g2", "g3"))
    s.rect(0, 0, T, T, base)
    for k in range(4 + variant % 2):
        x, y = 1 + int(h("tuft", variant, k, 0) * 11), 2 + int(h("tuft", variant, k, 1) * 12)
        col = tufts[int(h("tuft", variant, k, 2) * 3)]
        s.put(x, y, col); s.put(x + 2, y, col); s.put(x + 1, y + 1, col)
        if h("tuft", variant, k, 3) < 0.35:
            s.put(x + 1, y - 1, "g0")
    if variant == 3:                                          # one in four has a little flower
        x, y = 3 + int(h("fl", variant) * 9), 3 + int(h("fl", variant, 1) * 9)
        col = ["fl_w", "fl_o", "fl_y", "fl_p"][int(h("fl", variant, 2) * 4)]
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            s.put(x + dx, y + dy, col)
        s.put(x, y, "fl_y" if col != "fl_y" else "fl_o")
    return s


# ---------- raised ground: the top of a cliff ----------

# Three sets per level, so the level's own paths and water can sit between the grass and the edge:
# shadow (on the low ground east of the cliff top), fill (the grass on top), edge (outline and lit lip, drawn last).

def raised_shadow(sh, x, y, frame, v):
    if sh.inside(x, y):
        return None
    for k in (1, 2, 3):
        if sh.inside(x - k, y):
            return "g4" if k < 3 else "g3"
    return None


def raised_fill(sh, x, y, frame, v):
    if not sh.inside(x, y):
        return None
    gx, gy = gxy(x, y)
    return "gh2" if h("hi", gx, gy) < 0.07 else "gh"


def raised_edge(sh, x, y, frame, v):
    if not sh.inside(x, y):
        return None
    if sh.side(x, y):
        return "out"
    if sh.up(x, y, 2):
        return "g0"                                       # lit north lip
    return None


# ---------- paths ----------

def path_soft(sh, x, y, f, v):
    """Soft dirt: a darker rim, grass tufts nibbling the edge, pebbles (the v4 look)."""
    gx, gy = gxy(x, y)
    if not sh.inside(x, y):
        return "g3" if sh.dist(x, y) <= 1.0 and h("nib", gx, gy) < 0.18 else None
    d = sh.dist(x, y)
    if d <= 1.0:
        return "d2"
    if d >= 3 and h("peb", v, gx, gy) < 0.012:
        return "s1"
    return "d0" if (gx * 7 + gy * 13) % 29 == 0 else "d1"


def path_worn(sh, x, y, f, v):
    """Worn trail: no rim, a ragged edge where grass grows in, a lighter worn middle."""
    gx, gy = gxy(x, y)
    if not sh.inside(x, y):
        return None
    d = sh.dist(x, y)
    if d <= 1.0:
        return "g2" if h("rag", gx, gy) < 0.4 else "d2"
    if d <= 2.0:
        return "g3" if h("rag", gx, gy, 1) < 0.08 else "d1"
    if d >= 4:
        return "d1" if h("worn", gx, gy) < 0.25 else "d0"
    return "d1"


def path_crisp(sh, x, y, f, v):
    """Crisp sand: a clean brown outline and a light inner edge, like a GBA route."""
    gx, gy = gxy(x, y)
    if not sh.inside(x, y):
        return None
    d = sh.dist(x, y)
    if d <= 1.0:
        return "k2"
    if d <= 2.0 and (not sh.inside(x, y - 2) or not sh.inside(x - 2, y)):
        return "d0"
    return "d2" if (gx + gy * 5) % 23 == 0 else "d1"


# ---------- cobbles ----------

def cobbles(sh, x, y, f, v):
    gx, gy = gxy(x, y)
    if not sh.inside(x, y):
        return "s3" if sh.dist(x, y) <= 1.0 else None
    if sh.dist(x, y) <= 1.0:
        return "s2"
    bj, bi = gy % 4, (gx + (gy // 4) % 2 * 4) % 8
    return "s3" if bi == 0 or bj == 0 else "s0" if bj == 1 and bi < 5 else "s1"


# ---------- water (3 frames) ----------

def ripples(gx, gy, f):
    """Short ripple lines that move between frames."""
    row = gy % 8
    if row == 3 and (gx + (gy // 8) * 6 + f * 5) % 16 < 3:
        return True
    return False


def water_foam(sh, x, y, f, v):
    """Foam and stones: white foam at the edge, a dark line and stone bank on the land (the v4 look)."""
    gx, gy = gxy(x, y)
    d = sh.dist(x, y)
    if sh.inside(x, y):
        if d <= 1.0:
            return "w0" if (gx + gy + f) % 4 else "w1"
        if d <= 2.0:
            return "w2"
        if d <= 3.0:
            return "w2" if (gx + gy) % 3 == 0 else "w1"
        return "w2" if ripples(gx, gy, f) else "w0" if h("spark", gx, gy, f) < 0.006 else "w1"
    if d <= 1.0:
        return "out"
    if d <= 2.0:
        return "s2"
    if d <= 3.0:
        return "s0" if h("stone", gx, gy) < 0.2 else "s1"
    if d <= 4.0:
        return "g4"
    return None


def water_bank(sh, x, y, f, v):
    """Grassy bank: the land drops into the water, so the far (north) bank shows an earth face."""
    gx, gy = gxy(x, y)
    if sh.inside(x, y):
        j = sh.up(x, y, 4)
        if j:
            return {1: "g3", 2: "k2", 3: "k3", 4: "w3"}[j]
        d = sh.dist(x, y)
        if d <= 1.0:
            return "w3"
        if d <= 2.0:
            return "w2"
        return "w2" if ripples(gx, gy, f) else "w0" if h("spark", gx, gy, f) < 0.006 else "w1"
    d = sh.dist(x, y)
    if d <= 1.0:
        return "out"
    if d <= 2.0 and h("bank", gx, gy) < 0.5:
        return "g3"
    return None


def water_sand(sh, x, y, f, v):
    """Sandy shore: light shallows, foam, and a ring of sand on the land."""
    gx, gy = gxy(x, y)
    d = sh.dist(x, y)
    if sh.inside(x, y):
        if d <= 1.0:
            return "w0" if (gx + gy + f) % 3 else "fl_w"
        if d <= 3.0:
            return "w1"
        return "w1" if ripples(gx, gy, f) else "w0" if h("spark", gx, gy, f) < 0.006 else "w2"
    if d <= 1.0:
        return "d0"
    if d <= 3.0:
        return "d1"
    if d <= 4.0:
        return "d2" if h("sand", gx, gy) < 0.5 else None
    return None


# ---------- tilled soil (crops grow on it, one plant tile per cell) ----------

def soil(sh, x, y, f, v):
    gx, gy = gxy(x, y)
    if not sh.inside(x, y):
        return "g4" if sh.dist(x, y) <= 1.0 else None
    if sh.dist(x, y) <= 1.0:
        return "k3"
    return "k2" if gy % 8 < 4 else "k3"


@lru_cache(maxsize=None)
def crop_tile():
    s = Sprite(T, T)
    for j in (2, 10):
        for i in (2, 9):
            for (dx, dy, col) in ((1, -2, "t0"), (0, -1, "t1"), (2, -1, "t1"), (1, -1, "t2"), (1, 0, "t2"), (0, 0, "t3"), (2, 0, "t3")):
                s.put(i + dx, j + dy + 1, col)
    return s


# ---------- decoration ----------

# One tuft of tall grass in a 4x4 block (0 tip, 1 blade, 2 shade, 3 root, . shade between tufts).
TUFT = ["..0.", ".010", "0121", "3223"]


def tallgrass(sh, x, y, f, v):
    """Tall grass as rows of little tufts (every other row shifted), thinning out raggedly at the edge."""
    if not sh.inside(x, y):
        return None
    gx, gy = gxy(x, y)
    row = gy // 4
    sway = (0, 1, 0)[f % 3] if gy % 4 < 2 else 0          # the tips lean over and back
    ch = TUFT[gy % 4][(gx + (row % 2) * 2 - sway) % 4]
    if sh.dist(x, y) <= 1.0 and ch in ".3":
        return None
    return {"0": "t0", "1": "t1", "2": "t2", "3": "t3", ".": "t2"}[ch]


@lru_cache(maxsize=None)
def flower_tile(variant):
    """A patch of little flowers: four colour mixes."""
    mixes = [("fl_w", "fl_y"), ("fl_p", "fl_w"), ("fl_o", "fl_y"), ("fl_y", "fl_p")]
    a, b = mixes[variant % 4]
    s = Sprite(T, T)
    spots = [(3, 4), (10, 3), (6, 9), (13, 10), (2, 13), (9, 14)]
    for k, (x, y) in enumerate(spots):
        if h("flower", variant, k) < 0.2:
            continue
        x += int(h("fx", variant, k) * 3) - 1
        col = a if k % 2 else b
        s.put(x, y + 1, "t2"); s.put(x - 1, y + 2, "t1"); s.put(x + 1, y + 2, "t1")      # leaves
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            s.put(x + dx, y + dy, col)
        s.put(x, y, "fl_o" if col != "fl_o" else "fl_y")
    return s


@lru_cache(maxsize=None)
def gate_tile(horizontal):
    """A wooden gate in a rail fence: two posts and a braced gate between them."""
    s = Sprite(T, T)
    if horizontal:
        s.rect(4, 4, 8, 8, "k1"); s.rect(4, 4, 8, 1, "k0"); s.rect(4, 11, 8, 1, "k2")
        s.rect(5, 6, 6, 1, "k0"); s.rect(5, 9, 6, 1, "k2")
        for i in range(6):
            s.put(5 + i, 10 - i, "k3")                    # the brace
        for x0 in (1, 12):
            s.rect(x0, 1, 3, 13, "k1"); s.rect(x0, 1, 3, 1, "k0"); s.rect(x0 + 2, 2, 1, 12, "k2")
        s.rect(0, 5, 1, 2, "k1"); s.rect(15, 5, 1, 2, "k1"); s.rect(0, 9, 1, 2, "k1"); s.rect(15, 9, 1, 2, "k1")
    else:
        for y0 in (0, 12):                                # the posts above and below the opening
            s.rect(6, y0, 4, 4, "k1"); s.rect(6, y0, 4, 1, "k0"); s.rect(9, y0 + 1, 1, 3, "k2")
        s.rect(7, 4, 2, 8, "k3")                          # the hinge post's shadow
        s.rect(9, 4, 6, 7, "k1"); s.rect(9, 4, 6, 1, "k0"); s.rect(9, 10, 6, 1, "k2")      # the gate, swung open
        for i in range(5):
            s.put(10 + i, 9 - i, "k3")
    return outline_in_tile(s)


TERRAIN = {
    "raised_shadow": {"grass": raised_shadow},
    "raised_fill": {"grass": raised_fill},
    "raised_edge": {"grass": raised_edge},
    "path": {"soft": path_soft, "worn": path_worn, "crisp": path_crisp},
    "cobbles": {"stone": cobbles},
    "water": {"foam": water_foam, "bank": water_bank, "sand": water_sand},
    "soil": {"tilled": soil},
    "tallgrass": {"meadow": tallgrass},
}
ANIMATED = {"water", "tallgrass"}


@lru_cache(maxsize=None)
def terrain_tile(name, style, mask, radius, frame=0, variant=0):
    sh = Shape(mask, radius)
    fn = TERRAIN[name][style]
    s = Sprite(T, T)
    for y in range(T):
        for x in range(T):
            c = fn(sh, x, y, frame, variant)
            if c is not None:
                s.put(x, y, c)
    return s


# ---------- cliffs: faces, waterfalls, stairs ----------

def stone_face(gx, k, dtop, f):
    if dtop <= 1 and h("hang", gx) < 0.45:
        return "g3" if dtop == 0 else "g4"                   # grass hanging over the edge
    row, r = (k + 64) // 4, (k + 64) % 4
    bx = (gx + (row % 2) * 4) % 8
    return "s3" if bx == 0 or r == 3 else "s0" if r == 0 else "s2" if bx == 7 else "s1"


def earth_face(gx, k, dtop, f):
    drip = 2 + int(h("drip", gx) * 4)
    if dtop == 0:
        return "g3"
    if dtop < drip:
        return "g4"
    band = (k + int(2 * math.sin(gx * 0.8)) + 64) % 6
    if band == 0:
        return "k3"
    if h("pebble", gx, k) < 0.05:
        return "s1"
    return "k1" if dtop < drip + 2 else "k2"


_BOULDERS = [(3, 3, 4.6), (11, 4, 4.8), (7, 10, 4.6), (15, 11, 4.6), (3, 17, 4.8), (11, 18, 4.6), (7, 24, 4.6), (15, 25, 4.6)]


def rock_face(gx, k, dtop, f):
    if dtop == 0 and h("hang", gx) < 0.5:
        return "g3"
    y = (k + 64) % 14 + 3
    best, col = 0.0, "s3"
    for (cx, cy, r) in _BOULDERS:
        for wrap in (-16, 0, 16):
            dx, dy = gx - (cx + wrap), y - cy
            inside = r - math.hypot(dx, dy)
            if inside > best:
                best = inside
                lit = -(dx + dy) / r
                col = "s3" if inside < 0.9 else "s0" if lit > 0.55 else "s2" if lit < -0.35 else "s1"
    return col


def waterfall(gx, k, dtop, f):
    phase = int(h("wf", gx) * 6)
    v = (k - 2 * f + phase + 64) % 6
    if dtop == 0:
        return "w0"
    return "w0" if v == 0 else "w1" if v < 3 or h("streak", gx) < 0.3 else "w2"


def steps(material):
    top, mid, dark = ("s0", "s1", "s3") if material == "stone" else ("k0", "k1", "k3")

    def fn(gx, k, dtop, f):
        if gx in (0, 15):
            return "out"
        if gx in (1, 14):
            return dark
        r = (k + 64) % 4
        return top if r == 0 else dark if r == 3 else mid
    return fn


# ---------- side stairs: climbing onto a hill from its east or west side ----------

def _side_depth(x, y):
    """How far (x, y) is below the tread of its step (high ground to the west, going down eastwards); <0 = above."""
    return y - (2 + (x // 4) * 3)


@lru_cache(maxsize=None)
def side_stairs(style, side):
    """A 16x16 flight of four steps on the low cell beside a hill. side 'w': the hill is to the west; 'e': to the east."""
    s = Sprite(T, T)
    for y in range(T):
        for x in range(T):
            d = _side_depth(x, y)
            if d < 0:
                continue
            if y == T - 1:
                c = "out"
            elif style == "earth":
                band = (y + int(2 * math.sin(x * 0.8)) + 64) % 5
                c = "d0" if d < 1 else "d1" if d < 2 else "g3" if d < 3 and x % 4 < 2 else "k3" if band == 0 else "k1" if d < 5 else "k2"
            elif d < 1:
                c = "k0" if style == "wood" else "s0"
            elif d < 2:
                c = "k1" if style == "wood" else "s1"
            elif style == "wood":
                c = "k3" if x % 4 == 3 or d < 3 else "k2"
            else:
                row = (y + 64) // 4
                bx = (x + (row % 2) * 2) % 4
                c = "s3" if bx == 0 or y % 4 == 3 else "s2" if d < 3 else "s1"
            s.put(x, y, c)
    s = outline_in_tile(s)
    if side == "e":
        s.im = s.im.transpose(Image.FLIP_LEFT_RIGHT)
        s.px = s.im.load()
    return s


SIDE_STAIRS = ("wood", "stone", "earth")


CLIFF = {
    "stone": {"face": stone_face, "stairs": steps("stone")},
    "earth": {"face": earth_face, "stairs": steps("wood")},
    "rock": {"face": rock_face, "stairs": steps("stone")},
}


@lru_cache(maxsize=None)
def cliff_piece(style, kind, left, right, radius, frame=0):
    """A 16x48 piece for one cliff cell: 16 px of the cell above (the rounded corner wraps into it), the cell
    itself, and 16 px below (the face's foot and its shadow). kind: face, waterfall, stairs.
    left/right: 'continue' (the face goes on), 'outer' (the cliff ends), 'inner' (high ground carries on down)."""
    col = {"continue": [1, 1, 0, 0], "outer": [0, 0, 0, 0], "inner": [1, 1, 1, 1]}
    mid = [1, 1, 0, 0]
    cells = [[bool(col[left][r]), bool(mid[r]), bool(col[right][r])] for r in range(4)]
    hi = shape_canvas(cells, radius)                          # 48 x 64 px
    H = len(hi)

    def is_hi(x, y):
        return 0 <= y < H and hi[y][min(47, max(0, x))]

    face_memo = {}

    def is_face(x, y):
        if (x, y) not in face_memo:
            face_memo[(x, y)] = 0 <= y < H and not is_hi(x, y) and any(is_hi(x, y - j) for j in range(1, FACE + 1))
        return face_memo[(x, y)]

    colour = waterfall if kind == "waterfall" else CLIFF[style]["stairs" if kind == "stairs" else "face"]
    s = Sprite(T, 48)
    for y in range(16, 64):
        for x in range(16, 32):
            lx, ly, k = x - 16, y - 16, y - 32
            if is_face(x, y):
                dtop = next(j for j in range(FACE + 1) if is_hi(x, y - j - 1))
                edge = any(not is_face(x + dx, y) and not is_hi(x + dx, y) for dx in (-1, 1))
                bottom = not is_face(x, y + 1) and not is_hi(x, y + 1)
                if kind == "waterfall":
                    c = "w3" if edge else colour(lx, k, dtop, frame)
                elif kind == "stairs":
                    c = colour(lx, k, dtop, frame) if not bottom else "out"
                else:
                    c = "out" if edge or bottom else colour(lx, k, dtop, frame)
                s.put(lx, ly, c)
            elif not is_hi(x, y):
                j = next((j for j in (1, 2, 3) if is_face(x, y - j)), 0)
                if j:
                    if kind == "waterfall":
                        s.put(lx, ly, "fl_w" if (lx + j + frame) % 3 == 0 else "w0")
                    else:
                        s.put(lx, ly, SHADOW[j - 1])
    return s


# ---------- fences (one tile per cell, joined to fence neighbours: N1 E2 S4 W8) ----------

N_, E_, S_, W_ = 1, 2, 4, 8


def fence_picket(conn):
    s = Sprite(T, T)
    if conn & (E_ | W_):
        x0, x1 = (0 if conn & W_ else 6), (16 if conn & E_ else 10)
        s.rect(x0, 7, x1 - x0, 1, "c2"); s.rect(x0, 11, x1 - x0, 1, "c2")
        for x in range(x0, x1):
            if x % 4 in (1, 2):
                s.rect(x, 4, 1, 10, "c0" if x % 4 == 1 else "c1")
                if x % 4 == 1:
                    s.put(x, 3, "c0")
    if conn & N_:
        s.rect(7, 0, 2, 6, "c1"); s.rect(7, 0, 1, 6, "c0")
    if conn & S_:
        s.rect(7, 10, 2, 6, "c1"); s.rect(7, 10, 1, 6, "c0")
    s.rect(6, 2, 4, 12, "c0"); s.rect(9, 2, 1, 12, "c2"); s.rect(6, 2, 4, 1, "c1")
    return outline_in_tile(s)


CORNERS = {N_ | E_: (16, 0), E_ | S_: (16, 16), S_ | W_: (0, 16), W_ | N_: (0, 0)}


def rail_corner(conn):
    """A fence corner: both rails bend round in a quarter ellipse instead of meeting at a post."""
    s = Sprite(T, T)
    cx, cy = CORNERS[conn]
    for rail_y in (5.5, 9.5):
        rx, ry = 8.0, abs(rail_y - cy)
        for y in range(T):
            for x in range(T):
                px_, py_ = x + 0.5, y + 0.5
                d = math.hypot((px_ - cx) / rx, (py_ - cy) / ry)
                off = (d - 1) * min(rx, ry)
                if -1.0 <= off < 1.0:
                    toward_top = (py_ < cy) == (off > 0) if cy else off > 0
                    s.put(x, y, "k0" if off < -0.35 and not toward_top else "k2" if off > 0.4 else "k1")
    return outline_in_tile(s)


def fence_rail(conn):
    if conn in CORNERS:
        return rail_corner(conn)
    s = Sprite(T, T)
    if conn & (E_ | W_):
        x0, x1 = (0 if conn & W_ else 6), (16 if conn & E_ else 10)
        for y in (5, 9):
            s.rect(x0, y, x1 - x0, 2, "k1"); s.rect(x0, y, x1 - x0, 1, "k0"); s.rect(x0, y + 2, x1 - x0, 1, "k2")
    if conn & N_:
        s.rect(7, 0, 2, 5, "k1"); s.rect(8, 0, 1, 5, "k2")
    if conn & S_:
        s.rect(7, 12, 2, 4, "k1"); s.rect(8, 12, 1, 4, "k2")
    s.rect(6, 2, 4, 11, "k1"); s.rect(6, 2, 4, 1, "k0"); s.rect(9, 3, 1, 10, "k2"); s.rect(6, 12, 4, 1, "k3")
    return outline_in_tile(s)


def fence_hedge(conn):
    s = Sprite(T, T)
    on = lambda x, y: ((x - 7.5) ** 2 + (y - 8) ** 2 <= 36 or (conn & W_ and x < 8 and 3 <= y <= 13) or (conn & E_ and x >= 8 and 3 <= y <= 13)
                       or (conn & N_ and y < 8 and 2 <= x <= 13) or (conn & S_ and y >= 8 and 2 <= x <= 13))
    for y in range(T):
        for x in range(T):
            if on(x, y):
                top = not on(x, y - 1) or not on(x, y - 2)
                low = not on(x, y + 2)
                c = "t0" if top else "t3" if not on(x, y + 1) else "t2" if low else "t2" if h("leaf", x, y) < 0.22 else "t1"
                s.put(x, y, c)
    return outline_in_tile(s)


def outline_in_tile(s):
    """Outline, but leave the tile's own border alone where a fence runs on into the next tile."""
    edge = []
    for y in range(s.h):
        for x in range(s.w):
            if s.px[x, y][3] == 0 and any(0 <= x + dx < s.w and 0 <= y + dy < s.h and s.px[x + dx, y + dy][3]
                                          for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                edge.append((x, y))
    for x, y in edge:
        s.put(x, y, "out")
    return s


FENCE = {k: lru_cache(maxsize=None)(f) for k, f in {"picket": fence_picket, "rail": fence_rail, "hedge": fence_hedge}.items()}


# ---------- bridges (one tile per cell) ----------

@lru_cache(maxsize=None)
def bridge_tile(horizontal, start, end):
    """Planks across the water. start/end: the bridge's edge rails (top/bottom for a horizontal bridge)."""
    s = Sprite(T, T)
    for j in range(T):
        for i in range(T):
            k = (i if horizontal else j) % 4
            s.put(i, j, "k0" if k == 0 else "k2" if k == 3 else "k1")
    if horizontal:
        if start:
            s.rect(0, 0, T, 1, "out"); s.rect(0, 1, T, 2, "k3")
        if end:
            s.rect(0, T - 3, T, 2, "k3"); s.rect(0, T - 1, T, 1, "out")
    else:
        if start:
            s.rect(0, 0, 1, T, "out"); s.rect(1, 0, 2, T, "k3")
        if end:
            s.rect(T - 3, 0, 2, T, "k3"); s.rect(T - 1, 0, 1, T, "out")
    return s
