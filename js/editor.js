// The map builder: paint cells, place objects, undo, save. Plain ES module, no build step.

import { newMap, parseMap, stringifyMap } from "./format.js";
import { drawProp, drawTerrain, loadTileset, topGrass } from "./render.js";
import { bakeIso, grassPhase, groundLevel, isoView, loadIsoTileset } from "./iso.js";
import { ENTITIES, LAYERS, MAX_LEVEL, value } from "./registry.js";
import { History, brushCells, grow, inside, lineCells, paint, shapeHeight } from "./tools.js";
import { loadAutosave, openFile, saveFile, writeAutosave } from "./files.js";
import { area, copyArea, drawClip, loadBuiltinStamps, loadStamps, pasteArea, saveStamps } from "./stamps.js";
import { codeToMap, mapToCode } from "./share.js";
import { Walker } from "./walk.js";

const T = 16;
const EXAMPLE = "maps/market-village.ldtk";
const ZOOMS = [0.25, 0.5, 1, 2, 3, 4, 5, 6, 8];      // whole-map zoom levels Fit picks from
const STEPS = [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16];   // the − and + steps, as shares of the fitted view (100%)
const MAX_SIZE = 200;       // painting anywhere grows the map, up to this many cells a side
const $ = (id) => document.getElementById(id);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const phone = () => matchMedia("(max-width: 720px)").matches;

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

// Line icons, 24x24, drawn with the current text colour.
const ICONS = {
  brush: '<path d="M14.5 4.5l5 5-8.5 8.5H6v-5z"/><path d="M12.5 6.5l5 5"/>',
  rect: '<rect x="4.5" y="4.5" width="15" height="15" rx="1.5"/><path d="M4.5 12h15M12 4.5v15" opacity=".35"/>',
  fill: '<path d="M4.5 11.5l6.5-6.5 7.5 7.5-6.5 6.5z"/><path d="M4.5 11.5h14"/><path d="M20 15.5c.7 1.2 1.2 2 1.2 2.7a1.2 1.2 0 0 1-2.4 0c0-.7.5-1.5 1.2-2.7z"/>',
  plot: '<path d="M5.5 20V9l1.8-2.5L9 9v11M15 20V9l1.8-2.5L18.5 9v11M3.5 12h17M3.5 16.5h17"/>',
  pick: '<path d="M14.5 5.5l4 4M16.5 3.5a2 2 0 0 1 4 4l-2 2-4-4z"/><path d="M14.5 7.5l-9 9V19h2.5l9-9"/>',
  area: '<rect x="4.5" y="4.5" width="15" height="15" rx="1" stroke-dasharray="3 2.6"/>',
  erase: '<path d="M8.5 19.5h11M5.3 14.7l8.4-8.4a1.5 1.5 0 0 1 2.1 0l3 3a1.5 1.5 0 0 1 0 2.1L11 19.5H8.6z"/><path d="M9.5 10.5l5 5"/>',
  undo: '<path d="M9 6.5L4.5 11 9 15.5"/><path d="M4.5 11h10a5 5 0 0 1 0 10H12"/>',
  redo: '<path d="M15 6.5l4.5 4.5-4.5 4.5"/><path d="M19.5 11h-10a5 5 0 0 0 0 10H12"/>',
  cog: '<circle cx="12" cy="12" r="3"/><path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7"/><circle cx="12" cy="12" r="6.6"/>',
  chev: '<path d="M7 10l5 5 5-5"/>',
  dup: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  trash: '<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 12.5h9l1-12.5"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  paint: '<path d="M14.5 4.5l5 5-8.5 8.5H6v-5z"/>',
  objects: '<path d="M12 3.5l7.5 4v9L12 20.5l-7.5-4v-9z"/><path d="M4.5 7.5L12 11.5l7.5-4M12 11.5v9"/>',
};
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
  return t.content.firstChild;
}

// ---------- state ----------

// One tool is active at a time. "select" means no tool: a click selects an object, a drag moves it or pans the map.
// "brush" is on while a swatch is chosen. `place`, `scatter` and `stamp` carry what they put down in S.place and
// S.pasting; "area" picks the part of the map a new stamp keeps.
const S = {
  map: null, ts: null, sprites: {}, spriteNames: [], fileName: "town.ldtk",
  tool: "select", size: 1, brush: { layer: "Terrain", v: 1 },
  place: null, selected: null, scatter: { on: false, density: 0.35 }, scatterStroke: null,
  sel: null, selFrom: null, pasting: null, stamps: [], stroll: null, longPress: null,
  fx: [], squash: new Map(), isoTs: null, projection: "iso", V: null,
  zoom: 2, ox: 0, oy: 0,
  show: { terrain: true, props: true, characters: true, data: true, raw: false, grid: false, margin: true },
  frames: [], frame: 0, terrainDirty: true, needsDraw: true,
  hover: null, stroke: null, drag: null, pointers: new Map(), pinch: null, spaceDown: false, panning: null, dnd: null,
};
const history = new History();
window.tinyTown = { state: S, history };          // for poking around in the browser console

// ---------- the paint palette ----------

const PALETTE = [
  { group: "Ground", layer: "Terrain", items: [{ v: 0, label: "Grass", key: "grass" }, ...LAYERS.Terrain.values.map((x) => ({ v: x.v, label: x.label, key: x.id }))] },
  { group: "Height", layer: "Height", items: [{ op: "raise", label: "Raise", key: "raised", mark: "▲" }, { op: "lower", label: "Lower", key: "pit", mark: "▼" }, { op: "flat", label: "Flatten", key: "grass", mark: "=" }] },
  { group: "Features", layer: "Features", items: LAYERS.Features.values.map((x) => ({ v: x.v, label: x.label, key: x.id })) },
  { group: "Decoration", layer: "Deco", items: LAYERS.Deco.values.map((x) => ({ v: x.v, label: x.label, key: x.id })) },
];

// A small scene that shows what a palette item paints, drawn the way the map is (isometric or top-down).
// Each picture is drawn once and copied after that.
const swatches = new Map();
function swatch(key, color, mark) {
  const id = `${S.projection === "iso" && S.isoTs ? "iso" : "top"}:${key}:${mark || ""}`;
  if (!swatches.has(id)) swatches.set(id, id.startsWith("iso") ? isoSwatch(key) : topSwatch(key, color));
  const c = el("canvas", { width: 32, height: 32, "aria-hidden": "true" }), g = c.getContext("2d");
  g.drawImage(swatches.get(id), 0, 0);
  if (mark) {
    g.font = "bold 13px ui-monospace, monospace"; g.textAlign = "center"; g.textBaseline = "middle";
    g.lineWidth = 3; g.strokeStyle = "#26303f"; g.strokeText(mark, 24, 9); g.fillStyle = "#fff"; g.fillText(mark, 24, 9);
  }
  return c;
}

function topSwatch(key, color) {
  const c = el("canvas", { width: 32, height: 32 });
  const m = newMap(2, 2);
  const tv = LAYERS.Terrain.values.find((x) => x.id === key);
  if (tv) m.layers.Terrain.fill(tv.v);
  else if (key === "raised") { m.layers.Height[0] = m.layers.Height[1] = 1; }
  else if (key === "pit") { m.layers.Height.fill(1); m.layers.Height[3] = 0; }
  else if (key === "stairs") { m.layers.Height[0] = m.layers.Height[1] = 1; m.layers.Features[2] = m.layers.Features[3] = 1; m.layers.Terrain[0] = m.layers.Terrain[2] = 1; }
  else if (key === "fence") { m.layers.Deco[2] = m.layers.Deco[3] = 1; }
  else if (key === "gate") { m.layers.Deco[2] = 4; m.layers.Deco[3] = 1; }
  else if (key === "flowers") { m.layers.Deco.fill(2); }
  else if (key === "tallgrass") { m.layers.Deco.fill(3); }
  const g = c.getContext("2d");
  drawTerrain(g, m, S.ts, 0);
  if (!["grass", "raised", "pit", "stairs", "fence", "gate", "flowers", "tallgrass"].includes(key) && !tv && color) { g.fillStyle = color; g.fillRect(4, 4, 24, 24); }
  return c;
}

// A 3x3 isometric scene, cropped to the 32x32 round its middle cell, at the map's own pixel size.
function isoSwatch(key) {
  const m = newMap(3, 3), L = m.layers, at = (c, r) => r * 3 + c, row = (r, layer, v) => { for (let c = 0; c < 3; c++) L[layer][at(c, r)] = v; };
  const tv = LAYERS.Terrain.values.find((x) => x.id === key);
  if (key === "bridge") { L.Terrain.fill(value("Terrain", "water")); for (let r = 0; r < 3; r++) L.Terrain[at(1, r)] = tv.v; }
  else if (tv) L.Terrain.fill(tv.v);
  else if (key === "raised") { for (const [c, r] of [[0, 0], [1, 0], [0, 1], [1, 1]]) L.Height[at(c, r)] = 1; }
  else if (key === "pit") { L.Height.fill(1); L.Height[at(1, 1)] = 0; }
  else if (key === "stairs") { row(0, "Height", 1); L.Features[at(1, 1)] = 1; L.Terrain[at(1, 1)] = L.Terrain[at(1, 0)] = value("Terrain", "path"); }
  else if (key === "fence") row(1, "Deco", value("Deco", "fence"));
  else if (key === "gate") { row(1, "Deco", value("Deco", "fence")); L.Deco[at(1, 1)] = value("Deco", "gate"); }
  else if (key === "flowers") L.Deco.fill(value("Deco", "flowers"));
  else if (key === "tallgrass") L.Deco.fill(value("Deco", "tallgrass"));
  const v = isoView(m), big = bakeIso(m, S.isoTs, v, { objects: false, frames: [0] })[0];
  const [x, y] = v.cellTop(1, 1, key === "pit" ? 1 : 0), c = el("canvas", { width: 32, height: 32 });
  c.getContext("2d").drawImage(big, x - 16, y - 8, 32, 32, 0, 0, 32, 32);
  return c;
}

