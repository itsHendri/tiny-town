// Isometric view: the same map data drawn as 32x16 diamonds, with levels lifted 16 px each.
// Mirrors art/iso.py (the Python reference that draws the same pixels).
//
//   const ts = await loadIsoTileset("tiles/iso/");
//   const view = isoView(map);                       // layout: canvas size, where cells land
//   const frames = bakeIso(map, ts, view);           // the static scene (ground, cliffs, props), per frame
//   view.toScreen(u, v, level), view.cellPoly(c, r, level), view.pick(x, y, map)

import { OVERLAYS, value } from "./registry.js";
import { drawProp, mergeEdited } from "./render.js";

const HT = 16;

function loadImage(src) {
  return new Promise((ok, fail) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => fail(new Error(`Couldn't load ${src}`)); im.src = src; });
}

export async function loadIsoTileset(base) {
  const json = await (await fetch(base + "tileset.json")).json();
  const img = await loadImage(base + json.image);
  const edited = await loadImage(base + "tileset.edited.png").catch(() => null);
  const props = await (await fetch(base + "props.json")).json();
  const propsImg = await loadImage(base + props.image);
  return { json, sheet: mergeEdited(img, edited), props: props.props, propsImg, frames: json.frames, frameMs: json.frameMs, iso: true };
}

const ihash = (...xs) => { let v = 0; for (const x of xs) v = Math.imul((v ^ (x >>> 0)) >>> 0, 2654435761) >>> 0; return v / 4294967296; };
const phase = (dx, dy) => `${((dx - dy) % 4 + 4) % 4},${((dx + dy) % 4 + 4) % 4}`;

// The map's ground level: the height most of its edge stands at (a tie goes to the lower one). The meadow round the
// map sits on it, and anything lower is a pit dug into the map. Same rule in art/iso.py.
export function groundLevel(m) {
  const n = [0, 0, 0, 0, 0, 0, 0, 0], H = m.layers.Height;
  for (let r = 0; r < m.rows; r++) for (let c = 0; c < m.cols; c++) if (r === 0 || c === 0 || r === m.rows - 1 || c === m.cols - 1) n[H[r * m.cols + c]]++;
  return n.indexOf(Math.max(...n));
}

// `margin` cells of meadow and darker forest are drawn round the map so it fills the frame.
export function isoView(m, { margin = 0 } = {}) {
  let top = 0;
  for (const v of m.layers.Height) if (v > top) top = v;
  const M = margin;
  const X0 = (m.rows + 2 * M) * 16 + 8, Y0 = top * HT + 24 + 16 * M;
  const W = (m.cols + m.rows + 4 * M) * 16 + 16, H = (m.cols + m.rows + 2 * M) * 8 + Y0 + 24;
  const cellTop = (c, r, L = 0) => [X0 + (c - r) * 16, Y0 + (c + r) * 8 - L * HT];
  return {
    iso: true, W, H, X0, Y0, top, margin: M,
    cellTop,
    // where map pixels (u, v) land on screen; objects stand in the middle of their cell
    toScreen: (u, v, L = 0) => [X0 + u - v, Y0 + (u + v) / 2 - L * HT],
    feet: (e, L = 0) => [X0 + e.x - (e.y - 8), Y0 + (e.x + e.y - 8) / 2 - L * HT],
    cellPoly(c, r, L = 0) { const [x, y] = cellTop(c, r, L); return [[x, y], [x + 16, y + 8], [x, y + 16], [x - 16, y + 8]]; },
    // the highest cell whose top is under screen point (x, y)
    pick(x, y, map) {
      for (let L = top; L >= 0; L--) {
        const dx = x - X0, dy = y - Y0 + L * HT;
        const u = (dx + 2 * dy) / 2, v = (2 * dy - dx) / 2;
        const c = Math.floor(u / 16), r = Math.floor(v / 16);
        if (c >= 0 && r >= 0 && c < map.cols && r < map.rows && map.layers.Height[r * map.cols + c] === L) return { c, r, L, u, v };
      }
      const dx = x - X0, dy = y - Y0, u = (dx + 2 * dy) / 2, v = (2 * dy - dx) / 2;
      return { c: Math.floor(u / 16), r: Math.floor(v / 16), L: 0, u, v };
    },
  };
}

