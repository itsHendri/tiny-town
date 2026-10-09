"""Dual-grid autotiling: the shapes behind every terrain tile.

You paint one terrain per cell. Tiles are drawn on a second grid shifted by half a tile, so each 16x16 display
tile sits where 4 cells meet. Those 4 corners make a 4-bit mask (top-left 1, top-right 2, bottom-left 4,
bottom-right 8), and the mask picks one of 16 tiles. Cell edges run through the middle of the display tiles,
so the only corner a tile ever has is at its centre, and that corner is rounded here with a fixed radius.

    Shape(mask, radius)        which pixels of one display tile are inside the terrain, plus distances to the edge
    shape_canvas(cells, radius) the rounded shape of a whole grid of True/False cells, as rows of booleans
"""
import hashlib
import math

T = 16                      # tile size in pixels
TL, TR, BL, BR = 1, 2, 4, 8
PAD = 16                    # the shape is worked out on a 48x48 canvas, the tile is its middle
N = T + 2 * PAD
MAXD = 9                    # distances are exact up to 8 px (the nearest edge outside the tile is 8 px away)


def h(*key):
    """A stable random number in [0, 1) for any key (same key, same number, every run)."""
    return int(hashlib.md5(repr(key).encode()).hexdigest()[:8], 16) / 2 ** 32


def _disk(r):
    k = int(math.ceil(r))
    return [(dx, dy) for dy in range(-k, k + 1) for dx in range(-k, k + 1) if dx * dx + dy * dy <= r * r + 0.5]


def _morph(a, offs, want):
    """Erode (want=True: every pixel under the disk must be set) or dilate (want=False: any pixel)."""
    n = len(a)
    out = [[False] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if want:
                out[y][x] = all(a[min(n - 1, max(0, y + dy))][min(n - 1, max(0, x + dx))] for dx, dy in offs)
            else:
                out[y][x] = any(a[min(n - 1, max(0, y + dy))][min(n - 1, max(0, x + dx))] for dx, dy in offs)
    return out


_OFFS = sorted(((dx, dy) for dy in range(-MAXD, MAXD + 1) for dx in range(-MAXD, MAXD + 1) if 0 < dx * dx + dy * dy <= MAXD * MAXD),
               key=lambda o: o[0] * o[0] + o[1] * o[1])
_CACHE = {}


class Shape:
    """The inside of one display tile for a corner mask. Corners are rounded with `radius`: outer corners by an
    opening, inner corners by a closing. The two diagonal masks (6 and 9) stay two separate rounded corners."""

    def __new__(cls, mask, radius):
        key = (mask, radius)
        if key not in _CACHE:
            _CACHE[key] = super().__new__(cls)
            _CACHE[key]._build(mask, radius)
        return _CACHE[key]

    def _build(self, mask, radius):
        c = N // 2
        a = [[bool(mask & ((TL if x < c else TR) if y < c else (BL if x < c else BR))) for x in range(N)] for y in range(N)]
        if radius > 0 and mask not in (0, 15):
            d = _disk(radius)
            a = _morph(_morph(a, d, True), d, False)                       # opening: round the outer corners
            if mask not in (6, 9):
                a = _morph(_morph(a, d, False), d, True)                   # closing: round the inner corners
        self.mask, self.radius, self.a = mask, radius, a
        self._din, self._dout = {}, {}

    def inside(self, x, y):
        """Tile coordinates; works up to 16 px outside the tile."""
        X, Y = min(N - 1, max(0, x + PAD)), min(N - 1, max(0, y + PAD))
        return self.a[Y][X]

    def dist(self, x, y):
        """Distance (px, between pixel centres) to the nearest pixel on the other side of the edge; 99 if over 9."""
        me = self.inside(x, y)
        for dx, dy in _OFFS:
            if self.inside(x + dx, y + dy) != me:
                return math.sqrt(dx * dx + dy * dy)
        return 99

    def up(self, x, y, k=4):
        """How many pixels up to the first pixel on the other side (1 = right above), or 0 if none within k."""
        me = self.inside(x, y)
        for j in range(1, k + 1):
            if self.inside(x, y - j) != me:
                return j
        return 0

    def side(self, x, y):
        """True if the pixel to the left or right is on the other side."""
        me = self.inside(x, y)
        return self.inside(x - 1, y) != me or self.inside(x + 1, y) != me


def cell_mask(cells, r, c):
    """The corner mask of the display tile at the top-left corner of cell (r, c). Off-map cells copy the nearest."""
    rows, cols = len(cells), len(cells[0])
    at = lambda rr, cc: cells[min(rows - 1, max(0, rr))][min(cols - 1, max(0, cc))]
    return (TL if at(r - 1, c - 1) else 0) | (TR if at(r - 1, c) else 0) | (BL if at(r, c - 1) else 0) | (BR if at(r, c) else 0)


def shape_canvas(cells, radius):
    """The rounded shape of a grid of booleans, one boolean per pixel (cells * 16)."""
    rows, cols = len(cells), len(cells[0])
    W, H = cols * T, rows * T
    px = [[False] * W for _ in range(H)]
    for dy in range(rows + 1):
        for dx in range(cols + 1):
            s = Shape(cell_mask(cells, dy, dx), radius)
            x0, y0 = dx * T - T // 2, dy * T - T // 2
            for y in range(T):
                for x in range(T):
                    X, Y = x0 + x, y0 + y
                    if 0 <= X < W and 0 <= Y < H:
                        px[Y][X] = s.a[y + PAD][x + PAD]
    return px
