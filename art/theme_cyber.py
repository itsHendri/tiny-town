"""The cyberpunk theme: the same maps, as a neon city at night. Every terrain value and prop name keeps its meaning
(grass is the ground, water the water, a house a building on the same footprint); this module gives the colours
behind the names and redraws the things that need a new shape.

    import palettes, theme_cyber
    palettes.PALETTES["cyber"] = theme_cyber.palette(**theme_cyber.LOOKS["neon"]); palettes.use("cyber")
    theme_cyber.apply()            # after the art modules are imported: swaps the drawers

Ground: grass -> plaza panels with glowing seams, water -> a dark canal with neon reflections, path -> a lit
walkway, cobbles -> steel grates, dirt -> grime. Houses -> neon blocks. Trees keep their shapes in neon colours.
"""
import math

import palettes
from dualgrid import h
from ground import PX, PY


# ---------- palette ----------

def ramp(n, L0, L1, C0, C1, H0, H1=None):
    """n colours from (L0, C0, H0) to (L1, C1, H1), lightest first."""
    H1 = H0 if H1 is None else H1
    return [palettes.hexof(L0 + (L1 - L0) * k / (n - 1), C0 + (C1 - C0) * k / (n - 1), H0 + (H1 - H0) * k / (n - 1))
            for k in range(n)]


def palette(ground=275, ground_l=0.3, ground_c=0.035, a=345, b=200, c=75, glow=1.0):
    """Every colour name as a cyber colour. ground: hue, lightness, chroma of the plaza and concrete; a, b, c: the
    three neon hues (signs and foliage, water and glass, the walkway's light). glow scales neon chroma."""
    G, L = ground, ground_l
    P = dict(palettes.PALETTES[palettes.DEFAULT])
    names = lambda prefix, cols: dict(zip(prefix, cols))
    P.update(names(["g0", "gh", "g1l", "g1", "g1d", "gh2", "g2", "g3", "g4"],
                   [palettes.hexof(0.78, 0.13 * glow, b)] + ramp(8, L + 0.08, L - 0.12, ground_c * 1.2, ground_c, G - 8, G + 8)))
    P.update(names([f"t{k}" for k in range(6)], ramp(6, 0.82, 0.24, 0.17 * glow, 0.09, a + 15, a - 15)))
    P.update(names([f"p{k}" for k in range(4)], ramp(4, 0.78, 0.3, 0.13 * glow, 0.07, b - 10, b + 15)))
    P.update(names(["trunk", "trunk2"], ramp(2, L + 0.14, L, 0.02, 0.02, G)))
    P.update(names(["w0", "w1", "w2", "w3"], [palettes.hexof(0.93, 0.07, b), palettes.hexof(0.74, 0.14 * glow, b),
                                              palettes.hexof(L - 0.04, 0.05, b + 25), palettes.hexof(L - 0.1, 0.04, b + 35)]))
    P.update(names(["s0", "s1", "s2", "s3"], ramp(4, L + 0.3, L - 0.02, 0.015, 0.02, G)))
    P.update(names(["d0", "d1", "d2"], ramp(3, L + 0.14, L + 0.02, 0.05, 0.04, 45)))
    P.update(names([f"k{k}" for k in range(4)], ramp(4, L + 0.28, L - 0.02, 0.02, 0.025, G + 20)))
    P.update(names([f"c{k}" for k in range(4)], ramp(4, L + 0.2, L - 0.02, ground_c * 0.8, ground_c, G - 10)))
    P.update(names([f"r{k}" for k in range(4)], ramp(4, L + 0.16, L - 0.06, 0.07, 0.05, a)))
    P.update(names([f"y{k}" for k in range(4)], ramp(4, L + 0.18, L - 0.04, 0.06, 0.04, c)))
    P.update(names([f"b{k}" for k in range(4)], ramp(4, L + 0.16, L - 0.06, 0.06, 0.05, b)))
    P.update(names([f"cb{k}" for k in range(4)], [palettes.hexof(0.86, 0.15 * glow, c)] + ramp(3, L + 0.12, L - 0.06, 0.03, 0.03, c - 30)))
    P.update(names([f"cs{k}" for k in range(4)], ramp(4, L + 0.26, L - 0.04, 0.012, 0.015, G + 30)))
    P.update({"fl_w": palettes.hexof(0.95, 0.03, b), "fl_y": palettes.hexof(0.86, 0.16 * glow, c),
              "fl_p": palettes.hexof(0.7, 0.22 * glow, a), "fl_o": palettes.hexof(0.75, 0.16 * glow, b),
              "moss": palettes.hexof(0.72, 0.14 * glow, b), "moss2": palettes.hexof(0.55, 0.12 * glow, b),
              "light": palettes.hexof(0.9, 0.12 * glow, c), "door": palettes.hexof(0.66, 0.2 * glow, a),
              "door2": palettes.hexof(0.5, 0.17 * glow, a), "win": palettes.hexof(L - 0.12, 0.03, G),
              "win2": palettes.hexof(0.84, 0.13 * glow, c), "out": palettes.hexof(0.13, 0.03, G),
              "shade": palettes.hexof(0.08, 0.03, G),
              "jf1": palettes.hexof(0.65, 0.2 * glow, a + 25), "jf2": palettes.hexof(0.6, 0.18 * glow, b + 60),
              "sr3": palettes.hexof(0.4, 0.15, a + 40), "red": palettes.hexof(0.62, 0.21 * glow, 25),
              "vh0": palettes.hexof(0.36, 0.02, G), "vh1": palettes.hexof(0.26, 0.02, G), "vh2": palettes.hexof(0.18, 0.02, G),
              "neon_a": palettes.hexof(0.72, 0.2 * glow, a), "neon_b": palettes.hexof(0.8, 0.14 * glow, b),
              "neon_c": palettes.hexof(0.86, 0.15 * glow, c)})
    P.update(names(["lf0", "lf1", "lf2", "lf3"], ramp(4, L + 0.14, L - 0.1, 0.08, 0.06, (a + G) / 2 + 20, (a + G) / 2 + 40)))
    return P


PICK = "neon"   # picked 2026-10-11 (cyber palette round): neon night

# How each hero item is drawn (picked 2026-10-11, cyber and circuit builders: panels, coolant, tiles, random windows,
# mixed parts for trees, neon blocks). It stays a city: the circuit board is a flavour, not the subject.
CYBER = {"plaza": "panels", "canal": "coolant", "walkway": "tiles", "windows": "random", "trees": "tech-fibre", "buildings": "blocks",
         "parts": "city", "signs": "varied", "glow": "on", "roofs": "busy", "pines": "neon", "planter": "no",
         # street and market twins (art/cyber_props.py): "neon" or "recolour" (the cottage drawing in cyber colours);
         # picked 2026-10-12: all neon
         "stalls": "neon", "lamps": "neon", "bench": "neon", "barrel": "neon", "crates": "neon",
         "board": "neon", "cart": "neon", "well": "neon"}
