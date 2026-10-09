// The map builder: paint cells, place objects, undo, save. Plain ES module, no build step.

import { newMap, parseMap, stringifyMap } from "./format.js";
import { drawProp, drawTerrain, loadTileset } from "./render.js";
import { bakeIso, isoView, loadIsoTileset } from "./iso.js";
import { ENTITIES, LAYERS, MAX_LEVEL, value } from "./registry.js";
import { History, brushCells, floodCells, inside, lineCells, paint, plotCells, rectCells, resize, shapeHeight } from "./tools.js";
import { loadAutosave, openFile, saveFile, writeAutosave } from "./files.js";
import { area, clearArea, copyArea, drawClip, loadBuiltinStamps, loadStamps, pasteArea, saveStamps } from "./stamps.js";
import { codeToMap, mapToCode } from "./share.js";
import { Walker } from "./walk.js";

const T = 16;
const EXAMPLE = "maps/town-v5.ldtk";
const ZOOMS = [0.5, 1, 2, 3, 4, 5, 6, 8];
const $ = (id) => document.getElementById(id);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  e.append(...kids);
  return e;
}

// ---------- state ----------

const S = {
  map: null, ts: null, sprites: {}, spriteNames: [], fileName: "town.ldtk",
  mode: "paint", tool: "brush", size: 1, brush: { layer: "Terrain", v: 1 },
  place: null, selected: null, scatter: { on: false, density: 0.35 }, scatterStroke: null,
  sel: null, selFrom: null, clip: null, pasting: null, stamps: [], walk: null, walkView: null, eraseMode: false, longPress: null,
  fx: [], squash: new Map(), isoTs: null, projection: "iso", V: null,
  zoom: 2, ox: 0, oy: 0,
  show: { terrain: true, props: true, characters: true, data: true, raw: false, grid: false },
  frames: [], frame: 0, terrainDirty: true, needsDraw: true,
  hover: null, stroke: null, drag: null, pointers: new Map(), pinch: null, spaceDown: false, panning: null,
};
const history = new History();
window.tinyTown = { state: S, history };          // for poking around in the browser console

// ---------- the paint palette ----------

const PALETTE = [
  { group: "Ground", layer: "Terrain", items: [{ v: 0, label: "Grass", key: "grass" }, ...LAYERS.Terrain.values.map((x) => ({ v: x.v, label: x.label, key: x.id }))] },
  { group: "Height", layer: "Height", items: [{ op: "raise", label: "Raise", key: "raised", mark: "▲" }, { op: "lower", label: "Lower", key: "grass", mark: "▼" }, { op: "flat", label: "Flatten", key: "grass", mark: "=" }] },
  { group: "Features", layer: "Features", items: LAYERS.Features.values.map((x) => ({ v: x.v, label: x.label, key: x.id })) },
  { group: "Decoration", layer: "Deco", items: LAYERS.Deco.values.map((x) => ({ v: x.v, label: x.label, key: x.id })) },
];
const TOOLS = [["brush", "Brush", "B"], ["rect", "Box", "R"], ["fill", "Fill", "F"], ["plot", "Plot", "T"], ["pick", "Pick", "I"], ["select", "Select", "S"]];

// A 2x2-cell scene that shows what a palette item paints.
function swatch(key, color, mark) {
  const c = el("canvas", { width: 32, height: 32, "aria-hidden": "true" });
  const m = newMap(2, 2);
  const tv = LAYERS.Terrain.values.find((x) => x.id === key);
  if (tv) m.layers.Terrain.fill(tv.v);
  else if (key === "raised") { m.layers.Height[0] = m.layers.Height[1] = 1; }
  else if (key === "stairs") { m.layers.Height[0] = m.layers.Height[1] = 1; m.layers.Features[2] = m.layers.Features[3] = 1; m.layers.Terrain[0] = m.layers.Terrain[2] = 1; }
  else if (key === "fence") { m.layers.Deco[2] = m.layers.Deco[3] = 1; }
  else if (key === "gate") { m.layers.Deco[2] = 4; m.layers.Deco[3] = 1; }
  else if (key === "flowers") { m.layers.Deco.fill(2); }
  else if (key === "tallgrass") { m.layers.Deco.fill(3); }
  const g = c.getContext("2d");
  drawTerrain(g, m, S.ts, 0);
  if (!["grass", "raised", "stairs", "fence", "gate", "flowers", "tallgrass"].includes(key) && !tv && color) { g.fillStyle = color; g.fillRect(4, 4, 24, 24); }
  if (mark) {
    g.font = "bold 13px ui-monospace, monospace"; g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 3; g.strokeStyle = "#26303f"; g.strokeText(mark, 24, 9); g.fillStyle = "#fff"; g.fillText(mark, 24, 9);
  }
  return c;
}

function buildPaintPanel() {
  const row = $("toolrow");
  row.replaceChildren(...TOOLS.map(([id, label, key]) => el("button", {
    class: "tool", type: "button", id: `tool-${id}`, "aria-pressed": String(S.tool === id), title: `${label} (${key})`, onclick: () => setTool(id),
  }, el("span", { text: label }), el("kbd", { text: key }))));
  const pal = $("palette");
  pal.replaceChildren(...PALETTE.filter((g) => g.items.length).map((g) => el("div", {},
    el("h3", { text: g.group }),
    el("div", { class: "swatches" }, ...g.items.map((it) => {
      const on = S.brush.layer === g.layer && (it.op ? S.brush.op === it.op : S.brush.v === it.v && !S.brush.op);
      const color = LAYERS[g.layer].values.find((x) => x.v === it.v)?.color;
      return el("button", { class: "swatch", type: "button", "aria-pressed": String(on), title: `${g.group}: ${it.label}`,
        onclick: () => { S.brush = it.op ? { layer: g.layer, op: it.op } : { layer: g.layer, v: it.v }; if (S.tool === "pick") S.tool = "brush"; buildPaintPanel(); } },
      swatch(it.key, color, it.mark), el("span", { text: it.label }));
    })))));
  if (S.ts) queueMicrotask(syncBar);
  $("sizes").replaceChildren("Brush", ...[1, 2, 3].map((n) => el("button", { type: "button", "aria-pressed": String(S.size === n),
    title: `Brush ${n}×${n} cells`, onclick: () => { S.size = n; buildPaintPanel(); } }, sizeIcon(n), el("span", { text: `${n}×${n}` }))));
}

// A 3x3 grid of cells with the brush's footprint filled in.
function sizeIcon(n) {
  const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24"); svg.setAttribute("aria-hidden", "true");
  const lo = 1 - Math.floor((n - 1) / 2);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const q = document.createElementNS(NS, "rect");
    q.setAttribute("x", c * 8 + 0.5); q.setAttribute("y", r * 8 + 0.5); q.setAttribute("width", 7); q.setAttribute("height", 7); q.setAttribute("rx", 1.5);
    if (c >= lo && c < lo + n && r >= lo && r < lo + n) q.setAttribute("class", "on");
    svg.append(q);
  }
  return svg;
}

function buildStamps() {
  const box = $("stamps");
  if (!S.stamps.length) { box.replaceChildren(el("p", { class: "hint", text: "None yet. Select an area (S), then Save as stamp. Your stamps are kept in this browser." })); return; }
  box.replaceChildren(el("div", { class: "swatches" }, ...S.stamps.map((st, i) => {
    const c = drawClip(st.clip, S.ts, S.sprites);
    const t = thumb((g, x, y, w, h) => g.drawImage(c, x, y, w, h), c.width, c.height, 40);
    return el("div", { class: "stamp" },
      el("button", { class: "swatch", type: "button", title: `Place ${st.name}`, "aria-pressed": String(S.pasting?.name === st.name), onclick: () => startPaste(st.clip, st.name) }, t, el("span", { text: st.name })),
      st.builtin ? "" : el("button", { class: "remove", type: "button", title: `Remove ${st.name}`, "aria-label": `Remove ${st.name}`, onclick: () => { S.stamps.splice(i, 1); saveStamps(S.stamps); buildStamps(); } }, "×"));
  })));
}

function startPaste(clip, name = null) {
  S.pasting = { clip, name, canvas: drawClip(clip, S.ts, S.sprites) };
  S.sel = null; buildInspector(); buildStamps();
  toast("Click to place. Esc to stop.");
  S.needsDraw = true;
}

function stopPaste() { if (S.pasting) { S.pasting = null; buildStamps(); S.needsDraw = true; } }

const pasteAt = (hv) => [hv.c - Math.floor(S.pasting.clip.cols / 2), hv.r - Math.floor(S.pasting.clip.rows / 2)];

function copySel(cut) {
  if (!S.sel) return;
  S.clip = copyArea(S.map, S.sel);
  if (cut) { history.push(S.map); clearArea(S.map, S.sel); changed(true); }
  toast(`${cut ? "Cut" : "Copied"} ${S.clip.cols} × ${S.clip.rows} cells. Ctrl+V to paste.`);
}

