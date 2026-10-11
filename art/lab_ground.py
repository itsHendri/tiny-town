"""Candidate grass and water looks for the lab (art/lab.py, round "ground"). Each is a drop-in for iso.grass_px or
iso.SETS["water"]: screen-space pixel functions, repeating every 64 x 32 so the tile phases still join up.
"""
import math

from dualgrid import h

PX, PY = 64, 32                       # the pattern repeat


# ---------- helpers ----------

def smooth(gx, gy, key, sx=16, sy=8, px=PX, py=PY):
    """Soft value noise in [0, 1): hashed lattice every sx x sy px, blended, wrapping at the pattern repeat."""
    nx, ny = px // sx, py // sy
    fx, fy = gx / sx, gy / sy
    i, j = math.floor(fx), math.floor(fy)
    tx, ty = fx - i, fy - j
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    v = lambda a, b: h(key, a % nx, b % ny)
    top = v(i, j) + (v(i + 1, j) - v(i, j)) * tx
    bot = v(i, j + 1) + (v(i + 1, j + 1) - v(i, j + 1)) * tx
    return top + (bot - top) * ty


def stamps(gx, gy, key, cw, ch, shapes, p, jx=None, jy=None):
    """Small drawn shapes on a jittered grid (cells cw x ch, each used with chance p). shapes: lists of strings,
    the root is the bottom-middle character. Returns the shape's character at this pixel, or None."""
    gx, gy = gx % PX, gy % PY
    jx, jy = jx if jx is not None else cw - 3, jy if jy is not None else ch - 2
    ci, cj = gx // cw, gy // ch
    for dj in (0, 1, -1):
        for di in (0, -1, 1):
            i, j = (ci + di) % (PX // cw), (cj + dj) % (PY // ch)
            if h(key, "on", i, j) >= p:
                continue
            shape = shapes[int(h(key, "s", i, j) * len(shapes))]
            rx = i * cw + 1 + int(h(key, "x", i, j) * jx) + (cw // 2 if j % 2 else 0)
            ry = j * ch + 1 + int(h(key, "y", i, j) * jy)
            w, hh = len(shape[0]), len(shape)
            x0, y0 = rx - w // 2, ry - hh + 1
            dx, dy = (gx - x0) % PX, (gy - y0) % PY
            if dx < w and dy < hh and shape[dy][dx] != ".":
                return shape[dy][dx]
    return None


# Tufts: a = light tip, b = mid blade, c = dark root
TUFTS = [
    [".a.a.", "a.b.a", ".cbc."],
    ["a.a", "b.b", "cbc"],
    [".a.", "aba", ".c."],
    ["a...a", ".b.b.", ".ccc."],
]
BLADES = [["a.", ".b"], [".a", "b."], ["a", "b"]]


# ---------- grass ----------

def grass_calm(gx, gy, variant=0):
    """Big soft light and shade patches, a few tufts. Calm, very little noise."""
    gx, gy = gx % PX, gy % PY
    t = stamps(gx, gy, ("cg", variant), 16, 8, TUFTS, 0.35)
    if t:
        return {"a": "gh", "b": "g2", "c": "g3"}[t]
    n = smooth(gx, gy, ("cp", variant))
    return "gh" if n > 0.66 else "gh2" if n < 0.3 else "g1"


def grass_tufted(gx, gy, variant=0):
    """One flat green with lots of drawn tufts, sunlit tips."""
    t = stamps(gx, gy, ("tg", variant), 8, 8, TUFTS, 0.8)
    if t:
        return {"a": "g0", "b": "g2", "c": "g3"}[t]
    return "g1"


def grass_lush(gx, gy, variant=0):
    """Three-tone patches (light, mid, shade) with tufts and the odd flower: rich but ordered."""
    gx, gy = gx % PX, gy % PY
    if h("lf", gx, gy, variant) < 0.003:
        return "fl_w" if h("lfc", gx, gy) < 0.6 else "fl_y"
    n = smooth(gx, gy, ("lp", variant), 16, 8)
    t = stamps(gx, gy, ("lg", variant), 8, 8, TUFTS, 0.55)
    if t:
        return ({"a": "g0", "b": "g1", "c": "g2"} if n > 0.5 else {"a": "gh", "b": "g2", "c": "g3"})[t]
    return "gh" if n > 0.68 else "g2" if n < 0.28 else "gh2" if n < 0.42 else "g1"


def grass_blades(gx, gy, variant=0):
    """Short slanted blade strokes, dense and even: a fine combed texture."""
    gx, gy = gx % PX, gy % PY
    t = stamps(gx, gy, ("bg", variant), 4, 4, BLADES, 0.7, 2, 2)
    n = smooth(gx, gy, ("bp", variant), 32, 16)
    if t:
        return ({"a": "gh", "b": "g2"} if n > 0.45 else {"a": "g1", "b": "g3"})[t]
    return "g1" if n > 0.45 else "gh2"


def grass_clean(gx, gy, variant=0):
    """Nearly flat: one green, soft light patches, a sprinkle of tiny tufts. The cleanest option."""
    gx, gy = gx % PX, gy % PY
    t = stamps(gx, gy, ("kg", variant), 16, 8, [[".a.", "b.b"], ["a.a", ".b."]], 0.4)
    if t:
        return {"a": "gh", "b": "g2"}[t]
    return "gh" if smooth(gx, gy, ("kp", variant), 32, 16) > 0.7 else "g1"


def grass_clover(gx, gy, variant=0):
    """Rounded clumps (little clover-like blobs, lit top-left) on a mid green."""
    gx, gy = gx % PX, gy % PY
    t = stamps(gx, gy, ("vg", variant), 8, 6, [[".aa.", "abbc", ".cc."], [".a.", "abc", ".c."]], 0.6)
    if t:
        return {"a": "gh", "b": "g1", "c": "g3"}[t]
    return "gh2" if smooth(gx, gy, ("vp", variant)) < 0.4 else "g2" if h("vs", gx // 2, gy, variant) < 0.08 else "gh2"


# ---------- water ----------

def bank(sh, x, y, gx, gy):
    """Outside the water: a dark line, then stones on the bank (today's bank, kept for every option)."""
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "out"
    if d <= 2.5:
        return "s1" if h("bank", (gx % 64) // 2, (gy % 32) // 2) < 0.6 else "s2"
    if d <= 3.5 and h("bank2", (gx % 64) // 4, (gy % 32) // 2) < 0.35:
        return "s0"
    return None


def under_top_bank(sh, x, y, k):
    """Is the shore within k px straight above (the bank's shadow falls on the water there)?"""
    return any(not sh.inside(x, y - j) for j in range(1, k + 1))


def ripple(gx, gy, f, rows=8, length=4, every=32):
    """Short dashes along the screen rows, drifting with the frame."""
    return gy % rows == 2 and (gx + (gy // rows) * 7 + f * 5) % every < length


def water_depth(sh, x, y, gx, gy, f):
    """A clean foam line, then shallow, mid and deep bands; glints in the deep."""
    if not sh.inside(x, y):
        return bank(sh, x, y, gx, gy)
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "w0"
    if d <= 3.0:
        return "w1"
    if d <= 5.0:
        return "w2"
    if ripple(gx, gy, f, 8, 3):
        return "w2"
    return "w0" if h("spark", gx % 64, gy % 32, f) < 0.003 else "w3"


def water_shade(sh, x, y, gx, gy, f):
    """Depth bands plus the bank's shadow along the top shore and lighter ripples."""
    if not sh.inside(x, y):
        return bank(sh, x, y, gx, gy)
    d = sh.dist(x, y, 4)
    top = under_top_bank(sh, x, y, 3)
    if d <= 1.0:
        return "w4" if top else "w0"
    if top:
        return "w3"
    if d <= 2.5:
        return "w1"
    if ripple(gx, gy, f, 8, 4):
        return "w1"
    return "w2" if d <= 5.0 else "w3"


def water_calm(sh, x, y, gx, gy, f):
    """A still pond: no foam, a light rim, long soft highlight streaks."""
    if not sh.inside(x, y):
        return bank(sh, x, y, gx, gy)
    d = sh.dist(x, y, 4)
    if d <= 2.0:
        return "w1"
    if (gx + 2 * gy + f * 2) % 24 < 2 and h("st", (gx + 2 * gy) // 24, gy // 6) < 0.5:
        return "w1"
    return "w2"


def water_clear(sh, x, y, gx, gy, f):
    """Clear shallow water: a wide pale rim, the middle deeper, sparkles."""
    if not sh.inside(x, y):
        return bank(sh, x, y, gx, gy)
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "w0" if (gx + gy + f) % 3 else "w1"
    if d <= 4.0:
        return "w1"
    if h("cs", gx % 64, gy % 32, f) < 0.012:
        return "w0"
    return "w2"


def water_deep(sh, x, y, gx, gy, f):
    """Dark, deep water with a bright foam edge: strongest contrast."""
    if not sh.inside(x, y):
        return bank(sh, x, y, gx, gy)
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "w0"
    if d <= 2.0:
        return "w2"
    if under_top_bank(sh, x, y, 3):
        return "w4"
    if ripple(gx, gy, f, 6, 3, 24):
        return "w2"
    return "w3"


# ---------- round 2: clean flat grass without the blob pattern ----------

SPRINKLE = [[".a.", "b.b"], ["a.a", ".b."]]


def _sprinkle(gx, gy, variant, key="kg", p=0.4):
    t = stamps(gx, gy, (key, variant), 16, 8, SPRINKLE, p)
    return {"a": "gh", "b": "g2"}[t] if t else None


def grass_bare(gx, gy, variant=0):
    """Clean flat without patches: one green and the tiny tufts."""
    return _sprinkle(gx % PX, gy % PY, variant) or "g1"


def grass_faint(gx, gy, variant=0):
    """Clean flat, patches in a tone just above the base (g1l), so they hint rather than show."""
    gx, gy = gx % PX, gy % PY
    return _sprinkle(gx, gy, variant) or ("g1l" if smooth(gx, gy, ("kp", variant), 32, 16) > 0.7 else "g1")


def grass_flecks(gx, gy, variant=0):
    """Small ragged light flecks instead of big patches: no shape big enough to repeat visibly."""
    gx, gy = gx % PX, gy % PY
    t = _sprinkle(gx, gy, variant)
    if t:
        return t
    n = smooth(gx, gy, ("kf", variant), 8, 4)
    return "g1l" if n > 0.72 + 0.12 * h("kr", gx // 2, gy, variant) else "g1"


def grass_lit_tufts(gx, gy, variant=0):
    """No filled patches: where a patch would be, tufts get denser and catch the light."""
    gx, gy = gx % PX, gy % PY
    n = smooth(gx, gy, ("kp", variant), 32, 16)
    t = stamps(gx, gy, ("kl", variant), 8, 8, SPRINKLE, 0.15 + 0.6 * n)
    if t:
        return ({"a": "g0", "b": "gh"} if n > 0.6 else {"a": "gh", "b": "g2"})[t]
    return "g1"


def grass_diagonal(gx, gy, variant=0):
    """Faint patches stretched along the iso diagonals, so they read as gentle ground swells, not blobs."""
    gx, gy = gx % PX, gy % PY
    t = _sprinkle(gx, gy, variant)
    if t:
        return t
    u, v = (gx + 2 * gy) % PX, (2 * gy - gx) % PX               # along the two diagonals
    n = smooth(u % PX, (v // 2) % PY, ("kd", variant), 32, 8)
    return "g1l" if n > 0.68 else "g1"


def grass_two_tone(gx, gy, variant=0):
    """Base split into two close greens in soft blobs (no light patch at all): texture only from tufts."""
    gx, gy = gx % PX, gy % PY
    return _sprinkle(gx, gy, variant) or ("g1" if smooth(gx, gy, ("kt", variant), 16, 8) > 0.45 else "g1d")


# Big repeat: flat grass over 16 x 16 cells (iso.GRASS_N = 16), 256 x 128 px, so soft patches don't line up into dots.
BX, BY = 256, 128


def grass_faint_big(gx, gy, variant=0):
    """Faint patches, big repeat."""
    t = _sprinkle(gx % PX, gy % PY, variant)
    return t or ("g1l" if smooth(gx % BX, gy % BY, ("kb", variant), 32, 16, BX, BY) > 0.68 else "g1")


def grass_swells_big(gx, gy, variant=0):
    """Faint light and shade swells, big repeat: three close greens."""
    t = _sprinkle(gx % PX, gy % PY, variant)
    if t:
        return t
    n = smooth(gx % BX, gy % BY, ("ks", variant), 64, 32, BX, BY) * 0.7 + smooth(gx % BX, gy % BY, ("ks2", variant), 16, 8, BX, BY) * 0.3
    return "g1l" if n > 0.64 else "g1d" if n < 0.36 else "g1"


def grass_patches_big(gx, gy, variant=0):
    """Round 1's Clean flat patches (gh), big repeat: the same look, without the dot pattern."""
    t = _sprinkle(gx % PX, gy % PY, variant)
    return t or ("gh" if smooth(gx % BX, gy % BY, ("kq", variant), 32, 16, BX, BY) > 0.72 else "g1")