# Trees stay trees in the city (a dense wood reads as a glowing park): CYBER["trees"] for broadleaf kinds and
# CYBER["pines"] for conifers: neon, holo, biolum (dark crowns, glowing specks), outline (dark, a neon rim),
# cable (crowns of wire bundles, broadleaf only); "planter": trees standing in lit planter boxes. "tech-<concept>":
# tech objects that read as trees, every kind (art/tech_trees.py: data, circuit, wire, voxel, fibre).
# Picked 2026-10-12 (tech tree round): fibre trees, glow on.
# Polish switches (neon city polish round, picked 2026-10-11: city, random, varied, on, busy): parts v1 / city (city-scale tech), windows random / calm (a colour per
# floor, half dark), signs one / varied (blade signs, billboards), glow off / on (halos, light spill), roofs plain / busy.

def tweak(P):
    """Palette changes some choices need: a green circuit board, copper traces."""
    P = dict(P)
    if CYBER["plaza"] == "pcb-green":
        P.update(zip(["gh", "g1l", "g1", "g1d", "gh2", "g2", "g3", "g4"], ramp(8, 0.44, 0.22, 0.09, 0.06, 158, 168)))
    if CYBER["walkway"] == "copper":
        P.update(zip(["cb0", "cb1", "cb2", "cb3"], [palettes.hexof(0.86, 0.11, 75), palettes.hexof(0.7, 0.13, 60),
                                                     palettes.hexof(0.56, 0.12, 50), palettes.hexof(0.36, 0.07, 45)]))
    return P


LOOKS = {   # candidate palettes (cyber palette round)
    "neon": dict(ground=275, ground_l=0.3, a=345, b=200, c=75),
    "blade": dict(ground=230, ground_l=0.27, ground_c=0.025, a=40, b=195, c=70),
    "synth": dict(ground=295, ground_l=0.31, ground_c=0.06, a=330, b=255, c=20),
    "acid": dict(ground=170, ground_l=0.26, ground_c=0.03, a=135, b=180, c=105),
    "vapor": dict(ground=300, ground_l=0.4, ground_c=0.05, a=350, b=215, c=85, glow=0.8),
    "rain": dict(ground=245, ground_l=0.33, ground_c=0.02, a=0, b=210, c=60, glow=0.85),
}


# ---------- ground ----------

def mapxy(gx, gy):
    """Map pixels (u along a row, v down a column) of a screen pixel."""
    return (gx + 2 * gy) // 2, (2 * gy - gx) // 2


def _cell(u, v, size, m):
    """A key for the size x size map-pixel tile at (u, v) that repeats like the pattern (m: tiles per repeat)."""
    pu, pv = u // size, v // size
    return (pu + pv) % m, (pu - pv) % m


def plaza_px(gx, gy, variant=0, flat=True):
    """Plaza: dark panels laid on the map grid, a lit bevel on each panel's top edges, some seams glowing, the odd
    vent. CYBER["plaza"]: panels (2 x 2 per cell), slabs (one per cell), puddles (panels with neon puddles),
    quiet (panels, no glowing seams)."""
    return plaza_uv(*mapxy(gx, gy), variant, flat, gx, gy)