function deleteSel() {
  if (!S.sel) return;
  history.push(S.map); clearArea(S.map, S.sel); changed(true);
}

function syncBar() {
  for (const b of $("mbar").querySelectorAll("[data-tool]")) b.setAttribute("aria-pressed", String(S.mode === "paint" && S.tool === b.dataset.tool));
  $("m-erase").setAttribute("aria-pressed", String(S.eraseMode));
  $("m-mode").textContent = S.mode === "paint" ? "Objects" : "Paint";
  const it = PALETTE.find((g) => g.layer === S.brush.layer)?.items.find((x) => (S.brush.op ? x.op === S.brush.op : x.v === S.brush.v));
  $("m-brush").replaceChildren(it ? swatch(it.key, null, it.mark) : "");
  $("m-brush").title = it ? `Painting: ${it.label}` : "Choose what to paint";
  for (const b of $("mbar").querySelectorAll("[data-tool], #m-erase, #m-brush")) b.hidden = S.mode !== "paint";
}

function setTool(id) { S.tool = id; buildPaintPanel(); S.needsDraw = true; }

// ---------- the object catalog ----------

function thumb(draw, w, h, box = 40) {
  const c = el("canvas", { width: box, height: box, "aria-hidden": "true" });
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  const k = Math.min(box / w, box / h, 2);
  const s = k >= 1 ? Math.floor(k) : k;
  draw(g, (box - w * s) / 2, (box - h * s) / 2, w * s, h * s);
  return c;
}
const propThumb = (name, box) => {
  const p = S.ts.props[name];
  return p ? thumb((g, x, y, w, h) => g.drawImage(S.ts.propsImg, p.x, p.y, p.w, p.h, x, y, w, h), p.w, p.h, box) : el("canvas", { width: box, height: box });
};
const charThumb = (name, box) => {
  const im = S.sprites[name];
  return im ? thumb((g, x, y, w, h) => g.drawImage(im, x, y, w, h), im.width, im.height, box) : el("canvas", { width: box, height: box });
};

function propGroups() {
  const groups = { Trees: [], Pines: [], Bushes: [], Rocks: [], Houses: [], Things: [] };
  for (const name of Object.keys(S.ts.props)) {
    const g = name.startsWith("tree") ? "Trees" : name.startsWith("pine") ? "Pines" : name.startsWith("bush") ? "Bushes"
      : name.startsWith("rock") ? "Rocks" : name.startsWith("house") ? "Houses" : "Things";
    groups[g].push(name);
  }
  return groups;
}

function buildCatalog() {
  const same = (p) => S.place && S.place.type === p.type && S.place.sprite === p.sprite;
  const item = (p, label, canvas) => el("button", { class: "swatch", type: "button", "aria-pressed": String(same(p)), title: p.sprite || label,
    onclick: () => { S.place = same(p) ? null : p; buildCatalog(); S.needsDraw = true; } }, canvas, el("span", { text: label }));
  const sections = [el("div", { class: "swatches" }, el("button", { class: "swatch", type: "button", "aria-pressed": String(!S.place), title: "Select and move (V)",
    onclick: () => { S.place = null; buildCatalog(); } }, el("span", { text: "↖", style: "font-size:22px;line-height:32px" }), el("span", { text: "Select" }))),
  el("div", { class: "scatter" },
    el("label", { for: "scatter-on" }, el("input", { type: "checkbox", id: "scatter-on", checked: S.scatter.on,
      onchange: (ev) => { S.scatter.on = ev.target.checked; S.needsDraw = true; } }), "Scatter (drag to sprinkle props like the one picked)"),
    el("div", { class: "density", role: "group", "aria-label": "Scatter density" }, ...[["Few", 0.15], ["Some", 0.35], ["Lots", 0.7]].map(([label, d]) =>
      el("button", { type: "button", "aria-pressed": String(S.scatter.density === d), onclick: () => { S.scatter.density = d; S.scatter.on = true; buildCatalog(); } }, label))))];
  if (S.spriteNames.length) {
    sections.push(el("h3", { text: "Characters" }), el("div", { class: "swatches" },
      ...S.spriteNames.map((n) => item({ type: "Character", sprite: n }, n, charThumb(n, 40)))));
  }
  for (const [g, names] of Object.entries(propGroups())) {
    if (!names.length) continue;
    sections.push(el("h3", { text: g }), el("div", { class: "swatches" }, ...names.map((n) => item({ type: "Prop", sprite: n }, n.replace(/^(tree|pine|bush|rock|house)-/, ""), propThumb(n, 40)))));
  }
  sections.push(el("h3", { text: "Data" }), el("div", { class: "swatches" },
    item({ type: "Path" }, "Path", dataIcon("path")), item({ type: "Region" }, "Region", dataIcon("region"))));
  $("catalog").replaceChildren(...sections);
}

function dataIcon(kind) {
  const c = el("canvas", { width: 40, height: 40, "aria-hidden": "true" });
  const g = c.getContext("2d");
  g.strokeStyle = kind === "path" ? ENTITIES.Path.color : ENTITIES.Region.color;
  g.lineWidth = 2;
  if (kind === "path") { g.beginPath(); g.moveTo(6, 32); g.lineTo(18, 14); g.lineTo(34, 22); g.stroke(); for (const [x, y] of [[6, 32], [18, 14], [34, 22]]) g.strokeRect(x - 2, y - 2, 4, 4); }
  else { g.setLineDash([4, 3]); g.strokeRect(6, 8, 28, 24); }
  return c;
}

// ---------- entities ----------

const cellCentre = ([c, r]) => [c * T + T / 2, r * T + T / 2];

// The view: how map pixels (u, v), cells and objects land on the screen. Top-down is the identity; isometric is
// js/iso.js. Everything that draws or picks goes through S.V.
function orthoView(m) {
  return {
    iso: false, W: m.cols * T, H: m.rows * T,
    pt: (u, v) => [u, v],
    feet: (e) => [e.x, e.y],
    cellPoly: (c, r) => [[c * T, r * T], [(c + 1) * T, r * T], [(c + 1) * T, (r + 1) * T], [c * T, (r + 1) * T]],
    pick: (x, y) => ({ c: Math.floor(x / T), r: Math.floor(y / T), u: x, v: y }),
    border: () => [[0, 0], [m.cols * T, 0], [m.cols * T, m.rows * T], [0, m.rows * T]],
  };
}

function makeView() {
  const m = S.map;
  if (S.projection !== "iso" || !S.isoTs) return orthoView(m);
  const v = isoView(m);
  const lvl = (u, vv) => m.layers.Height[Math.min(m.rows - 1, Math.max(0, Math.floor(vv / T))) * m.cols + Math.min(m.cols - 1, Math.max(0, Math.floor(u / T)))];
  return {
    ...v,
    pt: (u, vv) => v.toScreen(u, vv, lvl(u, vv)),
    feet: (e) => v.feet(e, lvl(e.x, e.y - 1)),
    cellPoly: (c, r) => v.cellPoly(c, r, m.layers.Height[r * m.cols + c] || 0),
    pick: (x, y) => v.pick(x, y, m),
    border: () => [v.cellTop(0, 0), v.cellTop(m.cols, 0), v.cellTop(m.cols, m.rows), v.cellTop(0, m.rows)],
  };
}

function poly(g, pts) { g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); }

function bounds(e) {
  if (e.type === "Prop") { const p = S.ts.props[e.fields.sprite] || { w: T, h: T }; const [x, y] = S.V.feet(e); return [x - p.w / 2, y - p.h, p.w, p.h]; }
  if (e.type === "Character") { const im = S.sprites[e.fields.sprite]; const w = im?.width || T, h = im?.height || T; const [x, y] = S.V.feet(e); return [x - w / 2, y - h, w, h]; }
  if (e.type === "Region") return [e.x, e.y, e.w || T, e.h || T];
  const pts = (e.fields.points || []).map(cellCentre);
  if (!pts.length) return [e.x, e.y, T, T];
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs) - 4, Math.min(...ys) - 4, Math.max(...xs) - Math.min(...xs) + 8, Math.max(...ys) - Math.min(...ys) + 8];
}

// What's under the pointer: sprites by their picture on screen (wx, wy), paths and regions by map pixels (mx, my).
function hit(p) {
  const { mx, my, wx, wy } = p;
  const sprites = S.map.entities.filter((e) => (e.type === "Prop" && S.show.props) || (e.type === "Character" && S.show.characters))
    .sort((a, b) => (S.V.iso ? (b.x + b.y) - (a.x + a.y) : b.y - a.y));
  for (const e of sprites) {
    const [x, y, w, h] = bounds(e);
    if (wx >= x && wx < x + w && wy >= y && wy < y + h) return e;
  }
  if (!S.show.data) return null;
  const near = 6 / Math.max(1, S.zoom) + 3;
  for (const e of S.map.entities.filter((e) => e.type === "Path")) {
    if ((e.fields.points || []).map(cellCentre).some(([x, y]) => Math.abs(x - mx) <= near && Math.abs(y - my) <= near)) return e;
  }
  for (const e of S.map.entities.filter((e) => e.type === "Region")) {
    const [x, y, w, h] = [e.x, e.y, e.w || T, e.h || T];
    const inBox = mx >= x - near && mx <= x + w + near && my >= y - near && my <= y + h + near;
    const onEdge = mx <= x + near || mx >= x + w - near || my <= y + near || my >= y + h - near;
    if (inBox && onEdge) return e;
  }
  return null;
}

