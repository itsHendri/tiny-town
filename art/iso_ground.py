"""Isometric ground details, drawn in code: flower patches and crop plants (flat, part of the ground), and upright
things sorted with the props: fences that join their neighbours, gates, bridge rails and stairs up a cliff wall.

Upright pieces are sprites with an anchor at their cell's centre. Names start with "_" so the editor's catalog
leaves them out; the renderer picks them from the map's cells.
"""
import math

from dualgrid import h
from iso_props import Canvas3D, proj
from iso_market import finish
from sprites import RGB, Sprite

N_, E_, S_, W_ = 1, 2, 4, 8
HT = 16


# ---------- flat: flowers and crops, one 32x16 diamond per cell ----------

def diamond(fn):
    from PIL import Image
    im = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    px = im.load()
    for y in range(16):
        for x in range(32):
            if abs(x + 0.5 - 16) / 16 + abs(y + 0.5 - 8) / 8 <= 0.92:
                c = fn(x, y)
                if c:
                    px[x, y] = RGB[c]
    return im


def flowers_iso(variant):
    """A flower bed: round blooms on a jittered grid over dark leaves, filling the cell."""
    mixes = [("fl_p", "fl_w", "fl_y"), ("fl_y", "fl_o", "fl_w"), ("fl_w", "fl_p", "jf1"), ("fl_o", "fl_y", "fl_p")]
    cols = mixes[variant % 4]
    spots = []
    for j in range(5):
        for i in range(7):
            x, y = 3 + i * 4.3 + (2 if j % 2 else 0), 2 + j * 3
            x += h("fx", variant, i, j) * 2 - 1
            y += h("fy", variant, i, j) * 1.4 - 0.7
            if abs(x - 16) / 16 + abs(y - 8) / 8 < 0.8:
                spots.append((x, y, cols[int(h("fc", variant, i, j) * 3)]))

    def fn(x, y):
        best = None
        for (sx, sy, col) in spots:
            dx, dy = x + 0.5 - sx, (y + 0.5 - sy) * 1.6
            d2 = dx * dx + dy * dy
            if d2 <= 2.2:
                return ("fl_y" if col != "fl_y" else "fl_o") if d2 < 0.4 else col
            if d2 <= 5.5:
                best = "t3" if y > sy else "t2"
        return best
    return diamond(fn)


