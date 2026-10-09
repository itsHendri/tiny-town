# tiny-town

A small map builder for top-down pixel towns (GBA / Stardew style, 16 px tiles), made for drawing your own little world.
It runs in the browser with no install and no build step. The art is drawn in code and can be repainted by hand.

Status: early but usable. Paint ground, up to four levels of height with stairs and waterfalls, fences, gates,
flowers and tall grass; fence a yard in one drag; scatter trees; place props and characters; select, copy and paste
areas and keep them as stamps; undo; save and open `.ldtk` maps; export a PNG; share a map as a short text code.

## Running it

The page loads its tiles with `fetch`, so open it through any small web server, not as a file:

```bash
python3 -m http.server 8000
```

then visit http://localhost:8000. Your map is kept in the browser as you work; **Save** writes a `.ldtk` file.

| Do | How |
|---|---|
| Paint | Pick a swatch (or keys 1-9). Brush, Box or Fill; `[` `]` change the brush size. Right-click erases, Alt-click picks, Shift-click draws a straight line from the last stroke. |
| Height | Raise, Lower and Flatten. Neighbours are nudged so side-by-side cells are never more than one level apart; a cliff face appears under every south edge. Paint Stairs on a cliff face to climb it. |
| Yards | The Plot tool (T): drag a rectangle to fence it, with a gate on the side facing the nearest path. |
| Place | Objects mode: pick a prop or character, click the map. Click to select, drag to move, Shift for off-grid. Turn on Scatter and drag to sprinkle trees or bushes; right-drag clears them. |
| Reuse | Select (S) an area, then Copy, Cut or Save as stamp. Ctrl+V or a stamp places it again; Esc stops. |
| Share | Share code: the whole map as one line of text (a few KB). Paste one to open it. |
| Move around | Wheel or two fingers to pan, Ctrl+wheel or pinch to zoom, hold Space and drag. |
| Check the data | Shift+R shows the raw grid, like LDtk. |

## Map files

Maps are saved as `.ldtk` files: a small subset of [LDtk](https://ldtk.io)'s documented JSON format (version 1.5.3),
so they can also be opened in LDtk and read by its loaders.

| Layer | Kind | Holds |
|---|---|---|
| `Terrain` | IntGrid | grass, path, cobbles, water, crops, forest floor, bridge |
| `Height` | IntGrid | 0 to 4 (levels) |
| `Features` | IntGrid | stairs |
| `Deco` | IntGrid | fence, flowers, tall grass, gate |
| `Objects` | Entities | trees, houses, props, characters, paths, regions |

## Folders

| Path | What |
|---|---|
| `art/` | Python (Pillow) that draws the art: `dualgrid.py` (tile shapes), `styles.py` (every look), `props.py`, `tiles.py` (builds the sheets), `preview.py` (style comparisons), `ldtk.py` (writes maps) |
| `tiles/` | The tile sheet (`tileset.png` + `tileset.json`), the prop atlas (`props.png` + `props.json`), and `tileset.edited.png`, your hand edits (they win) |
| `index.html`, `js/` | The editor: `editor.js` (the page), `tools.js` (painting, fill, height, plots, undo), `stamps.js` (copy, paste, stamps), `share.js` (share codes), `files.js` (open, save, autosave), `registry.js` (what can be painted and placed), `format.js` (load/save maps), `render.js` (draws a map) |
| `maps/` | Example maps |
| `sprites/` | Example characters (one PNG each, feet at the bottom centre) |

## Regenerating the art

Needs Python 3 and Pillow (`pip install pillow`).

```bash
python art/tiles.py
```

writes `tiles/`. `python art/preview.py options out/options` draws every style option on a sample scene.

## Repainting tiles

Make `tiles/tileset.edited.png` the same size as `tiles/tileset.png` (copy it, then erase every tile you don't change)
and paint in your pixel editor (Aseprite, Pixelorama, Piskel, even Figma). Any 16x16 tile in the edited sheet that isn't
fully transparent replaces the generated one when the page loads, so regenerating the art never overwrites your edits.

## Roadmap

1. Repo skeleton (done)
2. Tile sheet drawn in code, picked in rounds (done)
3. Map format, renderer and an example map (done)
4. The editor: paint, height, stairs, entities, undo, save/open, export PNG (done)
5. Polish the example town
6. Publish on GitHub Pages

## Ideas, next up

From research into LDtk, Tiled, porymap, RPG Maker, CrossCode, OpenTTD, Mindustry and Mario Maker:

* **Walk mode:** drop a character and walk around (cliffs, water and fences block; stairs climb), then straight back to editing.
* **Built-in stamps:** a cottage with a yard and fence, a pond, a market square, so a town starts in a few clicks.
* **Art polish:** tall grass that sways, a nicer side gate, per-terrain cliff lips (a cobble edge on a cobbled square), slight tint per level.
* **Phone editing:** a fixed tool bar at the bottom, long-press to pick.
* **Cliffs facing east and west:** side ramps and stairs need extra art.

## License

Code: MIT (`LICENSE`). Art: CC BY 4.0 (`LICENSE-art`).