def plaza_uv(u, v, variant=0, flat=True, gx=None, gy=None):
    """The plaza at map pixel (u, v) (top-down draws it straight from map pixels; gx, gy: the screen pixel, for
    puddles)."""
    look = CYBER["plaza"]
    gx, gy = (u - v, (u + v) // 2) if gx is None else (gx, gy)
    if look in ("pcb", "pcb-green"):
        return pcb_px(u, v, variant, flat)
    if look == "silicon":
        key = _cell(u, v, 4, (256 if flat else 64) // 4)
        if u % 4 == 0 or v % 4 == 0:
            return "g3"
        k = h("die", variant, *key)
        return "neon_b" if k < 0.012 else "g1l" if k < 0.3 else "g1"
    size = 16 if look == "slabs" else 8
    key = _cell(u, v, size, (256 if flat else 64) // size)
    if look == "puddles":
        gxw, gyw = (gx % 256, gy % 128) if flat else (gx % PX, gy % PY)
        import ground
        n = ground.smooth(gxw, gyw, ("pud", variant), 32, 16, 256 if flat else PX, 128 if flat else PY)
        if n > 0.72:
            if h("pspark", gxw, gyw) < 0.05:
                return ("fl_p", "neon_b", "fl_y")[int(h("pc", gxw, gyw) * 3)]
            return "w3" if n < 0.76 else "w2"
    if u % size == 0 or v % size == 0:
        axis = "u" if u % size == 0 else "v"
        glow = 0 if look == "quiet" else 0.04 if look == "slabs" else 0.07
        return "g0" if h("seam", variant, axis, *key) < glow else "g3"
    if u % size == 1 or v % size == 1:
        return "gh"
    if size == 8 and h("vent", variant, *key) < 0.04 and 2 < u % 8 < 7 and 2 < v % 8 < 7:
        return "g4" if (u + v) % 2 else "g2"
    t = h("pt", variant, *key)
    return "g1l" if t < 0.25 else "g1d" if t > 0.8 else "g1"


def pcb_px(u, v, variant=0, flat=True):
    """Circuit board: solder mask with faint traces routed along the map grid, vias (plated holes) at their ends,
    the odd trace lit."""
    m = (256 if flat else 64) // 16
    pu, pv = u // 16, v // 16
    key = ((pu + pv) % m, (pu - pv) % m)
    lu, lv = u % 16, v % 16
    for axis, (a, b) in (("u", (lu, lv)), ("v", (lv, lu))):         # a trace across the panel, along u or v
        if h("tr", variant, axis, *key) < 0.45:
            off = 3 + int(h("to", variant, axis, *key) * 10)
            start, end = int(h("ts", variant, axis, *key) * 6), 10 + int(h("te", variant, axis, *key) * 6)
            for e in (start, end):                                   # vias at both ends
                d2 = (a - e) ** 2 + (b - off) ** 2
                if d2 <= 1:
                    return "g4"
                if d2 <= 3:
                    return "cs0"
            if b == off and start <= a <= end:
                return "neon_b" if h("tl", variant, axis, *key) < 0.12 else "gh"
    if lu == 0 or lv == 0:
        return "g1d"
    return "g1"


def canal_px(sh, x, y, gx, gy, f):
    """Canal: a steel rim, a cyan glow along the edge, dark water, neon reflections drifting with the frame."""
    if not sh.inside(x, y):
        d = sh.dist(x, y, 4)
        if d <= 1.0:
            return "out"
        if d <= 2.5:
            return "cs1" if d <= 1.8 else "cs2"
        return None
    d = sh.dist(x, y, 4)
    if d <= 1.0:
        return "w1"
    if d <= 2.0:
        return "w3"
    look = CYBER["canal"]
    if look == "databus":                                                     # lines, light pulses flowing
        if gy % 3 == 1:
            k = (gx + f * 6 + (gy // 3) * 13) % 48
            return "w0" if k == 0 else "w1" if k < 4 else "w2"
        return "w3"
    if look == "coolant":                                                     # glowing coolant, bubbles rising
        bx, by = gx % 16, (gy + f * 2) % 12
        if (bx - 5) ** 2 + (by - 6) ** 2 <= 1 or (h("bub", gx // 16, (gy + f * 2) // 12) < 0.3 and
                                                   (bx - 11) ** 2 + (by - 3) ** 2 <= 0):
            return "w0"
        return "w2" if h("cd", gx % 64 // 2, gy % 32) < 0.06 else "w1"
    if look == "fiber":                                                       # optical fibres, pulses along them
        u, v = mapxy(gx, gy)
        if u % 3 == 0:
            if (v + f * 5 + int(h("fib", u // 3 % 32) * 40)) % 40 < 3:
                return ("neon_b", "fl_p", "fl_y")[(u // 3) % 3]
            return "w2"
        return "w3"
    if look == "neon" and gy % 6 == 2 and (gx + (gy // 6) * 11 + f * 3) % 40 < 5:
        return ("fl_p", "w1", "fl_y")[(gy // 6 + gx // 40) % 3]              # neon reflections drifting
    if look == "bands" and gy % 4 == 1 and (gx + (gy // 4) * 7 + f * 4) % 32 < 9:
        return ("fl_p", "w1", "fl_y", "neon_a")[(gy // 4) % 4]                # long bands of reflected light
    if h("spark", gx % 64, gy % 32, f) < (0.002 if look == "calm" else 0.004):
        return "w0"
    return "w2"


def walkway_px(sh, x, y, gx, gy, view="iso"):
    """Walkway: small square tiles, a glowing amber curb along the edge."""
    if not sh.inside(x, y):
        return None
    look = CYBER["walkway"]
    d = sh.dist(x, y, 3)
    if d <= 1.0:
        if look == "hazard":
            return "cb0" if (gx + 2 * gy) // 3 % 2 else "out"                  # hazard stripes on the curb
        return "cb3" if look == "copper" else "cb0"
    if d <= 2.0 and look != "copper":
        return "cb3"
    u, v = mapxy(gx, gy) if view == "iso" else (gx, gy)
    if look == "copper":                                                       # copper with solder pads
        pk = _cell(u, v, 8, 8)
        if h("pad", *pk) < 0.2:
            d2 = (u % 8 - 4) ** 2 + (v % 8 - 4) ** 2
            if d2 <= 1:
                return "cs3"
            if d2 <= 5:
                return "cs0"
        return "cb0" if d <= 3.0 and not sh.inside(x - 2, y - 2) else "cb1" if (u + v) % 7 else "cb2"
    if look == "glow":                                                         # dark trace, glowing edge
        return "cb0" if h("gp", *_cell(u, v, 2, 32)) < 0.02 else "g4"
    if look == "road":                                                         # dark road, glowing dashes
        if (u % 16 == 8 and v % 8 < 4) or (v % 16 == 8 and u % 8 < 4):
            return "cb0"
        return "cb3" if h("asph", *_cell(u, v, 2, 32)) < 0.25 else "cb2"
    if u % 4 == 0 or v % 4 == 0:
        return "cb3"
    t = h("wt", *_cell(u, v, 4, 16))
    return "cb1" if t < 0.6 else "cb2"


def grate_px(sh, x, y, gx, gy, view="iso"):
    """Steel grates: plates with slots, a dark edge."""
    if not sh.inside(x, y):
        return None
    if sh.dist(x, y, 3) <= 1.0:
        return "cs3"
    u, v = mapxy(gx, gy) if view == "iso" else (gx, gy)
    if u % 8 == 0 or v % 8 == 0:
        return "cs3"
    if u % 8 == 1 or v % 8 == 1:
        return "cs0"
    return "cs2" if (u + v) % 3 == 0 else "cs1"


# ---------- buildings ----------

BLOCKS = {   # house name -> a neon block on the same footprint
    "cottage-red": dict(height=30, sign="neon_a", vent=True),
    "cottage-brown": dict(height=24, sign="neon_b"),
    "thatch-house": dict(height=22, sign="neon_c", vent=True, tank=True),
    "townhouse": dict(height=58, sign="neon_b", antenna=True),
    "longhouse": dict(height=34, sign="neon_a", tank=True, antenna=True),
}


def block(fw=2, fd=2, name="cottage-red", **_):
    """A neon block on a fw x fd footprint: concrete walls with a lit window grid and a shopfront, a neon sign on the
    lit wall, a flat roof with units, a glowing trim. Returns (sprite, anchor, footprint) like iso_props.house."""
    import iso_props
    from iso_props import OUTLINE, Canvas3D, Sprite, proj, with_ground_shadow
    spec = BLOCKS.get(name, BLOCKS["cottage-red"])
    X1, Y1, Hh = fw * 16, fd * 16, spec["height"]
    top = Hh + max(14 if spec.get("antenna") else 8, 14 if CYBER["signs"] == "varied" else 0)
    W, H = X1 + Y1 + 14, int((X1 + Y1) / 2 + top + 16)
    cv = Canvas3D(W, H, Y1 + 7, int(top) + 8)
    seed = name

    def wall(length, lit):
        def col(s, t, su, tu):
            x, z = su, tu
            base, line = ("c1", "c3") if lit else ("c2", "c3")
            if z > Hh - 1.2:
                return spec["sign"] if lit else "c0"                     # glowing trim along the roof edge
            if z < 9:                                                    # shopfront
                if 3 < x < length - 3 and 1.5 < z < 8:
                    door = length / 2 - 2 < x < length / 2 + 2 and lit
                    return ("door" if z < 7 else "door2") if door else ("win2" if lit else "w1") if z > 3 else "win"
                return line if z > 8 or z < 1.2 else base
            floor = int((z - 9) / 8)
            fz = (z - 9) % 8
            if fz < 1:
                return line                                              # floor line
            col_ = int(x / 6)
            if 1 < x % 6 < 5 and 2.5 < fz < 6.5 and 2 < x < length - 2:
                k = h("win", seed, lit, floor, col_)
                look = CYBER["windows"]
                if look == "one":                                                # one colour per building
                    return "win" if k < 0.4 else {"neon_a": "fl_p", "neon_b": "w1", "neon_c": "win2"}[spec["sign"]]
                if look == "warm":
                    return "win" if k < 0.45 else "win2"
                if look == "sparse":
                    return "win" if k < 0.78 else ("win2", "w1", "fl_p")[int(k * 97) % 3]
                if look == "calm":                                               # a colour per floor, half dark
                    f_ = h("floor", seed, lit, floor)
                    return "win" if k < 0.48 else "win2" if f_ < 0.5 else "w1" if f_ < 0.8 else "fl_p"
                return "win" if k < 0.35 else "win2" if k < 0.6 else "w1" if k < 0.8 else "fl_p"
            return base
        return col

    cv.face((0, Y1, 0), (X1, 0, 0), (0, 0, Hh), wall(X1, True))
    cv.face((X1, Y1, 0), (0, -Y1, 0), (0, 0, Hh), wall(Y1, False))
    cv.face((0, 0, Hh), (X1, 0, 0), (0, Y1, 0),
            lambda s, t, su, tu: "c0" if su < 1 or tu < 1 or su > X1 - 1 or tu > Y1 - 1 else "c3")   # flat roof, a lip
    # a neon sign standing out from the lit wall, near the top
    sx, sz, sw, sh_ = X1 * 0.25, Hh - 12, max(8, X1 * 0.4), 7
    cv.face((sx, Y1 + 0.5, sz), (sw, 0, 0), (0, 0, sh_),
            lambda s, t, su, tu: "out" if su < 1 or su > sw - 1 or tu < 1 or tu > sh_ - 1 else
            ("fl_w" if (int(su) % 3 == 1 and 2 < tu < sh_ - 2) else spec["sign"]))
    if CYBER["signs"] == "varied":
        # a blade sign sticking out from the lit wall's right end, letters stacked down it
        bz0, bh = max(10, Hh * 0.35), min(16, Hh - 6)
        blade = BLADES[int(h("blade", seed) * len(BLADES))]
        cv.face((X1 - 3, Y1, bz0), (0, 5, 0), (0, 0, bh),
                lambda s, t, su, tu: "out" if su < 0.8 or tu < 1 or tu > bh - 1 else
                ("fl_w" if 1.5 < su < 3.5 and int(tu) % 3 != 0 else blade))
        if Hh < 40:                                                      # a billboard on the roof's back edge
            bw = X1 * 0.6
            for px_ in (X1 * 0.2 + 1, X1 * 0.2 + bw - 2):
                cv.face((px_, 3, Hh), (1, 0, 0), (0, 0, 4), lambda *a: "s2")
            cv.face((X1 * 0.2, 3, Hh + 4), (bw, 0, 0), (0, 0, 8),
                    lambda s, t, su, tu: "out" if su < 1 or su > bw - 1 or tu < 1 or tu > 7 else
                    ("fl_w" if h("ad", seed, int(su / 2), int(tu / 2)) < 0.3 and 2 < tu < 6 else BILLBOARD[int(h("bb", seed) * 3)]))
    smoke = None
    units = []
    if spec.get("vent"):
        units.append((X1 * 0.55, Y1 * 0.25, 6, 5, 4))
    if spec.get("tank"):
        units.append((X1 * 0.15, Y1 * 0.2, 7, 7, 8))
    if CYBER["roofs"] == "busy":                                         # rows of AC units along the front edge
        for k in range(int((X1 - 8) / 7)):
            if h("ac", seed, k) < 0.7:
                units.append((4 + k * 7, Y1 - 8, 5, 4, 3))
    for (ux, uy, uw, ud, uh) in units:                                   # rooftop units: boxes on the roof
        cv.face((ux, uy + ud, Hh), (uw, 0, 0), (0, 0, uh), lambda s, t, su, tu: "s1" if tu < uh - 1 else "s0")
        cv.face((ux + uw, uy + ud, Hh), (0, -ud, 0), (0, 0, uh), lambda s, t, su, tu: "s2")
        cv.face((ux, uy, Hh + uh), (uw, 0, 0), (0, ud, 0), lambda s, t, su, tu: "s0" if (int(su) + int(tu)) % 3 else "s2")
    if spec.get("vent"):
        tx, ty = proj(X1 * 0.55 + 3, Y1 * 0.25 + 2.5, Hh + 4)
        smoke = (tx + cv.ox + 2, ty + cv.oy + 2)
    if spec.get("antenna") or CYBER["roofs"] == "busy":
        ax_, ay_ = proj(X1 * 0.8, Y1 * 0.7, Hh)
        for k in range(12):
            cv.s.put(int(ax_ + cv.ox), int(ay_ + cv.oy - k), "s1" if k < 11 else spec["sign"])
    if CYBER["roofs"] == "busy":                                         # a satellite dish
        dx_, dy_ = proj(X1 * 0.35, Y1 * 0.55, Hh + 3)
        for j in range(-3, 4):
            for i in range(-4, 5):
                if (i / 4.2) ** 2 + (j / 3.2) ** 2 <= 1:
                    cv.s.put(int(dx_ + cv.ox + i), int(dy_ + cv.oy + j), "s0" if i + j < 0 else "s1")
        cv.s.put(int(dx_ + cv.ox), int(dy_ + cv.oy + 4), "s2"); cv.s.put(int(dx_ + cv.ox), int(dy_ + cv.oy + 5), "s2")
    spr = cv.s
    spr.outline()
    sx_, sy_ = proj(X1, Y1, 0)
    ax, ay = sx_ + cv.ox + 1, sy_ + cv.oy + 1 - 8
    out = Sprite(spr.w + 2, spr.h + 2)
    out.im.paste(spr.im, (1, 1))
    out.px = out.im.load()
    if OUTLINE["double"]:
        out.outline()
    if CYBER["glow"] == "on":
        out = glow(out)
        out = light_spill(out, X1, Y1, cv.ox + 1, cv.oy + 1, spec["sign"])
    if iso_props.LOOK.get("ground_shadow"):
        out = with_ground_shadow(out, X1, Y1, cv.ox + 1, cv.oy + 1)
    out.anchor = (round(ax), round(ay))
    out.smoke = (round(smoke[0]), round(smoke[1])) if smoke else None
    return out, out.anchor, (fw, fd)


BLADES = ["neon_a", "neon_b", "neon_c"]
BILLBOARD = ["neon_b", "neon_a", "neon_c"]
GLOWS = ("neon_a", "neon_b", "neon_c", "fl_p")


def glow(spr, names=GLOWS, reach=2.6):
    """A soft halo round the neon pixels (signs, trims, lamps): see-through pixels of the same colour just outside
    the sprite. Pixel-exact, so both renderers draw it the same."""
    from PIL import Image
    from sprites import RGB, Sprite
    neon = {RGB[n][:3] for n in names}
    src = [(x, y, spr.px[x, y][:3]) for y in range(spr.h) for x in range(spr.w)
           if spr.px[x, y][3] and spr.px[x, y][:3] in neon]
    halo = Image.new("RGBA", (spr.w, spr.h), (0, 0, 0, 0))
    hp = halo.load()
    k = int(reach) + 1
    for (x, y, col) in src:
        for j in range(-k, k + 1):
            for i in range(-k, k + 1):
                d = math.hypot(i, j)
                X, Y = x + i, y + j
                if d <= reach and 0 <= X < spr.w and 0 <= Y < spr.h and not spr.px[X, Y][3]:
                    a = 130 if d < 1.5 else 60
                    if hp[X, Y][3] < a:
                        hp[X, Y] = col + (a,)
    halo.alpha_composite(spr.im)
    out = Sprite(spr.w, spr.h)
    out.im, out.px = halo, halo.load()
    for attr in ("anchor", "smoke"):
        if hasattr(spr, attr):
            setattr(out, attr, getattr(spr, attr))
    return out


def light_spill(spr, X1, Y1, ox, oy, colour):
    """The shopfront's light on the ground in front of the lit wall: a band of see-through neon, under the block."""
    from PIL import Image
    from iso_props import proj
    from sprites import RGB, Sprite
    sh = Image.new("RGBA", (spr.w, spr.h), (0, 0, 0, 0))
    px, col = sh.load(), RGB[colour][:3]
    (pxo, pyo), (ax, ay), (bx, by) = proj(2, Y1, 0), proj(X1 - 4, 0, 0), proj(0, 5, 0)
    det = ax * by - ay * bx
    for y in range(spr.h):
        for x in range(spr.w):
            dx, dy = x - ox + 0.5 - pxo, y - oy + 0.5 - pyo
            s, t = (dx * by - dy * bx) / det, (ax * dy - ay * dx) / det
            if 0 <= s < 1 and 0 <= t < 1:
                px[x, y] = col + (95 if t < 0.5 else 50,)
    sh.alpha_composite(spr.im)
    out = Sprite(spr.w, spr.h)
    out.im, out.px = sh, sh.load()
    return out


def weeds_px(sh, x, y, gx, gy, f):
    """Tall grass: dark weeds pushing up through the plaza, the odd neon tip."""
    if not sh.inside(x, y):
        return None
    sway = (0, 1, 0)[f % 3]
    t = ["..0.", ".1.1", "1211", "3223"][gy % 4][(gx + (gy // 4 % 2) * 2 - (sway if gy % 4 < 2 else 0)) % 4]
    if sh.dist(x, y, 2) <= 1.0 and t in ".3":
        return None
    if t == "0":
        return ("neon_b", "fl_p")[(gx // 4 + gy // 4) % 2] if h("tip", gx % 64, gy % 32) < 0.3 else "g2"
    return {"1": "g2", "2": "g3", "3": "g4", ".": "g3"}[t]


TREE_LEAVES = {   # CYBER["trees"] / ["pines"] -> leaf ramps (iso_trees.LEAVES), light to dark
    "neon": None,                                                       # the palette's neon foliage as it is
    "rim": ["neon_b", "g2", "g3", "g4", "out", "out"],                 # dark crowns, lit by neon on the edge
    "holo": ["fl_w", "w1", "neon_b", "p2", "p3", "p3"],                # cyan holograms
    "biolum": ["lf0", "lf1", "lf2", "lf3", "out", "out"],              # dark crowns (glowing specks added after)
    "outline": ["lf1", "lf2", "lf3", "lf3", "out", "out"],             # dark silhouettes (a neon rim added after)
    "cable": ["vh0", "vh1", "vh2", "vh2", "out", "out"],               # bundles of cable (wires and LEDs added after)
}
BROADLEAF_LEAVES = ("green", "olive", "deep", "autumn", "rust", "blossom", "birch")
PINE_LEAVES = ("fir", "fir_dark")
PINES = ("pine-2", "pine-3", "cypress-2")
RIMS = {"tree-1": "neon_b", "tree-2-d2": "neon_a", "oak-3": "neon_b", "maple-1": "neon_c", "blossom-1": "neon_a",
        "tree-6": "neon_c", "birch-2": "neon_b", "poplar-1": "neon_a", "willow-1": "neon_b", "pine-2": "neon_c",
        "pine-3": "neon_b", "cypress-2": "neon_a"}


def dress_tree(spr, name, look):
    """The finishing touch per look, on a finished tree sprite: glowing specks (biolum), a neon rim on the lit
    edges (outline), wires and LEDs (cable). Only crown pixels change (the leaf ramp's colours)."""
    from sprites import RGB
    if look not in ("biolum", "outline", "cable"):
        return spr
    crown = {RGB[c][:3] for c in TREE_LEAVES[look][:4]}
    rim = RIMS.get(name, "neon_b")
    px, W, H = spr.px, spr.w, spr.h
    src = [[px[x, y] for x in range(W)] for y in range(H)]
    clear = lambda x, y: not (0 <= x < W and 0 <= y < H) or not src[y][x][3]
    # the sprite's own outline: opaque pixels touching the outside
    rimline = {(x, y) for y in range(H) for x in range(W) if src[y][x][3]
               and any(clear(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    for y in range(H):
        for x in range(W):
            p = src[y][x]
            if not p[3] or p[:3] not in crown:
                continue
            if look == "biolum" and h("spk", name, x, y) < 0.07:
                spr.put(x, y, ("neon_b", "fl_p", "neon_c")[int(h("spc", name, x, y) * 3)])
            elif look == "outline":
                # a crown pixel just inside the outline on the top or left: the lit edge
                if (x, y - 1) in rimline or (x - 1, y) in rimline:
                    spr.put(x, y, rim)
            elif look == "cable":
                k = h("wire", name, x // 3, y)
                if k < 0.06:
                    spr.put(x, y, ("neon_a", "neon_b", "cb1", "neon_c")[int(k * 66) % 4])
                elif h("led", name, x, y) < 0.012:
                    spr.put(x, y, "fl_w")
    return spr


def planter(spr):
    """A tree standing in a lit planter box: a low concrete box, a neon rim along its top front edges."""
    from sprites import Sprite
    bw, bh = 16, 4                                         # box: 16 px wide diamond top, 4 px high
    W = max(spr.w, bw + 2)
    out = Sprite(W, spr.h + bh + 4)
    cx = W // 2
    top = out.h - bh - 9                                   # the box's top diamond centre row
    for y in range(out.h):
        for x in range(W):
            dx, dy = x + 0.5 - cx, y + 0.5 - top
            if abs(dx) / (bw / 2) + abs(dy) / (bw / 4) <= 1:
                edge = abs(dx) / (bw / 2) + abs(dy) / (bw / 4) > 0.75 and dy > 0
                out.put(x, y, "neon_b" if edge else "g3")                    # soil, a lit rim
            elif abs(dx) <= bw / 2 and 0 <= dy - (bw / 4 - abs(dx) / 2) < bh + 0.01 and dy > -bw / 4:
                out.put(x, y, "c1" if dx < 0 else "c2")                    # the box's two front faces
    out.outline()
    out.im.alpha_composite(spr.im, (cx - spr.w // 2, top + 1 - spr.h))
    out.px = out.im.load()
    return out


# ---------- components (instead of trees) and chips (instead of houses) ----------

def _cylinder(s, cx, base, r, hgt, body, top, stripe=None):
    """An upright cylinder, feet at (cx, base): body ramp (light, mid, dark) lit on the left, a top colour pair."""
    ry = r / 2
    for y in range(int(base - hgt - ry) - 1, int(base + ry) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dx = x + 0.5 - cx
            if abs(dx) > r:
                continue
            yb = ry * math.sqrt(max(0, 1 - (dx / r) ** 2))
            if base - hgt - yb <= y + 0.5 <= base + yb:
                f = dx / r
                c = body[0] if f < -0.45 else body[2] if f > 0.4 else body[1]
                if stripe and 0.15 < f < 0.6:
                    c = stripe
                s.put(x, y, c)
    for y in range(int(base - hgt - ry) - 1, int(base - hgt + ry) + 2):   # the top
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dx, dy = x + 0.5 - cx, (y + 0.5 - (base - hgt)) / ry
            if (dx / r) ** 2 + dy ** 2 <= 1:
                s.put(x, y, top[1] if abs(dx) < 0.8 or abs(dy * ry) < 0.6 else top[0])


def capacitor(seed, size=1.0, body=("b1", "b2", "b3")):
    from sprites import Sprite, rng, tight
    r_ = rng("cap", seed)
    r, hgt = 7.5 * size * r_.uniform(0.9, 1.1), 20 * size * r_.uniform(0.85, 1.15)
    s = Sprite(int(r * 2 + 6), int(hgt + r + 8))
    _cylinder(s, s.w / 2, s.h - 3 - r / 2, r, hgt, body, ("cs0", "cs2"), stripe="c0")
    return tight(s).outline()


def led(seed, colour="neon_a", stalk=0):
    """An LED on two legs (stalk: a tall pole under it), with a soft glow round the dome."""
    from PIL import Image
    from sprites import RGB, Sprite, tight
    hgt = 12 + stalk
    s = Sprite(20, hgt + 12)
    cx, base = 10, s.h - 3
    if stalk:
        for y in range(base - stalk, base + 1):
            s.put(cx - 1, y, "cs1"); s.put(cx, y, "cs2")
    else:
        for y in range(base - 4, base + 1):
            s.put(cx - 2, y, "cs1"); s.put(cx + 1, y, "cs2")
    top = base - (stalk or 4)
    _cylinder(s, cx, top, 3.2, 4, (colour, colour, "out"), ("fl_w", colour))
    for y in range(top - 8, top - 3):                                  # the dome
        for x in range(cx - 4, cx + 4):
            if (x + 0.5 - cx) ** 2 + ((y + 0.5 - (top - 4)) * 1.1) ** 2 <= 10.5:
                s.put(x, y, "fl_w" if x < cx - 1 and y < top - 5 else colour)
    s = tight(s, 3).outline()
    glow = Image.new("RGBA", s.im.size, (0, 0, 0, 0))
    gp, col = glow.load(), RGB[colour][:3]
    gy0 = 3 + top - 5
    for y in range(s.h):
        for x in range(s.w):
            d = math.hypot(x + 0.5 - (cx + 3), (y + 0.5 - gy0) * 1.2)
            if 4 < d < 8 and not s.px[x, y][3]:
                gp[x, y] = col + (70 if d < 6 else 35,)
    glow.alpha_composite(s.im)
    out = Sprite(s.w, s.h)
    out.im, out.px = glow, glow.load()
    return out


def coil(seed, size=1.0):
    """A toroid inductor lying on the board: a copper-wound ring."""
    from sprites import Sprite, tight
    R, rr = 9 * size, 3.6 * size
    s = Sprite(int(R * 2 + 6), int(R + 14))
    cx, cy = s.w / 2, s.h - 4 - R / 2
    for lift in range(5, -1, -1):
        for y in range(s.h):
            for x in range(s.w):
                dx, dy = x + 0.5 - cx, (y + 0.5 - (cy - lift)) * 2
                d = math.hypot(dx, dy)
                if R - rr * 2 < d < R:
                    a = math.atan2(dy, dx)
                    c = "cb1" if int((a + 3.2) * 6) % 2 else "cb2"
                    if lift == 0 and dx > R * 0.3:
                        c = "cb3"
                    if lift == 5 and dx < 0:
                        c = "cb0"
                    s.put(x, y, c)
    return tight(s).outline()


def transformer(seed, size=1.0):
    """A boxy transformer: a dark laminated core with a copper winding band."""
    from iso_props import Canvas3D, proj
    from sprites import Sprite
    w = 10 * size
    cv = Canvas3D(int(w * 2 + 12), int(w + 28), int(w + 6), 22)
    hgt = 14 * size
    band = lambda lit: (lambda s, t, su, tu: ("cb1" if lit else "cb2") if hgt * 0.3 < tu < hgt * 0.75 else
                        (("vh0" if lit else "vh1") if int(tu) % 2 else "vh2"))
    cv.face((0, w, 0), (w, 0, 0), (0, 0, hgt), band(True))
    cv.face((w, w, 0), (0, -w, 0), (0, 0, hgt), band(False))
    cv.face((0, 0, hgt), (w, 0, 0), (0, w, 0), lambda s, t, su, tu: "vh0" if 1 < su < w - 1 and 1 < tu < w - 1 else "s1")
    s = cv.s
    s.outline()
    return _feet(s)


def pylon(seed, size=1.0):
    """A power pylon: a lattice tower, a cross-arm with glowing insulators."""
    from sprites import Sprite, rng, tight
    r_ = rng("pylon", seed)
    hgt = int(44 * size * r_.uniform(0.9, 1.1))
    s = Sprite(30, hgt + 6)
    cx, base = 15, s.h - 2
    for y in range(base - hgt, base + 1):
        f = (base - y) / hgt
        half = 7 * (1 - f) + 1.5
        s.put(int(cx - half), y, "cs1"); s.put(int(cx + half), y, "cs2")
        if int(y) % 6 == 0:                                            # cross-bracing
            for x in range(int(cx - half), int(cx + half) + 1):
                s.put(x, y, "cs2")
        k = (base - y) % 6
        for side in (-1, 1):
            x = int(cx + side * (half - k * half / 3))
            if abs(x - cx) <= half:
                s.put(x, y, "cs3")
    for arm in (0, 9):
        ya = base - hgt + 4 + arm
        for x in range(cx - 12 + arm // 2, cx + 13 - arm // 2):
            s.put(x, ya, "cs2")
        for x in (cx - 12 + arm // 2, cx + 12 - arm // 2):
            s.put(x, ya + 1, "neon_b"); s.put(x, ya + 2, "neon_b")
    return tight(s).outline()


def _feet(s):
    """Crop a sprite to what's drawn (1 px spare), so its feet are at the bottom middle."""
    from sprites import Sprite
    x0, y0, x1, y1 = s.im.getbbox()
    out = Sprite(x1 - x0 + 2, y1 - y0 + 1)
    out.im.paste(s.im.crop((x0, y0, x1, y1)), (1, 0))
    out.px = out.im.load()
    return out


PARTS = {   # CYBER["trees"] -> which part each tree name becomes
    "capacitors": {n: (capacitor, k) for k, n in enumerate(
        ["tree-1", "tree-2-d2", "tree-6", "oak-3", "maple-1", "blossom-1", "birch-2", "poplar-1", "willow-1", "pine-2",
         "pine-3", "cypress-2"])},
    "mixed": {"tree-1": (capacitor, 0), "tree-2-d2": (capacitor, 1), "oak-3": (transformer, 0), "maple-1": (capacitor, 2),
              "blossom-1": (led, "neon_a"), "tree-6": (led, "neon_c"), "birch-2": (led, "neon_b"), "poplar-1": (capacitor, 3),
              "willow-1": (coil, 0), "pine-2": (pylon, 0), "pine-3": (pylon, 1), "cypress-2": (capacitor, 4)},
    "stalks": {n: (led, ("neon_a", "neon_b", "neon_c")[k % 3], 14 + (k * 7) % 22) for k, n in enumerate(
        ["tree-1", "tree-2-d2", "tree-6", "oak-3", "maple-1", "blossom-1", "birch-2", "poplar-1", "willow-1", "pine-2",
         "pine-3", "cypress-2"])},
    "pylons": {n: (pylon, k) for k, n in enumerate(
        ["tree-1", "tree-2-d2", "tree-6", "oak-3", "maple-1", "blossom-1", "birch-2", "poplar-1", "willow-1", "pine-2",
         "pine-3", "cypress-2"])},
}
CAP_BODIES = [("b1", "b2", "b3"), ("vh0", "vh1", "vh2"), ("r1", "r2", "r3"), ("y1", "y2", "y3"), ("p1", "p2", "p3")]


def tank(seed, size=1.0, body=("b1", "b2", "b3")):
    """A storage tank: a big cylinder with dark bands, a ladder up the lit side, a red light on top."""
    from sprites import Sprite, rng, tight
    r_ = rng("tank", seed)
    r, hgt = 9 * size * r_.uniform(0.92, 1.08), 24 * size * r_.uniform(0.9, 1.1)
    s = Sprite(int(r * 2 + 8), int(hgt + r + 10))
    cx, base = s.w / 2, s.h - 3 - r / 2
    _cylinder(s, cx, base, r, hgt, body, ("cs0", "cs1"))
    for k in range(1, int(hgt / 7) + 1):                              # bands
        yb = base - k * 7
        for x in range(int(cx - r) + 1, int(cx + r)):
            dx = x + 0.5 - cx
            s.put(x, int(yb + r / 2 * math.sqrt(max(0, 1 - (dx / r) ** 2))), body[2])
    lx = int(cx - r * 0.45)                                            # ladder
    for y in range(int(base - hgt + 2), int(base + 2)):
        s.put(lx, y, "cs0"); s.put(lx + 2, y, "cs0")
        if y % 2 == 0:
            s.put(lx + 1, y, "cs1")
    s.put(int(cx), int(base - hgt - r / 2 - 1), "neon_a")
    return tight(s).outline()


def station(seed, size=1.0):
    """A transformer station: a box with cooling fins, a hazard plate, glowing insulators on top."""
    from iso_props import Canvas3D
    w, d, hgt = 18 * size, 12 * size, 16 * size
    cv = Canvas3D(int(w + d + 12), int((w + d) / 2 + hgt + 20), int(d + 6), int(hgt + 14))
    fins = lambda lit: (lambda s, t, su, tu: ("cs0" if lit else "cs1") if int(su) % 2 else ("cs2" if lit else "cs3"))

    def front(s, t, su, tu):
        if abs(su - w * 0.5) + abs(tu - hgt * 0.55) * 1.1 < 3.2 and tu < hgt * 0.55 + 2.5:
            return "out" if abs(su - w * 0.5) < 0.6 and hgt * 0.45 < tu < hgt * 0.62 else "neon_c"   # hazard plate
        return fins(True)(s, t, su, tu)
    cv.face((0, d, 0), (w, 0, 0), (0, 0, hgt), front)
    cv.face((w, d, 0), (0, -d, 0), (0, 0, hgt), fins(False))
    cv.face((0, 0, hgt), (w, 0, 0), (0, d, 0), lambda s, t, su, tu: "s1" if su < 1 or tu < 1 else "s2")
    from iso_props import proj
    for k in range(3):                                                 # insulator stacks
        x_, y_ = proj(w * (0.25 + k * 0.25), d * 0.5, hgt)
        for j in range(5):
            cv.s.put(int(x_ + cv.ox), int(y_ + cv.oy - j), "neon_b" if j == 4 else ("s0" if j % 2 else "s2"))
    cv.s.outline()
    return _feet(cv.s)


def street_pole(seed, colour="neon_b", hgt=30):
    """An LED street pole: a tall post, an arm, a lamp head."""
    from sprites import Sprite, tight
    s = Sprite(16, hgt + 6)
    cx, base = 6, s.h - 2
    for y in range(base - hgt, base + 1):
        s.put(cx, y, "cs1"); s.put(cx + 1, y, "cs2")
    for x in range(cx, cx + 7):                                       # the arm
        s.put(x, base - hgt, "cs1")
    for y in range(base - hgt + 1, base - hgt + 4):                   # the lamp head
        for x in range(cx + 3, cx + 9):
            s.put(x, y, "fl_w" if y == base - hgt + 3 and 3 < x - cx < 8 else colour)
    s.put(cx - 1, base, "cs2"); s.put(cx + 2, base, "cs2")
    return tight(s).outline()


def ring(seed, size=1.0):
    """A ring monument: a big copper-wound ring on a plinth, glowing inside."""
    from sprites import Sprite, tight
    R, rr = 12 * size, 3.4 * size
    s = Sprite(int(R * 2 + 8), int(R * 2 + 14))
    cx, cy = s.w / 2, s.h - 7 - R
    for y in range(s.h - 6, s.h - 2):                                  # plinth
        for x in range(int(cx - 6), int(cx + 6)):
            s.put(x, y, "s1" if x < cx else "s2")
    for y in range(s.h):
        for x in range(s.w):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            if R - rr * 2 < d < R:
                a = math.atan2(dy, dx)
                c = "cb1" if int((a + 3.2) * 7) % 2 else "cb2"
                if dx > R * 0.4:
                    c = "cb3" if c == "cb2" else "cb2"
                s.put(x, y, c)
            elif R - rr * 2 - 1.5 < d <= R - rr * 2:
                s.put(x, y, "neon_b")                                  # the glow inside the ring
    return tight(s).outline()


def mast(seed, size=1.0):
    """A radio mast: a thin lattice tower, a dish, a red light on top."""
    from sprites import Sprite, tight
    hgt = int(52 * size)
    s = Sprite(16, hgt + 6)
    cx, base = 8, s.h - 2
    for y in range(base - hgt, base + 1):
        s.put(cx - 1, y, "cs1"); s.put(cx + 1, y, "cs2")
        if (base - y) % 4 == 0:
            s.put(cx, y, "cs2")
        elif (base - y) % 4 == 2:
            s.put(cx, y, "cs3")
    for j in range(-2, 3):                                             # a dish part way up
        for i in range(0, 4):
            if (i / 3.5) ** 2 + (j / 2.5) ** 2 <= 1:
                s.put(cx + 2 + i, base - int(hgt * 0.6) + j, "s0" if j < 0 else "s1")
    s.put(cx, base - hgt - 1, "neon_a"); s.put(cx, base - hgt - 2, "neon_a")
    return tight(s).outline()


CITY_PARTS = {"tree-1": (tank, ("b1", "b2", "b3")), "tree-2-d2": (tank, ("vh0", "vh1", "vh2")), "oak-3": (station, None),
              "maple-1": (tank, ("r1", "r2", "r3")), "blossom-1": (street_pole, "neon_a"), "tree-6": (street_pole, "neon_c"),
              "birch-2": (street_pole, "neon_b"), "poplar-1": (mast, None), "willow-1": (ring, None),
              "pine-2": (pylon, 0), "pine-3": (pylon, 1), "cypress-2": (mast, None)}


def city_part(name):
    fn, arg = CITY_PARTS[name]
    if fn is tank:
        return tank(name, 0.85 + h("ts", name) * 0.3, arg)
    if fn is street_pole:
        return street_pole(name, arg, 26 + int(h("ph", name) * 12))
    if fn is pylon:
        return pylon(name, 1.0 + arg * 0.2)
    return fn(name, 1.0)


def part_sprite(spec, name):
    if CYBER["parts"] == "city" and name in CITY_PARTS:
        spr = city_part(name)
        return glow(spr, reach=2.2) if CYBER["glow"] == "on" else spr
    fn, arg, *rest = spec
    if fn is capacitor:
        return capacitor(name, 0.8 + (arg % 3) * 0.25, CAP_BODIES[arg % len(CAP_BODIES)])
    if fn is led:
        return led(name, arg, *(rest or [0]))
    return fn(name, 1.0 + (arg if isinstance(arg, int) else 0) * 0.2)


def chip(fw=2, fd=2, name="cottage-red", **_):
    """A chip on the board instead of a house: a black package with silver pins, a pin-one dot and printing; the
    townhouse becomes a heatsink tower. Returns (sprite, anchor, footprint) like iso_props.house."""
    import iso_props
    from iso_props import OUTLINE, Canvas3D, Sprite, proj, with_ground_shadow
    X1, Y1 = fw * 16, fd * 16
    tower = name == "townhouse"
    Hh = 30 if tower else 6
    W, H = X1 + Y1 + 14, int((X1 + Y1) / 2 + Hh + 24)
    cv = Canvas3D(W, H, Y1 + 7, Hh + 10)
    m = 3                                                            # the package sits inside its footprint
    for i in range(int(m + 2), int(X1 - m - 1), 3):                  # pins along the two front sides
        cv.face((i, Y1 - m, 0), (1.6, 0, 0), (0, 2.6, 0), lambda *a: "cs0")
        cv.face((i, Y1 - m + 2.6, 0), (1.6, 0, 0), (0, 0, 1.2), lambda *a: "cs1")
    for j in range(int(m + 2), int(Y1 - m - 1), 3):
        cv.face((X1 - m, j, 0), (2.6, 0, 0), (0, 1.6, 0), lambda *a: "cs0")
        cv.face((X1 - m + 2.6, j, 0), (0, 1.6, 0), (0, 0, 1.2), lambda *a: "cs2")
    x0, y0, x1, y1 = m, m, X1 - m, Y1 - m
    if tower:
        fins = lambda lit: (lambda s, t, su, tu: ("cs0" if lit else "cs1") if int(su) % 3 else "cs3")
        cv.face((x0, y1, 0), (x1 - x0, 0, 0), (0, 0, Hh), fins(True))
        cv.face((x1, y1, 0), (0, y0 - y1, 0), (0, 0, Hh), fins(False))
        cv.face((x0, y0, Hh), (x1 - x0, 0, 0), (0, y1 - y0, 0), lambda s, t, su, tu: "cs3" if int(su) % 3 == 0 else "cs1")
    else:
        cv.face((x0, y1, 0), (x1 - x0, 0, 0), (0, 0, Hh), lambda *a: "vh1")
        cv.face((x1, y1, 0), (0, y0 - y1, 0), (0, 0, Hh), lambda *a: "vh2")

        def top(s, t, su, tu):
            if (su - 3) ** 2 + (tu - 3) ** 2 < 2.2:
                return "vh0"                                         # pin-one dot
            if 0.3 < s < 0.8 and int(tu) in (int((y1 - y0) * 0.45), int((y1 - y0) * 0.6)) and h("txt", int(su), name) < 0.7:
                return "s1"                                          # printing
            if (su - (x1 - x0 - 3)) ** 2 + (tu - 3) ** 2 < 1.5:
                return "neon_b"                                      # a status light
            return "vh1" if su < 1 or tu < 1 else "vh0" if (su + tu) < 2.5 else "vh2"
        cv.face((x0, y0, Hh), (x1 - x0, 0, 0), (0, y1 - y0, 0), top)
    spr = cv.s
    spr.outline()
    sx_, sy_ = proj(X1, Y1, 0)
    ax, ay = sx_ + cv.ox + 1, sy_ + cv.oy + 1 - 8
    out = Sprite(spr.w + 2, spr.h + 2)
    out.im.paste(spr.im, (1, 1))
    out.px = out.im.load()
    if OUTLINE["double"]:
        out.outline()
    if iso_props.LOOK.get("ground_shadow"):
        out = with_ground_shadow(out, X1, Y1, cv.ox + 1, cv.oy + 1)
    out.anchor = (round(ax), round(ay))
    out.smoke = None
    return out, out.anchor, (fw, fd)


# ---------- switching the drawers ----------

def apply():
    """Swap the hero drawers for the cyber ones (call after palettes.use and the art imports)."""
    import ground
    import iso
    import iso_props
    iso.grass_px = ground.grass_px = plaza_px
    iso.cobble_px = ground.cobble_px = walkway_px
    iso.grey_cobble_px = ground.grey_cobble_px = grate_px
    iso.SETS["water"] = ground.water_px = canal_px
    iso.SETS["tallgrass"] = weeds_px
    ground.grass_top = lambda u, v, variant=0: plaza_uv(u, v, variant)
    import styles                                                       # the top-down sheet's hooks
    styles.SHARED[("water", "shared")] = canal_px
    styles.SHARED[("raised_fill", "tufts")] = lambda sh, x, y, gx, gy, f: plaza_uv(gx, gy, 1, False) if sh.inside(x, y) else None
    styles.TERRAIN["tallgrass"]["meadow"] = lambda sh, x, y, f, v: weeds_px(styles.TopShape(sh), x, y, *styles.gxy(x, y), f)
    ramp_ = TREE_LEAVES.get(CYBER["trees"])
    pine_ramp = TREE_LEAVES.get(CYBER["pines"])
    if CYBER["trees"].startswith("tech-"):                             # tech trees (art/tech_trees.py)
        import iso_trees
        import tech_trees
        concept = CYBER["trees"][5:]
        iso_trees.trees = lambda: {n: (glow(spr, reach=2.2) if CYBER["glow"] == "on" else spr)
                                   for n, spr in tech_trees.trees(concept).items()}
    elif CYBER["trees"] not in PARTS:
        import iso_trees
        if pine_ramp:
            for k in PINE_LEAVES:
                iso_trees.LEAVES[k] = list(pine_ramp)
        old_trees = iso_trees.trees

        def themed_trees():
            out = {}
            for n, spr in old_trees().items():
                spr = dress_tree(spr, n, CYBER["pines"] if n in PINES else CYBER["trees"])
                if CYBER["planter"] == "yes" and n not in PINES:
                    spr = planter(spr)
                out[n] = glow(spr, reach=2.2) if CYBER["glow"] == "on" else spr
            return out
        iso_trees.trees = themed_trees
    if CYBER["trees"] in PARTS:
        import iso_trees
        parts = PARTS[CYBER["trees"]]
        old = iso_trees.trees
        iso_trees.trees = lambda: {n: (part_sprite(parts[n], n) if n in parts else spr) for n, spr in old().items()}
    if ramp_:
        import iso_trees
        for k in ("green", "olive", "deep", "autumn", "rust", "blossom", "birch"):
            iso_trees.LEAVES[k] = list(ramp_)
    import cyber_props                                                # street and market twins
    import iso_market
    m, plain = cyber_props.market(CYBER)
    gl = (lambda spr: glow(spr, reach=2.2)) if CYBER["glow"] == "on" else (lambda spr: spr)

    def glowing(make):
        def made():
            spr = make()
            out = gl(spr)
            for attr in ("anchor", "smoke"):
                if hasattr(spr, attr):
                    setattr(out, attr, getattr(spr, attr))
            return out
        return made
    iso_market.MARKET.update({k: glowing(v) for k, v in m.items()})
    iso_market.PLAIN.update({k: glowing(v) for k, v in plain.items()})
    import landmarks                                                  # the landmarks' city twins
    g = (lambda spr: glow(spr, reach=2.2)) if CYBER["glow"] == "on" else (lambda spr: spr)
    landmarks.OVERRIDE = {"tank": lambda: g(tank("tank", 1.0, ("b1", "b2", "b3"))), "pylon": lambda: g(pylon("pylon", 1.2)),
                          "station": lambda: g(station("station")), "street-pole": lambda: g(street_pole("pole", "neon_b", 32)),
                          "monument": lambda: g(ring("ring")), "mast": lambda: g(mast("mast"))}
    for name in iso_props.HOUSES:
        iso_props.HOUSES[name] = {**iso_props.HOUSES[name], "name": name}
    iso_props.house = chip if CYBER["buildings"] == "chips" else block
