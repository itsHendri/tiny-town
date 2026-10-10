"""Palettes. The art is drawn with colour names (sprites.PAL); a palette swaps the colours behind the names.

    import palettes; palettes.use("earthy")     # before drawing anything
"""
from sprites import PAL, RGB

BRIGHT = dict(PAL)          # the GBA-bright look everything was first drawn in

# Olive greens, warm wood, tan cobbles, brick roofs and dark brown outlines: a cosy storybook village.
EARTHY = {
    "out": "#2a1e16",
    "g0": "#b5c25a", "g1": "#8ea43f", "g2": "#74892f", "g3": "#5c7128", "g4": "#46591f",
    "gh": "#97ab45", "gh2": "#83973a",
    "t0": "#a9be4e", "t1": "#7f9a36", "t2": "#5d7a2b", "t3": "#3f5a22", "t4": "#2f4520", "t5": "#22331a",
    "p0": "#5f8a4a", "p1": "#44703c", "p2": "#335a33", "p3": "#26452a",
    "trunk": "#6b4a2e", "trunk2": "#4a3220",
    "w0": "#cfe6e8", "w1": "#6fa8c4", "w2": "#4a86ad", "w3": "#335f86",
    "s0": "#b8b0a0", "s1": "#918878", "s2": "#6e6658", "s3": "#4e473d",
    "d0": "#e6d3a3", "d1": "#cdb27c", "d2": "#a88d5c",
    "k0": "#c99a62", "k1": "#9c6f42", "k2": "#74502f", "k3": "#4e3420",
    "c0": "#efe2c4", "c1": "#d6c49c", "c2": "#b39e76", "c3": "#8a7756",
    "r0": "#b8644a", "r1": "#93452f", "r2": "#733423", "r3": "#52241a",
    "y0": "#e2c27a", "y1": "#c9a35a", "y2": "#a37f3f", "y3": "#7a5c2c",
    "b0": "#8a9ab8", "b1": "#6a7c9e", "b2": "#4f5f80", "b3": "#3a4660",
    "fl_w": "#f4efe0", "fl_y": "#f2cf4f", "fl_p": "#d9748f", "fl_o": "#e08a3c",
    "moss": "#8fa046", "moss2": "#6f8235", "light": "#ffe7a0",
    "door": "#8b3a2a", "door2": "#6b2a1e", "win": "#3a3550", "win2": "#e8c070",
}

# Cobblestones (new colours, used by the isometric paths)
COBBLE = {"cb0": "#e2cfa0", "cb1": "#c8b07f", "cb2": "#a68a5c", "cb3": "#7b6343"}
COBBLE_BRIGHT = {"cb0": "#fff6b8", "cb1": "#f4e48a", "cb2": "#e2c96a", "cb3": "#b8995a"}

# Earthy, but deeper: darker greens and stone-grey cobbles, like the shaded corners of a forest village.
DEEP = {**EARTHY,
        "g0": "#9fb04c", "g1": "#7a933a", "g2": "#62792e", "g3": "#4b6024", "g4": "#374a1b",
        "gh": "#86a03f", "gh2": "#6f8834",
        "t0": "#93ad45", "t1": "#6a8a30", "t2": "#4c6a27", "t3": "#34501f", "t4": "#263c1b", "t5": "#1b2b15",
        "p0": "#4f7a40", "p1": "#386234", "p2": "#2a4c2c", "p3": "#1f3a25",
        "k0": "#b88a55", "k1": "#8a603a", "k2": "#64432a", "k3": "#432c1c"}
COBBLE_DEEP = {"cb0": "#d6c8a8", "cb1": "#b5a584", "cb2": "#8f8062", "cb3": "#655843"}

# Picked 2026-10-09 (tiles round 3): earthy, but with the bright road and water for contrast.
WATER_BRIGHT = {k: BRIGHT[k] for k in ("w0", "w1", "w2", "w3")}

# Grey stones for the isometric Cobbles (the bright gold ones are Path): an old-town street
STONE = {"cs0": "#dcd6ca", "cs1": "#b6b0a6", "cs2": "#928c84", "cs3": "#605c58"}

PALETTES = {"bright": {**BRIGHT, **COBBLE_BRIGHT, **STONE}, "earthy": {**BRIGHT, **EARTHY, **COBBLE_BRIGHT, **WATER_BRIGHT, **STONE},
            "earthy-muted": {**BRIGHT, **EARTHY, **COBBLE, **STONE}, "deep": {**BRIGHT, **DEEP, **COBBLE_DEEP, **STONE}}


