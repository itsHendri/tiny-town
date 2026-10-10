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


def use(name):
    """Swap every colour behind the names (affects everything drawn afterwards)."""
    PAL.clear(); PAL.update(PALETTES[name])
    RGB.clear(); RGB.update({k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) + (255,) for k, v in PAL.items()})


use("bright")