const brushKey = (b) => `${b.layer}:${b.op || b.v}`;
const brushItem = () => PALETTE.find((g) => g.layer === S.brush.layer)?.items.find((x) => (S.brush.op ? x.op === S.brush.op : x.v === S.brush.v && !x.op));

function buildPaintPanel() {
  $("palette").replaceChildren(...PALETTE.filter((g) => g.items.length).map((g) => el("details", { class: "sec", open: true },
    el("summary", { text: g.group }),
    el("div", { class: "swatches" }, ...g.items.map((it) => {
      const color = LAYERS[g.layer].values.find((x) => x.v === it.v)?.color;
      return el("button", { class: "swatch", type: "button", "data-brush": brushKey(it.op ? { layer: g.layer, op: it.op } : { layer: g.layer, v: it.v }), title: `${g.group}: ${it.label}`,
        onclick: () => choosePaint(g.layer, it) }, swatch(it.key, color, it.mark), el("span", { text: it.label }));
    })))));
}

// Choosing a swatch picks up the brush; choosing it again puts the brush down.
function choosePaint(layer, it) {
  const b = it.op ? { layer, op: it.op } : { layer, v: it.v };
  if (S.tool === "brush" && brushKey(b) === brushKey(S.brush)) { setTool("select"); return; }
  S.brush = b;
  setTool("brush");
}

// Fences, gates and stairs are drawn a cell at a time; a 2x2 block of fence makes no sense.
const ONE_CELL = new Set(["Deco:1", "Deco:4", "Features:1"]);
const brushSize = () => (S.tool === "brush" && ONE_CELL.has(brushKey(S.brush)) ? 1 : S.size);
const STAIRS_KEY = "Features:1";