// Chimney smoke: three puffs rising and drifting right, moving up 2 px a frame (the 3 frames loop seamlessly).
function smoke(g, x, y, frame) {
  for (let k = 0; k < 3; k++) {
    const rise = k * 6 + frame * 2, r = 2 + rise * 0.12;
    g.fillStyle = `rgba(236, 232, 222, ${(0.7 - rise / 26).toFixed(2)})`;
    g.beginPath(); g.arc(Math.round(x + rise * 0.35), Math.round(y - 3 - rise), r, 0, Math.PI * 2); g.fill();
  }
}

function canvas(W, H) { const c = document.createElement("canvas"); c.width = W; c.height = H; return c; }

// Keep only what lies over the map: a pixel stays if its centre traces back inside the grid (same rule in Python).
// Each row's inside part is one span, so the rest is cleared a row at a time.
function clipToMap(g, m, view, L) {
  const W = g.canvas.width, H = g.canvas.height, UW = m.cols * 16, VH = m.rows * 16;
  for (let y = 0; y < H; y++) {
    const dy = y + 0.5 - view.Y0 + L * HT;
    // u = (dx + 2dy) / 2 in [0, UW) and v = (2dy - dx) / 2 in [0, VH), with dx = x + 0.5 - X0
    const lo = Math.max(-2 * dy, 2 * dy - 2 * VH), hi = Math.min(2 * UW - 2 * dy, 2 * dy);
    const inside = (x) => { const dx = x + 0.5 - view.X0, u = (dx + 2 * dy) / 2, v = (2 * dy - dx) / 2; return u >= 0 && u < UW && v >= 0 && v < VH; };
    let x0 = Math.ceil(lo + view.X0 - 0.5) - 1, x1 = Math.floor(hi + view.X0 - 0.5) + 1;    // then nudge onto the exact edge
    while (x0 <= x1 && !inside(x0)) x0++;
    while (x1 >= x0 && !inside(x1)) x1--;
    if (x1 < x0) { g.clearRect(0, y, W, 1); continue; }
    if (x0 > 0) g.clearRect(0, y, x0, 1);
    if (x1 < W - 1) g.clearRect(x1 + 1, y, W - x1 - 1, 1);
  }
}

// Clip to one raised cell's column at one level (its diamond and the wall below it). The shape is built from
// one-pixel-high rectangles, so the clip is pixel-exact (a slanted path would get soft edges).
function clipColumn(g, x, y) {
  g.beginPath();
  for (let py = y - 1; py < y + 17 + HT; py++) {
    const dy = py + 0.5 - y, lim = Math.min(16, 2 * dy, 2 * (16 + HT - dy));
    if (lim < 0) continue;
    const x0 = Math.ceil(x - lim - 0.5), x1 = Math.floor(x + lim - 0.5);
    if (x1 >= x0) g.rect(x0, py, x1 - x0 + 1, 1);
  }
  g.clip();
}

// Push the level's outline down HT pixels: front-left wall lit, front-right in shade, waterfalls where water is
// at the edge. `fill` holds just the level's grass (its shape); `lay` is the whole level layer.
function walls(lay, fill, colors, frame) {
  const W = lay.width, H = lay.height;
  const fa = fill.getContext("2d").getImageData(0, 0, W, H).data;
  const g = lay.getContext("2d"), img = g.getImageData(0, 0, W, H), lp = img.data;
  const rgb = Object.fromEntries(Object.entries(colors).map(([k, v]) => [k, [parseInt(v.slice(1, 3), 16), parseInt(v.slice(3, 5), 16), parseInt(v.slice(5, 7), 16)]]));
  const waterSet = new Set(["w0", "w1", "w2", "w3"].filter((k) => rgb[k]).map((k) => rgb[k].join(",")));
  const A = (x, y) => fa[(y * W + x) * 4 + 3];
  const put = (x, y, k) => { const i = (y * W + x) * 4, c = rgb[k]; lp[i] = c[0]; lp[i + 1] = c[1]; lp[i + 2] = c[2]; lp[i + 3] = 255; };
  const bottoms = new Map();
  for (let x = 0; x < W; x++) for (let y = 0; y < H - 1; y++) if (A(x, y) && !A(x, y + 1)) { if (!bottoms.has(x)) bottoms.set(x, []); bottoms.get(x).push(y); }
  const near = (xx, y) => { let best = null; for (const b of bottoms.get(xx) || []) if (Math.abs(b - y) <= 6 && (best === null || Math.abs(b - y) < Math.abs(best - y))) best = b; return best; };
  const isWaterAt = (x, y) => { const i = (y * W + x) * 4; return waterSet.has(`${lp[i]},${lp[i + 1]},${lp[i + 2]}`); };
  const drawn = [];
  for (const [x, ys] of bottoms) for (const y of ys) {
    const a = near(x - 2, y), b = near(x + 2, y);
    const slope = a !== null && b !== null ? b - a : b !== null ? b - y : a !== null ? y - a : 0;
    const light = slope > 0 ? "left" : slope < 0 ? "right" : "tip";
    const water = isWaterAt(x, y);
    for (let k = 1; k <= HT; k++) {
      const yy = y + k;
      if (yy >= H || A(x, yy)) break;
      let col;
      if (water) { const ph = ((k - 2 * frame + Math.floor(ihash(x, 7) * 6)) % 6 + 6) % 6; col = ph === 0 || k === 1 ? "w0" : ph < 3 ? "w1" : "w2"; }
      else if (k === HT) col = "out";
      else if (k === 1) col = "g3";
      else if (k === 2 && ihash(x, 3) < 0.5) col = "g4";
      else {
        const band = ((k + Math.trunc(2 * Math.sin(x * 0.5)) + 64) % 6);
        const [lo, hi] = { left: ["k1", "k2"], tip: ["k2", "k2"], right: ["k2", "k3"] }[light];
        col = band === 0 ? "k3" : k < 9 ? lo : hi;
      }
      put(x, yy, col);
    }
    if (water) for (let k = HT + 1; k < HT + 4; k++) if (y + k < H && !A(x, y + k)) put(x, y + k, (x + k + frame) % 3 ? "w0" : "fl_w");
    drawn.push([x, y]);
  }
  for (const [x, y] of drawn) for (const side of [-1, 1]) {
    const xx = x + side;
    if (xx >= 0 && xx < W && near(xx, y) === null) for (let k = 1; k <= HT; k++) if (y + k < H && !A(x, y + k)) put(x, y + k, "out");
  }
  g.putImageData(img, 0, 0);
}

