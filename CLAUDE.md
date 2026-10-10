# tiny-town

A browser map builder for pixel towns (isometric or top-down). Public repo: https://github.com/itsHendri/tiny-town,
live at https://itshendri.github.io/tiny-town/ (GitHub Pages from `main`, root; every push to `main` redeploys).
Code MIT (`LICENSE`), art CC BY 4.0 (`LICENSE-art`). Read `README.md` for the user-facing side.

## How to work with me

* I'm Hendri, a design engineer. Explain briefly, one step at a time. Keep answers short: key points only.
* When I'm exploring or deciding: push back, question assumptions, mention alternatives. When I ask you to build: just
  do it well.
* For visual choices, show me many drawn options and let me pick in rounds (a picker page with a pick and a note per
  option works well). I prefer art drawn in code over downloaded assets.
* Never use em dashes in anything you write for me (code comments, docs, commit messages included).
* This repo is **public**. Nothing private goes in: no secrets, no LAN addresses, hostnames or Tailscale names from my
  home server. Before every push: `grep -rnE "curiouscat\.local|192\.168|tail[b]a68|100\.75\." --exclude-dir=.git .` must return nothing.
* Commit when a piece of work is done and checked; push when I say so (pushing publishes the site).

## Running and building

* Serve the folder (the page fetches its tiles): `python3 -m http.server 8000`, then http://localhost:8000.
  No build step, no npm: plain ES modules.
* Python art needs Pillow. My venv: `~/.venvs/curiouscat-art/bin/python` (or any Python with `pip install pillow`).
  Run scripts from the repo root: `~/.venvs/curiouscat-art/bin/python art/<script>.py`.

| Command | Does |
|---|---|
| `art/iso_tiles.py earthy` | Rebuilds `tiles/iso/` (isometric tile sheet + prop atlas). Run after any art change. |
| `art/tiles.py` | Rebuilds `tiles/` (the top-down sheet, props, `sprites/index.json`). |
| `art/reference_town.py` | Rebuilds `maps/market-village.ldtk` (the default example) and `out/market-village*.png`. Copy the scene to `docs/market-village.png` when the look changes. |
| `art/render_map.py <map.ldtk> <out.png> [--crop]` | Draws any map in Python. |
| `art/dress.py <in.ldtk> <out.ldtk>` | Adds road-edge details and trees to any map (same result every time). |
| `art/parity_ref.py` | Writes the parity test map (see below). |
| `art/iso_village.py`, `art/preview.py` | Comparison sheets for picking looks (output in `out/`, which is gitignored). |

## Architecture

* **Python draws, the browser places.** `art/` draws every tile, prop and tree into PNG sheets plus JSON. The browser
  (`js/`) only places tiles and sprites, so the editor previews live.
* **Python is also the reference renderer** (`art/iso.py` for isometric, `art/preview.py` for top-down). `js/iso.js`
  and `js/render.js` must draw **the same pixels**. Any change to how the ground, walls, margin or uprights are drawn
  goes into both, then run the parity check.
* **Dual-grid autotiling** (`art/dualgrid.py`): one value per cell; display tiles sit half a cell off and read 4
  corners as a 4-bit mask, 16 shapes per terrain, corners rounded (radius 7). Terrains are layered by priority
  (`OVERLAYS` in `js/registry.js`: dirt, water+bridge, soil, path, cobbles).
* **Height** 0-4. Neighbouring cells never differ by more than one level (nudged when painting, OpenTTD style).
  The **ground level** is the height most of the map's edge stands at (`groundLevel` in `js/iso.js`, `ground_level`
  in `art/iso.py`): the margin sits on it, and lower cells are pits. Lowering a cell at 0 lifts the whole map a level
  first; a stroke that leaves nothing at 0 settles it back down.
  Cliff walls aren't tiles: each level's fill outline is pushed down 16 px (front-left lit, front-right shaded),
  waterfalls where water meets the edge.
* **Isometric view:** cell diamond 32x16, level height 16. `screen = (u-v, (u+v)/2 - L*16) + (X0, Y0)`; object feet
  use the cell centre (v-8). Ground patterns repeat every 64x32 with 8 lattice phases. Drawing is back to front, per
  cell column, clipped pixel-exactly (1 px row rects in JS, `in_column` in Python; no antialiased clips, they break
  parity). Sort key: cells (c+r, 0), uprights 0.5, objects 1.
* **Forest margin:** a darker meadow with trees round the map; roads and rivers run on past the edge (at most 3 cells).
  The margin tree list exists twice and must match: `MARGIN_TREES` in `art/iso.py` and in `js/iso.js`.
* **Palettes** (`art/palettes.py`) swap the colours behind names; `palettes.use()` must run before other art imports.
* **Props:** isometric buildings, stalls, fences, stairs use a face painter (`Canvas3D` in `art/iso_props.py`).
  Anchors (`ax`, `ay`) and footprints (`foot`) live in `tiles/iso/props.json`; aliases map old names to new ones so old
  maps keep working. Trees: `art/iso_trees.py` (many kinds, varied per seed); the editor groups them by name regex.