function snapFeet(mx, my, free) {
  if (free) return [Math.round(mx), Math.round(my)];
  const c = Math.floor(mx / T), r = Math.floor(my / T);
  return [c * T + T / 2, (r + 1) * T];
}

function placeAt(mx, my, free) {
  const p = S.place, c = Math.floor(mx / T), r = Math.floor(my / T);
  let e;
  if (p.type === "Prop") { const [x, y] = snapFeet(mx, my, free); e = { type: "Prop", x, y, w: T, h: T, fields: { sprite: p.sprite } }; }
  else if (p.type === "Character") {
    const [x, y] = snapFeet(mx, my, free);
    e = { type: "Character", x, y, w: T, h: T, fields: { id: p.sprite.split("-")[0], sprite: p.sprite, perch: null, flyTo: null, path: [] } };
  } else if (p.type === "Region") e = { type: "Region", x: c * T, y: r * T, w: 2 * T, h: 2 * T, fields: { name: "region" } };
  else e = { type: "Path", x: c * T, y: r * T, w: T, h: T, fields: { name: "path", points: [[c, r], [Math.min(S.map.cols - 1, c + 3), r]] } };
  history.push(S.map);
  S.map.entities.push(e);
  land(e);
  select(e);
  changed(false);
}

// ---------- scatter ----------

// Props in the same family as `name` (tree-3-d1 -> every tree-N-d1), to vary what gets scattered.
function family(name) {
  const m = name.match(/^(.*?)-\d+(-d\d)?$/);
  if (!m) return [name];
  const re = new RegExp(`^${m[1]}-\\d+${m[2] || ""}$`);
  return Object.keys(S.ts.props).filter((n) => re.test(n));
}

function freeCell(c, r) {
  const m = S.map, i = r * m.cols + c;
  if (m.layers.Terrain[i] || m.layers.Deco[i] || (r > 0 && m.layers.Height[i - m.cols] > m.layers.Height[i])) return false;
  return !m.entities.some((e) => (e.type === "Prop" || e.type === "Character") && Math.floor(e.x / T) === c && Math.floor((e.y - 1) / T) === r);
}

function scatterAt(p, erase) {
  const st = S.scatterStroke, names = family(S.place.sprite);
  for (const [c, r] of brushCells(S.map, p.c, p.r, 3)) {
    const key = r * S.map.cols + c;
    if (st.done.has(key)) continue;
    st.done.add(key);
    if (erase) {
      const before = S.map.entities.length;
      S.map.entities = S.map.entities.filter((e) => {
        const gone = e.type === "Prop" && names.includes(e.fields.sprite) && Math.floor(e.x / T) === c && Math.floor((e.y - 1) / T) === r;
        if (gone) puff(e.x, e.y);
        return !gone;
      });
      if (S.map.entities.length !== before) st.changed = true;
    } else if (Math.random() < S.scatter.density && freeCell(c, r)) {
      const sprite = names[Math.floor(Math.random() * names.length)];
      const e = { type: "Prop", x: c * T + 4 + Math.floor(Math.random() * 9), y: (r + 1) * T - Math.floor(Math.random() * 5), w: T, h: T, fields: { sprite } };
      S.map.entities.push(e);
      land(e);
      st.changed = true;
    }
  }
  S.needsDraw = true;
}

// ---------- a little feedback: things land with a squash, removed things leave a puff ----------

function land(e) { if (!reduceMotion) S.squash.set(e, performance.now()); }
function puff(x, y) {
  if (reduceMotion) return;
  const t = performance.now();
  for (let k = 0; k < 6; k++) S.fx.push({ x, y: y - 4, a: (k / 6) * Math.PI * 2 + Math.random() * 0.5, t });
}

function drawFx(g, now) {
  S.fx = S.fx.filter((p) => now - p.t < 380);
  for (const p of S.fx) {
    const k = (now - p.t) / 380, d = 3 + k * 9;
    g.globalAlpha = 0.75 * (1 - k);
    g.fillStyle = "#f6ecd2";
    g.beginPath(); g.arc(p.x + Math.cos(p.a) * d, p.y + Math.sin(p.a) * d * 0.6, 2.2 * (1 - k * 0.5), 0, Math.PI * 2); g.fill();
  }
  g.globalAlpha = 1;
}

// ---------- inspector ----------

const fmtPoint = (p) => (p ? `${p[0]},${p[1]}` : "");
const parsePoint = (s) => { const m = String(s).trim().match(/^(-?\d+)\s*[, ]\s*(-?\d+)$/); return m ? [+m[1], +m[2]] : null; };
const parsePoints = (s) => String(s).split(/[;\n]+|\s{2,}|\)\s*\(|\s(?=-?\d+\s*,)/).map(parsePoint).filter(Boolean);

function select(e) { S.selected = e; buildInspector(); S.needsDraw = true; }

function edit(fn) {
  return (ev) => { history.push(S.map); fn(ev.target.value, ev.target); changed(S.selected?.type === "Region"); buildInspector(); };
}

function buildInspector() {
  const box = $("inspector"), e = S.selected;
  if (!e || !S.map.entities.includes(e)) {
    S.selected = null;
    if (S.sel) {
      const w = S.sel.c1 - S.sel.c0 + 1, h = S.sel.r1 - S.sel.r0 + 1;
      const name = el("input", { id: "stamp-name", placeholder: "e.g. house with yard", value: "" });
      box.replaceChildren(
        el("div", { class: "inspect-head" }, el("div", {}, el("b", { text: "Area" }), el("small", { text: `${w} × ${h} cells from col ${S.sel.c0}, row ${S.sel.r0}` }))),
        el("div", { class: "actions" },
          el("button", { class: "btn quiet", type: "button", text: "Copy", onclick: () => copySel(false) }),
          el("button", { class: "btn quiet", type: "button", text: "Cut", onclick: () => copySel(true) }),
          el("button", { class: "btn danger", type: "button", text: "Clear", onclick: deleteSel })),
        el("div", { class: "field", style: "margin-top:12px" }, el("label", { for: "stamp-name", text: "Save as a stamp" }), name),
        el("button", { class: "btn", type: "button", text: "Save as stamp", onclick: () => {
          const n = name.value.trim() || `stamp ${S.stamps.length + 1}`;
          S.stamps.push({ name: n, clip: copyArea(S.map, S.sel) });
          toast(saveStamps(S.stamps) ? `Saved the stamp "${n}"` : "This browser can't keep stamps; it will be gone after a reload");
          buildStamps();
        } }));
      return;
    }
    box.replaceChildren(el("p", { class: "empty", text: "Nothing selected. In Objects mode, click a tree, a house or a character. In Paint mode, the Select tool (S) picks an area to copy or save as a stamp." }));
    return;
  }
  const head = el("div", { class: "inspect-head" },
    e.type === "Prop" ? propThumb(e.fields.sprite, 40) : e.type === "Character" ? charThumb(e.fields.sprite, 40) : dataIcon(e.type === "Path" ? "path" : "region"),
    el("div", {}, el("b", { text: ENTITIES[e.type].label }), el("small", { text: e.fields.sprite || e.fields.name || "" })));
  const field = (id, label, input) => el("div", { class: "field" }, el("label", { for: id, text: label }), input);
  const rows = [head];
  const xy = el("div", { class: "pair" },
    field("f-x", "x (px)", el("input", { id: "f-x", type: "number", value: e.x, onchange: edit((v) => { e.x = Math.round(+v); }) })),
    field("f-y", "y (px)", el("input", { id: "f-y", type: "number", value: e.y, onchange: edit((v) => { e.y = Math.round(+v); }) })));
  if (e.type === "Prop") {
    const sel = el("select", { id: "f-sprite", onchange: edit((v) => { e.fields.sprite = v; }) }, ...Object.keys(S.ts.props).map((n) => el("option", { value: n, text: n, selected: n === e.fields.sprite })));
    rows.push(field("f-sprite", "sprite", sel), xy);
  } else if (e.type === "Character") {
    const sel = el("select", { id: "f-sprite", onchange: edit((v) => { e.fields.sprite = v; }) }, ...S.spriteNames.map((n) => el("option", { value: n, text: n, selected: n === e.fields.sprite })));
    rows.push(
      field("f-id", "id (what it stands for)", el("input", { id: "f-id", value: e.fields.id || "", onchange: edit((v) => { e.fields.id = v.trim(); }) })),
      field("f-sprite", "sprite", sel), xy,
      field("f-perch", "perch (cell: col,row)", el("input", { id: "f-perch", value: fmtPoint(e.fields.perch), placeholder: "e.g. 3,7", onchange: edit((v) => { e.fields.perch = parsePoint(v); }) })),
      field("f-flyTo", "fly to (cell)", el("input", { id: "f-flyTo", value: fmtPoint(e.fields.flyTo), placeholder: "e.g. 15,12", onchange: edit((v) => { e.fields.flyTo = parsePoint(v); }) })),
      field("f-path", "walks along (cells, one per line)", el("textarea", { id: "f-path", rows: "3", onchange: edit((v) => { e.fields.path = parsePoints(v); }) }, (e.fields.path || []).map(fmtPoint).join("\n"))));
  } else if (e.type === "Path") {
    rows.push(
      field("f-name", "name", el("input", { id: "f-name", value: e.fields.name || "", onchange: edit((v) => { e.fields.name = v.trim(); }) })),
      field("f-points", "points (cells, one per line)", el("textarea", { id: "f-points", rows: "6", onchange: edit((v) => { e.fields.points = parsePoints(v); }) }, (e.fields.points || []).map(fmtPoint).join("\n"))));
  } else {
    rows.push(
      field("f-name", "name", el("input", { id: "f-name", value: e.fields.name || "", onchange: edit((v) => { e.fields.name = v.trim(); }) })), xy,
      el("div", { class: "pair" },
        field("f-w", "width (px)", el("input", { id: "f-w", type: "number", min: "1", value: e.w, onchange: edit((v) => { e.w = Math.max(1, Math.round(+v)); }) })),
        field("f-h", "height (px)", el("input", { id: "f-h", type: "number", min: "1", value: e.h, onchange: edit((v) => { e.h = Math.max(1, Math.round(+v)); }) }))));
  }
  rows.push(el("div", { class: "actions" },
    el("button", { class: "btn quiet", type: "button", text: "Duplicate", onclick: duplicate }),
    el("button", { class: "btn danger", type: "button", text: "Delete", onclick: removeSelected })));
  box.replaceChildren(...rows);
}

