"""Isometric drawing. The map data is unchanged (a grid of cells with heights, ground and objects); only the view
changes: each cell is a 32x16 diamond, and every level lifts the ground by 16 px.

Ground tiles are still dual-grid (16 shapes per terrain, round corners): an isometric display tile is the same
square as before, seen at an angle, so each pixel is traced back to the square and asks the existing Shape
whether it is inside. Colours are worked out in screen space so the pixels stay crisp.

Cliffs: for every level above 0, the outline of that level's ground is pushed straight down 16 px, which gives
both visible walls (front-left lit, front-right in shade) with the corners already round. Raised cells and
objects are drawn back to front, cell by cell, so things in front always cover things behind.

    python art/iso.py sample <out.png> [bright|earthy]
"""
import math
import sys
from functools import lru_cache

from PIL import Image, ImageDraw

from dualgrid import Shape, cell_mask, h


def ihash(*xs):
    """A tiny integer hash in [0, 1), the same in js/iso.js (used for the cliff walls' grass drips and waterfall streaks)."""
    v = 0
    for x in xs:
        v = ((v ^ (x & 0xffffffff)) * 2654435761) & 0xffffffff
    return v / 2 ** 32
from sprites import RGB, Sprite

CW, CH = 32, 16          # a cell's diamond
HT = 16                  # height of one level in screen pixels
R = 7                    # corner radius (round corners, as picked)


# ---------- projection: map pixels (u along columns, v along rows, 16 per cell) <-> screen ----------

def to_screen(u, v, level=0):
    return u - v, (u + v) / 2 - level * HT


def cell_top(c, r, level=0):
    """The north corner of cell (c, r)'s diamond, in screen pixels (before the map offset)."""
    return (c - r) * 16, (c + r) * 8 - level * HT


# ---------- dual-grid display tiles in iso ----------

class IsoShape:
    """Screen-space view of a dual-grid Shape: inside(x, y) for pixel offsets from the display tile's centre.
    Inside-ness and distances to the edge are worked out once per shape and kept."""
    _cache = {}

    def __new__(cls, mask, radius=R):
        key = (mask, radius)
        if key not in cls._cache:
            o = super().__new__(cls)
            o._build(mask, radius)
            cls._cache[key] = o
        return cls._cache[key]

    def _build(self, mask, radius):
        self.s = Shape(mask, radius)
        self.ins = {}
        for y in range(-16, 17):
            for x in range(-26, 27):
                dx, dy = x + 0.5, y + 0.5
                self.ins[x, y] = self.s.inside(math.floor((dx + 2 * dy) / 2 + 8), math.floor((2 * dy - dx) / 2 + 8))
        self.dists = {}

    def inside(self, x, y):
        return self.ins.get((x, y), False)

    def dist(self, x, y, k=5):
        key = (x, y)
        if key not in self.dists:
            me = self.inside(x, y)
            best = 99
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    d2 = dx * dx + dy * dy
                    if d2 < best * best and self.inside(x + dx, y + dy) != me:
                        best = math.sqrt(d2)
            self.dists[key] = best
        return self.dists[key]

    def edge(self, x, y):
        """Which way the outside is, for an inside pixel: a set of 'n', 's', 'e', 'w' (screen directions)."""
        out = set()
        for d, (dx, dy) in (("n", (0, -1)), ("s", (0, 1)), ("e", (1, 0)), ("w", (-1, 0))):
            if not self.inside(x + dx, y + dy):
                out.add(d)
        return out


def in_tile(x, y):
    """Is pixel (x, y) of a 32x16 tile box inside the diamond?"""
    dx, dy = x + 0.5 - 16, y + 0.5 - 8
    return abs(dx) / 16 + abs(dy) / 8 <= 1.0


def sx(x, y, ox, oy):
    """Screen coordinates (map-wide pattern space) of a tile pixel."""
    return x + ox, y + oy


# ---------- colours for each terrain, in screen space (gx, gy = map-wide screen pixel) ----------