// Stairs only show at the foot of a cliff that faces you: on the cell just south or just east of ground one level up.
// Painting on the top of that cliff steps down to its foot. Returns the cell, or null if no stairs can go here.
function stairsCell(c, r) {
  const m = S.map, H = (cc, rr) => m.layers.Height[rr * m.cols + cc];
  const ok = (cc, rr) => inside(m, cc, rr) && ((rr > 0 && H(cc, rr - 1) === H(cc, rr) + 1) || (cc > 0 && H(cc - 1, rr) === H(cc, rr) + 1));
  if (ok(c, r)) return [c, r];
  for (const [dc, dr] of [[0, 1], [1, 0]]) if (inside(m, c, r) && ok(c + dc, r + dr) && H(c + dc, r + dr) === H(c, r) - 1) return [c + dc, r + dr];
  return null;
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

// ---------- stamps ----------

// A stamp's picture in the current view: the isometric bake when it's isometric (cached on the clip).
function clipPicture(clip) {
  if (S.projection === "iso" && S.isoTs) {
    if (!clip.iso) {
      const m = newMap(clip.cols, clip.rows);
      for (const [k, L] of Object.entries(clip.layers)) if (m.layers[k]) m.layers[k].set(L);
      m.entities = structuredClone(clip.entities);
      const v = isoView(m);
      clip.iso = { canvas: bakeIso(m, S.isoTs, v, { objects: true, frames: [0] })[0], at: v.cellTop(0, 0) };
    }
    return clip.iso.canvas;
  }
  return drawClip(clip, S.ts, S.sprites);
}

function buildStamps() {
  const box = $("stamps");
  const add = el("button", { class: "swatch new-stamp", type: "button", "aria-pressed": String(S.tool === "area"), title: "Drag over part of the map to keep it as a stamp",
    onclick: () => setTool(S.tool === "area" ? "select" : "area") }, el("span", { class: "plus", text: "+" }), el("span", { text: "New stamp" }));
  box.replaceChildren(el("div", { class: "swatches" }, ...S.stamps.map((st, i) => {
    const c = clipPicture(st.clip);
    const t = thumb((g, x, y, w, h) => g.drawImage(c, x, y, w, h), c.width, c.height, 40);
    return el("div", { class: "stamp" },
      el("button", { class: "swatch", type: "button", title: `Stamp: ${st.name}`, "data-stamp": st.name, onclick: () => startPaste(st.clip, st.name) }, t, el("span", { text: st.name })),
      st.builtin ? "" : el("button", { class: "remove", type: "button", title: `Remove ${st.name}`, "aria-label": `Remove ${st.name}`, onclick: () => { S.stamps.splice(i, 1); saveStamps(S.stamps); buildStamps(); sync(); } }, "×"));
  }), add));
}

function startPaste(clip, name) {
  S.pasting = { clip, name, canvas: drawClip(clip, S.ts, S.sprites) };
  setTool("stamp");
}

const pasteAt = (hv) => [hv.c - Math.floor(S.pasting.clip.cols / 2), hv.r - Math.floor(S.pasting.clip.rows / 2)];

// ---------- tools ----------

function setTool(id) {
  S.tool = id;
  if (id !== "place" && id !== "scatter") S.place = null;
  if (id !== "stamp") S.pasting = null;
  if (id !== "area") { S.sel = null; S.selFrom = null; }
  if (id !== "select" && S.selected) S.selected = null;
  sync();
}

// Armed with an object: placing it once, or scattering it (props only).
function arm(p) {
  S.place = p;
  setTool(p.type === "Prop" && S.scatter.on ? "scatter" : "place");
}

// The toolbox, its context options, the pressed states in both panels, and the selection card.
function sync() {
  buildToolbox();
  const paintOn = S.tool === "brush";
  for (const b of $("palette").querySelectorAll("[data-brush]")) b.setAttribute("aria-pressed", String(paintOn && b.dataset.brush === brushKey(S.brush)));
  for (const b of $("catalog").querySelectorAll("[data-obj]")) b.setAttribute("aria-pressed", String(!!S.place && b.dataset.obj === objKey(S.place)));
  for (const b of $("stamps").querySelectorAll("[data-stamp]")) b.setAttribute("aria-pressed", String(S.tool === "stamp" && S.pasting?.name === b.dataset.stamp));
  $("stamps").querySelector(".new-stamp")?.setAttribute("aria-pressed", String(S.tool === "area"));
  $("stage").dataset.tool = S.tool;
  buildCard();
  S.needsDraw = true;
}

function buildToolbox() {
  const kids = [
    el("button", { class: "tbtn sheet", type: "button", "aria-pressed": String($("paint-panel").classList.contains("open")), onclick: () => sheet("left") }, icon("paint"), el("span", { text: "Paint" })),
    el("button", { class: "tbtn sheet", type: "button", "aria-pressed": String($("objects-panel").classList.contains("open")), onclick: () => sheet("right") }, icon("objects"), el("span", { text: "Objects" })),
    el("span", { class: "tdiv sheet-div", hidden: !phone() }),
  ];
  kids.push(chip());
  const opts = options();
  if (opts.length) kids.push(el("span", { class: "tdiv" }), el("span", { class: "opts" }, ...opts));
  $("erase").setAttribute("aria-pressed", String(S.tool === "erase"));
  $("toolbox").replaceChildren(...kids);
}

// What the next click puts down: the swatch, the object or the stamp.
function chip() {
  let pic, text, side = "left";
  if (S.place) {
    pic = S.place.type === "Prop" ? propThumb(S.place.sprite, 32) : S.place.type === "Character" ? charThumb(S.place.sprite, 32) : dataIcon(S.place.type === "Path" ? "path" : "region");
    text = S.place.sprite || S.place.type; side = "right";
  } else if (S.pasting) {
    const c = S.pasting.canvas;
    pic = thumb((g, x, y, w, h) => g.drawImage(c, x, y, w, h), c.width, c.height, 32);
    text = S.pasting.name || "Clipboard";
  } else if (S.tool === "erase") {
    pic = el("span", { class: "chip-empty" }, icon("erase")); text = "Eraser";
  } else if (S.tool === "area") {
    pic = el("span", { class: "chip-empty" }, icon("area")); text = "New stamp";
  } else if (S.tool === "brush") {
    const it = brushItem();
    pic = it ? swatch(it.key, LAYERS[S.brush.layer].values.find((x) => x.v === S.brush.v)?.color, it.mark) : el("canvas", { width: 32, height: 32 });
    text = it?.label || "Paint";
  } else {
    pic = el("span", { class: "chip-empty" }, icon("brush")); text = "Pick a swatch";
  }
  const title = side === "right" ? "What you're placing (opens Objects)" : S.tool === "brush" ? "What you're painting (opens Paint). Esc puts the brush down." : "Choose what to paint (opens Paint)";
  return el("button", { class: S.tool === "select" ? "chip off" : "chip", type: "button", title, onclick: () => reveal(side) }, pic, el("span", { text }));
}

// Only the options that apply to the active tool.
function options() {
  const seg = (items, cur, set, label) => el("span", { class: "seg", role: "group", "aria-label": label }, ...items.map(([v, kids, title]) =>
    el("button", { type: "button", "aria-pressed": String(cur === v), title, onclick: () => set(v) }, kids)));
  switch (S.tool) {
    case "brush":
      if (brushKey(S.brush) === STAIRS_KEY) return [el("span", { text: "At the foot of a cliff that faces you" })];
      if (ONE_CELL.has(brushKey(S.brush))) return [el("span", { text: "One cell at a time" })];
      return ["Size", seg([1, 2, 3].map((n) => [n, sizeIcon(n), `${n}×${n} cells ([ and ]). Shift-click draws a line.`]), S.size, (n) => { S.size = n; sync(); }, "Brush size")];
    case "erase":
      return ["Size", seg([1, 2, 3].map((n) => [n, sizeIcon(n), `${n}×${n} cells ([ and ])`]), S.size, (n) => { S.size = n; sync(); }, "Eraser size")];
    case "area": return [el("span", { text: S.sel ? "Name it in the card, then save" : "Drag over the part to keep · Esc cancels" })];
    case "stamp": return [el("span", { text: "Click to stamp · Esc stops" })];
    case "place":
    case "scatter": {
      const out = [];
      if (S.place?.type === "Prop") {
        out.push("Scatter", seg([[0, "Off"], [0.15, "Few"], [0.35, "Some"], [0.7, "Lots"]].map(([d, l]) => [d, l, d ? `Drag to sprinkle (${l.toLowerCase()})` : "Place one at a time"]),
          S.scatter.on ? S.scatter.density : 0, (d) => { S.scatter.on = !!d; if (d) S.scatter.density = d; setTool(d ? "scatter" : "place"); }, "Scatter"));
      }
      out.push(el("span", { text: S.tool === "scatter" ? "Right-drag clears" : "Shift keeps placing · Esc stops" }));
      return out;
    }
    default: return [];
  }
}

function toggleErase() { setTool(S.tool === "erase" ? "select" : "erase"); }
$("erase").prepend(icon("erase"));
$("erase").addEventListener("click", toggleErase);

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
// The props of the current view (the isometric set has its own buildings).
const propSet = () => (S.projection === "iso" && S.isoTs ? S.isoTs : S.ts);
const propThumb = (name, box) => {
  const ts = propSet(), p = ts.props[name];
  return p ? thumb((g, x, y, w, h) => g.drawImage(ts.propsImg, p.x, p.y, p.w, p.h, x, y, w, h), p.w, p.h, box) : el("canvas", { width: box, height: box });
};
const charThumb = (name, box) => {
  const im = S.sprites[name];
  return im ? thumb((g, x, y, w, h) => g.drawImage(im, x, y, w, h), im.width, im.height, box) : el("canvas", { width: box, height: box });
};
const objKey = (p) => `${p.type}:${p.sprite || ""}`;

function propGroups() {
  const groups = { Houses: [], Market: [], Trees: [], Pines: [], Bushes: [], Rocks: [], Details: [], Things: [] };
  const props = propSet().props;
  for (const name of Object.keys(props)) {
    if (props[name].alias) continue;                         // old names kept so old maps still open
    if (name.startsWith("_")) continue;                       // fences, rails and stairs come from the cells
    const g = name.startsWith("detail") ? "Details" : /^(tree|oak|birch|poplar|willow|maple|blossom|fruit)/.test(name) ? "Trees"
      : /^(pine|spruce|cypress)/.test(name) ? "Pines" : name.startsWith("bush") ? "Bushes"
      : name.startsWith("rock") ? "Rocks" : name.startsWith("stall") || name.startsWith("crate") || name === "flower-cart" || name === "chalkboard" ? "Market"
      : name.startsWith("house") || props[name].foot ? "Houses" : "Things";
    groups[g].push(name);
  }
  return groups;
}

function buildCatalog() {
  const item = (p, label, canvas) => {
    const b = el("button", { class: "swatch", type: "button", "data-obj": objKey(p), "data-name": `${p.sprite || ""} ${label}`.toLowerCase(), title: p.sprite || label }, canvas, el("span", { text: label }));
    b.addEventListener("pointerdown", (ev) => dndStart(ev, p, canvas));
    b.addEventListener("click", () => { if (S.dnd?.done) return; if (S.place && objKey(S.place) === objKey(p)) setTool("select"); else arm(p); if (phone()) sheet(null); });
    return b;
  };
  const sec = (title, kids) => el("details", { class: "sec", open: true }, el("summary", { text: title }), el("div", { class: "swatches" }, ...kids));
  const sections = [];
  if (S.spriteNames.length) sections.push(sec("Characters", S.spriteNames.map((n) => item({ type: "Character", sprite: n }, n, charThumb(n, 40)))));
  for (const [g, names] of Object.entries(propGroups())) {
    if (names.length) sections.push(sec(g, names.map((n) => item({ type: "Prop", sprite: n }, n.replace(/^(tree|bush|rock|house|detail)-/, "").replace(/-iso$/, ""), propThumb(n, 40)))));
  }
  $("catalog").replaceChildren(...sections);
  filterCatalog();
}

function filterCatalog() {
  const q = $("obj-search").value.trim().toLowerCase();
  for (const d of $("catalog").querySelectorAll("details")) {
    let any = false;
    for (const b of d.querySelectorAll("[data-obj]")) { const ok = !q || b.dataset.name.includes(q); b.hidden = !ok; any ||= ok; }
    d.hidden = !any;
    if (q && any) d.open = true;
  }
}
$("obj-search").addEventListener("input", filterCatalog);

function dataIcon(kind) {
  const c = el("canvas", { width: 40, height: 40, "aria-hidden": "true" });
  const g = c.getContext("2d");
  g.strokeStyle = kind === "path" ? ENTITIES.Path.color : ENTITIES.Region.color;
  g.lineWidth = 2;
  if (kind === "path") { g.beginPath(); g.moveTo(6, 32); g.lineTo(18, 14); g.lineTo(34, 22); g.stroke(); for (const [x, y] of [[6, 32], [18, 14], [34, 22]]) g.strokeRect(x - 2, y - 2, 4, 4); }
  else { g.setLineDash([4, 3]); g.strokeRect(6, 8, 28, 24); }
  return c;
}

// ---------- drag and drop from the Objects panel ----------
// Pointer events rather than HTML drag and drop, so the map can show the object where it will land.

function dndStart(ev, p, canvas) {
  if (ev.button !== 0 || ev.pointerType === "touch") return;
  ev.preventDefault();                                     // no text selection while dragging
  S.dnd = { p, x: ev.clientX, y: ev.clientY, live: false, done: false, src: canvas.toDataURL(), was: { tool: S.tool, place: S.place, pasting: S.pasting } };
}

window.addEventListener("pointermove", (ev) => {
  const d = S.dnd;
  if (!d || d.done) return;
  if (!d.live) {
    if (Math.hypot(ev.clientX - d.x, ev.clientY - d.y) < 5) return;
    d.live = true;
    $("ghost").src = d.src;
    S.place = d.p; S.tool = "place"; S.pasting = null;
  }
  const over = document.elementFromPoint(ev.clientX, ev.clientY) === canvas;
  $("ghost").hidden = over;
  $("ghost").style.left = `${ev.clientX}px`; $("ghost").style.top = `${ev.clientY}px`;
  S.hover = over ? toMap(ev) : null;
  S.needsDraw = true;
});

window.addEventListener("pointerup", (ev) => {
  const d = S.dnd;
  if (!d) return;
  if (!d.live) { S.dnd = null; return; }
  d.done = true;
  $("ghost").hidden = true;
  setTimeout(() => { if (S.dnd === d) S.dnd = null; }, 0);   // the click that follows a drop is not a pick
  const over = document.elementFromPoint(ev.clientX, ev.clientY) === canvas;
  S.tool = d.was.tool; S.place = d.was.place; S.pasting = d.was.pasting;
  if (over && placeFrom(ev, d.p)) { setTool("select"); select(S.selected); }
  else sync();
});

// ---------- entities ----------

const cellCentre = ([c, r]) => [c * T + T / 2, r * T + T / 2];

// The view: how map pixels (u, v), cells and objects land on the screen. Top-down is the identity; isometric is
// js/iso.js. Everything that draws or picks goes through S.V.
function orthoView(m) {
  return {
    iso: false, W: m.cols * T, H: m.rows * T,
    pt: (u, v) => [u, v],
    feet: (e) => [e.x, e.y],
    cellTop: (c, r) => [c * T, r * T],
    cellPoly: (c, r) => [[c * T, r * T], [(c + 1) * T, r * T], [(c + 1) * T, (r + 1) * T], [c * T, (r + 1) * T]],
    pick: (x, y) => ({ c: Math.floor(x / T), r: Math.floor(y / T), u: x, v: y }),
    border: () => [[0, 0], [m.cols * T, 0], [m.cols * T, m.rows * T], [0, m.rows * T]],
  };
}

function makeView() {
  const m = S.map;
  if (S.projection !== "iso" || !S.isoTs) return orthoView(m);
  const v = isoView(m, { margin: S.show.margin ? 6 : 0 });
  const lvl = (u, vv) => m.layers.Height[Math.min(m.rows - 1, Math.max(0, Math.floor(vv / T))) * m.cols + Math.min(m.cols - 1, Math.max(0, Math.floor(u / T)))];
  return {
    ...v,
    pt: (u, vv) => v.toScreen(u, vv, lvl(u, vv)),
    feet: (e) => v.feet(e, lvl(e.x, e.y - 1)),
    cellPoly: (c, r) => v.cellPoly(c, r, (inside(m, c, r) && m.layers.Height[r * m.cols + c]) || 0),
    pick: (x, y) => v.pick(x, y, m),
    border: () => [v.cellTop(0, 0), v.cellTop(m.cols, 0), v.cellTop(m.cols, m.rows), v.cellTop(0, m.rows)],
  };
}

// A new view after the map changed shape (grew, a new top level, the margin): the cell that was (0, 0) is now
// (dc, dr), and it stays where it was on screen.
function rebuildView(dc = 0, dr = 0) {
  const old = S.V;
  S.V = makeView();
  if (!old || old.iso !== S.V.iso) return;
  const [ax, ay] = old.cellTop(0, 0), [bx, by] = S.V.cellTop(dc, dr);
  S.ox += (ax - bx) * S.zoom; S.oy += (ay - by) * S.zoom;
}

function poly(g, pts) { g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); }

// Where an object's picture sits, in view pixels: [left, top, width, height] (whole pixels, as it's drawn).
function bounds(e) {
  if (e.type === "Prop") {
    const p = (S.V.iso ? S.isoTs : S.ts).props[e.fields.sprite] || { w: T, h: T };
    const [x, y] = S.V.feet(e);
    return p.ax !== undefined ? [Math.round(x - p.ax), Math.round(y - p.ay), p.w, p.h] : [Math.round(x - p.w / 2), Math.round(y - p.h), p.w, p.h];
  }
  if (e.type === "Character") { const im = S.sprites[e.fields.sprite]; const w = im?.width || T, h = im?.height || T; const [x, y] = S.V.feet(e); return [Math.round(x - w / 2), Math.round(y - h), w, h]; }
  const pts = e.type === "Region" ? [S.V.pt(e.x, e.y), S.V.pt(e.x + (e.w || T), e.y), S.V.pt(e.x + (e.w || T), e.y + (e.h || T)), S.V.pt(e.x, e.y + (e.h || T))]
    : (e.fields.points || []).map(cellCentre).map(([u, v]) => S.V.pt(u, v));
  if (!pts.length) { const [x, y] = S.V.pt(e.x, e.y); return [x, y, T, T]; }
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return [Math.min(...xs) - 4, Math.min(...ys) - 4, Math.max(...xs) - Math.min(...xs) + 8, Math.max(...ys) - Math.min(...ys) + 8];
}

