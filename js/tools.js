// Map edits that don't need the screen: painting cells, shaping height, resizing and growing, and undo history.

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

// Grow or shrink the map from its bottom-right corner. Objects keep their positions.
export function resize(m, cols, rows) {
  for (const k of Object.keys(m.layers)) {
    const old = m.layers[k], next = new Uint8Array(cols * rows);
    for (let r = 0; r < Math.min(rows, m.rows); r++) for (let c = 0; c < Math.min(cols, m.cols); c++) next[r * cols + c] = old[r * m.cols + c];
    m.layers[k] = next;
  }
  m.cols = cols; m.rows = rows;
}

// Move an object by whole cells, with everything it points at (its feet, path points, perch, where it flies to).
export function moveEntity(e, dc, dr) {
  e.x += dc * 16; e.y += dr * 16;
  for (const k of ["points", "path"]) if (Array.isArray(e.fields[k])) e.fields[k] = e.fields[k].map(([c, r]) => [c + dc, r + dr]);
  for (const k of ["perch", "flyTo"]) if (e.fields[k]) e.fields[k] = [e.fields[k][0] + dc, e.fields[k][1] + dr];
}

// Add empty cells on any side. Cells and objects keep their place in the world; `m.shift` counts the cells added on
// the left and top this session, so the editor can keep the screen still (it isn't saved).
export function grow(m, left, top, right, bottom) {
  const cols = m.cols + left + right, rows = m.rows + top + bottom;
  for (const k of Object.keys(m.layers)) {
    const old = m.layers[k], next = new Uint8Array(cols * rows);
    for (let r = 0; r < m.rows; r++) next.set(old.subarray(r * m.cols, (r + 1) * m.cols), (r + top) * cols + left);
    m.layers[k] = next;
  }
  m.cols = cols; m.rows = rows;
  if (left || top) for (const e of m.entities) moveEntity(e, left, top);
  m.shift = [(m.shift?.[0] || 0) + left, (m.shift?.[1] || 0) + top];
}

const snap = (m) => ({
  cols: m.cols, rows: m.rows, shift: [...(m.shift || [0, 0])],
  layers: Object.fromEntries(Object.entries(m.layers).map(([k, v]) => [k, v.slice()])),
  entities: structuredClone(m.entities),
});
const restore = (m, s) => {
  m.cols = s.cols; m.rows = s.rows; m.shift = [...s.shift];
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
