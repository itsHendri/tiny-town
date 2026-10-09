"""Props: trees, houses and small things you place on the map, drawn in code and packed into one atlas.
A prop's feet are the bottom-centre of its rectangle.
"""
import math

from sprites import RGB, Sprite, bush, house, pine, rock, tight, tree


def blob(s, cx, cy, rx, ry, shades):
    """A shaded ellipse, lit from the top-left."""
    for j in range(int(cy - max(rx, ry)) - 1, int(cy + max(rx, ry)) + 2):
        for i in range(int(cx - max(rx, ry)) - 1, int(cx + max(rx, ry)) + 2):
            dx, dy = i + 0.5 - cx, j + 0.5 - cy
            if (dx / rx) ** 2 + (dy / ry) ** 2 > 1:
                continue
            lit = -(dx / max(rx, ry) * 0.8 + dy / max(rx, ry))
            s.put(i, j, shades[0] if lit > 0.55 else shades[2] if lit < -0.45 else shades[1])


def lamp():
    s = Sprite(6, 22)
    s.rect(2, 4, 2, 18, "vh1"); s.rect(0, 0, 6, 5, "vh1"); s.rect(1, 1, 4, 3, "light")
    return tight(s).outline()


def bench():
    s = Sprite(30, 8)
    s.rect(0, 0, 30, 3, "k1"); s.rect(0, 0, 30, 1, "k0"); s.rect(2, 3, 3, 4, "k3"); s.rect(25, 3, 3, 4, "k3")
    return tight(s).outline()


def barrel():
    s = Sprite(10, 11)
    blob(s, 5, 6, 4.5, 5, ("k0", "k1", "k2")); s.rect(0, 3, 10, 1, "k3"); s.rect(0, 8, 10, 1, "k3")
    return tight(s).outline()


def crate():
    s = Sprite(10, 11)
    s.rect(0, 1, 10, 10, "k1"); s.rect(0, 1, 10, 1, "k0"); s.rect(8, 1, 2, 10, "k2"); s.rect(0, 5, 10, 1, "k2")
    return tight(s).outline()


def well():
    s = Sprite(18, 20)
    blob(s, 9, 14, 8, 5, ("s0", "s1", "s2")); blob(s, 9, 13, 5, 2.4, ("w2", "w2", "w3"))
    s.rect(2, 2, 2, 12, "k2"); s.rect(14, 2, 2, 12, "k2"); s.rect(1, 1, 16, 2, "r2")
    return tight(s).outline()


def catalog():
    """Every prop by name: (sprite, casts a ground shadow)."""
    p = {}
    for dark in (0, 1, 2):
        for k, size in enumerate((0.95, 1.0, 1.0, 1.05, 1.15, 1.2)):
            p[f"tree-{k + 1}" + (f"-d{dark}" if dark else "")] = (tree(f"t{k}", size, dark), True)
    for k, size in enumerate((1.0, 1.05, 1.2, 1.25)):
        p[f"pine-{k + 1}"] = (pine(f"p{k}", size), True)
    for k in range(3):
        p[f"bush-{k + 1}"] = (bush(f"b{k}"), True)
    for k in range(2):
        p[f"rock-{k + 1}"] = (rock(f"k{k}"), False)
    for roof, name in (("r", "red"), ("y", "yellow"), ("b", "blue")):
        for size, w in (("s", 46), ("m", 50), ("l", 54)):
            p[f"house-{name}-{size}"] = (house(f"h{roof}{w}", w=w, wall_h=22, roof=roof, moss=0.15), True)
    p.update({"lamp": (lamp(), False), "bench": (bench(), False), "barrel": (barrel(), False), "crate": (crate(), False), "well": (well(), True)})
    return p
