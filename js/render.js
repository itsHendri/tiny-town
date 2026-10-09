// Draws a map from the tile sheet. Shared by the editor and any page that shows a town.
//
//   const ts = await loadTileset("tiles/");
//   drawTerrain(ctx, map, ts, frame);   // ground, water, cliffs, fences (frame 0..ts.frames-1 animates water)
//   drawProps(ctx, map, ts);            // trees, houses and other props, sorted by their feet
//
// `map` is the in-memory map from format.js: { cols, rows, layers: { Height, Terrain, Features, Deco }, entities }.

import { OVERLAYS, value } from "./registry.js";

const T = 16;

function loadImage(src) {
  return new Promise((ok, fail) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => fail(new Error(`Couldn't load ${src}`));
    im.src = src;
  });
}

// The generated sheet, with any non-empty tile of tileset.edited.png painted over it.
export function mergeEdited(img, edited) {
  const c = document.createElement("canvas");
  c.width = img.width; c.height = img.height;
  const g = c.getContext("2d");
  g.drawImage(img, 0, 0);
  if (!edited) return c;
  const e = document.createElement("canvas");
  e.width = edited.width; e.height = edited.height;
  const eg = e.getContext("2d");
  eg.drawImage(edited, 0, 0);
  const px = eg.getImageData(0, 0, e.width, e.height).data;
  for (let ty = 0; ty < Math.min(c.height, e.height); ty += T) {
    for (let tx = 0; tx < Math.min(c.width, e.width); tx += T) {
      let used = false;
      for (let y = ty; y < ty + T && !used; y++) for (let x = tx; x < tx + T; x++) if (px[(y * e.width + x) * 4 + 3]) { used = true; break; }
      if (used) { g.clearRect(tx, ty, T, T); g.drawImage(e, tx, ty, T, T, tx, ty, T, T); }
    }
  }
  return c;
}

export async function loadTileset(base) {
  const json = await (await fetch(base + "tileset.json")).json();
  const img = await loadImage(base + json.image);
  const edited = await loadImage(base + "tileset.edited.png").catch(() => null);
  const props = await (await fetch(base + "props.json")).json();
  const propsImg = await loadImage(base + props.image);
  const sets = Object.fromEntries(json.sets.map((s) => [s.name, s]));
  return { json, sheet: mergeEdited(img, edited), sets, props: props.props, propsImg, frames: json.frames, frameMs: json.frameMs, edited: !!edited };
}