// Is the picture solid near (sx, sy)? Sprites are mostly see-through, so a click has to land on paint, give or take
// two pixels. The alpha of each sheet is read once.
const alphas = new Map();
function solid(img, x0, y0, w, h, sx, sy) {
  let a = alphas.get(img);
  if (a === undefined) {
    try {
      const c = el("canvas", { width: img.width, height: img.height }), g = c.getContext("2d", { willReadFrequently: true });
      g.drawImage(img, 0, 0);
      a = { w: img.width, d: g.getImageData(0, 0, img.width, img.height).data };
    } catch { a = null; }
    alphas.set(img, a);
  }
  if (!a) return true;
  for (const dy of [0, -2, 2]) for (const dx of [0, -2, 2]) {
    const x = sx + dx, y = sy + dy;
    if (x >= 0 && y >= 0 && x < w && y < h && a.d[((y0 + y) * a.w + x0 + x) * 4 + 3] > 24) return true;
  }
  return false;
}

// What's under the pointer: sprites by their painted pixels on screen (wx, wy), paths and regions by map pixels.
function hit(p) {
  const { mx, my, wx, wy } = p;
  const sprites = S.map.entities.filter((e) => (e.type === "Prop" && S.show.props) || (e.type === "Character" && S.show.characters))
    .sort((a, b) => (S.V.iso ? (b.x + b.y) - (a.x + a.y) : b.y - a.y));
  for (const e of sprites) {
    const [x, y, w, h] = bounds(e);
    if (wx < x - 2 || wx >= x + w + 2 || wy < y - 2 || wy >= y + h + 2) continue;
    const lx = Math.floor(wx - x), ly = Math.floor(wy - y);
    if (e.type === "Prop") {
      const ts = S.V.iso ? S.isoTs : S.ts, pr = ts.props[e.fields.sprite];
      if (!pr || solid(ts.propsImg, pr.x, pr.y, pr.w, pr.h, lx, ly)) return e;
    } else {
      const im = S.sprites[e.fields.sprite];
      if (!im || solid(im, 0, 0, im.width, im.height, lx, ly)) return e;
    }
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

// ---------- the map grows when you paint past its edge ----------

// Can the map grow to reach this cell?
const near = (c, r) => Math.max(S.map.cols, c + 1) - Math.min(0, c) <= MAX_SIZE && Math.max(S.map.rows, r + 1) - Math.min(0, r) <= MAX_SIZE;

// Grow the map so cells c0..c1, r0..r1 fit (up to MAX_SIZE). Returns true if it grew.
function growTo(c0, r0, c1, r1) {
  const m = S.map;
  let room = MAX_SIZE - m.cols;
  const l = Math.min(Math.max(0, -c0), room); room -= l;
  const rt = Math.min(Math.max(0, c1 - m.cols + 1), room);
  room = MAX_SIZE - m.rows;
  const t = Math.min(Math.max(0, -r0), room); room -= t;
  const b = Math.min(Math.max(0, r1 - m.rows + 1), room);
  if (!(l || t || rt || b)) return false;
  const oldCols = m.cols;
  grow(m, l, t, rt, b);
  const mv = (a) => a && [a[0] + l, a[1] + t];               // cells in flight move with the map
  if (S.stroke) {
    S.stroke.rectFrom = mv(S.stroke.rectFrom); S.stroke.last = mv(S.stroke.last); S.stroke.changed = true;
    S.stroke.touched = new Set([...S.stroke.touched].map((i) => (((i / oldCols) | 0) + t) * m.cols + (i % oldCols) + l));
  }
  S.lastCell = mv(S.lastCell); S.selFrom = mv(S.selFrom);
  rebuildView(l, t);
  S.terrainDirty = true;
  return true;
}

// The cells a brush of the current size covers around (c, r), even off the map.
function footprint(c, r) {
  const n = brushSize(), lo = -Math.floor((n - 1) / 2);
  return [c + lo, r + lo, c + lo + n - 1, r + lo + n - 1];
}

// Grow for the pointer if it's just off the map with a tool that paints there; returns the fresh map point.
function growFor(ev, p) {
  if (inside(S.map, p.c, p.r) || !near(p.c, p.r)) return p;
  const box = S.tool === "brush" ? footprint(p.c, p.r) : [p.c, p.r, p.c, p.r];
  return growTo(...box) ? toMap(ev) : p;
}

// ---------- placing ----------

// Put one object where the pointer is (growing the map if that's just off it). Returns false if it's too far out.
function placeFrom(ev, p) {
  let q = toMap(ev);
  if (!near(q.c, q.r)) return false;
  history.push(S.map);
  if (!inside(S.map, q.c, q.r)) { growTo(q.c, q.r, q.c, q.r); q = toMap(ev); }
  const { mx, my, free } = q, c = Math.floor(mx / T), r = Math.floor(my / T);
  let e;
  if (p.type === "Prop") { const [x, y] = snapFeet(mx, my, free); e = { type: "Prop", x, y, w: T, h: T, fields: { sprite: p.sprite } }; }
  else if (p.type === "Character") {
    const [x, y] = snapFeet(mx, my, free);
    e = { type: "Character", x, y, w: T, h: T, fields: { id: p.sprite.split("-")[0], sprite: p.sprite, perch: null, flyTo: null, path: [] } };
  } else if (p.type === "Region") e = { type: "Region", x: c * T, y: r * T, w: 2 * T, h: 2 * T, fields: { name: "region" } };
  else e = { type: "Path", x: c * T, y: r * T, w: T, h: T, fields: { name: "path", points: [[c, r], [Math.min(S.map.cols - 1, c + 3), r]] } };
  S.map.entities.push(e);
  land(e);
  S.selected = e;
  changed(false);
  return true;
}

// ---------- scatter ----------

// Props in the same family as `name` (tree-3-d1 -> every tree-N-d1), to vary what gets scattered.
function family(name) {
  const m = name.match(/^(.*?)-\d+(-d\d)?$/);
  if (!m) return [name];
  const re = new RegExp(`^${m[1]}-\\d+${m[2] || ""}$`);
  return Object.keys(propSet().props).filter((n) => re.test(n) && !propSet().props[n].alias);
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
  if (st.changed && S.V?.iso) S.terrainDirty = true;
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
    const [x, y] = S.V.pt(p.x + Math.cos(p.a) * d, p.y + Math.sin(p.a) * d * 0.6);
    g.globalAlpha = 0.75 * (1 - k);
    g.fillStyle = "#f6ecd2";
    g.beginPath(); g.arc(x, y, 2.2 * (1 - k * 0.5), 0, Math.PI * 2); g.fill();
  }
  g.globalAlpha = 1;
}

// ---------- the selection card ----------

function select(e) { S.selected = e; sync(); }

function edit(fn) {
  return (ev) => { history.push(S.map); fn(ev.target.value, ev.target); changed(S.selected?.type === "Region"); buildCard(true); };
}

let cardFor = null;
function buildCard(force = false) {
  const box = $("selcard"), e = S.selected;
  if (e && !S.map.entities.includes(e)) S.selected = null;
  const key = S.selected || (S.sel && !S.selFrom ? `${S.sel.c0},${S.sel.r0},${S.sel.c1},${S.sel.r1}` : null);
  if (key === cardFor && !force) return;
  cardFor = key;
  if (!key) { box.hidden = true; box.replaceChildren(); return; }
  box.hidden = false;
  const close = el("button", { class: "ib", type: "button", "aria-label": "Close", title: "Close (Esc)", onclick: () => { if (S.tool === "area") setTool("select"); else select(null); } }, icon("x"));
  if (!S.selected) {
    const w = S.sel.c1 - S.sel.c0 + 1, h = S.sel.r1 - S.sel.r0 + 1;
    const name = el("input", { id: "stamp-name", placeholder: "e.g. house with yard", value: "" });
    box.replaceChildren(
      el("div", { class: "inspect-head" }, el("div", {}, el("b", { text: "New stamp" }), el("small", { text: `${w} × ${h} cells` })), close),
      el("div", { class: "field" }, el("label", { for: "stamp-name", text: "name" }), name),
      el("div", { class: "row" }, el("button", { class: "btn pri", type: "button", text: "Save stamp", onclick: () => {
        const n = name.value.trim() || `stamp ${S.stamps.length + 1}`;
        S.stamps.push({ name: n, clip: copyArea(S.map, S.sel) });
        toast(saveStamps(S.stamps) ? `Saved the stamp "${n}"` : "This browser can't keep stamps; it will be gone after a reload");
        buildStamps(); setTool("select");
      } })));
    placeCard();
    name.focus();
    return;
  }
  const head = el("div", { class: "inspect-head" },
    e.type === "Prop" ? propThumb(e.fields.sprite, 36) : e.type === "Character" ? charThumb(e.fields.sprite, 36) : dataIcon(e.type === "Path" ? "path" : "region"),
    el("div", {}, el("b", { text: ENTITIES[e.type].label }), el("small", { text: e.fields.sprite || e.fields.name || "" })), close);
  const rows = [head];
  if (e.type === "Path" || e.type === "Region") {
    rows.push(el("div", { class: "field" }, el("label", { for: "f-name", text: "name" }),
      el("input", { id: "f-name", value: e.fields.name || "", onchange: edit((v) => { e.fields.name = v.trim(); }) })));
  }
  rows.push(el("div", { class: "row" },
    el("button", { class: "btn quiet", type: "button", onclick: duplicate }, icon("dup"), "Duplicate"),
    el("button", { class: "btn danger", type: "button", "aria-label": "Delete", title: "Delete (Del)", onclick: removeSelected }, icon("trash"))));
  box.replaceChildren(...rows);
  placeCard();
}

// Beside the selection, on whichever side has room, with its pointer at the selection's middle.
function placeCard() {
  const box = $("selcard");
  if (box.hidden || !S.V) return;
  let b;
  if (S.selected) b = bounds(S.selected);
  else if (S.sel) {
    const pts = [[S.sel.c0, S.sel.r0], [S.sel.c1 + 1, S.sel.r0], [S.sel.c1 + 1, S.sel.r1 + 1], [S.sel.c0, S.sel.r1 + 1]].map(([c, r]) => S.V.pt(c * T, r * T));
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    b = [Math.min(...xs), Math.min(...ys), Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)];
  } else return;
  const busy = S.drag?.moved || S.stroke || S.panning || S.pinch;
  box.style.visibility = busy ? "hidden" : "";
  const st = $("stage"), sw = st.clientWidth, sh = st.clientHeight, W = box.offsetWidth, H = box.offsetHeight;
  const cs = getComputedStyle(st), lw = phone() ? 0 : parseFloat(cs.getPropertyValue("--lw")) || 0, rw = phone() ? 0 : parseFloat(cs.getPropertyValue("--rw")) || 0;
  const x0 = S.ox + b[0] * S.zoom, y0 = S.oy + b[1] * S.zoom, x1 = x0 + b[2] * S.zoom, y1 = y0 + b[3] * S.zoom, my = (y0 + y1) / 2;
  let left = x1 + 14, side = "right";
  if (left + W > sw - rw - 8) { left = x0 - 14 - W; side = "left"; }
  if (left < lw + 8) { left = Math.min(sw - W - 8, Math.max(lw + 8, x1 + 14)); side = "none"; }
  const top = Math.min(Math.max(72, my - 40), Math.max(72, sh - H - 84));       // clear of the top pill and the bottom row
  box.dataset.side = my - top < 14 || my - top > H - 14 ? "none" : side;
  box.style.left = `${Math.round(left)}px`; box.style.top = `${Math.round(top)}px`;
  box.style.setProperty("--ay", `${Math.round(my - top)}px`);
}