def grass_px(gx, gy, variant=0):
    """Meadow grass: blades in small strokes, darker clumps, lighter sunny patches, the odd tiny flower."""
    gx, gy = gx % 64, gy % 32
    patch = h("gp", gx // 8, gy // 4, variant)                # sunny or shaded patches, 8x4 px
    k = h("gt", gx // 2, gy // 2, variant)
    if h("gf", gx, gy, variant) < 0.006:
        return "fl_w" if h("gfc", gx, gy) < 0.6 else "fl_y"
    if k < 0.07 or (patch < 0.18 and k < 0.3):
        return "g3"
    if k < 0.18:
        return "g2"
    if patch > 0.82 and k > 0.6:
        return "g0"
    return "g1"


def _stone(gx, gy):
    """Irregular rounded cobbles (a jittered grid of stone centres, repeating every 48 px): returns the nearest
    stone's id, the offset from its centre, and how close the pixel is to the mortar line."""
    i0, j0 = gx // 8, gy // 4
    best = second = 99.0
    sid = off = None
    for j in range(j0 - 1, j0 + 2):
        for i in range(i0 - 1, i0 + 2):
            key = (i % 8, j % 8)
            px_ = i * 8 + 1.5 + h("cbx", *key) * 5 + (4 if j % 2 else 0)
            py_ = j * 4 + 0.5 + h("cby", *key) * 3
            d = math.hypot(gx + 0.5 - px_, (gy + 0.5 - py_) * 1.6)
            if d < best:
                second, best, sid, off = best, d, key, (gx + 0.5 - px_, gy + 0.5 - py_)
            elif d < second:
                second = d
    return sid, off, second - best


def cobble_px(sh, x, y, gx, gy):
    """Cobblestones: irregular rounded stones lit from the top-left, dark mortar between; at the edge grass tufts
    creep in and a few loose stones lie out on the grass."""
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
    sid, (ox, oy), gap = _stone(gx, gy)
    if gap < 1.0:
        return "cb3"
    if ox + oy * 1.6 < -2.2:
        return "cb0"
    if ox + oy * 1.6 > 2.0:
        return "cb2"
    return "cb2" if h("cbs", *sid) < 0.22 else "cb1"


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


def soil_px(sh, x, y, gx, gy):
    if not sh.inside(x, y):
        return "g4" if sh.dist(x, y, 2) <= 1.0 else None
    if sh.dist(x, y, 2) <= 1.0:
        return "k3"
    return "k2" if (gx + 2 * gy) % 8 < 4 else "k3"           # furrows run along the diamond


def tallgrass_px(sh, x, y, gx, gy, f):
    if not sh.inside(x, y):
        return None
    sway = (0, 1, 0)[f % 3]
    t = ["..0.", ".010", "0121", "3223"][gy % 4][(gx + (gy // 4 % 2) * 2 - (sway if gy % 4 < 2 else 0)) % 4]
    if sh.dist(x, y, 2) <= 1.0 and t in ".3":
        return None
    return {"0": "t0", "1": "t1", "2": "t2", "3": "t3", ".": "t2"}[t]


def raised_fill_px(sh, x, y, gx, gy):
    return grass_px(gx, gy, 1) if sh.inside(x, y) else None


def raised_edge_px(sh, x, y, gx, gy):
    if not sh.inside(x, y):
        return None
    e = sh.edge(x, y)
    if not e:
        return None
    if "s" in e:
        return None                                           # the wall below draws this edge
    if "n" in e:
        return "g0"                                           # lit back edge
    return "out"


SETS = {
    "raised_fill": lambda sh, x, y, gx, gy, f: raised_fill_px(sh, x, y, gx, gy),
    "raised_edge": lambda sh, x, y, gx, gy, f: raised_edge_px(sh, x, y, gx, gy),
    "water": water_px,
    "dirt": lambda sh, x, y, gx, gy, f: dirt_px(sh, x, y, gx, gy),
    "soil": lambda sh, x, y, gx, gy, f: soil_px(sh, x, y, gx, gy),
    "path": lambda sh, x, y, gx, gy, f: cobble_px(sh, x, y, gx, gy),
    "cobbles": lambda sh, x, y, gx, gy, f: cobble_px(sh, x, y, gx, gy),
    "tallgrass": tallgrass_px,
}
ANIMATED = {"water", "tallgrass"}


def phase_of(dx, dy):
    """The tile lattice repeats every 4 cells: (dx - dy) % 4 and (dx + dy) % 4 pick one of 8 pattern phases."""
    return (dx - dy) % 4, (dx + dy) % 4


@lru_cache(maxsize=None)
def iso_tile(name, mask, frame, phase):
    """A 32x16 display tile for the grid corner whose lattice phase is `phase`. Patterns use world screen pixels
    (repeating every 64 x 32), so tiles in the same phase are identical and neighbours join up."""
    sh = IsoShape(mask)
    a, b = phase
    ox, oy = (a * 16 - 16) % 64, (b * 8 - 8) % 32
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    px = im.load()
    fn = SETS[name]
    for y in range(-4, CH + 4):                               # banks may reach a few pixels past the diamond
        for x in range(-4, CW + 4):
            if not (0 <= x < CW and 0 <= y < CH):
                continue
            c = fn(sh, x - 16, y - 8, x + ox, y + oy, frame)
            if c is not None:
                px[x, y] = RGB[c] if isinstance(c, str) else c
    return im


@lru_cache(maxsize=None)
def grass_cell(phase):
    a, b = phase
    ox, oy = (a * 16 - 16) % 64, (b * 8) % 32
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    px = im.load()
    for y in range(CH):
        for x in range(CW):
            if in_tile(x, y):
                px[x, y] = RGB[grass_px(x + ox, y + oy)]
    return im


# ---------- the renderer ----------

class IsoMap:
    """Same data as preview.Map (terrain names, heights, features, fence/deco, objects at map pixels)."""


MARGIN_TREES = ["tree-1-d1", "tree-3-d1", "tree-5-d2", "pine-1", "pine-2", "tree-2-d2", "pine-3", "tree-4-d1"]


def render(m, frame=0, objects=True, margin=0):
    """Draw a preview.Map in isometric. Returns an RGBA image. `margin` cells of meadow and darker forest are
    drawn around the map so it fills the frame (they aren't part of the map)."""
    cols, rows = m.cols, m.rows
    top = max(max(row) for row in m.height)
    M = margin
    X0 = (rows + 2 * M) * 16 + 8                             # screen x of map column/row 0's north corner
    Y0 = top * HT + 24 + 16 * M
    W = (cols + rows + 4 * M) * 16 + 16
    Hh = (cols + rows + 2 * M) * 8 + Y0 + 24

    def blank():
        return Image.new("RGBA", (W, Hh), (0, 0, 0, 0))

    def put(layer, im, x, y):
        layer.alpha_composite(im, (int(x), int(y))) if x >= 0 and y >= 0 else layer.paste(im, (int(x), int(y)), im)

    def dual(layer, name, cells, level, ext=0):
        for dy in range(-ext, rows + 1 + ext):
            for dx in range(-ext, cols + 1 + ext):
                mask = cell_mask(cells, dy, dx)
                if not mask:
                    continue
                cx, cy = cell_top(dx, dy, level)              # the grid corner (dx, dy) is the display tile's centre
                X, Y = X0 + cx - 16, Y0 + cy - 8
                t = iso_tile(name, mask, frame if name in ANIMATED else 0, phase_of(dx, dy))
                put(layer, t, X, Y)

    from iso_ground import flats, uprights
    FL, UP = _cached(flats), _cached(uprights)

    def dual_ext(layer, name, ext, M):
        """A dual-grid set over a grid that reaches M cells past the map on every side."""
        for dy in range(-M, rows + M + 1):
            for dx in range(-M, cols + M + 1):
                mask = cell_mask(ext, dy + M, dx + M)
                if mask:
                    cx, cy = cell_top(dx, dy, 0)
                    put(layer, iso_tile(name, mask, frame if name in ANIMATED else 0, phase_of(dx, dy)), X0 + cx - 16, Y0 + cy - 8)

    def overlays(layer, level):
        for name in ("dirt", "water", "soil", "path", "cobbles"):
            dual(layer, name, m.cells(name, level), level)
        dual(layer, "tallgrass", m.cells("tallgrass", level), level)
        for r in range(rows):                                # flat things on single cells: flowers, crops, bridge decks
            for c in range(cols):
                if m.height[r][c] != level:
                    continue
                x, y = cell_top(c, r, level)
                X, Y = X0 + x - 16, Y0 + y
                if m.deco[r][c] == "flowers":
                    put(layer, FL[f"flowers-{(r * 5 + c * 11) % 13 * 4 // 13}"], X, Y)
                if m.terrain[r][c] == "soil":
                    put(layer, FL["crops"], X, Y)
                if m.terrain[r][c] == "bridge":
                    put(layer, FL[f"deck-{bridge_axis(m, r, c)}"], X, Y)

    # the margin: meadow round the map, a little darker
    outside = blank()
    if M:
        for r in range(-M, rows + M):
            for c in range(-M, cols + M):
                if 0 <= c < cols and 0 <= r < rows:
                    continue
                x, y = cell_top(c, r)
                put(outside, grass_cell(phase_of(c, r)), X0 + x - 16, Y0 + y)
        for name in ("water", "path", "cobbles"):            # roads and rivers run on out into the forest
            dual_ext(outside, name, margin_cells(m.cells(name, 0), M), M)
        shade = Image.new("RGBA", outside.size, (34, 40, 18, 70))
        outside = Image.composite(Image.alpha_composite(outside, shade), outside, outside.getchannel("A"))

    # level 0: grass, then its overlays
    base = blank()
    for r in range(rows):
        for c in range(cols):
            x, y = cell_top(c, r)
            X, Y = X0 + x - 16, Y0 + y
            put(base, grass_cell(phase_of(c, r)), X, Y)
    overlays(base, 0)
    clip_to_map(base, cols, rows, X0, Y0, 0)

    # every level above: its top (grass, overlays, edge) and its wall, on its own layer
    levels = {}
    for L in range(1, top + 1):
        lay = blank()
        cells = m.cells("raised_fill", L)
        dual(lay, "raised_fill", cells, L)
        overlays(lay, L)
        dual(lay, "raised_edge", cells, L)
        fill = blank(); dual(fill, "raised_fill", cells, L)
        clip_to_map(lay, cols, rows, X0, Y0, L)
        clip_to_map(fill, cols, rows, X0, Y0, L)
        walls(lay, fill, m, L, X0, Y0, frame)
        levels[L] = lay

    # back to front: each raised cell's column (its level layers, clipped), then the objects standing there
    out = outside
    out.alpha_composite(base)
    items = []
    for r in range(rows):
        for c in range(cols):
            if m.height[r][c] > 0:
                items.append((c + r, 0, "cell", (c, r)))
    RUNS = [margin_cells(m.cells(n, 0), M) for n in ("water", "path", "cobbles")] if M else []
    if objects and M:                                         # the forest round the edge
        from iso_nature import nature
        NAT = _cached(nature)
        for r in range(-M, rows + M):
            for c in range(-M, cols + M):
                if (0 <= c < cols and 0 <= r < rows) or ihash(c & 0xffff, r & 0xffff, 11) >= 0.45:
                    continue
                if any(ext[r + M][c + M] for ext in RUNS):
                    continue                                  # keep the road or river leaving the map clear
                spr = NAT[MARGIN_TREES[int(ihash(c & 0xffff, r & 0xffff, 13) * len(MARGIN_TREES))]]
                items.append((c + r, 1, "obj", (spr, c * 16 + 8, (r + 1) * 16, 0)))
    for spr, c, r in upright_items(m, UP):                     # fences, gates, bridge rails, stairs
        items.append((c + r, 0.5, "obj", (spr, c * 16 + 8, (r + 1) * 16, m.height[r][c])))
    if objects:
        for k, (spr, u, v) in enumerate(m.objects):
            c, r = int(u // 16), int((v - 1) // 16)
            items.append((c + r, 1, "obj", (spr, u, v, m.height[min(rows - 1, max(0, r))][min(cols - 1, max(0, c))])))
    items.sort(key=lambda it: (it[0], it[1]))
    for _, _, kind, data in items:
        if kind == "cell":
            c, r = data
            for L in range(1, m.height[r][c] + 1):
                x, y = cell_top(c, r, L)
                X, Y = X0 + x, Y0 + y
                bx, by = X - 17, Y - 1
                piece = levels[L].crop((bx, by, bx + 34, by + 18 + HT))
                pp = piece.load()
                for j in range(piece.height):
                    for i in range(piece.width):
                        if not in_column(bx + i, by + j, X, Y):
                            pp[i, j] = (0, 0, 0, 0)
                out.alpha_composite(piece, (bx, by))
        else:
            spr, u, v, lvl = data
            x, y = to_screen(u, v - 8, lvl)
            X, Y = X0 + x, Y0 + y
            place(out, spr, X, Y)
    return out


_CACHE = {}


def _cached(fn):
    if fn.__name__ not in _CACHE:
        _CACHE[fn.__name__] = fn()
    return _CACHE[fn.__name__]


def bridge_axis(m, r, c):
    """'x' when the bridge crosses along columns (land or bridge to its left or right), else 'y'."""
    at = lambda rr, cc: m.terrain[min(m.rows - 1, max(0, rr))][min(m.cols - 1, max(0, cc))]
    return "x" if at(r, c - 1) != "water" or at(r, c + 1) != "water" else "y"


def upright_items(m, UP):
    """(sprite, c, r) for every fence, gate, bridge rail and stairs, to be sorted with the props."""
    out = []
    fence = lambda rr, cc, lv: 0 <= rr < m.rows and 0 <= cc < m.cols and (m.fence[rr][cc] or m.deco[rr][cc] == "gate") and m.height[rr][cc] == lv
    for r in range(m.rows):
        for c in range(m.cols):
            lv = m.height[r][c]
            if m.deco[r][c] == "gate":
                out.append((UP["_gate-x" if fence(r, c - 1, lv) or fence(r, c + 1, lv) else "_gate-y"], c, r))
            elif m.fence[r][c]:
                conn = (1 if fence(r - 1, c, lv) else 0) | (2 if fence(r, c + 1, lv) else 0) | (4 if fence(r + 1, c, lv) else 0) | (8 if fence(r, c - 1, lv) else 0)
                out.append((UP[f"_fence-{conn}"], c, r))
            if m.terrain[r][c] == "bridge":
                axis = bridge_axis(m, r, c)
                at = lambda rr, cc: m.terrain[min(m.rows - 1, max(0, rr))][min(m.cols - 1, max(0, cc))]
                sides = ("a" if at(r - 1, c) != "bridge" else "") + ("b" if at(r + 1, c) != "bridge" else "") if axis == "x" else \
                        ("a" if at(r, c - 1) != "bridge" else "") + ("b" if at(r, c + 1) != "bridge" else "")
                if sides:
                    out.append((UP[f"_rail-{axis}-{sides}"], c, r))
            if m.feature[r][c] == "stairs":
                if r > 0 and m.height[r - 1][c] == lv + 1:
                    out.append((UP["_stairs-n"], c, r))
                elif c > 0 and m.height[r][c - 1] == lv + 1:
                    out.append((UP["_stairs-w"], c, r))
    return out


RUN_ON = 3                       # how far roads and rivers run on into the margin, in cells


def margin_cells(cells, M):
    """The map's cells plus M cells round it. Outside, a cell copies the nearest edge cell only where the ground
    crosses the edge (the edge cell and the one two steps further in agree), so a road or river leaving the map
    runs on, but one running along the edge doesn't spread into a lake."""
    rows, cols = len(cells), len(cells[0])
    out = [[False] * (cols + 2 * M) for _ in range(rows + 2 * M)]
    for r in range(-M, rows + M):
        for c in range(-M, cols + M):
            if 0 <= r < rows and 0 <= c < cols:
                v = cells[r][c]
            else:
                rc, cc = min(rows - 1, max(0, r)), min(cols - 1, max(0, c))
                if max(abs(r - rc), abs(c - cc)) > RUN_ON:
                    continue                                   # past that, the forest takes over
                ri = rc + (2 if r < 0 else -2 if r >= rows else 0)
                ci = cc + (2 if c < 0 else -2 if c >= cols else 0)
                v = cells[rc][cc] and cells[min(rows - 1, max(0, ri))][min(cols - 1, max(0, ci))]
            out[r + M][c + M] = v
    return out


def clip_to_map(layer, cols, rows, X0, Y0, level):
    """Keep only what lies over the map: a pixel stays if its centre traces back inside the grid (same rule in JS)."""
    W, Hh = layer.size
    a = layer.getchannel("A")
    ap = a.load()
    for y in range(Hh):
        for x in range(W):
            if not ap[x, y]:
                continue
            dx, dy = x + 0.5 - X0, y + 0.5 - Y0 + level * HT
            u, v = (dx + 2 * dy) / 2, (2 * dy - dx) / 2
            if not (0 <= u < cols * 16 and 0 <= v < rows * 16):
                ap[x, y] = 0
    layer.putalpha(a)


def in_column(px, py, x, y):
    """Is pixel (px, py) in the column of the cell whose top corner is at (x, y): its diamond and the wall below?"""
    dx, dy = abs(px + 0.5 - x), py + 0.5 - y
    return dx <= 16 and dx / 2 <= dy <= 16 + HT - dx / 2


def walls(lay, fill, m, L, X0, Y0, frame):
    """Push the level's outline down HT pixels. Where the edge runs down to the right it is the front-left wall
    (lit), where it runs up to the right the front-right wall (in shade). Water at the edge falls as a waterfall."""
    W, Hh = lay.size
    fa = fill.getchannel("A").load()
    lp = lay.load()
    water = {RGB[k][:3] for k in ("w0", "w1", "w2", "w3")}
    bottoms = {}                                             # x -> list of bottom-edge ys
    for x in range(W):
        for y in range(Hh - 1):
            if fa[x, y] and not fa[x, y + 1]:
                bottoms.setdefault(x, []).append(y)

    def near(xx, y):
        ys = [b for b in bottoms.get(xx, []) if abs(b - y) <= 6]
        return min(ys, key=lambda b: abs(b - y)) if ys else None

    for x, ys in bottoms.items():
        for y in ys:
            a, b = near(x - 2, y), near(x + 2, y)
            slope = (b - a) if a is not None and b is not None else (b - y if b is not None else y - a if a is not None else 0)
            light = "left" if slope > 0 else "right" if slope < 0 else "tip"
            is_water = lp[x, y][:3] in water
            for k in range(1, HT + 1):
                yy = y + k
                if yy >= Hh or fa[x, yy]:
                    break
                if is_water:
                    ph = (k - 2 * frame + int(ihash(x, 7) * 6)) % 6
                    col = "w0" if ph == 0 or k == 1 else "w1" if ph < 3 else "w2"
                elif k == HT:
                    col = "out"
                elif k == 1:
                    col = "g3"
                elif k == 2 and ihash(x, 3) < 0.5:
                    col = "g4"
                else:
                    band = (k + int(2 * math.sin(x * 0.5)) + 64) % 6
                    lo, hi = {"left": ("k1", "k2"), "tip": ("k2", "k2"), "right": ("k2", "k3")}[light]
                    col = "k3" if band == 0 else lo if k < 9 else hi
                lp[x, yy] = RGB[col]
            if is_water:
                for k in range(HT + 1, HT + 4):
                    if y + k < Hh and not fa[x, y + k]:
                        lp[x, y + k] = RGB["w0" if (x + k + frame) % 3 else "fl_w"]
    # a dark line down both ends of every wall
    for x, ys in bottoms.items():
        for y in ys:
            for side in (-1, 1):
                xx = x + side
                if 0 <= xx < W and near(xx, y) is None:
                    for k in range(1, HT + 1):
                        if y + k < Hh and not fa[x, y + k]:
                            lp[x, y + k] = RGB["out"]


def place(canvas, spr, X, Y):
    """A sprite with its feet at screen (X, Y), with a soft shadow. A building (a sprite with an `anchor`) is placed
    so its anchor (its front cell's centre) lands on (X, Y), without a shadow."""
    if getattr(spr, "anchor", None):
        left, top = int(round(X - spr.anchor[0])), int(round(Y - spr.anchor[1]))
        canvas.alpha_composite(spr.im, (left, top))
        if getattr(spr, "smoke", None):
            sm = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(sm)
            for k in range(3):
                rise = k * 6
                r = 2 + rise * 0.12
                cx, cy = left + spr.smoke[0] + rise * 0.35, top + spr.smoke[1] - 3 - rise
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(236, 232, 222, int(255 * (0.7 - rise / 26))))
            canvas.alpha_composite(sm)
        return
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((X - spr.w * 0.42, Y - 3, X + spr.w * 0.46, Y + 2), fill=(30, 22, 16, 70))
    canvas.alpha_composite(sh)
    canvas.alpha_composite(spr.im, (int(X - spr.w / 2), int(Y - spr.h)))


if __name__ == "__main__":
    import palettes
    palettes.use(sys.argv[3] if len(sys.argv) > 3 else "bright")
    import preview
    from sprites import bush, pine, tree
    m = preview.Map(14, 12)
    m.fill("height", 1, 8, 6, 13, 1)
    m.fill("height", 2, 10, 4, 13, 2)
    m.fill("terrain", 6, 0, 8, 14, "path")
    m.fill("terrain", 0, 4, 6, 6, "path")
    m.fill("terrain", 8, 2, 11, 6, "water")
    m.fill("terrain", 2, 9, 4, 10, "water")
    m.fill("terrain", 1, 1, 4, 3, "soil")
    for r in range(9, 12):
        for c in range(8, 13):
            m.deco[r][c] = "tallgrass"
    m.objects += [(tree("a", 1.0), 2 * 16 + 8, 6 * 16), (pine("b"), 12 * 16 + 8, 1 * 16), (tree("c", 0.9), 7 * 16 + 8, 10 * 16),
                  (bush("d"), 6 * 16 + 8, 2 * 16), (tree("e", 1.1), 11 * 16 + 8, 3 * 16)]
    im = render(m, 0)
    im.save(sys.argv[2])
    print("wrote", sys.argv[2], im.size)