export function bakeIso(m, ts, view, { objects = true, frames: only = null } = {}) {
  const { cols, rows } = m, H = m.layers.Height, TER = m.layers.Terrain, FEAT = m.layers.Features, D = m.layers.Deco;
  const idx = (r, c) => Math.min(rows - 1, Math.max(0, r)) * cols + Math.min(cols - 1, Math.max(0, c));
  const STAIRS = value("Features", "stairs"), TALL = value("Deco", "tallgrass");
  const B = groundLevel(m);
  const onLevel = (i, L) => H[i] === L || (FEAT[i] === STAIRS && H[i] === L - 1);
  const sets = ts.json.sets;

  function dual(g, name, has, L, frame, ext = 0) {
    const tiles = sets[name];
    if (!tiles) return;
    for (let dy = -ext; dy <= rows + ext; dy++) for (let dx = -ext; dx <= cols + ext; dx++) {
      const mask = (has(idx(dy - 1, dx - 1)) ? 1 : 0) | (has(idx(dy - 1, dx)) ? 2 : 0) | (has(idx(dy, dx - 1)) ? 4 : 0) | (has(idx(dy, dx)) ? 8 : 0);
      if (!mask) continue;
      const frames = tiles[mask][phase(dx, dy)];
      const [x, y] = view.cellTop(dx, dy, L);
      const xy = frames[frame % frames.length];
      g.drawImage(ts.sheet, xy[0], xy[1], 32, 16, x - 16, y - 8, 32, 16);
    }
  }
  const FLOWERS = value("Deco", "flowers"), SOIL = value("Terrain", "soil"), BRIDGE = value("Terrain", "bridge"), WATER = value("Terrain", "water");
  const FENCE = value("Deco", "fence"), GATE = value("Deco", "gate");
  const ter = (r, c) => TER[idx(r, c)];
  const bridgeAxis = (r, c) => (ter(r, c - 1) !== WATER || ter(r, c + 1) !== WATER ? "x" : "y");
  const flat = (g, name, c, r, L) => { const xy = ts.json.flats?.[name]; if (!xy) return; const [x, y] = view.cellTop(c, r, L); g.drawImage(ts.sheet, xy[0], xy[1], 32, 16, x - 16, y, 32, 16); };

  function overlays(g, L, frame) {
    for (const o of OVERLAYS) {
      const vs = o.ids.map((id) => value("Terrain", id));
      dual(g, o.name, (i) => vs.includes(TER[i]) && onLevel(i, L), L, frame);
    }
    dual(g, "tallgrass", (i) => D[i] === TALL && H[i] === L, L, frame);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {   // flat things on single cells
      const i = r * cols + c;
      if (H[i] !== L) continue;
      if (D[i] === FLOWERS) flat(g, `flowers-${Math.floor(((r * 5 + c * 11) % 13) * 4 / 13)}`, c, r, L);
      if (TER[i] === SOIL) flat(g, "crops", c, r, L);
      if (TER[i] === BRIDGE) flat(g, `deck-${bridgeAxis(r, c)}`, c, r, L);
    }
  }

  // fences, gates, bridge rails and stairs stand up, so they're sorted with the props: [sprite name, c, r]
  function uprights() {
    const out = [];
    const fence = (r, c, L) => r >= 0 && r < rows && c >= 0 && c < cols && (D[r * cols + c] === FENCE || D[r * cols + c] === GATE) && H[r * cols + c] === L;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c, L = H[i];
      if (D[i] === GATE) out.push([fence(r, c - 1, L) || fence(r, c + 1, L) ? "_gate-x" : "_gate-y", c, r]);
      else if (D[i] === FENCE) out.push([`_fence-${(fence(r - 1, c, L) ? 1 : 0) | (fence(r, c + 1, L) ? 2 : 0) | (fence(r + 1, c, L) ? 4 : 0) | (fence(r, c - 1, L) ? 8 : 0)}`, c, r]);
      if (TER[i] === BRIDGE) {
        const axis = bridgeAxis(r, c);
        const sides = axis === "x" ? (ter(r - 1, c) !== BRIDGE ? "a" : "") + (ter(r + 1, c) !== BRIDGE ? "b" : "")
          : (ter(r, c - 1) !== BRIDGE ? "a" : "") + (ter(r, c + 1) !== BRIDGE ? "b" : "");
        if (sides) out.push([`_rail-${axis}-${sides}`, c, r]);
      }
      if (FEAT[i] === STAIRS) {
        if (r > 0 && H[i - cols] === L + 1) out.push(["_stairs-n", c, r]);
        else if (c > 0 && H[i - 1] === L + 1) out.push(["_stairs-w", c, r]);
      }
    }
    return out;
  }

  const M = view.margin || 0;
  // outside the map, a cell copies the nearest edge cell only where the ground crosses the edge (it and the cell two
  // further in agree), and only up to 3 cells out; past that the forest takes over
  function runOnFor(o) {
    const vs = o.ids.map((id) => value("Terrain", id));
    const has = (i) => vs.includes(TER[i]) && H[i] === B;
    return (r, c) => {
      if (r >= 0 && c >= 0 && r < rows && c < cols) return has(r * cols + c);
      const rc = Math.min(rows - 1, Math.max(0, r)), cc = Math.min(cols - 1, Math.max(0, c));
      if (Math.max(Math.abs(r - rc), Math.abs(c - cc)) > 3) return false;
      const ri = rc + (r < 0 ? 2 : r >= rows ? -2 : 0), ci = cc + (c < 0 ? 2 : c >= cols ? -2 : 0);
      return has(rc * cols + cc) && has(idx(ri, ci));
    };
  }
  const runs = OVERLAYS.filter((o) => ["water", "path", "cobbles"].includes(o.name)).map(runOnFor);
  const runOn = (r, c) => runs.some((f) => f(r, c));
  return Array.from({ length: ts.frames }, (_, frame) => {
    if (only && !only.includes(frame)) return null;
    const out = canvas(view.W, view.H), g = out.getContext("2d");
    g.imageSmoothingEnabled = false;
    if (M) {                                               // the margin: meadow round the map, a little darker
      const o = canvas(view.W, view.H), og = o.getContext("2d");
      for (let r = -M; r < rows + M; r++) for (let c = -M; c < cols + M; c++) {
        if (c >= 0 && r >= 0 && c < cols && r < rows) continue;
        const xy = ts.json.grass[phase(c, r)], [x, y] = view.cellTop(c, r, B);
        og.drawImage(ts.sheet, xy[0], xy[1], 32, 16, x - 16, y, 32, 16);
      }
      for (const o of OVERLAYS) {                           // roads and rivers run on out into the forest
        if (!["water", "path", "cobbles"].includes(o.name)) continue;
        const at = runOnFor(o);
        const tiles = sets[o.name];
        for (let dy = -M; dy <= rows + M; dy++) for (let dx = -M; dx <= cols + M; dx++) {
          const cl = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
          const A = (r, c) => at(cl(r, -M, rows + M - 1), cl(c, -M, cols + M - 1));
          const mask = (A(dy - 1, dx - 1) ? 1 : 0) | (A(dy - 1, dx) ? 2 : 0) | (A(dy, dx - 1) ? 4 : 0) | (A(dy, dx) ? 8 : 0);
          if (!mask) continue;
          const frames = tiles[mask][phase(dx, dy)], xy = frames[frame % frames.length], [x, y] = view.cellTop(dx, dy, B);
          og.drawImage(ts.sheet, xy[0], xy[1], 32, 16, x - 16, y - 8, 32, 16);
        }
      }
      og.globalCompositeOperation = "source-atop"; og.fillStyle = "rgba(34, 40, 18, 0.275)"; og.fillRect(0, 0, view.W, view.H);
      g.drawImage(o, 0, 0);
    }
    const ground = canvas(view.W, view.H), gg = ground.getContext("2d");
    gg.imageSmoothingEnabled = false;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const xy = ts.json.grass[phase(c, r)], [x, y] = view.cellTop(c, r);
      gg.drawImage(ts.sheet, xy[0], xy[1], 32, 16, x - 16, y, 32, 16);
    }
    overlays(gg, 0, frame);
    clipToMap(gg, m, view, 0);
    if (B) clipToMap(gg, m, view, B);                     // below the ground level it only shows inside the pits
    g.drawImage(ground, 0, 0);

    const levels = [];
    for (let L = 1; L <= view.top; L++) {
      const lay = canvas(view.W, view.H), lg = lay.getContext("2d"), fill = canvas(view.W, view.H), fg = fill.getContext("2d");
      const high = (i) => H[i] >= L;
      dual(lg, "raised_fill", high, L, frame);
      overlays(lg, L, frame);
      dual(lg, "raised_edge", high, L, frame);
      // up to the ground level the fill runs on past the edge, so the map's edge gets no wall
      dual(fg, "raised_fill", high, L, frame, L <= B ? Math.max(M, 1) : 0);
      clipToMap(lg, m, view, L);
      if (L < B) clipToMap(lg, m, view, B);
      if (L > B) clipToMap(fg, m, view, L);
      walls(lay, fill, ts.json.colors, frame);
      levels[L] = lay;
    }

    // back to front: each raised cell's column, then the objects standing there
    const items = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) if (H[r * cols + c] > 0) items.push([c + r, 0, c, r]);
    if (objects) for (const e of m.entities) if (e.type === "Prop") {
      const c = Math.floor(e.x / 16), r = Math.floor((e.y - 1) / 16);
      items.push([c + r, 1, e]);
    }
    if (objects && M) {                                    // the forest round the edge
      const trees = ["tree-1-d1", "tree-1-d2", "tree-5-d2", "pine-1", "pine-3", "tree-2-d2", "pine-2", "tree-4-d1", "spruce-2", "oak-3", "pine-5", "tree-4-d2"];   // the same list is in art/iso.py
      for (let r = -M; r < rows + M; r++) for (let c = -M; c < cols + M; c++) {
        if ((c >= 0 && r >= 0 && c < cols && r < rows) || ihash(c & 0xffff, r & 0xffff, 11) >= 0.45) continue;
        if (runOn(r, c)) continue;                         // keep the road or river leaving the map clear
        items.push([c + r, 1, { type: "Prop", x: c * 16 + 8, y: (r + 1) * 16, fields: { sprite: trees[Math.floor(ihash(c & 0xffff, r & 0xffff, 13) * trees.length)] } }]);
      }
    }
    for (const [name, c, r] of uprights()) items.push([c + r, 0.5, { type: "Prop", x: c * 16 + 8, y: (r + 1) * 16, fields: { sprite: name } }]);
    items.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    for (const it of items) {
      if (it[1] === 0) {
        const [, , c, r] = it;
        for (let L = 1; L <= H[r * cols + c]; L++) {
          const [x, y] = view.cellTop(c, r, L);
          g.save();
          clipColumn(g, x, y);
          g.drawImage(levels[L], x - 17, y - 1, 34, 18 + HT, x - 17, y - 1, 34, 18 + HT);
          g.restore();
        }
      } else {
        const e = it[2], c = Math.floor(e.x / 16), r = Math.floor((e.y - 1) / 16);
        const L = c >= 0 && r >= 0 && c < cols && r < rows ? H[r * cols + c] : B;      // the forest round the edge stands on the ground level
        const [x, y] = view.feet(e, L);
        drawProp(g, ts, e.fields.sprite, x, y);
        const p = ts.props[e.fields.sprite];
        if (p?.smoke) smoke(g, Math.round(x - p.ax) + p.smoke[0], Math.round(y - p.ay) + p.smoke[1], frame);
      }
    }
    return out;
  });
}
