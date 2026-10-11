"""Built-in stamps: little ready-made pieces of town, written to tiles/stamps.json.

    python art/builtin_stamps.py

Each stamp is drawn here as text rows, one letter per cell, plus objects placed by cell:
    .  grass      -  path       o  cobbles     ~  water      c  crops
    #  fence      g  gate (a path runs under it)        *  flowers     "  tall grass
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
T = 16
TERRAIN = {"-": 1, "g": 1, "o": 2, "~": 3, "c": 4}
DECO = {"#": 1, "*": 2, '"': 3, "g": 4}

STAMPS = [
    ("cottage", [
        "#######",
        "#.....#",
        "#.....#",
        "#.....#",
        "#*.-.*#",
        "#..-..#",
        "###g###",
        "...-...",
    ], [("house-red-m", 3, 3, 0), ("bush-1", 1, 2, 0)]),
    ("blue cottage", [
        "#######",
        "#.....#",
        "#.....#",
        "#.....#",
        "#..-.*#",
        "###g###",
        "...-...",
    ], [("house-blue-m", 3, 3, 0), ("barrel", 5, 3, 0)]),
    ("pond", [
        '..""...',
        '.~~~~..',
        '.~~~~~.',
        '..~~~~.',
        '...""*.',
    ], [("rock-1", 0, 1, 4), ("bush-2", 6, 1, 0)]),
    ("market", [
        "ooooooo",
        "ooooooo",
        "ooooooo",
        "ooooooo",
        "ooooooo",
    ], [("well", 3, 2, 0), ("lamp", 0, 1, 4), ("lamp", 6, 1, -4), ("bench", 2, 4, 0), ("bench", 5, 4, -8),
        ("barrel", 0, 3, 0), ("crate", 1, 4, -4), ("crate", 6, 3, 0)]),
    ("orchard", [
        "......",
        "......",
        "......",
        "......",
        "......",
        "******",
    ], [("tree-6", 1, 2, 0), ("blossom-1", 3, 2, 4), ("tree-6", 5, 2, 0), ("blossom-1", 0, 4, 8), ("tree-6", 2, 4, 8),
        ("blossom-1", 4, 4, 8)]),
    ("farm plot", [
        "#######",
        "#ccccc#",
        "#ccccc#",
        "#ccccc#",
        "###g###",
        "...-...",
    ], []),
]


def build():
    out = []
    for name, rows, objects in STAMPS:
        cols = len(rows[0])
        assert all(len(r) == cols for r in rows), name
        flat = "".join(rows)
        clip = {
            "cols": cols, "rows": len(rows),
            "layers": {
                "Height": [0] * len(flat),
                "Terrain": [TERRAIN.get(ch, 0) for ch in flat],
                "Features": [0] * len(flat),
                "Deco": [DECO.get(ch, 0) for ch in flat],
            },
            "entities": [{"type": "Prop", "x": c * T + T // 2 + dx, "y": (r + 1) * T, "w": T, "h": T, "fields": {"sprite": sprite}}
                         for sprite, c, r, dx in objects],
        }
        out.append({"name": name, "builtin": True, "clip": clip})
    return out


if __name__ == "__main__":
    path = ROOT / "tiles" / "stamps.json"
    path.write_text(json.dumps({"version": 1, "stamps": build()}, separators=(",", ":")) + "\n")
    print("wrote", path)