# ---------- ramp tools (OKLCH: perceptual lightness L 0-1, chroma C, hue H in degrees) ----------

# Every ramp, lightest first. Shifts act on whole ramps so each material keeps its order of values.
RAMPS = {
    "grass": ["g0", "gh", "g1", "gh2", "g2", "g3", "g4"], "leaves": ["t0", "t1", "t2", "t3", "t4", "t5"],
    "pine": ["p0", "p1", "p2", "p3"], "trunk": ["trunk", "trunk2"], "water": ["w0", "w1", "w2", "w3"],
    "stone": ["s0", "s1", "s2", "s3"], "dirt": ["d0", "d1", "d2"], "wood": ["k0", "k1", "k2", "k3"],
    "wall": ["c0", "c1", "c2", "c3"], "roof": ["r0", "r1", "r2", "r3"], "thatch": ["y0", "y1", "y2", "y3"],
    "slate": ["b0", "b1", "b2", "b3"], "path": ["cb0", "cb1", "cb2", "cb3"], "cobble": ["cs0", "cs1", "cs2", "cs3"],
    "moss": ["moss", "moss2"], "door": ["door", "door2"],
}


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch(hexc):
    import math
    r, g, b = (_lin(int(hexc[i:i + 2], 16) / 255) for i in (1, 3, 5))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def hexof(L, C, H):
    """OKLCH to hex; chroma is reduced until the colour fits in sRGB."""
    import math
    for _ in range(40):
        a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        l_, m_, s_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, \
            (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        if all(-0.001 <= c <= 1.001 for c in rgb):
            break
        C *= 0.95
    return "#" + "".join(f"{round(_gam(c) * 255):02x}" for c in rgb)


def _toward(h, target, deg):
    """Hue h moved up to deg degrees toward target along the short way round."""
    d = (target - h + 540) % 360 - 180
    return (h + max(-deg, min(deg, d))) % 360


def shift(pal, hue=0.0, chroma=1.0, spread=1.0, lift=0.0, dark=None, dark_mix=0.0, tint=None, ramps=None):
    """A new palette where each ramp gets warm lights and cool shadows.

    hue: degrees the lightest step moves toward yellow (90) and the darkest toward blue-violet (275).
    chroma: saturation multiplier, strongest mid-ramp. spread: lightness contrast around each ramp's middle.
    lift: added to every lightness. dark + dark_mix: the darkest step of every ramp blends toward one shared colour.
    tint: (hue, amount) pulls every hue a little toward one hue (a light colour for the whole scene).
    """
    out = dict(pal)
    for key, names in RAMPS.items():
        if ramps and key not in ramps:
            continue
        names = [n for n in names if n in pal]
        cols = [oklch(pal[n]) for n in names]
        mid = sum(c[0] for c in cols) / len(cols)
        for i, (n, (L, C, H)) in enumerate(zip(names, cols)):
            t = i / max(1, len(names) - 1)                    # 0 lightest .. 1 darkest
            if C > 0.02:                                       # leave greys grey
                H = _toward(H, 90, hue * (1 - 2 * t)) if t < 0.5 else _toward(H, 275, hue * (2 * t - 1))
            C *= 1 + (chroma - 1) * (1 - abs(2 * t - 1) * 0.5)
            L = mid + (L - mid) * spread + lift
            if tint:
                H = _toward(H, tint[0], tint[1])
            if dark and i == len(names) - 1 and len(names) > 2:
                dL, dC, dH = oklch(dark)
                L, C, H = L + (dL - L) * dark_mix, C + (dC - C) * dark_mix, _toward(H, dH, 180 * dark_mix)
            out[n] = hexof(max(0.0, min(1.0, L)), max(0.0, C), H)
    return out


# Picked 2026-10-10 (palette round, "storybook rich"): earthy with warm lights, cool shadows, more colour and contrast.
PALETTES["rich"] = shift(PALETTES["earthy"], hue=14, chroma=1.35, spread=1.18)
DEFAULT = "rich"


def use(name):
    """Swap every colour behind the names (affects everything drawn afterwards)."""
    PAL.clear(); PAL.update(PALETTES[name])
    RGB.clear(); RGB.update({k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) + (255,) for k, v in PAL.items()})


use("bright")