function duplicate() {
  const e = S.selected; if (!e) return;
  history.push(S.map);
  const copy = structuredClone(e); delete copy.iid;
  copy.x += T;
  if (copy.fields.points) copy.fields.points = copy.fields.points.map(([c, r]) => [c + 1, r]);
  S.map.entities.push(copy);
  select(copy); changed(false);
}

function removeSelected() {
  const e = S.selected; if (!e) return;
  puff(e.x, e.y);
  history.push(S.map);
  S.map.entities = S.map.entities.filter((x) => x !== e);
  select(null); changed(false);
}

// ---------- drawing ----------

const canvas = $("view"), ctx = canvas.getContext("2d");

function bake() {
  S.V = makeView();
  if (S.V.iso) {
    // while painting, only the first frame; the other two follow once things are quiet
    const quick = S.stroke || S.drag || S.scatterStroke;
    if (quick) {
      S.frames = bakeIso(S.map, S.isoTs, S.V, { objects: S.show.props, frames: [0] }).slice(0, 1);
      S.restDirty = true;
    } else S.frames = bakeIso(S.map, S.isoTs, S.V, { objects: S.show.props });
    S.terrainDirty = false;
    return;
  }
  S.frames = Array.from({ length: S.ts.frames }, (_, f) => {
    const c = S.frames[f] && S.frames[f].width === S.map.cols * T && S.frames[f].height === S.map.rows * T ? S.frames[f] : document.createElement("canvas");
    c.width = S.map.cols * T; c.height = S.map.rows * T;
    drawTerrain(c.getContext("2d"), S.map, S.ts, f);
    return c;
  });
  S.terrainDirty = false;
}

function drawSprites(g, list) {
  const now = performance.now();
  for (const e of list) {
    const t0 = S.squash.get(e);
    if (t0 !== undefined) {
      const k = (now - t0) / 220;
      if (k >= 1) S.squash.delete(e);
      else {                                                   // squash on landing, stretch back, settle
        const sy = 1 - 0.22 * Math.cos(k * Math.PI * 1.5) * (1 - k), sx = 2 - sy;
        const [fx, fy] = S.V.feet(e);
        g.save(); g.translate(fx, fy); g.scale(sx, sy); g.translate(-fx, -fy);
        drawSprites(g, [{ ...e }]);              // a copy, so it draws plainly
        g.restore();
        continue;
      }
    }
    const [fx, fy] = S.V.feet(e);
    if (e.type === "Prop") drawProp(g, S.V.iso ? S.isoTs : S.ts, e.fields.sprite, fx, fy);
    else {
      const im = S.sprites[e.fields.sprite];
      if (im) g.drawImage(im, Math.round(fx - im.width / 2), Math.round(fy - im.height));
      else { g.fillStyle = ENTITIES.Character.color; g.fillRect(fx - 6, fy - 12, 12, 12); }
    }
  }
}

