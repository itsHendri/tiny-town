"""Ground materials shared by both views (art/iso.py and art/styles.py), as screen-space pixel functions
(gx, gy = map-wide screen pixel).

Grass, picked 2026-10-11 (clean grass round 2, "soft swells, big repeat"): one green with faint light and shade
swells in three close greens (g1l, g1, g1d), plus small tufts that get denser and catch the light on the swells.
Flat grass repeats every GRASS_N cells (256 x 128 px), so the swells don't line up into a pattern; raised grass
uses 64 x 32 px tiles like every other set, so it keeps only the tufts.
"""
import math

from dualgrid import h

PX, PY = 64, 32                # the repeat of the dual-grid sets (8 tile phases)
GRASS_N = 16                   # flat grass repeats every GRASS_N cells: 16 * N x 8 * N px
BX, BY = 16 * GRASS_N, 8 * GRASS_N


def smooth(gx, gy, key, sx=16, sy=8, px=PX, py=PY):
    """Soft value noise in [0, 1): a hashed lattice every sx x sy px, blended, wrapping at px x py."""
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
    """Small drawn shapes on a jittered grid (cells cw x ch, repeating every PX x PY), each cell used with chance p
    (a number, or a function of the cell's position). shapes: lists of strings, root at the bottom middle.
    Returns the shape's character at this pixel, or None."""
    gx, gy = gx % PX, gy % PY
    jx, jy = jx if jx is not None else cw - 3, jy if jy is not None else ch - 2
    ci, cj = gx // cw, gy // ch
    for dj in (0, 1, -1):
        for di in (0, -1, 1):
            i, j = (ci + di) % (PX // cw), (cj + dj) % (PY // ch)
            rx = i * cw + 1 + int(h(key, "x", i, j) * jx) + (cw // 2 if j % 2 else 0)
            ry = j * ch + 1 + int(h(key, "y", i, j) * jy)
            if h(key, "on", i, j) >= (p(rx, ry) if callable(p) else p):
                continue
            shape = shapes[int(h(key, "s", i, j) * len(shapes))]
            w, hh = len(shape[0]), len(shape)
            x0, y0 = rx - w // 2, ry - hh + 1
            dx, dy = (gx - x0) % PX, (gy - y0) % PY
            if dx < w and dy < hh and shape[dy][dx] != ".":
                return shape[dy][dx]
    return None


TUFTS = [[".a.", "b.b"], ["a.a", ".b."], [".a.", "aba"]]       # a: tip, b: blade


def swell(gx, gy, variant=0):
    """The grass's soft light (near 1) and shade (near 0), repeating every BX x BY."""
    gx, gy = gx % BX, gy % BY
    return smooth(gx, gy, ("ks", variant), 64, 32, BX, BY) * 0.7 + smooth(gx, gy, ("ks2", variant), 16, 8, BX, BY) * 0.3


def grass_px(gx, gy, variant=0, flat=True):
    """Meadow grass at screen pixel (gx, gy). flat: the big-repeat swells (flat grass cells); otherwise tufts only
    (raised grass, in 64 x 32 tiles)."""
    return grass_at(swell(gx, gy, variant) if flat else 0.5, gx, gy, variant)

def grass_at(n, gx, gy, variant=0):
    """Grass colour at a pixel, given its swell n (0 shade .. 1 light): tufts denser and lit where it's light."""
    t = stamps(gx, gy, ("gt", variant), 8, 8, TUFTS, 0.3 + 0.4 * n)
    if t:
        if n > 0.6:
            return "g0" if t == "a" else "gh"
        return "gh" if t == "a" else "g2"
    return "g1l" if n > 0.64 else "g1d" if n < 0.36 else "g1"


def grass_top(u, v, variant=0):
    """Top-down grass at map pixel (u, v): the swells sit where they do in isometric (sampled through the
    projection), the tufts stand upright on screen. Repeats every 16 cells each way."""
    return grass_at(swell(u - v, (u + v) // 2, variant), u, v, variant)


# ---------- path stones, grey cobbles, dirt, water ----------
# sh: the dual-grid shape seen from this pixel (inside, and dist to the edge); x, y: the pixel in it;
# gx, gy: the map-wide screen pixel, for textures. view "iso" squashes stones for the angle, "top" keeps them round.

STONE = {"iso": (8, 4, 5, 3, 1.6), "top": (8, 8, 5, 5, 1.0)}     # grid w, h, jitter x, y, vertical squash


def _stone(gx, gy, view="iso"):
    """Irregular rounded cobbles (a jittered grid of stone centres, repeating every 64 x 32 px): returns the nearest
    stone's id, the offset from its centre (y squashed), and how close the pixel is to the mortar line."""
    gw, gh, jx, jy, sq = STONE[view]
    gx, gy = gx % PX, gy % PY
    i0, j0 = gx // gw, gy // gh
    best = second = 99.0
    sid = off = None
    for j in range(j0 - 1, j0 + 2):
        for i in range(i0 - 1, i0 + 2):
            key = (i % (PX // gw), j % (PY // gh))
            px_ = i * gw + 1.5 + h("cbx", *key) * jx + (gw // 2 if j % 2 else 0)
            py_ = j * gh + 0.5 + h("cby", *key) * jy
            d = math.hypot(gx + 0.5 - px_, (gy + 0.5 - py_) * sq)
            if d < best:
                second, best, sid, off = best, d, key, (gx + 0.5 - px_, (gy + 0.5 - py_) * sq)
            elif d < second:
                second = d
    return sid, off, second - best


def cobble_px(sh, x, y, gx, gy, view="iso"):
    """Path: irregular rounded stones lit from the top-left, dark mortar between; at the edge grass tufts creep in
    and a few loose stones lie out on the grass."""
    if not sh.inside(x, y):
        d = sh.dist(x, y, 3)
        if d <= 2.5 and h("loose", gx % 64, gy % 32) < 0.08:
            return "cb2"
        return None
    d = sh.dist(x, y, 3)
    if d <= 1.0:
        return "g3" if h("tuft", gx % 64, gy % 32) < 0.45 else "cb3"
    if d <= 2.0 and h("tuft2", gx % 64, gy % 32) < 0.15:
        return "g2"
    sid, (ox, oy), gap = _stone(gx, gy, view)
    if gap < 1.0:
        return "cb3"
    if ox + oy < -2.2:
        return "cb0"
    if ox + oy > 2.0:
        return "cb2"
    return "cb2" if h("cbs", *sid) < 0.22 else "cb1"


GREY_STONE = {"cb0": "cs0", "cb1": "cs1", "cb2": "cs2", "cb3": "cs3"}


def grey_cobble_px(sh, x, y, gx, gy, view="iso"):
    """Cobbles: the same rounded stones as the path, in cool grey."""
    c = cobble_px(sh, x, y, gx, gy, view)
    return GREY_STONE.get(c, c)


def dirt_px(sh, x, y, gx, gy):
    """Trampled earth: warm dirt with pebbles, thinning raggedly into the grass."""
    if not sh.inside(x, y):
        return None
    gx, gy = gx % 64, gy % 32
    d = sh.dist(x, y, 3)
    if d <= 1.0 and h("dthin", gx, gy) < 0.55:
        return None
    if d <= 2.0 and h("dtuft", gx, gy) < 0.2:
        return "g3"
    k = h("dirt", gx // 2, gy, 1)
    if h("peb", gx, gy) < 0.02:
        return "s0"
    return "d2" if k < 0.55 else "k0" if k < 0.8 else "d1"


def water_px(sh, x, y, gx, gy, f):
    """Water: a foam edge, ripple dashes drifting with the frame, the odd sparkle; a dark line and stones on the bank."""
    if not sh.inside(x, y):
        d = sh.dist(x, y, 4)
        if d <= 1.0:
            return "out"
        if d <= 2.5:
            return "s1" if h("bank", (gx % 64) // 2, (gy % 32) // 2) < 0.6 else "s2"
        if d <= 3.5 and h("bank2", (gx % 64) // 4, (gy % 32) // 2) < 0.35:
            return "s0"
        return None
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "w0" if (gx + gy + f) % 4 else "w1"
    if d <= 2.5:
        return "w2"
    if gy % 8 == 2 and (gx + (gy // 8) * 7 + f * 5) % 32 < 4:
        return "w1"
    return "w0" if h("spark", gx % 64, gy % 32, f) < 0.004 else "w2"