function duplicate() {
  const e = S.selected; if (!e) return;
  history.push(S.map);
  const copy = structuredClone(e); delete copy.iid;
  copy.x += T;
  if (copy.fields.points) copy.fields.points = copy.fields.points.map(([c, r]) => [c + 1, r]);
  S.map.entities.push(copy);
  land(copy);
  select(copy); changed(false);
}

function removeSelected() {
  const e = S.selected; if (!e) return;
  puff(e.x, e.y);
  history.push(S.map);
  S.map.entities = S.map.entities.filter((x) => x !== e);
  select(null); changed(false);
}

function nudge(dx, dy) {
  const e = S.selected;
  history.push(S.map);
  e.x += dx; e.y += dy;
  if (e.type === "Path" && e.fields.points && dx % T === 0 && dy % T === 0) e.fields.points = e.fields.points.map(([c, r]) => [c + dx / T, r + dy / T]);
  changed(e.type === "Region"); buildCard(true);
}

// ---------- drawing ----------

const canvas = $("view"), ctx = canvas.getContext("2d");

function bake() {
  rebuildView();
  if (S.V.iso) {
    // while painting, only the first frame; the other two follow once things are quiet
    const quick = S.stroke || S.drag || S.scatterStroke;
    if (quick) {
      S.frames = bakeIso(S.map, S.isoTs, S.V, { objects: S.show.props, woods: false, frames: [0] }).slice(0, 1);
      S.restDirty = true;
    } else S.frames = bakeIso(S.map, S.isoTs, S.V, { objects: S.show.props, woods: false });
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
  if (S.show.terrain) grassEverywhere(W, H);
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
  drawSprites(ctx, sprites);
  if (S.fx.length) drawFx(ctx, performance.now());
  if (S.fx.length || S.squash.size) S.needsDraw = true;

  const line = (w) => { ctx.lineWidth = w / S.zoom; };
  if (S.show.data) {
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

  const hv = S.hover;
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
  if (hv && !S.panning && !S.pinch) {
    if (S.tool === "select" && !S.drag) {
      const e = hit(hv);
      if (e && e !== sel) { const [x, y, w, h] = bounds(e); ctx.strokeStyle = "rgba(232,103,58,0.55)"; line(1.5); ctx.strokeRect(x - 1, y - 1, w + 2, h + 2); }
    } else if (S.tool === "brush" || S.tool === "erase") {
      const n = brushSize(), shiftLine = !S.stroke && hv.free && S.lastCell, erasing = S.tool === "erase";
      let cells = shiftLine ? lineCells(S.lastCell[0], S.lastCell[1], hv.c, hv.r).flatMap(([c, r]) => brushCells(S.map, c, r, n))
        : inside(S.map, hv.c, hv.r) ? brushCells(S.map, hv.c, hv.r, n) : [];
      let off = false, bad = false;
      if (!S.stroke && !erasing && !inside(S.map, hv.c, hv.r) && near(hv.c, hv.r)) {      // past the edge: this grows the map
        const [c0, r0, c1, r1] = footprint(hv.c, hv.r);
        cells = []; off = true;
        for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) cells.push([c, r]);
      } else if (!erasing && brushKey(S.brush) === STAIRS_KEY && cells.length) {   // where the stairs will land, or red where they can't
        const at = stairsCell(hv.c, hv.r);
        if (at) cells = [at]; else bad = true;
      }
      ctx.strokeStyle = bad ? "rgba(232,72,58,0.95)" : erasing ? "rgba(240,138,98,0.95)" : "rgba(255,255,255,0.9)"; line(1.5);
      if (erasing && !S.stroke) {                                                // what goes with it: whole objects, outlined
        const set = new Set(cells.map(([c, r]) => `${c},${r}`)), under = hit(hv);
        for (const e of S.map.entities) if ((e.type === "Prop" || e.type === "Character") && (e === under || cellsOf(e).some(([c, r]) => set.has(`${c},${r}`)))) { const [x, y, w, h] = bounds(e); ctx.strokeRect(x - 1, y - 1, w + 2, h + 2); }
      }
      if (off || bad) ctx.setLineDash([3 / S.zoom, 3 / S.zoom]);
      for (const [c, r] of cells) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
      ctx.setLineDash([]);
    } else if (S.tool === "scatter") {
      ctx.strokeStyle = "rgba(255,255,255,0.9)"; line(1.5); ctx.setLineDash([3 / S.zoom, 3 / S.zoom]);
      for (const [c, r] of brushCells(S.map, hv.c, hv.r, 3)) { poly(ctx, V.cellPoly(c, r)); ctx.stroke(); }
      ctx.setLineDash([]);
    } else if (S.tool === "place" && S.place && near(hv.c, hv.r)) {
      if (S.place.type === "Prop" || S.place.type === "Character") {
        const [x, y] = snapFeet(hv.mx, hv.my, hv.free);
        ctx.globalAlpha = 0.7;
        drawSprites(ctx, [{ type: S.place.type, x, y, fields: { sprite: S.place.sprite } }]);
        ctx.globalAlpha = 1;
      } else { ctx.strokeStyle = ENTITIES[S.place.type].color; line(2); poly(ctx, V.cellPoly(hv.c, hv.r)); ctx.stroke(); }
    }
  }
  const area4 = (c0, r0, c1, r1) => [V.pt(c0 * T, r0 * T), V.pt((c1 + 1) * T, r0 * T), V.pt((c1 + 1) * T, (r1 + 1) * T), V.pt(c0 * T, (r1 + 1) * T)];
  if (S.sel) {
    const { c0, r0, c1, r1 } = S.sel;
    ctx.fillStyle = "rgba(58,118,240,0.12)"; poly(ctx, area4(c0, r0, c1, r1)); ctx.fill();
    ctx.strokeStyle = "#3a76f0"; line(2); ctx.setLineDash([4 / S.zoom, 3 / S.zoom]); ctx.stroke(); ctx.setLineDash([]);
  }
  if (S.tool === "stamp" && S.pasting && hv) {
    const [c0, r0] = pasteAt(hv), clip = S.pasting.clip;
    ctx.globalAlpha = 0.8;
    if (!V.iso) ctx.drawImage(S.pasting.canvas, c0 * T, r0 * T);
    else { clipPicture(clip); const [dx, dy] = V.cellTop(c0, r0); ctx.drawImage(clip.iso.canvas, dx - clip.iso.at[0], dy - clip.iso.at[1]); }
    ctx.globalAlpha = 1;
    const corners = V.iso ? [V.cellTop(c0, r0), V.cellTop(c0 + clip.cols, r0), V.cellTop(c0 + clip.cols, r0 + clip.rows), V.cellTop(c0, r0 + clip.rows)] : area4(c0, r0, c0 + clip.cols - 1, r0 + clip.rows - 1);
    poly(ctx, corners); ctx.strokeStyle = "#3a76f0"; line(2); ctx.setLineDash([4 / S.zoom, 3 / S.zoom]); ctx.stroke(); ctx.setLineDash([]);
  }
  placeCard();
}

// The grass runs on forever round the map: one tile of the grass pattern (it repeats every grassN cells: in
// isometric 16 * grassN x 8 * grassN px), laid under the whole screen and lined up with the map's own grass.
const grassTiles = {};
function grassPattern(iso) {
  if (grassTiles[iso]) return grassTiles[iso];
  const ts = iso ? S.isoTs : S.ts, n = ts.json.grassN || (iso ? 4 : 11);
  const c = el("canvas", { width: iso ? 16 * n : n * T, height: iso ? 8 * n : n * T }), g = c.getContext("2d");
  if (iso) {
    for (let u = -4; u <= n + 2; u++) for (let v = -4; v <= n + 2; v++) {  // u = c - r, v = c + r: the diamonds round the tile
      if ((u + v) & 1) continue;
      const col = (u + v) / 2, row = (v - u) / 2, xy = ts.json.grass[grassPhase(ts, col, row)];
      g.drawImage(ts.sheet, xy[0], xy[1], 32, 16, u * 16 - 16, v * 8, 32, 16);
    }
  } else {
    for (let r = 0; r < n; r++) for (let col = 0; col < n; col++) {
      const xy = topGrass(ts, col, r);
      g.drawImage(ts.sheet, xy[0], xy[1], T, T, col * T, r * T, T, T);
    }
  }
  return (grassTiles[iso] = ctx.createPattern(c, "repeat"));
}
function grassEverywhere(W, H) {
  const V = S.V, p = grassPattern(V.iso), [x0, y0] = V.iso ? V.cellTop(0, 0, groundLevel(S.map)) : [0, 0];
  p.setTransform(new DOMMatrix([1, 0, 0, 1, x0, y0]));
  ctx.fillStyle = p;
  ctx.fillRect(-S.ox / S.zoom, -S.oy / S.zoom, W / S.zoom, H / S.zoom);
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
    if (S.stroll) strollFrame();
    if (S.show.terrain && !reduceMotion && now - lastTick > S.ts.frameMs) { lastTick = now; S.frame = (S.frame + 1) % S.ts.frames; S.needsDraw = true; }
    if (S.needsDraw) draw();
  }
  requestAnimationFrame(loop);
}

