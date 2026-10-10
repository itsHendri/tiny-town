// Copy, cut and paste rectangles of the map (every cell layer plus the objects standing in them), and stamps:
// saved copies you can place again and again, kept in this browser.

import { newMap } from "./format.js";
import { drawProp, drawTerrain } from "./render.js";
import { moveEntity } from "./tools.js";

const T = 16;
const KEY = "tiny-town/stamps";

export const area = (a, b) => ({ c0: Math.min(a[0], b[0]), r0: Math.min(a[1], b[1]), c1: Math.max(a[0], b[0]), r1: Math.max(a[1], b[1]) });

// The cell an object belongs to: where its feet are (props, characters), its first point (paths), its corner (regions).
function cellOf(e) {
  if (e.type === "Path") return e.fields.points?.[0] || [Math.floor(e.x / T), Math.floor(e.y / T)];
  if (e.type === "Region") return [Math.floor(e.x / T), Math.floor(e.y / T)];
  return [Math.floor(e.x / T), Math.floor((e.y - 1) / T)];
}
const within = (e, s) => { const [c, r] = cellOf(e); return c >= s.c0 && c <= s.c1 && r >= s.r0 && r <= s.r1; };

function shifted(e, dc, dr) {
  const copy = structuredClone(e);
  delete copy.iid;
  moveEntity(copy, dc, dr);
  return copy;
}

export function copyArea(m, s) {
  const cols = s.c1 - s.c0 + 1, rows = s.r1 - s.r0 + 1, layers = {};
  for (const [k, L] of Object.entries(m.layers)) {
    const out = new Uint8Array(cols * rows);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) out[r * cols + c] = L[(s.r0 + r) * m.cols + s.c0 + c];
    layers[k] = out;
  }
  return { cols, rows, layers, entities: m.entities.filter((e) => within(e, s)).map((e) => shifted(e, -s.c0, -s.r0)) };
}

export function clearArea(m, s) {
  for (const L of Object.values(m.layers)) for (let r = s.r0; r <= s.r1; r++) for (let c = s.c0; c <= s.c1; c++) L[r * m.cols + c] = 0;
  m.entities = m.entities.filter((e) => !within(e, s));
}

// Writes the clip with its top-left cell at (c0, r0); the parts that fall off the map are dropped.
export function pasteArea(m, clip, c0, r0) {
  for (const [k, L] of Object.entries(clip.layers)) {
    if (!m.layers[k]) continue;
    for (let r = 0; r < clip.rows; r++) for (let c = 0; c < clip.cols; c++) {
      const C = c0 + c, R = r0 + r;
      if (C >= 0 && R >= 0 && C < m.cols && R < m.rows) m.layers[k][R * m.cols + C] = L[r * clip.cols + c];
    }
  }
  const s = { c0: 0, r0: 0, c1: m.cols - 1, r1: m.rows - 1 };
  for (const e of clip.entities) {
    const placed = shifted(e, c0, r0);
    if (within(placed, s)) m.entities.push(placed);
  }
}

// A picture of a clip: its ground, then its props and characters.
export function drawClip(clip, ts, sprites) {
  const m = newMap(clip.cols, clip.rows);
  for (const [k, L] of Object.entries(clip.layers)) if (m.layers[k]) m.layers[k].set(L);
  const c = document.createElement("canvas");
  c.width = clip.cols * T; c.height = clip.rows * T;
  const g = c.getContext("2d");
  drawTerrain(g, m, ts, 0);
  for (const e of [...clip.entities].sort((a, b) => a.y - b.y)) {
    if (e.type === "Prop") drawProp(g, ts, e.fields.sprite, e.x, e.y);
    else if (e.type === "Character" && sprites[e.fields.sprite]) { const im = sprites[e.fields.sprite]; g.drawImage(im, Math.round(e.x - im.width / 2), Math.round(e.y - im.height)); }
  }
  return c;
}

// The ready-made stamps that ship with the tiles (tiles/stamps.json, from art/builtin_stamps.py).
export async function loadBuiltinStamps(base) {
  try {
    const json = await (await fetch(base + "stamps.json")).json();
    return json.stamps.map((s) => ({ name: s.name, builtin: true, clip: { ...s.clip, layers: Object.fromEntries(Object.entries(s.clip.layers).map(([k, v]) => [k, Uint8Array.from(v)])) } }));
  } catch { return []; }
}

export function loadStamps() {
  try {
    return (JSON.parse(localStorage.getItem(KEY)) || []).map((s) => ({
      name: s.name, clip: { ...s.clip, layers: Object.fromEntries(Object.entries(s.clip.layers).map(([k, v]) => [k, Uint8Array.from(v)])) },
    }));
  } catch { return []; }
}

export function saveStamps(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.filter((s) => !s.builtin).map((s) => ({
      name: s.name, clip: { ...s.clip, layers: Object.fromEntries(Object.entries(s.clip.layers).map(([k, v]) => [k, Array.from(v)])) },
    }))));
    return true;
  } catch { return false; }
}
