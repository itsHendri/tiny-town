"""Draw a small map with a chosen style, in Python (the browser renderer does the same with the tile sheet).
Used to compare tile styles side by side.

    python art/preview.py options <out_dir>     one animated PNG per style option, on the same sample scene
"""
import sys
from pathlib import Path

from dualgrid import T, cell_mask
from sprites import Sprite, bush, house, pine, place, rock, tree
from styles import ANIMATED, FENCE, SHARED, bridge_tile, cliff_piece, crop_tile, flower_tile, gate_tile, grass_cell_top, side_stairs, terrain_tile

# picked 2026-10-09 (tiles round 1); 2026-10-11: path and water shared with isometric (art/ground.py)
DEFAULT = {"radius": 7, "path": "stones", "water": "shared", "cliff": "earth", "fence": "rail", "side": "earth"}
# The dual-grid sets in the tile sheet: (name, which style key picks its look; None = its only style)
SETS = [("raised_shadow", None), ("raised_fill", None), ("raised_edge", None), ("dirt", None), ("water", "water"), ("soil", None),
        ("path", "path"), ("cobbles", None), ("tallgrass", None)]
OVERLAYS = ["dirt", "water", "soil", "path", "cobbles"]          # drawn on each level, in this order (js/registry.js)
STYLE_OF = {"raised_shadow": "grass", "raised_fill": "tufts", "raised_edge": "grass", "cobbles": "grey", "dirt": "trodden",
            "soil": "tilled", "tallgrass": "meadow"}
GRASS_N = 16                     # top-down flat grass repeats every 16 x 16 cells (styles.grass_cell_top)
FRAMES = 3
MAX_LEVEL = 4


class Map:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.terrain = [["grass"] * cols for _ in range(rows)]  # grass, path, cobbles, water, soil, bridge
        self.height = [[0] * cols for _ in range(rows)]          # 0 .. MAX_LEVEL
        self.feature = [[None] * cols for _ in range(rows)]     # stairs
        self.fence = [[False] * cols for _ in range(rows)]
        self.deco = [[None] * cols for _ in range(rows)]        # flowers, tallgrass, gate (fences live in self.fence)
        self.objects = []                                        # (sprite, x, y): feet at x, y

    def fill(self, layer, r0, c0, r1, c1, value):
        for r in range(max(0, r0), min(self.rows, r1)):
            for c in range(max(0, c0), min(self.cols, c1)):
                getattr(self, layer)[r][c] = value

    def cells(self, name, level):
        """Which cells feed a set on one level. Overlays only join cells on the same level."""
        if name.startswith("raised"):
            return [[v >= level for v in row] for row in self.height]
        if name == "tallgrass":
            return [[dv == "tallgrass" and hh == level for dv, hh in zip(drow, hrow)] for drow, hrow in zip(self.deco, self.height)]
        want = {"water": ("water", "bridge")}.get(name, (name,))
        # stairs belong to the level above too, so a path runs on into its stairs instead of stopping at the lip
        return [[t in want and (hh == level or (f == "stairs" and hh == level - 1)) for t, hh, f in zip(trow, hrow, frow)]
                for trow, hrow, frow in zip(self.terrain, self.height, self.feature)]


def to_json(m):
    """The map's cell layers as the browser's numbers (for checking the two renderers draw the same pixels)."""
    T_ = {"grass": 0, "path": 1, "cobbles": 2, "water": 3, "soil": 4, "bridge": 5, "dirt": 6}
    D_ = {"flowers": 2, "tallgrass": 3, "gate": 4}
    flat = lambda g: [v for row in g for v in row]
    return {"cols": m.cols, "rows": m.rows, "H": flat(m.height), "T": [T_[t] for t in flat(m.terrain)],
            "F": [1 if f == "stairs" else 0 for f in flat(m.feature)],
            "D": [1 if f else D_.get(d, 0) for f, d in zip(flat(m.fence), flat(m.deco))]}


def is_face(m, r, c, level):
    """A cliff face of `level` stands on cell (r, c): the cell above is at least that high, this one lower."""
    return 0 < r < m.rows and 0 <= c < m.cols and m.height[r - 1][c] >= level > m.height[r][c]