// Bottom up, one level at a time: level 0's ground and overlays; then for each level above: its shadow, grass,
// overlays and edge, and the cliff faces under its south edges (which stand on the level below).
export function drawTerrain(ctx, m, ts, frame = 0) {
  const tile = (xy, dx, dy, w = T, h = T) => ctx.drawImage(ts.sheet, xy[0], xy[1], w, h, dx, dy, w, h);
  ctx.imageSmoothingEnabled = false;
  const { cols, rows } = m, H = m.layers.Height, TER = m.layers.Terrain, FEAT = m.layers.Features, D = m.layers.Deco;
  const idx = (r, c) => Math.min(rows - 1, Math.max(0, r)) * cols + Math.min(cols - 1, Math.max(0, c));
  const STAIRS = value("Features", "stairs"), SOIL = value("Terrain", "soil"), BRIDGE = value("Terrain", "bridge"),
    WATER = value("Terrain", "water"), FENCE = value("Deco", "fence"), GATE = value("Deco", "gate"),
    FLOWERS = value("Deco", "flowers"), TALL = value("Deco", "tallgrass");

  function dual(name, has) {
    const tiles = ts.sets[name]?.tiles;
    if (!tiles) return;
    for (let dy = 0; dy <= rows; dy++) for (let dx = 0; dx <= cols; dx++) {
      const mask = (has(idx(dy - 1, dx - 1)) ? 1 : 0) | (has(idx(dy - 1, dx)) ? 2 : 0) | (has(idx(dy, dx - 1)) ? 4 : 0) | (has(idx(dy, dx)) ? 8 : 0);
      if (!mask) continue;
      const frames = tiles[mask];
      tile(frames[frame % frames.length], dx * T - T / 2, dy * T - T / 2);
    }
  }

  // stairs belong to the level above too, so a path runs on into its stairs instead of stopping at the lip
  const onLevel = (i, L) => H[i] === L || (FEAT[i] === STAIRS && H[i] === L - 1);
  const isFace = (r, c, L) => r > 0 && r < rows && c >= 0 && c < cols && H[(r - 1) * cols + c] >= L && L > H[r * cols + c];

  function singles(L) {
    const ter = (r, c) => TER[idx(r, c)];
    const fence = (r, c) => r >= 0 && r < rows && c >= 0 && c < cols && (D[r * cols + c] === FENCE || D[r * cols + c] === GATE) && H[r * cols + c] === L;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      if (H[i] !== L) continue;
      if (TER[i] === SOIL) tile(ts.json.crop, c * T, r * T);
      if (TER[i] === BRIDGE) {
        const horiz = ter(r, c - 1) !== WATER || ter(r, c + 1) !== WATER;
        const key = horiz ? `h${+(ter(r - 1, c) !== BRIDGE)}${+(ter(r + 1, c) !== BRIDGE)}` : `v${+(ter(r, c - 1) !== BRIDGE)}${+(ter(r, c + 1) !== BRIDGE)}`;
        tile(ts.json.bridge[key], c * T, r * T);
      }
      if (D[i] === FLOWERS) tile(ts.json.flowers[Math.floor(((r * 5 + c * 11) % 13) / 13 * 4)], c * T, r * T);
      if (D[i] === GATE) tile(ts.json.gate[fence(r, c - 1) || fence(r, c + 1) ? "h" : "v"], c * T, r * T);
      else if (fence(r, c)) tile(ts.json.fence[(fence(r - 1, c) ? 1 : 0) | (fence(r, c + 1) ? 2 : 0) | (fence(r + 1, c) ? 4 : 0) | (fence(r, c - 1) ? 8 : 0)], c * T, r * T);
    }
  }

  function faces(L) {
    const cliff = ts.json.cliff;
    for (let r = 1; r < rows; r++) for (let c = 0; c < cols; c++) {
      if (!isFace(r, c, L)) continue;
      const above = TER[(r - 1) * cols + c];
      const kind = FEAT[r * cols + c] === STAIRS ? "stairs" : above === WATER || above === BRIDGE ? "waterfall" : "face";
      const end = (cc) => (cc < 0 || cc >= cols || isFace(r, cc, L)) ? "continue" : H[r * cols + cc] >= L ? "inner" : "outer";
      const frames = cliff.pieces[`${kind}/${end(c - 1)}/${end(c + 1)}`];
      tile(frames[frame % frames.length], c * T, r * T + cliff.offsetY, cliff.size[0], cliff.size[1]);
    }
    if (!ts.json.side) return;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {      // stairs up the east or west side of a hill
      const i = r * cols + c;
      if (FEAT[i] !== STAIRS || H[i] !== L - 1 || isFace(r, c, L)) continue;
      if (c > 0 && H[i - 1] === L) tile(ts.json.side.w, c * T, r * T);
      else if (c + 1 < cols && H[i + 1] === L) tile(ts.json.side.e, c * T, r * T);
    }
  }

  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) tile(ts.json.grass[Math.floor(((r * 7 + c * 13) % 11) / 11 * 4)], c * T, r * T);
  let top = 0;
  for (let i = 0; i < H.length; i++) if (H[i] > top) top = H[i];
  for (let L = 0; L <= top; L++) {
    if (L) { dual("raised_shadow", (i) => H[i] >= L); dual("raised_fill", (i) => H[i] >= L); }
    for (const o of OVERLAYS) {
      const vs = o.ids.map((id) => value("Terrain", id));
      dual(o.name, (i) => vs.includes(TER[i]) && onLevel(i, L));
    }
    dual("tallgrass", (i) => D[i] === TALL && H[i] === L);
    singles(L);
    if (L) { dual("raised_edge", (i) => H[i] >= L); faces(L); }
  }
}

// One prop, feet at (x, y), with a soft ground shadow.
export function drawProp(ctx, ts, name, x, y) {
  const p = ts.props[name];
  if (!p) return false;
  if (p.shadow) {
    ctx.fillStyle = "rgba(38, 48, 63, 0.28)";
    ctx.beginPath();
    ctx.ellipse(Math.round(x + 2), Math.round(y - 1), p.w * 0.46, 2.6, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.drawImage(ts.propsImg, p.x, p.y, p.w, p.h, Math.round(x - p.w / 2), Math.round(y - p.h), p.w, p.h);
  return true;
}

export function drawProps(ctx, m, ts) {
  ctx.imageSmoothingEnabled = false;
  const props = m.entities.filter((e) => e.type === "Prop").sort((a, b) => a.y - b.y);
  for (const e of props) drawProp(ctx, ts, e.fields.sprite, e.x, e.y);
}

// The whole static town (terrain + props) for each animation frame, ready to blit.
export function bakeFrames(m, ts) {
  return Array.from({ length: ts.frames }, (_, f) => {
    const c = document.createElement("canvas");
    c.width = m.cols * T; c.height = m.rows * T;
    const g = c.getContext("2d");
    drawTerrain(g, m, ts, f);
    drawProps(g, m, ts);
    return c;
  });
}
