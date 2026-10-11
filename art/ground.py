"""Ground materials shared by the views, as screen-space pixel functions (gx, gy = map-wide screen pixel).

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
    """Meadow grass. flat: the big-repeat swells (flat grass cells); otherwise tufts only (64 x 32 tiles)."""
    n = swell(gx, gy, variant) if flat else 0.5
    t = stamps(gx, gy, ("gt", variant), 8, 8, TUFTS, 0.3 + 0.4 * n)
    if t:
        if n > 0.6:
            return "g0" if t == "a" else "gh"
        return "gh" if t == "a" else "g2"
    return "g1l" if n > 0.64 else "g1d" if n < 0.36 else "g1"
