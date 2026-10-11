"""Build the tile sheet and the prop atlas that the browser renderer uses.

    python art/tiles.py [palette]  -> tiles/tileset.png + tileset.json, tiles/props.png + props.json, sprites/index.json

The look comes from preview.DEFAULT (the styles picked so far). Everything is drawn in code; a hand-painted
tiles/tileset.edited.png with the same layout wins tile by tile when the page loads.
"""
import json
import sys
from pathlib import Path

from PIL import Image

from dualgrid import T
from preview import DEFAULT, FRAMES, GRASS_N, SETS, STYLE_OF
from props import catalog
from styles import ANIMATED, FENCE, SHARED, TOP_PHASES, bridge_tile, cliff_piece, crop_tile, flower_tile, gate_tile, grass_cell_top, side_stairs, terrain_tile

ROOT = Path(__file__).resolve().parent.parent
COLS = 16                                                     # sheet width in tiles
ENDS = ("continue", "outer", "inner")


class Sheet:
    """Packs 16 px tiles left to right, top to bottom; taller pieces take a column of tiles."""

    def __init__(self):
        self.items = []                                           # (image, x, y)
        self.x = self.y = 0
        self.row_h = 1

    def add(self, im):
        w, h = im.width // T, im.height // T
        if self.x + w > COLS:
            self.newline()
        x, y = self.x * T, self.y * T
        self.items.append((im, x, y))
        self.x += w
        self.row_h = max(self.row_h, h)
        return [x, y]

    def newline(self):
        if self.x:
            self.x, self.y, self.row_h = 0, self.y + self.row_h, 1

    def image(self):
        H = max(y + im.height for im, x, y in self.items)
        out = Image.new("RGBA", (COLS * T, H), (0, 0, 0, 0))
        for im, x, y in self.items:
            out.alpha_composite(im, (x, y))
        return out


def build_tileset(style):
    sh = Sheet()
    meta = {"version": 1, "tileSize": T, "image": "tileset.png", "style": style, "frames": FRAMES, "frameMs": 320}
    meta["grassN"] = GRASS_N                                  # flat grass: a tile per (column % N, row % N)
    meta["grass"] = {f"{a},{b}": sh.add(grass_cell_top((a, b)).im) for b in range(GRASS_N) for a in range(GRASS_N)}
    meta["crop"] = sh.add(crop_tile().im)
    meta["bridge"] = {}
    for horiz in (True, False):
        for start in (0, 1):
            for end in (0, 1):
                meta["bridge"][f"{'h' if horiz else 'v'}{start}{end}"] = sh.add(bridge_tile(horiz, bool(start), bool(end)).im)
    sh.newline()
    meta["sets"] = []
    for name, key in SETS:
        st = style[key] if key else STYLE_OF[name]
        frames = FRAMES if name in ANIMATED else 1
        tiles = [None] * 16
        if (name, st) in SHARED:                              # textures shared with isometric: a tile per phase
            for mask in range(1, 16):                         # (display tile column % 4, row % 2)
                tiles[mask] = {f"{a},{b}": [sh.add(terrain_tile(name, st, mask, style["radius"], f, 0, (a, b)).im)
                                            for f in range(frames)] for a, b in TOP_PHASES}
            sh.newline()
        else:
            for f in range(frames):
                for mask in range(1, 16):
                    xy = sh.add(terrain_tile(name, st, mask, style["radius"], f).im)
                    tiles[mask] = (tiles[mask] or []) + [xy]
                sh.newline()
        meta["sets"].append({"name": name, "style": st, "tiles": tiles})
    meta["fence"] = [sh.add(FENCE[style["fence"]](conn).im) for conn in range(16)]
    meta["gate"] = {"h": sh.add(gate_tile(True).im), "v": sh.add(gate_tile(False).im)}
    meta["flowers"] = [sh.add(flower_tile(v).im) for v in range(4)]
    meta["side"] = {side: sh.add(side_stairs(style["side"], side).im) for side in ("w", "e")}
    sh.newline()
    pieces = {}
    for kind in ("face", "stairs", "waterfall"):
        for left in ENDS:
            for right in ENDS:
                frames = FRAMES if kind == "waterfall" else 1
                pieces[f"{kind}/{left}/{right}"] = [sh.add(cliff_piece(style["cliff"], kind, left, right, style["radius"], f).im) for f in range(frames)]
    meta["cliff"] = {"size": [T, 3 * T], "offsetY": -T, "pieces": pieces}
    return sh.image(), meta


def build_props():
    """Shelf-pack every prop into one atlas."""
    props = catalog()
    order = sorted(props.items(), key=lambda kv: -kv[1][0].h)
    W = 512
    x = y = shelf = 0
    placed = {}
    for name, (spr, shadow) in order:
        if x + spr.w > W:
            x, y, shelf = 0, y + shelf + 1, 0
        placed[name] = {"x": x, "y": y, "w": spr.w, "h": spr.h, "shadow": shadow}
        x += spr.w + 1
        shelf = max(shelf, spr.h)
    out = Image.new("RGBA", (W, y + shelf), (0, 0, 0, 0))
    for name, (spr, _) in props.items():
        p = placed[name]
        out.alpha_composite(spr.im, (p["x"], p["y"]))
    return out, {"version": 1, "image": "props.png", "props": dict(sorted(placed.items()))}


if __name__ == "__main__":
    import palettes
    palettes.use(sys.argv[1] if len(sys.argv) > 1 else palettes.DEFAULT)      # the same palette as tiles/iso/
    d = ROOT / "tiles"
    d.mkdir(exist_ok=True)
    im, meta = build_tileset(DEFAULT)
    im.save(d / "tileset.png")
    (d / "tileset.json").write_text(json.dumps(meta, separators=(",", ":")) + "\n")
    im, meta = build_props()
    im.save(d / "props.png")
    (d / "props.json").write_text(json.dumps(meta, indent=1) + "\n")
    sprites = ROOT / "sprites"                                   # the editor can't list a folder, so list the characters
    names = sorted(p.stem for p in sprites.glob("*.png"))
    (sprites / "index.json").write_text(json.dumps({"sprites": names}, indent=1) + "\n")
    print("wrote", d, "and", sprites / "index.json")