def crops_iso():
    """Leafy rows on tilled soil (the soil is the ground set; this is the plants)."""
    def fn(x, y):
        if (x + 2 * y) % 8 in (0, 1) and (x // 2 + y) % 3 == 0:
            return "t1" if (x + y) % 2 else "t2"
        if (x + 2 * y) % 8 == 2 and (x // 2 + y) % 3 == 0:
            return "t0"
        return None
    return diamond(fn)


# ---------- upright: fences, gates, rails, stairs ----------

def fence_iso(conn, style="rail"):
    """A post at the cell's centre and rails toward each joined neighbour (north is up-right on screen)."""
    cv = Canvas3D(40, 34, 20, 22)
    c = 8                                                  # the cell centre, in map pixels within the cell
    rail = lambda lit: (lambda s, t, su, tu: ("k0" if tu < 0.6 else "k1") if lit else ("k1" if tu < 0.6 else "k2"))
    for bit, (dx, dy) in ((N_, (0, -1)), (W_, (-1, 0)), (E_, (1, 0)), (S_, (0, 1))):
        if not conn & bit:
            continue
        for z in (3.5, 7):
            if dx:
                cv.face((c, c, z), (dx * 8.5, 0, 0), (0, 0, 1.6), rail(dy == 0 and dx > 0 or True))
            else:
                cv.face((c, c, z), (0, dy * 8.5, 0), (0, 0, 1.6), rail(False))
    # the post
    cv.face((c - 1, c + 1, 0), (2, 0, 0), (0, 0, 10), lambda s, t, su, tu: "k1")
    cv.face((c + 1, c + 1, 0), (0, -2, 0), (0, 0, 10), lambda s, t, su, tu: "k2")
    cv.face((c - 1, c - 1, 10), (2, 0, 0), (0, 2, 0), lambda s, t, su, tu: "k0")
    return finish_cell(cv)


def gate_iso(axis):
    """A gate between two posts; axis 'x' when the fence runs along columns, 'y' along rows."""
    cv = Canvas3D(40, 34, 20, 22)
    if axis == "x":
        for x in (0.5, 14):
            cv.face((x, 9, 0), (1.6, 0, 0), (0, 0, 11), lambda s, t, su, tu: "k1")
        cv.face((2, 8, 2), (12, 0, 0), (0, 0, 7), lambda s, t, su, tu: "k3" if abs(su / 12 * 7 - tu) < 0.9 or tu < 0.8 or tu > 6.2 or su < 0.8 or su > 11.2 else None)
    else:
        for y in (0.5, 14):
            cv.face((9, y, 0), (0, 1.6, 0), (0, 0, 11), lambda s, t, su, tu: "k2")
        cv.face((8, 2, 2), (0, 12, 0), (0, 0, 7), lambda s, t, su, tu: "k3" if abs(su / 12 * 7 - tu) < 0.9 or tu < 0.8 or tu > 6.2 or su < 0.8 or su > 11.2 else None)
    return finish_cell(cv)


def bridge_iso(axis, sides):
    """Bridge rails for one bridge cell: a low railing along each open side. axis: the way you cross."""
    cv = Canvas3D(40, 34, 20, 22)
    for side in sides:
        if axis == "x":
            y = 0.5 if side == "a" else 15
            for x in (1, 8, 15):
                cv.face((x, y, 0), (1.2, 0, 0), (0, 0, 7), lambda s, t, su, tu: "k2")
            cv.face((0, y, 6), (16, 0, 0), (0, 0, 1.6), lambda s, t, su, tu: "k1" if tu > 0.6 else "k0")
        else:
            x = 0.5 if side == "a" else 15
            for y in (1, 8, 15):
                cv.face((x, y, 0), (0, 1.2, 0), (0, 0, 7), lambda s, t, su, tu: "k2")
            cv.face((x, 0, 6), (0, 16, 0), (0, 0, 1.6), lambda s, t, su, tu: "k2" if tu > 0.6 else "k1")
    return finish_cell(cv)


def deck_iso(axis):
    """The bridge's planks (flat, drawn with the ground): boards across the way you cross."""
    def fn(x, y):
        dx, dy = x + 0.5 - 16, y + 0.5 - 8
        u, v = (dx + 2 * dy) / 2 + 8, (2 * dy - dx) / 2 + 8         # cell coordinates, 0..16
        along = v if axis == "x" else u
        k = int(along) % 4
        return "k0" if k == 0 else "k2" if k == 3 else "k1"
    return diamond(fn)


def stairs_iso(direction, lit=True):
    """Four steps climbing from a low cell up to the cell behind it. direction: where the high cell is, 'n'
    (up-right, a front-left wall) or 'w' (up-left, a front-right wall)."""
    cv = Canvas3D(44, 44, 22, 30)
    for k in reversed(range(4)):                           # back (highest) step first, so nearer steps cover it
        z = (k + 1) * HT / 4
        if direction == "n":
            y0 = 16 - (k + 1) * 4
            cv.face((1, y0 + 4, 0), (14, 0, 0), (0, 0, z), lambda s, t, su, tu: "k3" if tu > z - 1 else "k2")
            cv.face((1, y0, z), (14, 0, 0), (0, 4, 0), lambda s, t, su, tu: "k0" if tu < 1 else "k1")
            cv.face((15, y0 + 4, 0), (0, -4, 0), (0, 0, z), lambda s, t, su, tu: "k3")
        else:
            x0 = 16 - (k + 1) * 4
            cv.face((x0 + 4, 15, 0), (0, -14, 0), (0, 0, z), lambda s, t, su, tu: "k3" if tu > z - 1 else "k2")
            cv.face((x0, 1, z), (4, 0, 0), (0, 14, 0), lambda s, t, su, tu: "k0" if su < 1 else "k1")
            cv.face((x0, 15, 0), (4, 0, 0), (0, 0, z), lambda s, t, su, tu: "k2")
    return finish_cell(cv)


def finish_cell(cv):
    """Outline, and anchor at the cell's centre."""
    spr = cv.s
    out = Sprite(spr.w + 2, spr.h + 2)
    out.im.paste(spr.im, (1, 1))
    out.px = out.im.load()
    out.outline()
    sx_, sy_ = proj(8, 8, 0)
    out.anchor = (round(sx_ + cv.ox + 1), round(sy_ + cv.oy + 1))
    return out


def uprights():
    """Every upright ground piece, by the name the renderer asks for."""
    out = {}
    for conn in range(16):
        out[f"_fence-{conn}"] = fence_iso(conn)
    out["_gate-x"], out["_gate-y"] = gate_iso("x"), gate_iso("y")
    for axis in ("x", "y"):
        for sides in ("", "a", "b", "ab"):
            if sides:
                out[f"_rail-{axis}-{sides}"] = bridge_iso(axis, sides)
    out["_stairs-n"], out["_stairs-w"] = stairs_iso("n"), stairs_iso("w")
    return out


def flats():
    """Flat ground pieces (32x16 diamonds)."""
    return {**{f"flowers-{v}": flowers_iso(v) for v in range(4)}, "crops": crops_iso(), "deck-x": deck_iso("x"), "deck-y": deck_iso("y")}