* **Editor** (`js/editor.js`): one state object `S` (projection `"iso"` or top-down, view `S.V`). One active tool,
  `S.tool` (`brush` while a swatch is chosen, `place scatter stamp`, `area` for a new stamp, or `select`: nothing in hand,
  clicks select and drags move or pan); `S.place` / `S.pasting` are only what
  `place` / `stamp` put down, and `setTool` clears the rest. Painting just past the edge grows the map (`grow` in
  `tools.js`); `rebuildView(dc, dr)` keeps the screen still when the view changes shape. A view abstraction
  (`pt`, `feet`, `cellPoly`, `pick`, `border`) keeps tools projection-free. Undo is snapshots; autosave in
  localStorage; `window.tinyTown = { state, history }` for debugging in the console.
* Other modules: `tools.js` (brush, line, rect, fill, height shaping, plots, resize, History), `stamps.js`,
  `share.js` (share codes: gzip + base64url, prefix `tinytown1:`), `files.js` (save picker, then a download fallback),
  `walk.js` (walk mode; props with a `foot` block their cells), `format.js` (parse/build `.ldtk`).

## Map format (keep it stable)

`.ldtk` files, a subset of LDtk 1.5.3. Layers: `Height`, `Terrain`, `Features`, `Deco` (IntGrid) and `Objects`
(Entities: `Prop`, `Character`, `Path`, `Region`). uids are fixed: layers Objects=1, Deco=2, Features=3, Terrain=4,
Height=5; entities 10/20/30/40; fields 11, 21-25, 31-32, 41; `nextUid` 100. Terrain values: grass 0, path 1,
cobbles 2, water 3, soil 4, bridge 5, dirt 6. `art/ldtk.py` writes stable uuid5 ids so a rebuilt map only changes
where it really changed.

Add new terrains, deco or entity kinds in `js/registry.js` (and the Python dicts that mirror it). Never renumber
existing values. If the format must change, bump `tinyTownVersion` in `js/format.js` and migrate old files on load.

## The look (Hendri's picks, keep them)

* Isometric is the main view; top-down still works.
* Palette `earthy`, but with the **bright road (cobbles) and bright water** (`COBBLE_BRIGHT`, `WATER_BRIGHT`).
* Houses: the `storybook` look (`LOOK` in `art/iso_tiles.py`).
* Trees: lots of variety, no two alike; leaves use hash speckle, not dither stripes.
* Reference: the market village (`docs/market-village.png`) was rebuilt from a storybook-style picture of a market
  town; it is the quality bar.

## Checking work

* **Parity** (after any renderer change): run `art/parity_ref.py` (a level-0 map, and a dug map with a margin), serve
  the folder, open the editor, and run in the browser console:

  ```js
  const I = await import("/js/iso.js"), { newMap } = await import("/js/format.js");
  const ts = tinyTown.state.isoTs || await I.loadIsoTileset("tiles/iso/"), res = {};
  for (const name of ["iso-ref", "iso-ref-dig"]) {
    const d = await (await fetch(`/out/${name}.json`, { cache: "reload" })).json();
    const m = newMap(d.cols, d.rows); m.layers.Height.set(d.H); m.layers.Terrain.set(d.T); m.layers.Features.set(d.F); m.layers.Deco.set(d.D);
    const c = I.bakeIso(m, ts, I.isoView(m, { margin: d.margin || 0 }), { objects: false })[1];
    const im = await new Promise((ok) => { const i = new Image(); i.onload = () => ok(i); i.src = `/out/${name}.png?` + Date.now(); });
    const c2 = document.createElement("canvas"); c2.width = c.width; c2.height = c.height; c2.getContext("2d").drawImage(im, 0, 0);
    const A = c.getContext("2d").getImageData(0, 0, c.width, c.height).data, B = c2.getContext("2d").getImageData(0, 0, c.width, c.height).data;
    let big = 0; for (let i = 0; i < A.length; i += 4) if (Math.max(...[0, 1, 2, 3].map((k) => Math.abs(A[i + k] - B[i + k]))) > 3) big++;
    res[name] = big;
  }
  res  // every count must be 0
  ```

  Extend `art/parity_ref.py` when you add something the test map doesn't cover (fences, stairs, bridges, dirt).
* In the browser pane: paint each terrain, raise and lower, stairs, place and move a prop, undo/redo, save and reopen,
  walk mode, both projections, and phone width.
* Gotchas: the page caches modules (reload, or fetch with `cache: "reload"`); a hidden browser pane pauses
  `requestAnimationFrame`, so test logic directly instead of waiting on animation.

## CuriousCat uses this

My home server project (`~/Development/curiouscat`, private) shows its "town" page with a copy of this renderer. It
is synced by hand from that repo (`look/sync-tiny-town.sh look/town5`), never from here. Last synced at commit
`577080c`, so `git log 577080c..` lists what's new for the next sync.

So the town page keeps working, keep these stable (or note the change in the commit message):

* `parseMap` in `js/format.js`; `loadIsoTileset`, `isoView(map, { margin })` and `bakeIso(map, ts, view)` (returns
  one canvas per water frame) in `js/iso.js`.
* `tiles/iso/` layout and prop names (use aliases when renaming).
* Entities: `Character` fields `id`, `sprite`, `path`, `perch`, `flyTo`; `Path` with `name` and `points`; `Region`
  with `name`; `Prop` with `sprite` (lamps are found by a `lamp` name prefix).

## Ideas, next up

From the README's list: isometric palette swatches; more buildings (mill,
tavern, chapel), stall goods, carts; sounds (off by default); per-terrain cliff lips; a darker roof option;
characters drawn for the isometric angle (the sprites in `sprites/` are still straight-on).