// ---------- view: zoom and pan ----------

// 100% is the map fitted to the screen (S.fit), whatever its pixel scale.
const showZoom = () => { $("zoom-level").textContent = `${Math.round((S.zoom / (S.fit || S.zoom)) * 100)}%`; };
function zoomTo(z, sx, sy) {
  const r = canvas.getBoundingClientRect();
  sx ??= r.width / 2; sy ??= r.height / 2;
  z = Math.min(12, Math.max(0.2, z));
  const mx = (sx - S.ox) / S.zoom, my = (sy - S.oy) / S.zoom;
  S.zoom = z; S.ox = sx - mx * z; S.oy = sy - my * z;
  showZoom();
  S.needsDraw = true;
}
const stepZoom = (dir) => {
  const f = S.fit || S.zoom, rel = S.zoom / f, i = STEPS.findIndex((z) => z >= rel - 1e-6);
  const next = dir > 0 ? STEPS[Math.min(STEPS.length - 1, i < 0 ? STEPS.length - 1 : STEPS[i] > rel + 1e-6 ? i : i + 1)] : STEPS[Math.max(0, (i < 0 ? STEPS.length : i) - 1)];
  zoomTo(next * f);
};
// Fit the map into the room between the panels and above the toolbox.
function fit() {
  const r = canvas.getBoundingClientRect();
  if (r.width < 60 || r.height < 60) { requestAnimationFrame(fit); return; }   // not laid out yet
  S.V = makeView();
  const cs = getComputedStyle($("stage")), lw = parseFloat(cs.getPropertyValue("--lw")) || 0, rw = parseFloat(cs.getPropertyValue("--rw")) || 0;
  const top = phone() ? 56 : 70, bottom = phone() ? 70 : 76, w = r.width - lw - rw, h = r.height - top - bottom;
  const MW = S.V.W, MH = S.V.H;
  const best = Math.min((w - 24) / MW, (h - 24) / MH);
  const z = best >= 1 ? ZOOMS.filter((x) => x <= best).pop() : Math.max(0.2, Math.floor(best * 20) / 20);   // whole steps when it's big enough
  S.zoom = S.fit = z; S.ox = Math.round(lw + (w - MW * z) / 2); S.oy = Math.round(top + (h - MH * z) / 2);
  showZoom();
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
  const [c0, r0] = S.stroke.last || [p.c, p.r];
  S.stroke.last = [p.c, p.r];
  return lineCells(c0, r0, p.c, p.r).flatMap(([c, r]) => brushCells(S.map, c, r, brushSize()));
}

// Alt-click (or a long press): the swatch for what's in that cell.
function pickAt(p) {
  if (!inside(S.map, p.c, p.r)) return;
  for (const g of [...PALETTE].reverse()) {
    const v = S.map.layers[g.layer][p.r * S.map.cols + p.c];
    if (v && g.items.some((it) => it.v === v)) { S.brush = { layer: g.layer, v }; break; }
    if (g.layer === "Terrain") S.brush = { layer: "Terrain", v: 0 };
  }
  setTool("brush");
}

function beginPaint(ev, erase, pick, line) {
  let p = toMap(ev);
  if (pick) { pickAt(p); return; }
  history.push(S.map);
  S.stroke = erase ? { erase: true, ground: groundLevel(S.map), touched: new Set(), changed: false }
    : { v: S.brush.v, op: S.brush.op, target: 0, touched: new Set(), changed: false, roomed: false };
  if (!erase) p = growFor(ev, p);
  S.stroke.target = inside(S.map, p.c, p.r) ? S.map.layers.Height[p.r * S.map.cols + p.c] : 0;
  if (line && S.lastCell) S.stroke.last = S.lastCell;      // Shift: a straight line from the last stroke
  applyStroke(p);
}

// The cells an object stands on: a building's whole footprint (ending at its front cell), or the cell at its feet.
function cellsOf(e) {
  const c = Math.floor(e.x / T), r = Math.floor((e.y - 1) / T), foot = e.type === "Prop" && propSet().props[e.fields.sprite]?.foot;
  if (!foot) return [[c, r]];
  const out = [];
  for (let rr = r - foot[1] + 1; rr <= r; rr++) for (let cc = c - foot[0] + 1; cc <= c; cc++) out.push([cc, rr]);
  return out;
}

// The eraser takes everything from these cells: ground, fences, stairs, hills and pits (back to the ground level), and
// every prop or character standing on them, all of it. Paths and regions are data and stay.
function eraseCells(cells, at) {
  const st = S.stroke, m = S.map;
  let ch = false;
  for (const L of ["Terrain", "Features", "Deco"]) ch = paint(m, L, 0, cells) || ch;
  ch = shapeHeight(m, cells, "flat", st.ground, MAX_LEVEL, st.touched) || ch;
  const hitCells = new Set(cells.map(([c, r]) => `${c},${r}`)), under = at && hit(at);
  const keep = m.entities.filter((e) => {
    if (e.type !== "Prop" && e.type !== "Character") return true;
    const gone = e === under || cellsOf(e).some(([c, r]) => hitCells.has(`${c},${r}`));
    if (gone) puff(e.x, e.y);
    return !gone;
  });
  if (keep.length !== m.entities.length) { m.entities = keep; ch = true; if (S.selected && !keep.includes(S.selected)) S.selected = null; }
  return ch;
}

// Paint cells with the brush's value, or shape the height.
function apply(cells, at) {
  const st = S.stroke, m = S.map, H = m.layers.Height;
  if (st.erase) return eraseCells(cells, at);
  if (st.op === "lower" && !st.roomed && cells.some(([c, r]) => !H[r * m.cols + c])) {
    // digging below the bottom level: lift the whole map one level first (it looks the same; the meadow round it
    // follows the ground), so the dug cells can go down to where the ground was
    st.roomed = true;
    if (Math.max(...H) < MAX_LEVEL) { for (let i = 0; i < H.length; i++) H[i]++; st.target++; st.changed = true; }
    else toast("No room to dig: the highest ground is already at the top level");
  }
  if (!st.op && st.v && brushKey(S.brush) === STAIRS_KEY) {          // stairs step to the foot of the cliff
    const seen = new Set();
    cells = cells.map(([c, r]) => stairsCell(c, r)).filter((at) => at && !seen.has(at.join()) && seen.add(at.join()));
  }
  return st.op ? shapeHeight(m, cells, st.op, st.target, MAX_LEVEL, st.touched) : paint(m, S.brush.layer, st.v, cells);
}

function applyStroke(p) {
  if (!S.stroke) return;
  if (apply(strokeCells(p), p)) { S.stroke.changed = true; S.terrainDirty = true; }
  if (S.stroke.roomed) S.terrainDirty = true;
}

function endPaint(p) {
  const st = S.stroke;
  if (!st) return;
  S.stroke = null;
  const H = S.map.layers.Height, low = Math.min(...H);
  if ((st.op || st.erase) && low > 0) { for (let i = 0; i < H.length; i++) H[i] -= low; st.changed = true; }   // nothing left down at 0: settle back, keeping room to dig
  if (p) S.lastCell = [p.c, p.r];
  if (st.changed) changed(true); else history.drop();
}

// Put the map back as the last snapshot had it, keeping the screen still if the map shrinks back.
function restore(fn) {
  S.stroll = null;                                           // a walk in progress is already one undo step; let it go
  const s0 = S.map.shift || [0, 0];
  if (!fn()) return false;
  const s1 = S.map.shift || [0, 0];
  rebuildView(s1[0] - s0[0], s1[1] - s0[1]);
  S.terrainDirty = true;
  return true;
}

