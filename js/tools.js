// Map edits that don't need the screen: painting cells, flood fill, resizing, and undo history.

export const at = (m, c, r) => r * m.cols + c;
export const inside = (m, c, r) => c >= 0 && r >= 0 && c < m.cols && r < m.rows;

// The cells under a square brush of `size` centred on (c, r).
export function brushCells(m, c, r, size) {
  const out = [], lo = -Math.floor((size - 1) / 2);
  for (let dr = lo; dr < lo + size; dr++) for (let dc = lo; dc < lo + size; dc++) if (inside(m, c + dc, r + dr)) out.push([c + dc, r + dr]);
  return out;
}

// The cells on a straight line between two cells (so a fast stroke leaves no gaps).
export function lineCells(c0, r0, c1, r1) {
  const out = [], n = Math.max(Math.abs(c1 - c0), Math.abs(r1 - r0));
  for (let i = 0; i <= n; i++) out.push([Math.round(c0 + (c1 - c0) * (n ? i / n : 0)), Math.round(r0 + (r1 - r0) * (n ? i / n : 0))]);
  return out;
}

export function rectCells(m, c0, r0, c1, r1) {
  const out = [];
  for (let r = Math.max(0, Math.min(r0, r1)); r <= Math.min(m.rows - 1, Math.max(r0, r1)); r++)
    for (let c = Math.max(0, Math.min(c0, c1)); c <= Math.min(m.cols - 1, Math.max(c0, c1)); c++) out.push([c, r]);
  return out;
}

// Every cell joined to (c, r) through edges that holds the same value on this layer.
export function floodCells(m, layer, c, r) {
  if (!inside(m, c, r)) return [];
  const L = m.layers[layer], want = L[at(m, c, r)], seen = new Uint8Array(m.cols * m.rows), out = [], stack = [[c, r]];
  while (stack.length) {
    const [x, y] = stack.pop();
    if (!inside(m, x, y) || seen[at(m, x, y)] || L[at(m, x, y)] !== want) continue;
    seen[at(m, x, y)] = 1;
    out.push([x, y]);
    stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
  }
  return out;
}

// Returns true if anything changed.
export function paint(m, layer, value, cells) {
  const L = m.layers[layer];
  let changed = false;
  for (const [c, r] of cells) if (L[at(m, c, r)] !== value) { L[at(m, c, r)] = value; changed = true; }
  return changed;
}

// Raise, lower or flatten cells (each cell once per stroke: `touched`), then keep every cell within one level of
// its four neighbours by nudging them along, spreading outwards (like OpenTTD's terraforming).
export function shapeHeight(m, cells, op, target, max, touched) {
  const H = m.layers.Height, queue = [];
  let changed = false;
  for (const [c, r] of cells) {
    const i = at(m, c, r);
    if (touched.has(i)) continue;
    touched.add(i);
    const next = op === "raise" ? Math.min(max, H[i] + 1) : op === "lower" ? Math.max(0, H[i] - 1) : target;
    if (next !== H[i]) { H[i] = next; changed = true; queue.push(i); }
  }
  while (queue.length) {
    const i = queue.shift(), c = i % m.cols, r = (i / m.cols) | 0;
    for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      if (!inside(m, c + dc, r + dr)) continue;
      const j = at(m, c + dc, r + dr);
      if (H[j] < H[i] - 1) { H[j] = H[i] - 1; queue.push(j); changed = true; }
      else if (H[j] > H[i] + 1) { H[j] = H[i] + 1; queue.push(j); changed = true; }
    }
  }
  return changed;
}

// A fenced plot: fence on the rectangle's edge, and a gate in the side that faces the nearest path
// (looking up to 8 cells straight out from each edge cell), or in the middle of the bottom side.
export function plotCells(m, c0, r0, c1, r1, pathValue) {
  [c0, c1] = [Math.max(0, Math.min(c0, c1)), Math.min(m.cols - 1, Math.max(c0, c1))];
  [r0, r1] = [Math.max(0, Math.min(r0, r1)), Math.min(m.rows - 1, Math.max(r0, r1))];
  const edge = [];
  for (let c = c0; c <= c1; c++) { edge.push([c, r0, 0, -1]); if (r1 !== r0) edge.push([c, r1, 0, 1]); }
  for (let r = r0 + 1; r < r1; r++) { edge.push([c0, r, -1, 0]); if (c1 !== c0) edge.push([c1, r, 1, 0]); }
  let gate = null, best = 99;
  const corner = (c, r) => (c === c0 || c === c1) && (r === r0 || r === r1);
  for (const [c, r, dc, dr] of edge) {
    if (corner(c, r)) continue;
    for (let k = 1; k <= 8; k++) {
      const x = c + dc * k, y = r + dr * k;
      if (!inside(m, x, y)) break;
      if (m.layers.Terrain[at(m, x, y)] === pathValue) { if (k < best) { best = k; gate = [c, r]; } break; }
    }
  }
  if (!gate && c1 - c0 >= 2) gate = [Math.round((c0 + c1) / 2), r1];
  return { fence: edge.map(([c, r]) => [c, r]).filter(([c, r]) => !gate || c !== gate[0] || r !== gate[1]), gate };
}

// Grow or shrink the map from its bottom-right corner. Objects keep their positions.
export function resize(m, cols, rows) {
  for (const k of Object.keys(m.layers)) {
    const old = m.layers[k], next = new Uint8Array(cols * rows);
    for (let r = 0; r < Math.min(rows, m.rows); r++) for (let c = 0; c < Math.min(cols, m.cols); c++) next[r * cols + c] = old[r * m.cols + c];
    m.layers[k] = next;
  }
  m.cols = cols; m.rows = rows;
}

const snap = (m) => ({
  cols: m.cols, rows: m.rows,
  layers: Object.fromEntries(Object.entries(m.layers).map(([k, v]) => [k, v.slice()])),
  entities: structuredClone(m.entities),
});
const restore = (m, s) => {
  m.cols = s.cols; m.rows = s.rows;
  m.layers = Object.fromEntries(Object.entries(s.layers).map(([k, v]) => [k, v.slice()]));
  m.entities = structuredClone(s.entities);
};

// Undo keeps whole copies of the map: a 40x50 town is a few kilobytes.
export class History {
  constructor(limit = 200) { this.limit = limit; this.past = []; this.future = []; }
  push(m) { this.past.push(snap(m)); if (this.past.length > this.limit) this.past.shift(); this.future = []; }
  drop() { this.past.pop(); }             // the last push turned out to change nothing
  undo(m) { if (!this.past.length) return false; this.future.push(snap(m)); restore(m, this.past.pop()); return true; }
  redo(m) { if (!this.future.length) return false; this.past.push(snap(m)); restore(m, this.future.pop()); return true; }
  clear() { this.past = []; this.future = []; }
}