function draw() {
  S.needsDraw = false;
  const dpr = window.devicePixelRatio || 1, W = canvas.clientWidth, H = canvas.clientHeight;
  if (canvas.width !== Math.round(W * dpr) || canvas.height !== Math.round(H * dpr)) { canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr); }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!S.map) return;
  if (!S.V) S.V = makeView();
  const V = S.V, k = S.zoom * dpr;
  ctx.setTransform(k, 0, 0, k, Math.round(S.ox * dpr), Math.round(S.oy * dpr));
  ctx.imageSmoothingEnabled = false;
  if (S.show.terrain && S.frames.length) ctx.drawImage(S.frames[S.frame % S.frames.length], 0, 0);
  else { ctx.fillStyle = "#b4d566"; poly(ctx, V.border()); ctx.fill(); }

  if (S.show.raw) {
    ctx.globalAlpha = 0.62;
    for (const name of ["Height", "Terrain", "Features", "Deco"]) {
      const L = S.map.layers[name];
      for (let i = 0; i < L.length; i++) {
        if (!L[i]) continue;
        const v = LAYERS[name].values.find((x) => x.v === L[i]);
        ctx.fillStyle = v?.color || "#f0f";
        const c = i % S.map.cols, r = (i / S.map.cols) | 0;
        const pts = V.cellPoly(c, r), cx = pts.reduce((a, q) => a + q[0], 0) / 4, cy = pts.reduce((a, q) => a + q[1], 0) / 4;
        const shrink = name === "Height" ? 1 : name === "Terrain" ? 0.75 : 0.4;
        poly(ctx, pts.map(([x, y]) => [cx + (x - cx) * shrink, cy + (y - cy) * shrink])); ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }
  if (S.show.grid || S.show.raw) {
    ctx.strokeStyle = "rgba(38,48,63,0.18)"; ctx.lineWidth = 1 / S.zoom;
    for (let r = 0; r < S.map.rows; r++) for (let c = 0; c < S.map.cols; c++) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
  }

  const sprites = S.map.entities.filter((e) => (e.type === "Prop" && S.show.props && !V.iso) || (e.type === "Character" && S.show.characters))
    .sort((a, b) => (V.iso ? (a.x + a.y) - (b.x + b.y) : a.y - b.y));
  if (S.walk) {
    const [wu, wv] = S.walk.feet(), depth = (e) => (V.iso ? e.x + e.y : e.y), wd = V.iso ? wu + wv : wv;
    drawSprites(ctx, sprites.filter((e) => depth(e) <= wd)); drawWalker(ctx); drawSprites(ctx, sprites.filter((e) => depth(e) > wd));
  } else drawSprites(ctx, sprites);
  if (S.fx.length) drawFx(ctx, performance.now());
  if (S.fx.length || S.squash.size) S.needsDraw = true;

  const line = (w) => { ctx.lineWidth = w / S.zoom; };
  if (S.show.data && !S.walk) {
    for (const e of S.map.entities) {
      if (e.type === "Region") {
        ctx.strokeStyle = ENTITIES.Region.color; line(1.5); ctx.setLineDash([4 / S.zoom, 3 / S.zoom]);
        const corners = [V.pt(e.x, e.y), V.pt(e.x + e.w, e.y), V.pt(e.x + e.w, e.y + e.h), V.pt(e.x, e.y + e.h)];
        poly(ctx, corners); ctx.stroke(); ctx.setLineDash([]);
        label(e.fields.name, corners[0][0] + 2, corners[0][1] + 2, ENTITIES.Region.color);
      } else if (e.type === "Path") {
        const pts = (e.fields.points || []).map(cellCentre).map(([u, v]) => V.pt(u, v));
        if (!pts.length) continue;
        ctx.strokeStyle = ENTITIES.Path.color; line(2);
        ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
        ctx.fillStyle = ENTITIES.Path.color;
        for (const [x, y] of pts) ctx.fillRect(x - 2, y - 2, 4, 4);
        label(e.fields.name, pts[0][0] + 4, pts[0][1] - 12, ENTITIES.Path.color);
      }
    }
  }

  const sel = S.selected;
  if (sel) {
    const [x, y, w, h] = bounds(sel);
    ctx.strokeStyle = "#e8673a"; line(2); ctx.strokeRect(x - 1, y - 1, w + 2, h + 2);
    if (sel.type === "Character") {
      const mark = (p, color) => { if (!p) return; const [cx, cy] = V.pt(...cellCentre(p)); ctx.strokeStyle = color; line(2); ctx.strokeRect(cx - 5, cy - 5, 10, 10); };
      mark(sel.fields.perch, "#3a76f0"); mark(sel.fields.flyTo, "#3a76f0");
      const pts = (sel.fields.path || []).map(cellCentre).map(([u, v]) => V.pt(u, v));
      if (pts.length) { ctx.strokeStyle = "#e8673a"; line(1.5); ctx.beginPath(); pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py))); ctx.stroke(); }
    }
  }

  // what the next click will do
  const hv = S.hover;
  if (hv && !S.panning && !S.pinch && !S.pasting && !S.walk) {
    if (S.mode === "paint" && S.tool !== "select") {
      if (S.stroke?.plot) {
        const { fence, gate } = plotCells(S.map, S.stroke.rectFrom[0], S.stroke.rectFrom[1], hv.c, hv.r, value("Terrain", "path"));
        ctx.strokeStyle = "rgba(255,255,255,0.9)"; line(1.5);
        for (const [c, r] of fence) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
        if (gate) { ctx.strokeStyle = "#f2c94c"; line(2.5); poly(ctx, V.cellPoly(gate[0], gate[1])); ctx.stroke(); }
      }
      const shiftLine = !S.stroke && hv.free && S.tool === "brush" && S.lastCell;
      const cells = S.stroke?.plot ? [] : S.stroke?.rectFrom ? rectCells(S.map, S.stroke.rectFrom[0], S.stroke.rectFrom[1], hv.c, hv.r)
        : shiftLine ? lineCells(S.lastCell[0], S.lastCell[1], hv.c, hv.r).flatMap(([c, r]) => brushCells(S.map, c, r, S.size))
        : S.tool === "brush" ? brushCells(S.map, hv.c, hv.r, S.size) : inside(S.map, hv.c, hv.r) ? [[hv.c, hv.r]] : [];
      ctx.strokeStyle = "rgba(255,255,255,0.9)"; line(1.5);
      for (const [c, r] of cells) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
    } else if (S.place?.type === "Prop" && S.scatter.on) {
      ctx.strokeStyle = "rgba(255,255,255,0.9)"; line(1.5); ctx.setLineDash([3 / S.zoom, 3 / S.zoom]);
      for (const [c, r] of brushCells(S.map, hv.c, hv.r, 3)) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
      ctx.setLineDash([]);
    } else if (S.place && !S.drag && (S.place.type === "Prop" || S.place.type === "Character") && !hit(hv)) {
      const [x, y] = snapFeet(hv.mx, hv.my, hv.free);
      ctx.globalAlpha = 0.6;
      drawSprites(ctx, [{ type: S.place.type, x, y, fields: { sprite: S.place.sprite } }]);
      ctx.globalAlpha = 1;
    }
  }
  const footprint = (c0, r0, c1, r1) => [V.pt(c0 * T, r0 * T), V.pt((c1 + 1) * T, r0 * T), V.pt((c1 + 1) * T, (r1 + 1) * T), V.pt(c0 * T, (r1 + 1) * T)];
  if (S.sel) {
    const { c0, r0, c1, r1 } = S.sel;
    ctx.fillStyle = "rgba(58,118,240,0.12)"; poly(ctx, footprint(c0, r0, c1, r1)); ctx.fill();
    ctx.strokeStyle = "#3a76f0"; line(2); ctx.setLineDash([4 / S.zoom, 3 / S.zoom]); ctx.stroke(); ctx.setLineDash([]);
  }
  if (S.pasting && hv) {
    const [c0, r0] = pasteAt(hv);
    if (!V.iso) { ctx.globalAlpha = 0.75; ctx.drawImage(S.pasting.canvas, c0 * T, r0 * T); ctx.globalAlpha = 1; }
    ctx.fillStyle = "rgba(58,118,240,0.12)"; poly(ctx, footprint(c0, r0, c0 + S.pasting.clip.cols - 1, r0 + S.pasting.clip.rows - 1));
    if (V.iso) ctx.fill();
    ctx.strokeStyle = "#3a76f0"; line(2); ctx.stroke();
  }
  ctx.strokeStyle = "rgba(38,48,63,0.8)"; line(1); poly(ctx, V.border()); ctx.stroke();
}

function label(text, x, y, color) {
  if (!text) return;
  ctx.save();
  ctx.font = `600 ${11 / S.zoom}px "IBM Plex Mono", ui-monospace, monospace`;
  const w = ctx.measureText(text).width;
  ctx.fillStyle = color; ctx.fillRect(x, y, w + 6 / S.zoom, 14 / S.zoom);
  ctx.fillStyle = "#fff"; ctx.textBaseline = "top"; ctx.fillText(text, x + 3 / S.zoom, y + 2 / S.zoom);
  ctx.restore();
}

let lastTick = 0;
function loop(now) {
  if (S.map && S.ts) {
    if (S.terrainDirty) { bake(); S.needsDraw = true; }
    else if (S.restDirty && !S.stroke && !S.drag && !S.scatterStroke) { S.restDirty = false; S.terrainDirty = true; }
    if (S.walk) walkFrame();
    if (S.show.terrain && !reduceMotion && now - lastTick > S.ts.frameMs) { lastTick = now; S.frame = (S.frame + 1) % S.ts.frames; S.needsDraw = true; }
    if (S.needsDraw) draw();
  }
  requestAnimationFrame(loop);
}

// ---------- view: zoom and pan ----------

function zoomTo(z, sx, sy) {
  const r = canvas.getBoundingClientRect();
  sx ??= r.width / 2; sy ??= r.height / 2;
  z = Math.min(12, Math.max(0.25, z));
  const mx = (sx - S.ox) / S.zoom, my = (sy - S.oy) / S.zoom;
  S.zoom = z; S.ox = sx - mx * z; S.oy = sy - my * z;
  $("zoom-level").textContent = `${+z.toFixed(2)}×`;
  S.needsDraw = true;
}
const stepZoom = (dir) => {
  const i = ZOOMS.findIndex((z) => z >= S.zoom - 1e-6);
  zoomTo(dir > 0 ? ZOOMS[Math.min(ZOOMS.length - 1, (ZOOMS[i] > S.zoom + 1e-6 ? i : i + 1))] : ZOOMS[Math.max(0, i - 1)]);
};
function fit() {
  const r = canvas.getBoundingClientRect();
  if (r.width < 60 || r.height < 60) { requestAnimationFrame(fit); return; }   // not laid out yet
  S.V = makeView();
  const MW = S.V.W, MH = S.V.H;
  const best = Math.min((r.width - 24) / MW, (r.height - 24) / MH);
  const z = ZOOMS.filter((x) => x <= best).pop() || Math.max(0.25, best);
  S.zoom = z; S.ox = Math.round((r.width - MW * z) / 2); S.oy = Math.round((r.height - MH * z) / 2);
  $("zoom-level").textContent = `${+z.toFixed(2)}×`;
  S.needsDraw = true;
}

// ---------- input ----------

function toMap(ev) {
  const r = canvas.getBoundingClientRect();
  const sx = ev.clientX - r.left, sy = ev.clientY - r.top;
  const wx = (sx - S.ox) / S.zoom, wy = (sy - S.oy) / S.zoom;
  const k = (S.V || (S.V = makeView())).pick(wx, wy);
  return { sx, sy, wx, wy, mx: k.u, my: k.v, c: k.c, r: k.r, free: ev.shiftKey };
}

function strokeCells(p) {
  if (S.tool === "fill") return floodCells(S.map, S.brush.layer, p.c, p.r);
  if (S.tool !== "brush") return [];
  const [c0, r0] = S.stroke.last || [p.c, p.r];
  S.stroke.last = [p.c, p.r];
  return lineCells(c0, r0, p.c, p.r).flatMap(([c, r]) => brushCells(S.map, c, r, S.size));
}

