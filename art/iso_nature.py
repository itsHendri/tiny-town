"""Lush trees and bushes for the isometric view (the storybook look): oaks built from many small leaf clumps,
dark firs with drooping tiers, flowering bushes and mossy rocks. They take over the tree/pine/bush/rock names in
the isometric prop set, so maps keep working.
"""
import math

from sprites import Sprite, rng, tight


def oak(seed, size=1.0, dark=0):
    r = rng("oak", seed)
    R = 17 * size
    w, h = int(R * 2.4 + 8), int(R * 2.3 + 18)
    s = Sprite(w, h)
    cx, cy = w / 2, R + 4
    # trunk, a little flared at the foot, with two branches up into the crown
    base = h - 3
    for y in range(int(cy + R * 0.3), base + 1):
        half = 2.2 + max(0, (y - (base - 4)) * 0.7)
        for x in range(int(cx - half), int(cx + half) + 1):
            s.put(x, y, "trunk2" if x > cx + 0.5 else "trunk")
    for (dx, k) in ((-1, 1), (1, -1)):
        for t in range(int(R * 0.55)):
            s.put(int(cx + dx * t * 0.6), int(cy + R * 0.35 - t), "trunk")
    # the crown: many small clumps in a rounded mass, each lit from the top-left
    clumps = []
    for k in range(int(26 * size)):
        a = r.uniform(0, math.pi * 2)
        d = R * math.sqrt(r.uniform(0, 1)) * 0.78
        x, y = cx + math.cos(a) * d * 1.18, cy + math.sin(a) * d * 0.95 - R * 0.05
        clumps.append((x, y, R * r.uniform(0.24, 0.34)))
    clumps.sort(key=lambda c: c[1])
    for (x, y, rr) in clumps:
        for j in range(int(y - rr) - 1, int(y + rr) + 2):
            for i in range(int(x - rr) - 1, int(x + rr) + 2):
                dx, dy = i + 0.5 - x, j + 0.5 - y
                if dx * dx + dy * dy > rr * rr:
                    continue
                lit = -(dx * 0.8 + dy) / rr                       # this clump's own top-left light
                whole = ((j - cy) / R) + 0.6 * ((i - cx) / R)    # the crown's bottom-right is in shade
                k = 1
                if lit > 0.55 and whole < 0.3:
                    k = 0
                elif lit < -0.45 or whole > 0.55:
                    k = 2 if whole < 0.85 else 3
                if whole > 1.0:
                    k = 3
                if (i * 7 + j * 3) % 11 == 0 and k < 3:
                    k += 1                                       # a little leaf texture
                s.put(i, j, f"t{min(5, k + dark)}")
    for _ in range(int(10 * size)):                              # leaf glints on the lit side
        x, y = int(cx + r.uniform(-R, R * 0.3)), int(cy + r.uniform(-R * 0.9, 0))
        if s.get(x, y)[3]:
            s.put(x, y, f"t{dark}")
    return tight(s).outline()


def fir(seed, size=1.0):
    r = rng("fir", seed)
    w, h = int(26 * size), int(50 * size)
    s = Sprite(w, h)
    cx = w / 2
    s.rect(int(cx - 2), h - 7, 4, 7, "trunk2"); s.rect(int(cx - 2), h - 7, 2, 7, "trunk")
    tiers = 6
    for t in range(tiers):
        top = int(t * (h - 9) / (tiers + 0.3))
        bottom = int(top + (h - 9) / tiers * 1.65)
        half = (w / 2 - 1) * (0.32 + 0.68 * (t + 1) / tiers)
        for j in range(top, min(bottom, h - 6)):
            f = (j - top) / max(1, bottom - top)
            span = half * f ** 0.85 + 1
            droop = (j == min(bottom, h - 6) - 1)
            for i in range(int(cx - span), int(cx + span) + 1):
                rel = (i - cx) / max(1, span)
                if droop and (i + t) % 3 == 0:
                    continue                                     # jagged branch tips
                c = "p3" if f > 0.86 else "p2" if rel > 0.3 else "p0" if rel < -0.45 and f < 0.75 else "p1"
                if c == "p1" and (i * 5 + j * 3) % 13 == 0:
                    c = "p2"
                s.put(i, j, c)
    s.put(int(cx), 0, "p0"); s.put(int(cx), 1, "p1")
    return tight(s).outline()