function cancelStroke() {
  const back = () => { restore(() => history.undo(S.map)); history.future = []; };
  if (S.scatterStroke) { if (S.scatterStroke.changed) back(); else history.drop(); S.scatterStroke = null; }
  if (S.stroke) { if (S.stroke.changed) back(); else history.drop(); S.stroke = null; }
  if (S.drag) { if (S.drag.moved) { back(); select(null); } else history.drop(); S.drag = null; }
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
  if (phone()) sheet(null);
  let p = toMap(ev);
  if (ev.button === 1 || S.spaceDown) { S.panning = { x: ev.clientX, y: ev.clientY, ox: S.ox, oy: S.oy }; $("stage").classList.add("pan"); return; }
  const tool = S.tool;
  if (tool === "stamp") {
    if (ev.button === 2) { setTool("select"); return; }
    if (!near(p.c, p.r)) return;
    history.push(S.map);
    let [c0, r0] = pasteAt(p);
    if (growTo(c0, r0, c0 + S.pasting.clip.cols - 1, r0 + S.pasting.clip.rows - 1)) { p = toMap(ev); [c0, r0] = pasteAt(p); }
    pasteArea(S.map, S.pasting.clip, c0, r0);
    changed(true);
  } else if (tool === "area") {
    S.selFrom = [p.c, p.r]; S.sel = inside(S.map, p.c, p.r) ? area(S.selFrom, S.selFrom) : null; sync();
  } else if (tool === "brush" || tool === "erase") {
    beginPaint(ev, ev.button === 2 || tool === "erase", ev.altKey && tool === "brush", ev.shiftKey);
    if (ev.pointerType === "touch") {                                // hold still to pick instead of paint
      const at = { x: ev.clientX, y: ev.clientY };
      S.longPress = { at, timer: setTimeout(() => { cancelStroke(); pickAt(toMap(ev)); toast("Picked what was there"); S.longPress = null; }, 500) };
    }
  } else if (tool === "scatter") {
    history.push(S.map);
    S.scatterStroke = { done: new Set(), changed: false, erase: ev.button === 2 };
    scatterAt(p, S.scatterStroke.erase);
  } else if (tool === "place") {
    if (ev.button === 2) { setTool("select"); return; }
    const what = S.place;
    if (placeFrom(ev, what)) { if (ev.shiftKey) { S.place = what; sync(); } else { setTool("select"); select(S.selected); } }
  } else {
    const e = ev.button === 0 ? hit(p) : null;
    if (e) {
      select(e);
      history.push(S.map);
      S.drag = { e, start: p, x: e.x, y: e.y, points: e.fields.points ? structuredClone(e.fields.points) : null, moved: false };
    } else {                                                  // empty ground: let go of the selection and pan
      select(null);
      S.panning = { x: ev.clientX, y: ev.clientY, ox: S.ox, oy: S.oy }; $("stage").classList.add("pan");
    }
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
  let p = toMap(ev);
  if (S.stroke && !S.stroke.erase) p = growFor(ev, p);
  S.hover = p;
  canvas.style.cursor = S.tool === "select" && !S.drag && !S.panning && hit(p) ? "pointer" : "";   // over an object: it can be picked up
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
    if (!d.moved && Math.hypot(dx, dy) * S.zoom < 3) { S.needsDraw = true; return; }
    d.moved = true;
    if (e.type === "Prop" || e.type === "Character") [e.x, e.y] = p.free ? [Math.round(d.x + dx), Math.round(d.y + dy)] : snapFeet(d.x + dx, d.y + dy - 1, false);
    else {
      const dc = Math.round(dx / T), dr = Math.round(dy / T);
      e.x = d.x + dc * T; e.y = d.y + dr * T;
      if (d.points) e.fields.points = d.points.map(([c, r]) => [c + dc, r + dr]);
    }
    if (e.type === "Prop" && S.V.iso) S.terrainDirty = true;     // isometric props are part of the baked picture
  }
  S.needsDraw = true;
});

function pointerEnd(ev) {
  S.pointers.delete(ev.pointerId);
  if (S.longPress) { clearTimeout(S.longPress.timer); S.longPress = null; }
  if (S.pinch) { if (S.pointers.size < 2) S.pinch = null; return; }
  if (S.panning) { S.panning = null; $("stage").classList.remove("pan"); S.needsDraw = true; return; }
  const p = S.map ? toMap(ev) : null;
  if (S.selFrom) { S.selFrom = null; sync(); }
  if (S.stroke) endPaint(p);
  if (S.scatterStroke) { const st = S.scatterStroke; S.scatterStroke = null; if (st.changed) changed(false); else history.drop(); }
  if (S.drag) {
    const moved = S.drag.moved;
    S.drag = null;
    if (moved) { changed(S.selected?.type === "Region"); buildCard(true); } else history.drop();
  }
  S.needsDraw = true;
}
canvas.addEventListener("pointerup", pointerEnd);
canvas.addEventListener("pointercancel", (ev) => { cancelStroke(); pointerEnd(ev); });
canvas.addEventListener("pointerleave", () => { if (!S.dnd) { S.hover = null; S.needsDraw = true; } });

canvas.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const r = canvas.getBoundingClientRect();
  if (ev.ctrlKey || ev.metaKey) zoomTo(S.zoom * Math.exp(-ev.deltaY * 0.01), ev.clientX - r.left, ev.clientY - r.top);
  else { S.ox -= ev.deltaX; S.oy -= ev.deltaY; S.needsDraw = true; }
}, { passive: false });

const typing = () => ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName) || document.querySelector("dialog[open]");
window.addEventListener("keydown", (ev) => {
  const mod = ev.ctrlKey || ev.metaKey;
  if (mod && ev.key.toLowerCase() === "s") { ev.preventDefault(); save(); return; }
  if (mod && ev.key.toLowerCase() === "o") { ev.preventDefault(); openMap(); return; }
  if (typing()) return;
  if (!$("file-menu").hidden) return;
  const dir = !mod && S.selected?.type === "Character" && WALK_KEYS[ev.key.toLowerCase()];
  if (dir) { ev.preventDefault(); strollKey(dir); return; }
  if (mod && ev.key.toLowerCase() === "z") { ev.preventDefault(); ev.shiftKey ? redo() : undo(); return; }
  if (mod && ev.key.toLowerCase() === "y") { ev.preventDefault(); redo(); return; }
  if (mod && ev.key === "\\") { ev.preventDefault(); foldBoth(); return; }
  if (mod && ev.key === "0") { ev.preventDefault(); fit(); return; }
  if (mod) return;
  if (ev.key === " ") { if (!S.spaceDown) { S.spaceDown = true; $("stage").classList.add("pan"); } ev.preventDefault(); return; }
  const k = ev.key.toLowerCase();
  if (ev.shiftKey && (ev.code === "Digit1")) { fit(); return; }
  if (ev.shiftKey && (ev.code === "Digit0")) { fit(); return; }
  if (k === "r" && ev.shiftKey) { S.show.raw = !S.show.raw; buildShow(); S.needsDraw = true; return; }
  const keyTool = { v: "select", b: "brush" }[k];
  if (keyTool) { setTool(keyTool); return; }
  if (k === "e") { toggleErase(); return; }
  if (/^[1-9]$/.test(ev.key)) {
    const all = PALETTE.flatMap((g) => g.items.map((it) => ({ layer: g.layer, it })));
    const pickd = all[+ev.key - 1];
    if (pickd) choosePaint(pickd.layer, pickd.it);
    return;
  }
  if (k === "[" || k === "]") { S.size = Math.min(3, Math.max(1, S.size + (k === "]" ? 1 : -1))); sync(); return; }
  if (k === "shift" && S.hover) { S.hover.free = true; S.needsDraw = true; return; }
  if (k === "+" || k === "=") { stepZoom(1); return; }
  if (k === "-" || k === "_") { stepZoom(-1); return; }
  const arrow = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] }[k];
  if (arrow && S.selected) { ev.preventDefault(); const n = ev.shiftKey ? 1 : T; nudge(arrow[0] * n, arrow[1] * n); return; }
  if ((k === "delete" || k === "backspace") && S.selected) { ev.preventDefault(); removeSelected(); return; }
  if (k === "escape") {
    if (S.selected || S.sel) { S.sel = null; select(null); return; }
    setTool("select");
  }
});
window.addEventListener("keyup", (ev) => {
  if (S.stroll) { const dir = WALK_KEYS[ev.key.toLowerCase()]; if (dir) S.stroll.w.release(dir); }
  if (ev.key === " ") { S.spaceDown = false; if (!S.panning) $("stage").classList.remove("pan"); }
  if (ev.key === "Shift" && S.hover) { S.hover.free = false; S.needsDraw = true; }
});
window.addEventListener("resize", () => { S.needsDraw = true; buildToolbox(); });

// ---------- panels: fold on a desk, sheets on a phone ----------

function setFold(side, folded) {
  $("stage").classList.toggle(`fold-${side}`, folded);
  $(`tab-${side}`).hidden = !folded;
  try { localStorage.setItem(`tiny-town/fold-${side}`, folded ? "1" : ""); } catch { /* fine */ }
  S.needsDraw = true;
}
function foldBoth() {
  const st = $("stage"), any = !st.classList.contains("fold-left") || !st.classList.contains("fold-right");
  setFold("left", any); setFold("right", any);
}
// Show a panel: unfold it on a desk, slide it up on a phone.
function reveal(side) {
  if (phone()) { sheet(side); return; }
  setFold(side, false);
  const on = side === "left" ? $("palette").querySelector('[aria-pressed="true"]') : $("catalog").querySelector('[aria-pressed="true"]');
  on?.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
}
function sheet(side) {
  const L = $("paint-panel"), R = $("objects-panel");
  const open = side && !(side === "left" ? L : R).classList.contains("open") ? side : null;
  L.classList.toggle("open", open === "left"); R.classList.toggle("open", open === "right");
  buildToolbox();
}
for (const b of document.querySelectorAll("[data-fold]")) b.addEventListener("click", () => (phone() ? sheet(null) : setFold(b.dataset.fold, true)));
for (const b of document.querySelectorAll("[data-unfold]")) b.addEventListener("click", () => setFold(b.dataset.unfold, false));

const SHOW = [["terrain", "Terrain"], ["props", "Props"], ["characters", "Characters"], ["data", "Paths and regions"], ["raw", "Raw grid (Shift R)"], ["grid", "Grid lines"], ["margin", "Roads and rivers run on past the edge"]];
function buildShow() {
  $("show").replaceChildren(...SHOW.map(([k, label]) => el("label", { for: `show-${k}` },
    el("input", { type: "checkbox", id: `show-${k}`, checked: S.show[k], onchange: (ev) => { S.show[k] = ev.target.checked; if (k === "props" || k === "margin") { S.terrainDirty = true; rebuildView(); } S.needsDraw = true; } }), label)));
}

$("zoom-in").addEventListener("click", () => stepZoom(1));
$("zoom-out").addEventListener("click", () => stepZoom(-1));
$("zoom-fit").addEventListener("click", fit);
$("settings").addEventListener("click", () => $("settings-dialog").showModal());

// ---------- saving ----------