function beginPaint(p, erase, pick, line) {
  if (pick || S.tool === "pick") {
    if (!inside(S.map, p.c, p.r)) return;
    for (const g of [...PALETTE].reverse()) {
      const v = S.map.layers[g.layer][p.r * S.map.cols + p.c];
      if (v && g.items.some((it) => it.v === v)) { S.brush = { layer: g.layer, v }; break; }
      if (g.layer === "Terrain") S.brush = { layer: "Terrain", v: 0 };
    }
    if (S.tool === "pick") S.tool = "brush";
    buildPaintPanel();
    return;
  }
  history.push(S.map);
  const op = S.brush.op && (erase ? { raise: "lower", lower: "raise", flat: "lower" }[S.brush.op] : S.brush.op);
  const target = inside(S.map, p.c, p.r) ? S.map.layers.Height[p.r * S.map.cols + p.c] : 0;
  S.stroke = { v: erase ? 0 : S.brush.v, op, target, touched: new Set(), changed: false, rectFrom: S.tool === "rect" || S.tool === "plot" ? [p.c, p.r] : null, plot: S.tool === "plot" };
  if (line && S.tool === "brush" && S.lastCell) S.stroke.last = S.lastCell;      // Shift: a straight line from the last stroke
  if (!S.stroke.rectFrom) applyStroke(p);
}

// Paint cells with the brush's value, or shape the height.
function apply(cells) {
  const st = S.stroke;
  return st.op ? shapeHeight(S.map, cells, st.op, st.target, MAX_LEVEL, st.touched) : paint(S.map, S.brush.layer, st.v, cells);
}

function applyStroke(p) {
  if (!S.stroke || S.stroke.rectFrom) return;
  if (apply(strokeCells(p))) { S.stroke.changed = true; S.terrainDirty = true; }
}

function endPaint(p) {
  const st = S.stroke;
  if (!st) return;
  if (st.plot && p) {
    const { fence, gate } = plotCells(S.map, st.rectFrom[0], st.rectFrom[1], p.c, p.r, value("Terrain", "path"));
    const ch1 = paint(S.map, "Deco", value("Deco", "fence"), fence), ch2 = gate ? paint(S.map, "Deco", value("Deco", "gate"), [gate]) : false;
    if (ch1 || ch2) { st.changed = true; S.terrainDirty = true; }
  } else if (st.rectFrom && p && apply(rectCells(S.map, st.rectFrom[0], st.rectFrom[1], p.c, p.r))) { st.changed = true; S.terrainDirty = true; }
  S.stroke = null;
  if (p && S.tool === "brush") S.lastCell = [p.c, p.r];
  if (st.changed) changed(true); else history.drop();
}

function cancelStroke() {
  if (S.scatterStroke) { if (S.scatterStroke.changed) { history.undo(S.map); history.future = []; } else history.drop(); S.scatterStroke = null; }
  if (S.stroke) { if (S.stroke.changed) { history.undo(S.map); history.future = []; S.terrainDirty = true; } else history.drop(); S.stroke = null; }
  if (S.drag) { if (S.drag.moved) { history.undo(S.map); history.future = []; select(null); } else history.drop(); S.drag = null; }
}

canvas.addEventListener("contextmenu", (ev) => ev.preventDefault());

canvas.addEventListener("pointerdown", (ev) => {
  if (!S.map) return;
  try { canvas.setPointerCapture(ev.pointerId); } catch { /* the pointer is already gone */ }
  S.pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
  if (S.pointers.size === 2) {                                          // two fingers: pinch and pan, drop the stroke
    if (S.longPress) { clearTimeout(S.longPress.timer); S.longPress = null; }
    cancelStroke();
    const [a, b] = [...S.pointers.values()];
    S.pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2, zoom: S.zoom };
    return;
  }
  if (S.pointers.size > 2) return;
  if (S.walk) return;
  const p = toMap(ev);
  if (ev.button === 1 || S.spaceDown) { S.panning = { x: ev.clientX, y: ev.clientY, ox: S.ox, oy: S.oy }; $("stage").classList.add("pan"); return; }
  if (S.pasting) {
    if (ev.button === 2) { stopPaste(); return; }
    history.push(S.map);
    const [c0, r0] = pasteAt(p);
    pasteArea(S.map, S.pasting.clip, c0, r0);
    changed(true);
    return;
  }
  if (S.mode === "paint" && S.tool === "select") {
    S.selFrom = [p.c, p.r]; S.sel = inside(S.map, p.c, p.r) ? area(S.selFrom, S.selFrom) : null; select(null);
    S.needsDraw = true; return;
  }
  if (S.mode === "paint") {
    beginPaint(p, ev.button === 2 || S.eraseMode, ev.altKey, ev.shiftKey);
    if (ev.pointerType === "touch" && S.tool !== "pick") {           // hold still to pick instead of paint
      const at = { x: ev.clientX, y: ev.clientY };
      S.longPress = { at, timer: setTimeout(() => { cancelStroke(); beginPaint(p, false, true, false); toast("Picked what was there"); S.longPress = null; }, 500) };
    }
  }
  else if (S.place?.type === "Prop" && S.scatter.on) {
    history.push(S.map);
    S.scatterStroke = { done: new Set(), changed: false, erase: ev.button === 2 };
    scatterAt(p, S.scatterStroke.erase);
  } else {
    const e = hit(p);
    if (e) {
      select(e);
      history.push(S.map);
      S.drag = { e, start: p, x: e.x, y: e.y, points: e.fields.points ? structuredClone(e.fields.points) : null, moved: false };
    } else if (S.place && inside(S.map, p.c, p.r)) placeAt(p.mx, p.my, p.free);
    else select(null);
  }
  S.needsDraw = true;
});

canvas.addEventListener("pointermove", (ev) => {
  if (!S.map) return;
  if (S.pointers.has(ev.pointerId)) S.pointers.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
  if (S.pinch && S.pointers.size >= 2) {
    const [a, b] = [...S.pointers.values()];
    const d = Math.hypot(a.x - b.x, a.y - b.y), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
    const r = canvas.getBoundingClientRect();
    S.ox += mx - S.pinch.mx; S.oy += my - S.pinch.my;
    zoomTo(S.pinch.zoom * d / S.pinch.d, mx - r.left, my - r.top);
    S.pinch.mx = mx; S.pinch.my = my;
    return;
  }
  const p = toMap(ev);
  S.hover = p;
  if (S.longPress && Math.hypot(ev.clientX - S.longPress.at.x, ev.clientY - S.longPress.at.y) > 6) { clearTimeout(S.longPress.timer); S.longPress = null; }
  if (S.panning) { S.ox = S.panning.ox + ev.clientX - S.panning.x; S.oy = S.panning.oy + ev.clientY - S.panning.y; S.needsDraw = true; return; }
  if (S.selFrom) {
    const cl = (v, n) => Math.min(n - 1, Math.max(0, v));
    S.sel = area([cl(S.selFrom[0], S.map.cols), cl(S.selFrom[1], S.map.rows)], [cl(p.c, S.map.cols), cl(p.r, S.map.rows)]);
  }
  if (S.stroke) applyStroke(p);
  if (S.scatterStroke) scatterAt(p, S.scatterStroke.erase);
  if (S.drag) {
    const d = S.drag, e = d.e;
    const dx = p.mx - d.start.mx, dy = p.my - d.start.my;
    if (!d.moved && Math.hypot(dx, dy) * S.zoom < 3) { S.needsDraw = true; updateHud(p); return; }
    d.moved = true;
    if (e.type === "Prop" || e.type === "Character") [e.x, e.y] = p.free ? [Math.round(d.x + dx), Math.round(d.y + dy)] : snapFeet(d.x + dx, d.y + dy - 1, false);
    else {
      const dc = Math.round(dx / T), dr = Math.round(dy / T);
      e.x = d.x + dc * T; e.y = d.y + dr * T;
      if (d.points) e.fields.points = d.points.map(([c, r]) => [c + dc, r + dr]);
    }
  }
  updateHud(p);
  S.needsDraw = true;
});

function pointerEnd(ev) {
  S.pointers.delete(ev.pointerId);
  if (S.longPress) { clearTimeout(S.longPress.timer); S.longPress = null; }
  if (S.pinch) { if (S.pointers.size < 2) S.pinch = null; return; }
  if (S.panning) { S.panning = null; $("stage").classList.remove("pan"); return; }
  const p = S.map ? toMap(ev) : null;
  if (S.selFrom) { S.selFrom = null; buildInspector(); }
  if (S.stroke) endPaint(p);
  if (S.scatterStroke) { const st = S.scatterStroke; S.scatterStroke = null; if (st.changed) changed(false); else history.drop(); }
  if (S.drag) {
    const moved = S.drag.moved;
    S.drag = null;
    if (moved) { changed(S.selected?.type === "Region"); buildInspector(); } else history.drop();
  }
  S.needsDraw = true;
}
canvas.addEventListener("pointerup", pointerEnd);
canvas.addEventListener("pointercancel", (ev) => { cancelStroke(); pointerEnd(ev); });
canvas.addEventListener("pointerleave", () => { S.hover = null; S.needsDraw = true; updateHud(null); });