def flower_bush(seed):
    r = rng("fbush", seed)
    s = Sprite(20, 15)
    for (x, y, rr) in [(6, 8, 5.5), (13, 8, 5.5), (9.5, 5, 5.5)]:
        for j in range(15):
            for i in range(20):
                dx, dy = i + 0.5 - x, j + 0.5 - y
                if dx * dx + dy * dy <= rr * rr:
                    lit = -(dx + dy) / rr
                    s.put(i, j, "t0" if lit > 0.7 else "t2" if lit < -0.4 or j > 11 else "t1")
    col = r.choice(["fl_p", "fl_w", "fl_y", "fl_o"])
    for _ in range(9):
        x, y = r.randint(3, 16), r.randint(2, 10)
        if s.get(x, y)[3]:
            s.put(x, y, col); s.put(x + 1, y, col)
    return tight(s).outline()


def mossy_rock(seed):
    r = rng("mrock", seed)
    w = r.choice([12, 14])
    s = Sprite(w, 9)
    s.disc(w / 2 - 0.5, 5, w / 2, "s1", squash=0.65)
    for i in range(1, w - 2):
        s.put(i, 3, "s0")
    for i in range(w // 2, w - 1):
        s.put(i, 6, "s2")
    for _ in range(4):
        s.put(r.randint(2, w - 3), r.randint(2, 4), "moss")
    return tight(s).outline()


def pebbles(seed):
    r = rng("peb", seed)
    s = Sprite(14, 7)
    for _ in range(4):
        x, y, rr = r.uniform(2, 11), r.uniform(2.5, 4.5), r.uniform(1.3, 2.2)
        s.disc(x, y, rr, "s1", squash=0.7)
        s.put(int(x - 0.5), int(y - 0.8), "s0")
    return tight(s).outline()


def tuft(seed):
    r = rng("tuft", seed)
    s = Sprite(12, 9)
    for k in range(7):
        x = 1 + k * 1.5 + r.uniform(-0.4, 0.4)
        hgt = r.randint(4, 8)
        for j in range(hgt):
            s.put(int(x + (j / hgt) * r.uniform(-1.5, 1.5)), 8 - j, "t0" if j > hgt - 2 else "t1" if j > 1 else "t3")
    return tight(s)


def mushrooms(seed):
    r = rng("mush", seed)
    s = Sprite(12, 9)
    for k in range(r.randint(2, 3)):
        x = 2 + k * 4 + r.randint(0, 1)
        s.rect(x, 5, 1, 3, "c0")
        s.rect(x - 2, 3, 5, 2, "r1"); s.rect(x - 1, 2, 3, 1, "r1"); s.put(x - 1, 3, "fl_w"); s.put(x + 1, 2, "fl_w")
    return tight(s).outline()


def flower_clump(seed):
    r = rng("fclump", seed)
    s = Sprite(12, 10)
    col = r.choice(["fl_p", "fl_w", "fl_y", "fl_o", "jf1"])
    for k in range(5):
        x, y = r.randint(2, 9), r.randint(2, 6)
        s.put(x, y + 2, "t2"); s.put(x, y + 3, "t3")
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            s.put(x + dx, y + dy, col)
        s.put(x, y, "fl_y" if col != "fl_y" else "fl_o")
    return tight(s).outline()


def details():
    out = {}
    for k in range(2):
        out[f"detail-pebbles-{k + 1}"] = pebbles(k)
        out[f"detail-tuft-{k + 1}"] = tuft(k)
        out[f"detail-flowers-{k + 1}"] = flower_clump(k)
    out["detail-mushrooms"] = mushrooms(0)
    return out


def nature():
    """The isometric versions of the nature props, by their catalog names."""
    out = {}
    for dark in (0, 1, 2):
        for k, size in enumerate((0.95, 1.0, 1.05, 1.1, 1.25, 1.35)):
            out[f"tree-{k + 1}" + (f"-d{dark}" if dark else "")] = oak(f"o{k}", size, dark)
    for k, size in enumerate((1.0, 1.1, 1.25, 1.4)):
        out[f"pine-{k + 1}"] = fir(f"f{k}", size)
    for k in range(3):
        out[f"bush-{k + 1}"] = flower_bush(f"b{k}")
    for k in range(2):
        out[f"rock-{k + 1}"] = mossy_rock(f"r{k}")
    out.update(details())
    return out
