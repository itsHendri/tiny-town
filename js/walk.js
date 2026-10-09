// Walk mode: a character steps cell to cell (Pokemon style) so you can try the town you built.
// Water, cliff faces, fences and the bases of props block; stairs are the only way between levels.

import { value } from "./registry.js";

const T = 16;
const STEP_FRAMES = 8;              // frames per cell at 60 fps
const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };

// Cells that props stand on: the feet cell, the cells under a wide base, and the row behind a house.
function propCells(m, props) {
  const blocked = new Set();
  for (const e of m.entities) {
    if (e.type !== "Prop") continue;
    const p = props[e.fields.sprite];
    if (!p || e.fields.sprite.startsWith("bush") || e.fields.sprite.startsWith("rock")) continue;
    const r = Math.floor((e.y - 1) / T);
    if (p.foot) {                                            // a building: its whole footprint, ending at its front cell
      const c = Math.floor(e.x / T);
      for (let rr = r - p.foot[1] + 1; rr <= r; rr++) for (let cc = c - p.foot[0] + 1; cc <= c; cc++) blocked.add(rr * m.cols + cc);
      continue;
    }
    const half = Math.max(0, p.w / 2 - 6);
    const c0 = Math.floor((e.x - half) / T), c1 = Math.floor((e.x + half) / T);
    const rows = e.fields.sprite.startsWith("house") ? 2 : 1;
    for (let rr = r - rows + 1; rr <= r; rr++) for (let c = c0; c <= c1; c++) blocked.add(rr * m.cols + c);
  }
  return blocked;
}

export class Walker {
  constructor(m, props, start) {
    this.m = m;
    this.blocked = propCells(m, props);
    this.c = start[0]; this.r = start[1];
    this.from = null; this.t = 0; this.facing = "down"; this.held = [];
    if (!this.free(this.c, this.r)) this.findFree();
  }

  findFree() {
    for (let d = 1; d < 30; d++) for (let dr = -d; dr <= d; dr++) for (let dc = -d; dc <= d; dc++) {
      if (this.free(this.c + dc, this.r + dr)) { this.c += dc; this.r += dr; return; }
    }
  }

  free(c, r) {
    const m = this.m;
    if (c < 0 || r < 0 || c >= m.cols || r >= m.rows) return false;
    const i = r * m.cols + c, H = m.layers.Height;
    const ter = m.layers.Terrain[i], deco = m.layers.Deco[i];
    if (ter === value("Terrain", "water")) return false;
    if (deco === value("Deco", "fence")) return false;
    if (this.blocked.has(i)) return false;
    const face = r > 0 && H[i - m.cols] > H[i];
    if (face && m.layers.Features[i] !== value("Features", "stairs")) return false;
    return true;
  }

  // Same level, or through stairs (a stairs cell joins the level above it to its own).
  canStep(c0, r0, c1, r1) {
    if (!this.free(c1, r1)) return false;
    const m = this.m, H = m.layers.Height, a = r0 * m.cols + c0, b = r1 * m.cols + c1;
    if (H[a] === H[b]) return true;
    const stairs = value("Features", "stairs");
    if (m.layers.Features[b] === stairs && r1 === r0 + 1 && H[a] === H[b] + 1) return true;   // onto stairs from above
    if (m.layers.Features[a] === stairs && r1 === r0 - 1 && H[b] === H[a] + 1) return true;   // up off the stairs
    if (r1 === r0 && Math.abs(H[a] - H[b]) === 1) {                                           // side stairs, east or west
      const low = H[a] < H[b] ? a : b;
      if (m.layers.Features[low] === stairs) return true;
    }
    return false;
  }

  press(dir) { if (!this.held.includes(dir)) this.held.push(dir); this.queued = dir; }   // a quick tap still takes one step
  release(dir) { this.held = this.held.filter((d) => d !== dir); }

  update() {
    if (this.from) {
      if (++this.t >= STEP_FRAMES) { this.from = null; this.t = 0; } else return;
    }
    const dir = this.held[this.held.length - 1] || this.queued;
    this.queued = null;
    if (!dir) return;
    this.facing = dir;
    const [dc, dr] = DIRS[dir];
    if (this.canStep(this.c, this.r, this.c + dc, this.r + dr)) {
      this.from = [this.c, this.r]; this.c += dc; this.r += dr; this.t = 0;
    }
  }

  // Feet position in map pixels, with a little hop while stepping.
  feet() {
    const k = this.from ? this.t / STEP_FRAMES : 1;
    const fc = this.from ? this.from[0] : this.c, fr = this.from ? this.from[1] : this.r;
    const x = (fc + (this.c - fc) * k) * T + T / 2, y = (fr + (this.r - fr) * k) * T + T;
    return [x, y - (this.from ? Math.round(Math.sin(k * Math.PI) * 2) : 0)];
  }
}