canvas.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const r = canvas.getBoundingClientRect();
  if (ev.ctrlKey || ev.metaKey) zoomTo(S.zoom * Math.exp(-ev.deltaY * 0.01), ev.clientX - r.left, ev.clientY - r.top);
  else { S.ox -= ev.deltaX; S.oy -= ev.deltaY; S.needsDraw = true; }
}, { passive: false });

function updateHud(p) {
  const hud = $("hud");
  if (!p || !S.map || !inside(S.map, p.c, p.r)) { hud.textContent = S.map ? `${S.map.cols}×${S.map.rows}` : "–"; return; }
  const i = p.r * S.map.cols + p.c;
  const name = (layer) => LAYERS[layer].values.find((x) => x.v === S.map.layers[layer][i])?.label;
  const bits = [name("Terrain") || "Grass", `level ${S.map.layers.Height[i]}`, name("Features"), name("Deco")].filter(Boolean);
  hud.textContent = `col ${p.c}, row ${p.r} · ${bits.join(", ")}`;
}

const typing = () => ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
window.addEventListener("keydown", (ev) => {
  const mod = ev.ctrlKey || ev.metaKey;
  if (mod && ev.key.toLowerCase() === "s") { ev.preventDefault(); save(); return; }
  if (typing()) return;
  if (S.walk) {
    const dir = WALK_KEYS[ev.key.toLowerCase()];
    if (dir) { ev.preventDefault(); S.walk.press(dir); }
    if (ev.key === "Escape" || ev.key === "Enter") walkStop();
    return;
  }
  if (ev.key === "Enter" && !mod && document.activeElement?.tagName !== "BUTTON") { ev.preventDefault(); walkStart(); return; }
  if (mod && ev.key.toLowerCase() === "z") { ev.preventDefault(); ev.shiftKey ? redo() : undo(); return; }
  if (mod && ev.key.toLowerCase() === "y") { ev.preventDefault(); redo(); return; }
  if (mod && ev.key.toLowerCase() === "c" && S.sel) { ev.preventDefault(); copySel(false); return; }
  if (mod && ev.key.toLowerCase() === "x" && S.sel) { ev.preventDefault(); copySel(true); return; }
  if (mod && ev.key.toLowerCase() === "v" && S.clip) { ev.preventDefault(); startPaste(S.clip); return; }
  if (mod) return;
  if (ev.key === " ") { if (!S.spaceDown) { S.spaceDown = true; $("stage").classList.add("pan"); } ev.preventDefault(); return; }
  const k = ev.key.toLowerCase();
  if (k === "r" && ev.shiftKey) { S.show.raw = !S.show.raw; buildShow(); S.needsDraw = true; return; }
  if (S.mode === "paint" && { b: 1, r: 1, f: 1, i: 1, s: 1, t: 1 }[k]) { setTool({ b: "brush", r: "rect", f: "fill", i: "pick", s: "select", t: "plot" }[k]); return; }
  if (k === "p") { setMode(S.mode === "paint" ? "objects" : "paint"); return; }
  if (k === "v") { setMode("objects"); S.place = null; buildCatalog(); return; }
  if (S.mode === "paint" && /^[1-9]$/.test(ev.key)) {
    const all = PALETTE.flatMap((g) => g.items.map((it) => ({ layer: g.layer, it })));
    const pickd = all[+ev.key - 1];
    if (pickd) { S.brush = pickd.it.op ? { layer: pickd.layer, op: pickd.it.op } : { layer: pickd.layer, v: pickd.it.v }; buildPaintPanel(); }
    return;
  }
  if (k === "[" || k === "]") { S.size = Math.min(3, Math.max(1, S.size + (k === "]" ? 1 : -1))); buildPaintPanel(); S.needsDraw = true; return; }
  if (k === "shift" && S.hover) { S.hover.free = true; S.needsDraw = true; return; }
  if (k === "+" || k === "=") { stepZoom(1); return; }
  if (k === "-" || k === "_") { stepZoom(-1); return; }
  if ((k === "delete" || k === "backspace") && S.selected) { ev.preventDefault(); removeSelected(); return; }
  if ((k === "delete" || k === "backspace") && S.sel) { ev.preventDefault(); deleteSel(); return; }
  if (k === "escape") { if (S.pasting) { stopPaste(); return; } S.place = null; S.sel = null; select(null); buildCatalog(); }
});
window.addEventListener("keyup", (ev) => {
  if (S.walk) { const dir = WALK_KEYS[ev.key.toLowerCase()]; if (dir) S.walk.release(dir); }
  if (ev.key === " ") { S.spaceDown = false; if (!S.panning) $("stage").classList.remove("pan"); }
  if (ev.key === "Shift" && S.hover) { S.hover.free = false; S.needsDraw = true; }
});
window.addEventListener("resize", () => { S.needsDraw = true; });

// ---------- modes, panels ----------

function setMode(mode) {
  S.mode = mode;
  $("mode-paint").setAttribute("aria-pressed", String(mode === "paint"));
  $("mode-objects").setAttribute("aria-pressed", String(mode === "objects"));
  $("paint-panel").hidden = mode !== "paint";
  $("objects-panel").hidden = mode !== "objects";
  syncBar();
  S.needsDraw = true;
}
$("m-mode").addEventListener("click", () => setMode(S.mode === "paint" ? "objects" : "paint"));
for (const b of $("mbar").querySelectorAll("[data-tool]")) b.addEventListener("click", () => setTool(b.dataset.tool));
$("m-erase").addEventListener("click", () => { S.eraseMode = !S.eraseMode; syncBar(); });
$("m-undo").addEventListener("click", () => undo());
$("m-redo").addEventListener("click", () => redo());
$("m-brush").addEventListener("click", () => $("palette").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" }));
$("mode-paint").addEventListener("click", () => setMode("paint"));
$("mode-objects").addEventListener("click", () => setMode("objects"));

const SHOW = [["terrain", "Terrain"], ["props", "Props"], ["characters", "Characters"], ["data", "Paths and regions"], ["raw", "Raw grid (Shift R)"], ["grid", "Grid lines"]];
function buildShow() {
  $("show").replaceChildren(...SHOW.map(([k, label]) => el("label", { for: `show-${k}` },
    el("input", { type: "checkbox", id: `show-${k}`, checked: S.show[k], onchange: (ev) => { S.show[k] = ev.target.checked; if (k === "props") S.terrainDirty = true; S.needsDraw = true; } }), label)));
}

$("zoom-in").addEventListener("click", () => stepZoom(1));
$("zoom-out").addEventListener("click", () => stepZoom(-1));
$("zoom-fit").addEventListener("click", fit);

$("resize").addEventListener("click", () => {
  const cols = Math.max(4, Math.min(200, +$("cols").value | 0)), rows = Math.max(4, Math.min(200, +$("rows").value | 0));
  if (cols === S.map.cols && rows === S.map.rows) return;
  history.push(S.map);
  resize(S.map, cols, rows);
  changed(true);
  toast(`Map is now ${cols} × ${rows} cells`);
});

// ---------- saving ----------

let autosaveTimer = null;
function changed(terrain) {
  if (terrain) { S.terrainDirty = true; if (S.V?.iso) S.V = makeView(); }
  else if (S.V?.iso) S.terrainDirty = true;                  // props are part of the isometric picture
  S.needsDraw = true;
  updateUndo();
  $("cols").value = S.map.cols; $("rows").value = S.map.rows;
  setState("Unsaved changes · kept in this browser");
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => { if (!writeAutosave(S.fileName, stringifyMap(S.map))) setState("Unsaved changes · this browser can't keep them, save to a file"); }, 600);
}