let autosaveTimer = null;
function changed(terrain) {
  if (terrain) { S.terrainDirty = true; if (S.V?.iso) rebuildView(); }
  else if (S.V?.iso) S.terrainDirty = true;                  // props are part of the isometric picture
  S.needsDraw = true;
  updateUndo();
  buildCard(true);
  clearTimeout(autosaveTimer);
  autosaveTimer = setTimeout(() => { if (!writeAutosave(S.fileName, stringifyMap(S.map))) toast("This browser can't keep the map; save it to a file"); }, 600);
}

function toast(text) {
  const t = $("toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 2600);
}

function updateUndo() {
  $("undo").disabled = !history.past.length;
  $("redo").disabled = !history.future.length;
}
function undo() { if (restore(() => history.undo(S.map))) afterHistory(); }
function redo() { if (restore(() => history.redo(S.map))) afterHistory(); }
function afterHistory() {
  if (S.selected && !S.map.entities.includes(S.selected)) S.selected = null;
  if (S.sel && (S.sel.c1 >= S.map.cols || S.sel.r1 >= S.map.rows)) S.sel = null;
  sync(); changed(true);
}
$("undo").addEventListener("click", undo);
$("redo").addEventListener("click", redo);

async function save() {
  const blob = new Blob([stringifyMap(S.map) + "\n"], { type: "application/json" });
  try {
    const r = await saveFile(blob, S.fileName, { fallbackName: S.fileName.replace(/\.ldtk$/, "") + ".json",
      types: [{ description: "Map (LDtk)", accept: { "application/json": [".ldtk"] } }] });
    if (r === "saved") toast("Saved");
  } catch (e) { toast(`Couldn't save: ${e.message}`); }
}
$("save").addEventListener("click", save);

async function savePng() {
  const V = makeView(), c = document.createElement("canvas");
  c.width = V.W; c.height = V.H;
  const g = c.getContext("2d");
  if (V.iso) g.drawImage(bakeIso(S.map, S.isoTs, V, { woods: false })[0], 0, 0); else drawTerrain(g, S.map, S.ts, 0);
  drawSprites(g, S.map.entities.filter((e) => (e.type === "Prop" && !V.iso) || e.type === "Character").sort((a, b) => (V.iso ? (a.x + a.y) - (b.x + b.y) : a.y - b.y)));
  const blob = await new Promise((ok) => c.toBlob(ok, "image/png"));
  try {
    const r = await saveFile(blob, S.fileName.replace(/\.(ldtk|json)$/, "") + ".png", { types: [{ description: "PNG image", accept: { "image/png": [".png"] } }] });
    if (r === "saved") toast("Saved the map as a PNG");
  } catch (e) { toast(`Couldn't save the picture: ${e.message}`); }
}

async function copyCode() {
  let code;
  try { code = await mapToCode(S.map); } catch (e) { toast(`Couldn't make a code here: ${e.message}`); return; }
  try { await navigator.clipboard.writeText(code); toast(`Copied a ${Math.round(code.length / 1024)} KB share code. Paste it anywhere.`); }
  catch { codeDialog(code); }
}

// The share code box: shows a code to copy by hand, or takes one to open.
function codeDialog(code = "") {
  $("code-text").value = code; $("code-text").readOnly = !!code;
  $("code-title").firstChild.textContent = code ? "Copy this share code" : "Open a share code";
  $("code-hint").textContent = code ? "Select it all and copy it. Whoever pastes it into Open a share code gets this map (with the same tiles and sprites)."
    : "Paste a code (it starts with tinytown1:). Undo brings your map back.";
  $("code-go").hidden = !!code;
  $("code-dialog").showModal();
  if (code) $("code-text").select(); else $("code-text").focus();
}
$("code-go").addEventListener("click", async () => {
  try {
    const m = await codeToMap($("code-text").value);
    history.push(S.map);
    useMap(m, "shared.ldtk", "Opened the shared map. Undo brings yours back.");
    changed(true);
    $("code-dialog").close();
  } catch (e) { toast(e.message); }
});

function useMap(m, name, note) {
  strollEnd();
  S.V = null;
  S.map = m; S.fileName = name; S.selected = null; S.sel = null;
  sync(); fit(); S.terrainDirty = true; updateUndo();
  if (note) toast(note);
}

async function openMap() {
  const f = await openFile(".ldtk,.json,application/json");
  if (!f) return;
  try {
    const m = parseMap(JSON.parse(f.text));
    history.push(S.map);
    useMap(m, f.name.endsWith(".json") ? f.name.replace(/(\.ldtk)?\.json$/, ".ldtk") : f.name, `Opened ${f.name}`);
    changed(true);
  } catch (e) { toast(`Couldn't open ${f.name}: ${e.message}`); }
}

async function openExample(url) {
  try {
    const m = parseMap(await (await fetch(url)).json());
    history.push(S.map);
    useMap(m, url.split("/").pop(), "Opened the example. Undo brings your map back.");
    changed(true);
  } catch (e) { toast(`Couldn't load the example: ${e.message}`); }
}

function newTown() {
  history.push(S.map);
  useMap(newMap(24, 24), "town.ldtk", "A new empty map. Paint past the edge to make it bigger; undo brings the old one back.");
  changed(true);
}

// ---------- the file menu (the arrow beside Save) ----------

const menu = $("file-menu"), menuBtn = $("file-btn");
function openMenu(open) {
  menu.hidden = !open;
  menuBtn.setAttribute("aria-expanded", String(open));
  if (open) menu.querySelector("button").focus();
}
menuBtn.addEventListener("click", () => openMenu(menu.hidden));
document.addEventListener("pointerdown", (ev) => { if (!menu.hidden && !menu.contains(ev.target) && ev.target !== menuBtn && !menuBtn.contains(ev.target)) openMenu(false); });
menu.addEventListener("keydown", (ev) => {
  const items = [...menu.querySelectorAll("button")], i = items.indexOf(document.activeElement);
  if (ev.key === "Escape") { openMenu(false); menuBtn.focus(); }
  else if (ev.key === "ArrowDown") { ev.preventDefault(); items[(i + 1) % items.length].focus(); }
  else if (ev.key === "ArrowUp") { ev.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
});
menu.addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-act]");
  if (!b) return;
  openMenu(false);
  ({ save, png: savePng, "copy-code": copyCode, open: openMap, "open-code": () => codeDialog(), example: () => openExample(b.dataset.url), new: newTown })[b.dataset.act]();
});

// ---------- isometric or top-down ----------

function syncProjection() {
  for (const b of document.querySelectorAll("[data-proj]")) {          // one switch at the bottom, one in the top pill on narrow screens
    b.setAttribute("aria-pressed", String((S.projection === "iso") === (b.dataset.proj === "iso")));
    if (b.dataset.proj === "iso") b.disabled = !S.isoTs;
  }
}
function setProjection(p) {
  if (p === S.projection || (p === "iso" && !S.isoTs)) return;
  S.projection = p;
  try { localStorage.setItem("tiny-town/projection", S.projection); } catch { /* fine */ }
  syncProjection();
  S.V = null; S.terrainDirty = true;
  if (S.map) { fit(); buildPaintPanel(); buildCatalog(); buildStamps(); sync(); buildCard(true); }
}
for (const b of document.querySelectorAll("[data-proj]")) b.addEventListener("click", () => setProjection(b.dataset.proj));

// ---------- a selected character walks with the arrow keys (or WASD) ----------
// Cell by cell, with a little hop: water, fences and buildings block it, stairs take it up and down (js/walk.js).
// One walk is one undo step.

const WALK_KEYS = { arrowup: "up", w: "up", arrowdown: "down", s: "down", arrowleft: "left", a: "left", arrowright: "right", d: "right" };

function strollKey(dir) {
  const e = S.selected;
  if (!S.stroll || S.stroll.e !== e) {
    strollEnd();
    history.push(S.map);
    const w = new Walker(S.map, propSet().props, [Math.floor(e.x / T), Math.floor((e.y - 1) / T)], { faces: !S.V?.iso });
    S.stroll = { e, w, moved: false };
  }
  S.stroll.w.press(dir);
}

function strollFrame() {
  const st = S.stroll, w = st.w;
  w.update();
  const [x, y] = w.feet();
  if (x !== st.e.x || y !== st.e.y) { st.e.x = Math.round(x); st.e.y = Math.round(y); st.moved = true; }
  const [fx, fy] = S.V.feet(st.e), r = canvas.getBoundingClientRect(), px = S.ox + fx * S.zoom, py = S.oy + fy * S.zoom, pad = 140;
  if (px < pad) S.ox += (pad - px) * 0.15; else if (px > r.width - pad) S.ox -= (px - r.width + pad) * 0.15;     // keep it in view
  if (py < pad) S.oy += (pad - py) * 0.15; else if (py > r.height - pad) S.oy -= (py - r.height + pad) * 0.15;
  S.needsDraw = true;
  if (!w.held.length && !w.from && !w.queued) strollEnd();
}

function strollEnd() {
  const st = S.stroll;
  if (!st) return;
  S.stroll = null;
  if (st.moved) changed(false); else history.drop();
}

// ---------- start ----------

async function start() {
  $("undo").append(icon("undo")); $("redo").append(icon("redo")); $("settings").append(icon("cog")); $("file-btn").append(icon("chev"));
    for (const side of ["left", "right"]) { let f = false; try { f = localStorage.getItem(`tiny-town/fold-${side}`) === "1"; } catch { /* fine */ } if (f) setFold(side, true); }
  try {
    S.ts = await loadTileset("tiles/");
  } catch (e) {
    toast("Couldn't load the tiles. Open this page through a web server (see README).");
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
  let m = null, name = EXAMPLE.split("/").pop(), note = null;
  if (saved) {
    try { m = parseMap(JSON.parse(saved.text)); name = saved.name || "town.ldtk"; note = "Picked up where you left off"; } catch { m = null; }
  }
  if (!m) {
    try { m = parseMap(await (await fetch(EXAMPLE)).json()); } catch { m = newMap(40, 50); name = "town.ldtk"; }
  }
  useMap(m, name, note);
  requestAnimationFrame(loop);
}
start();