def render(m, style, frame=0):
    """Bottom up, one level at a time: level 0's ground and overlays; then for each level above: its shadow, grass,
    overlays and edge, and the cliff faces under its south edges (which stand on the level below)."""
    P = 16                                                       # padding, so tiles can hang over the edge
    cv = Sprite(m.cols * T + 2 * P, m.rows * T + 2 * P)
    put = lambda im, x, y: cv.im.alpha_composite(im, (P + x, P + y))

    def dual(name, level):
        cells = m.cells(name, level)
        st = style[dict(SETS)[name]] if dict(SETS)[name] else STYLE_OF[name]
        for dy in range(m.rows + 1):
            for dx in range(m.cols + 1):
                mask = cell_mask(cells, dy, dx)
                if mask:
                    phase = (dx % 4, dy % 2) if (name, st) in SHARED else None
                    put(terrain_tile(name, st, mask, style["radius"], frame if name in ANIMATED else 0, 0, phase).im,
                        dx * T - T // 2, dy * T - T // 2)

    def singles(level):
        at = lambda rr, cc: m.terrain[min(m.rows - 1, max(0, rr))][min(m.cols - 1, max(0, cc))]
        fence = lambda rr, cc: (0 <= rr < m.rows and 0 <= cc < m.cols and (m.fence[rr][cc] or m.deco[rr][cc] == "gate")
                                and m.height[rr][cc] == level)
        for r in range(m.rows):
            for c in range(m.cols):
                if m.height[r][c] != level:
                    continue
                if m.terrain[r][c] == "soil":
                    put(crop_tile().im, c * T, r * T)
                if m.terrain[r][c] == "bridge":
                    if at(r, c - 1) != "water" or at(r, c + 1) != "water":
                        t = bridge_tile(True, at(r - 1, c) != "bridge", at(r + 1, c) != "bridge")
                    else:
                        t = bridge_tile(False, at(r, c - 1) != "bridge", at(r, c + 1) != "bridge")
                    put(t.im, c * T, r * T)
                if m.deco[r][c] == "flowers":
                    put(flower_tile(int(((r * 5 + c * 11) % 13) / 13 * 4)).im, c * T, r * T)
                if m.deco[r][c] == "gate":
                    put(gate_tile(fence(r, c - 1) or fence(r, c + 1)).im, c * T, r * T)
                elif fence(r, c):
                    conn = (1 if fence(r - 1, c) else 0) | (2 if fence(r, c + 1) else 0) | (4 if fence(r + 1, c) else 0) | (8 if fence(r, c - 1) else 0)
                    put(FENCE[style["fence"]](conn).im, c * T, r * T)

    def faces(level):
        for r in range(1, m.rows):
            for c in range(m.cols):
                if not is_face(m, r, c, level):
                    continue
                above = m.terrain[r - 1][c]
                kind = "stairs" if m.feature[r][c] == "stairs" else "waterfall" if above in ("water", "bridge") else "face"
                ends = []
                for cc in (c - 1, c + 1):
                    if cc < 0 or cc >= m.cols or is_face(m, r, cc, level):
                        ends.append("continue")
                    elif m.height[r][cc] >= level:
                        ends.append("inner")
                    else:
                        ends.append("outer")
                put(cliff_piece(style["cliff"], kind, ends[0], ends[1], style["radius"], frame).im, c * T, (r - 1) * T)
        for r in range(m.rows):                                   # stairs up the east or west side of a hill
            for c in range(m.cols):
                if m.feature[r][c] != "stairs" or m.height[r][c] != level - 1 or is_face(m, r, c, level):
                    continue
                if c > 0 and m.height[r][c - 1] == level:
                    put(side_stairs(style["side"], "w").im, c * T, r * T)
                elif c + 1 < m.cols and m.height[r][c + 1] == level:
                    put(side_stairs(style["side"], "e").im, c * T, r * T)

    for r in range(m.rows):
        for c in range(m.cols):
            put(grass_cell_top((c % GRASS_N, r % GRASS_N)).im, c * T, r * T)
    top = max(max(row) for row in m.height)
    for level in range(top + 1):
        if level:
            dual("raised_shadow", level)
            dual("raised_fill", level)
        for name in OVERLAYS:
            dual(name, level)
        dual("tallgrass", level)
        singles(level)
        if level:
            dual("raised_edge", level)
            faces(level)
    for spr, x, y in sorted(m.objects, key=lambda o: o[2]):
        place(cv, spr, P + x, P + y)
    return cv.im.crop((P, P, P + m.cols * T, P + m.rows * T))


def px(c, r):
    return c * T + T // 2, r * T + T


def sample():
    """A 14x10 scene with every case: a cliff with an inner and outer corner, a waterfall, stairs, a pond on
    high ground, a river with a bend and a bridge, paths, a cobbled square and a fenced crop plot."""
    m = Map(14, 10)
    m.fill("height", 0, 0, 3, 11, 1)
    m.fill("height", 3, 0, 4, 4, 1)
    m.fill("terrain", 1, 1, 3, 3, "water")                      # pond on the hill
    m.fill("terrain", 0, 7, 6, 9, "water")                      # the river, over the waterfall
    m.fill("terrain", 6, 8, 10, 10, "water")
    m.fill("terrain", 1, 5, 3, 6, "path")                       # path on the hill to the stairs
    m.fill("terrain", 3, 5, 10, 6, "path")
    m.feature[3][5] = "stairs"
    m.fill("terrain", 7, 5, 8, 14, "path")
    m.fill("terrain", 7, 8, 8, 10, "bridge")
    m.fill("terrain", 8, 10, 10, 14, "cobbles")
    m.fill("terrain", 6, 1, 9, 3, "soil")
    for c in range(0, 4):
        m.fence[5][c] = m.fence[9][c] = True
    for r in range(5, 10):
        m.fence[r][0] = m.fence[r][3] = True
    m.objects += [(tree("a", 0.9), *px(3, 0)), (pine("b"), *px(10, 0)), (tree("c", 1.0), *px(12, 2)),
                  (house("h", w=44, wall_h=20, roof="r"), 11 * T + 12, 6 * T + 6), (bush("d"), *px(6, 5)),
                  (rock("e"), *px(13, 4)), (bush("f"), *px(4, 2))]
    return m


OPTIONS = {
    "corners": [("radius", 3), ("radius", 5), ("radius", 7)],
    "path": [("path", "soft"), ("path", "worn"), ("path", "crisp")],
    "water": [("water", "foam"), ("water", "bank"), ("water", "sand")],
    "cliff": [("cliff", "stone"), ("cliff", "earth"), ("cliff", "rock")],
    "fence": [("fence", "picket"), ("fence", "rail"), ("fence", "hedge")],
}


def options(out):
    out.mkdir(parents=True, exist_ok=True)
    m = sample()
    for group, opts in OPTIONS.items():
        for key, value in opts:
            style = dict(DEFAULT, **{key: value})
            frames = [render(m, style, f) for f in range(FRAMES)]
            name = out / f"{group}-{value}.png"
            frames[0].save(name, save_all=True, append_images=frames[1:], duration=320, loop=0)
            print("wrote", name)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "options":
        options(Path(sys.argv[2]))
    else:
        print(__doc__)