function setState(text) { $("state").textContent = text; }
function toast(text) {
  const t = $("toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2600);
}

function updateUndo() {
  $("undo").disabled = $("m-undo").disabled = !history.past.length;
  $("redo").disabled = $("m-redo").disabled = !history.future.length;
}
function undo() { if (history.undo(S.map)) afterHistory(); }
function redo() { if (history.redo(S.map)) afterHistory(); }
function afterHistory() {
  if (S.selected && !S.map.entities.includes(S.selected)) S.selected = null;
  buildInspector(); changed(true);
}
$("undo").addEventListener("click", undo);
$("redo").addEventListener("click", redo);

async function save() {
  const blob = new Blob([stringifyMap(S.map) + "\n"], { type: "application/json" });
  try {
    const r = await saveFile(blob, S.fileName, { fallbackName: S.fileName.replace(/\.ldtk$/, "") + ".json",
      types: [{ description: "Map (LDtk)", accept: { "application/json": [".ldtk"] } }] });
    if (r === "saved") { setState(`Saved ${S.fileName}`); toast("Saved"); }
  } catch (e) { toast(`Couldn't save: ${e.message}`); }
}
$("save").addEventListener("click", save);

$("export").addEventListener("click", async () => {
  const c = document.createElement("canvas");
  c.width = S.V.W; c.height = S.V.H;
  const g = c.getContext("2d");
  if (S.V.iso) g.drawImage(bakeIso(S.map, S.isoTs, S.V)[0], 0, 0); else drawTerrain(g, S.map, S.ts, 0);
  drawSprites(g, S.map.entities.filter((e) => (e.type === "Prop" && !S.V.iso) || e.type === "Character").sort((a, b) => (S.V.iso ? (a.x + a.y) - (b.x + b.y) : a.y - b.y)));
  const blob = await new Promise((ok) => c.toBlob(ok, "image/png"));
  try {
    const r = await saveFile(blob, S.fileName.replace(/\.(ldtk|json)$/, "") + ".png", { types: [{ description: "PNG image", accept: { "image/png": [".png"] } }] });
    if (r === "saved") toast("Exported the map as a PNG");
  } catch (e) { toast(`Couldn't export: ${e.message}`); }
});

function useMap(m, name, note) {
  walkStop();
  S.V = null;
  S.map = m; S.fileName = name; S.selected = null; S.sel = null;
  $("file-name").textContent = name;
  $("cols").value = m.cols; $("rows").value = m.rows;
  buildInspector(); fit(); S.terrainDirty = true; updateUndo(); updateHud(null);
  if (note) toast(note);
}

$("open").addEventListener("click", async () => {
  const f = await openFile(".ldtk,.json,application/json");
  if (!f) return;
  try {
    const m = parseMap(JSON.parse(f.text));
    history.push(S.map);
    useMap(m, f.name.endsWith(".json") ? f.name.replace(/(\.ldtk)?\.json$/, ".ldtk") : f.name, `Opened ${f.name}`);
    changed(true);
  } catch (e) { toast(`Couldn't open ${f.name}: ${e.message}`); }
});

let confirmNew = 0;
$("new").addEventListener("click", () => {
  const b = $("new");
  if (Date.now() - confirmNew > 3000) { confirmNew = Date.now(); b.textContent = "Sure? Click again"; setTimeout(() => { b.textContent = "New"; }, 3000); return; }
  b.textContent = "New";
  history.push(S.map);
  useMap(newMap(S.map.cols, S.map.rows), "town.ldtk", "New empty map. Undo brings the old one back.");
  changed(true);
});

$("example").addEventListener("click", async () => {
  try {
    const m = parseMap(await (await fetch(EXAMPLE)).json());
    history.push(S.map);
    useMap(m, "town-v5.ldtk", "Opened the example town. Undo brings your map back.");
    changed(true);
  } catch (e) { toast(`Couldn't load the example: ${e.message}`); }
});

$("share").addEventListener("click", async () => {
  const out = $("share-out");
  out.value = "Packing…";
  $("share-dialog").showModal();
  try { out.value = await mapToCode(S.map); out.select(); } catch (e) { out.value = `Couldn't make a code here: ${e.message}`; }
});
$("share-copy").addEventListener("click", async () => {
  const out = $("share-out");
  try { await navigator.clipboard.writeText(out.value); toast(`Copied a ${Math.round(out.value.length / 1024)} KB code`); }
  catch { out.select(); toast("Select the code and copy it with Ctrl+C"); }
});
$("share-open").addEventListener("click", async () => {
  try {
    const m = await codeToMap($("share-in").value);
    history.push(S.map);
    useMap(m, "shared.ldtk", "Opened the shared map. Undo brings yours back.");
    changed(true);
    $("share-dialog").close();
  } catch (e) { toast(e.message); }
});

// ---------- isometric or top-down ----------

function syncProjection() {
  const b = $("projection");
  b.textContent = S.projection === "iso" ? "Isometric" : "Top-down";
  b.title = `Showing ${S.projection === "iso" ? "isometric" : "top-down"}; click to switch`;
  b.disabled = !S.isoTs;
}
$("projection").addEventListener("click", () => {
  S.projection = S.projection === "iso" ? "ortho" : "iso";
  try { localStorage.setItem("tiny-town/projection", S.projection); } catch { /* fine */ }
  syncProjection();
  S.V = null; S.terrainDirty = true;
  if (S.map) fit();
});

// ---------- walk mode ----------

const WALK_KEYS = { arrowup: "up", w: "up", arrowdown: "down", s: "down", arrowleft: "left", a: "left", arrowright: "right", d: "right" };

function walkStart() {
  const m = S.map;
  const startRegion = m.entities.find((e) => e.type === "Region" && e.fields.name === "start");
  const cat = m.entities.find((e) => e.type === "Character" && e.fields.id === "cat");
  const at = startRegion ? [Math.floor(startRegion.x / T), Math.floor(startRegion.y / T)]
    : cat ? [Math.floor(cat.x / T), Math.floor((cat.y - 1) / T)] : [Math.floor(m.cols / 2), Math.floor(m.rows / 2)];
  S.walk = new Walker(m, S.ts.props, at);
  S.walkView = { zoom: S.zoom, ox: S.ox, oy: S.oy };
  S.zoom = 3; $("zoom-level").textContent = "3×";
  S.pasting = null; S.sel = null; select(null);
  $("walk").setAttribute("aria-pressed", "true"); $("pad").hidden = false; $("walking").hidden = false; $("mbar").hidden = true;
  S.needsDraw = true;
}

function walkStop() {
  if (!S.walk) return;
  S.walk = null;
  Object.assign(S, S.walkView); $("zoom-level").textContent = `${+S.zoom.toFixed(2)}×`;
  $("walk").setAttribute("aria-pressed", "false"); $("pad").hidden = true; $("walking").hidden = true; $("mbar").hidden = false;
  S.needsDraw = true;
}

$("walk").addEventListener("click", () => (S.walk ? walkStop() : walkStart()));
for (const b of $("pad").querySelectorAll("button")) {
  b.addEventListener("pointerdown", (ev) => { ev.preventDefault(); S.walk?.press(b.dataset.dir); });
  for (const t of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(t, () => S.walk?.release(b.dataset.dir));
}

function walkFrame() {
  const w = S.walk;
  w.update();
  const [x, y] = S.V.feet({ x: w.feet()[0], y: w.feet()[1] }), r = canvas.getBoundingClientRect();
  const tx = r.width / 2 - x * S.zoom, ty = r.height / 2 - (y - 12) * S.zoom;
  S.ox += (tx - S.ox) * 0.2; S.oy += (ty - S.oy) * 0.2;
  S.needsDraw = true;
}

function drawWalker(g) {
  const w = S.walk, im = S.sprites["cat-walk"] || S.sprites["cat-sit"] || S.sprites[S.spriteNames[0]];
  const [u, v] = w.feet(), [x, y] = S.V.feet({ x: u, y: v });
  g.fillStyle = "rgba(38, 48, 63, 0.28)";
  g.beginPath(); g.ellipse(x, y - 1, 6, 2.2, 0, 0, Math.PI * 2); g.fill();
  if (!im) { g.fillStyle = "#e8673a"; g.fillRect(x - 5, y - 12, 10, 12); return; }
  g.save();
  g.translate(Math.round(x), Math.round(y));
  if (w.facing === "left") g.scale(-1, 1);
  g.drawImage(im, -Math.round(im.width / 2), -im.height);
  g.restore();
}

// ---------- start ----------

async function start() {
  try {
    S.ts = await loadTileset("tiles/");
  } catch (e) {
    $("file-name").textContent = "Couldn't load the tiles. Open this page through a web server (see README).";
    return;
  }
  S.isoTs = await loadIsoTileset("tiles/iso/").catch(() => null);
  try { S.projection = localStorage.getItem("tiny-town/projection") || "iso"; } catch { /* default */ }
  if (!S.isoTs) S.projection = "ortho";
  syncProjection();
  try {
    const idx = await (await fetch("sprites/index.json")).json();
    await Promise.all(idx.sprites.map((n) => new Promise((ok) => {
      const im = new Image();
      im.onload = () => { S.sprites[n] = im; ok(); };
      im.onerror = () => ok();
      im.src = `sprites/${n}.png`;
    })));
    S.spriteNames = idx.sprites.filter((n) => S.sprites[n]);
  } catch { S.spriteNames = []; }

  S.stamps = [...await loadBuiltinStamps("tiles/"), ...loadStamps()];
  buildPaintPanel(); buildCatalog(); buildShow(); buildStamps();
  const saved = loadAutosave();
  let m = null, name = "town-v5.ldtk", note = null;
  if (saved) {
    try { m = parseMap(JSON.parse(saved.text)); name = saved.name || "town.ldtk"; note = "Picked up where you left off"; } catch { m = null; }
  }
  if (!m) {
    try { m = parseMap(await (await fetch(EXAMPLE)).json()); } catch { m = newMap(40, 50); name = "town.ldtk"; }
  }
  useMap(m, name, note);
  setState(saved ? "Restored from this browser" : "Example town · changes are kept in this browser");
  requestAnimationFrame(loop);
}
start();
