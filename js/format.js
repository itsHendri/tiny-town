// Map files: a small subset of LDtk's project JSON (version 1.5.3), so maps also open in LDtk.
//
//   const map = parseMap(json);        // -> { cols, rows, layers: { Height, Terrain, Features, Deco }, entities }
//   const json = buildMap(map);        // -> a complete .ldtk project object (stringify it to save)
//   const map = newMap(40, 50);
//
// One level, 16 px cells. IntGrid layers hold the cells; the Objects layer holds entities with typed fields.
// `version` is tiny-town's own file version; MIGRATIONS[n] upgrades a file from version n to n + 1.

import { ENTITIES, LAYERS, LAYER_ORDER, OBJECTS_UID } from "./registry.js";

export const VERSION = 1;
const LDTK = "1.5.3";
const GRID = 16;
const MIGRATIONS = {};

const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
  const r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 3) | 8).toString(16);
}));

export function newMap(cols, rows) {
  const layers = Object.fromEntries(Object.keys(LAYERS).map((k) => [k, new Uint8Array(cols * rows)]));
  return { cols, rows, layers, entities: [], iids: {} };
}

// ---------- reading ----------

function fieldValue(f) {
  const v = f.__value;
  if (f.__type === "Point") return v ? [v.cx, v.cy] : null;
  if (f.__type === "Array<Point>") return (v || []).filter(Boolean).map((p) => [p.cx, p.cy]);
  return v;
}

export function parseMap(json) {
  let version = json.tinyTownVersion || 1;
  while (version < VERSION) { json = MIGRATIONS[version](json); version++; }
  const level = (json.levels || [])[0];
  if (!level) throw new Error("This file has no level in it.");
  const cols = Math.round(level.pxWid / GRID), rows = Math.round(level.pxHei / GRID);
  const m = newMap(cols, rows);
  m.iids = { project: json.iid, level: level.iid, world: json.dummyWorldIid, layers: {} };
  for (const li of level.layerInstances || []) {
    const name = li.__identifier;
    m.iids.layers[name] = li.iid;
    if (m.layers[name] && li.intGridCsv?.length === cols * rows) m.layers[name].set(li.intGridCsv);
    if (name === "Objects") {
      for (const e of li.entityInstances || []) {
        if (!ENTITIES[e.__identifier]) continue;
        const fields = {};
        for (const f of e.fieldInstances || []) fields[f.__identifier] = fieldValue(f);
        m.entities.push({ iid: e.iid, type: e.__identifier, x: e.px[0], y: e.px[1], w: e.width, h: e.height, fields });
      }
    }
  }
  return m;
}

// ---------- writing ----------

const LAYER_DEF_COMMON = {
  doc: null, uiColor: null, gridSize: GRID, guideGridWid: 0, guideGridHei: 0, displayOpacity: 1, inactiveOpacity: 1,
  hideInList: false, hideFieldsWhenInactive: true, canSelectWhenInactive: true, renderInWorldView: true,
  pxOffsetX: 0, pxOffsetY: 0, parallaxFactorX: 0, parallaxFactorY: 0, parallaxScaling: true,
  requiredTags: [], excludedTags: [], uiFilterTags: [], useAsyncRender: false, autoTilesKilledByOtherLayerUid: null,
  biomeFieldUid: null, intGridValuesGroups: [], autoRuleGroups: [], autoSourceLayerDefUid: null, tilesetDefUid: null,
  tilePivotX: 0, tilePivotY: 0,
};

function layerDefs() {
  return LAYER_ORDER.map((name) => {
    if (name === "Objects") return { ...LAYER_DEF_COMMON, __type: "Entities", type: "Entities", identifier: name, uid: OBJECTS_UID, intGridValues: [], inactiveOpacity: 0.6 };
    const L = LAYERS[name];
    return { ...LAYER_DEF_COMMON, __type: "IntGrid", type: "IntGrid", identifier: name, uid: L.uid,
      intGridValues: L.values.map((x) => ({ value: x.v, identifier: x.id, color: x.color, tile: null, groupUid: 0 })) };
  });
}

function fieldDef(identifier, type, uid) {
  const point = type !== "String", array = type.startsWith("Array");
  return {
    identifier, doc: null, __type: type, uid, type: point ? "F_Point" : "F_String", isArray: array, canBeNull: !array,
    arrayMinLength: null, arrayMaxLength: null, editorDisplayMode: array ? "PointPath" : point ? "PointStar" : "ValueOnly",
    editorDisplayScale: 1, editorDisplayPos: "Above", editorLinkStyle: array ? "ArrowsLine" : "StraightArrow",
    editorDisplayColor: null, editorAlwaysShow: false, editorShowInWorld: true, editorCutLongValues: true,
    editorTextSuffix: null, editorTextPrefix: null, useForSmartColor: false, exportToToc: false, searchable: false,
    min: null, max: null, regex: null, acceptFileTypes: null, defaultOverride: null, textLanguageMode: null,
    symmetricalRef: false, autoChainRef: true, allowOutOfLevelRef: true, allowedRefs: "OnlySame",
    allowedRefsEntityUid: null, allowedRefTags: [], tilesetUid: null,
  };
}

function entityDefs() {
  return Object.entries(ENTITIES).map(([identifier, E]) => ({
    identifier, uid: E.uid, tags: [], exportToToc: false, allowOutOfBounds: false, doc: null, width: GRID, height: GRID,
    resizableX: !!E.resizable, resizableY: !!E.resizable, minWidth: null, maxWidth: null, minHeight: null, maxHeight: null,
    keepAspectRatio: false, tileOpacity: 1, fillOpacity: 0.08, lineOpacity: 0, hollow: !!E.resizable, color: E.color,
    renderMode: "Rectangle", showName: true, tilesetId: null, tileRenderMode: "FitInside", tileRect: null, uiTileRect: null,
    nineSliceBorders: [], maxCount: 0, limitScope: "PerLevel", limitBehavior: "MoveLastOne", pivotX: E.pivot[0], pivotY: E.pivot[1],
    fieldDefs: Object.entries(E.fields).map(([name, [type, uid]]) => fieldDef(name, type, uid)),
  }));
}

function fieldInstance(name, type, uid, v) {
  const base = { __identifier: name, __type: type, __tile: null, defUid: uid };
  if (type === "Point") {
    return v ? { ...base, __value: { cx: v[0], cy: v[1] }, realEditorValues: [{ id: "V_String", params: [`${v[0]},${v[1]}`] }] }
      : { ...base, __value: null, realEditorValues: [] };
  }
  if (type === "Array<Point>") {
    const pts = v || [];
    return { ...base, __value: pts.map((p) => ({ cx: p[0], cy: p[1] })), realEditorValues: pts.map((p) => ({ id: "V_String", params: [`${p[0]},${p[1]}`] })) };
  }
  return v == null ? { ...base, __value: null, realEditorValues: [] } : { ...base, __value: String(v), realEditorValues: [{ id: "V_String", params: [String(v)] }] };
}

function entityInstance(e) {
  const E = ENTITIES[e.type];
  e.iid = e.iid || uuid();
  return {
    __identifier: e.type, __grid: [Math.floor(e.x / GRID), Math.floor(e.y / GRID)], __pivot: E.pivot, __tags: [], __tile: null,
    __smartColor: E.color, iid: e.iid, width: e.w || GRID, height: e.h || GRID, defUid: E.uid, px: [e.x, e.y],
    __worldX: e.x, __worldY: e.y,
    fieldInstances: Object.entries(E.fields).map(([name, [type, uid]]) => fieldInstance(name, type, uid, e.fields[name])),
  };
}

export function buildMap(m) {
  const iids = m.iids = { project: m.iids?.project || uuid(), level: m.iids?.level || uuid(), world: m.iids?.world || uuid(), layers: m.iids?.layers || {} };
  const layerInstances = LAYER_ORDER.map((name) => {
    const isObj = name === "Objects";
    const iid = iids.layers[name] = iids.layers[name] || uuid();
    return {
      __identifier: name, __type: isObj ? "Entities" : "IntGrid", __cWid: m.cols, __cHei: m.rows, __gridSize: GRID, __opacity: 1,
      __pxTotalOffsetX: 0, __pxTotalOffsetY: 0, __tilesetDefUid: null, __tilesetRelPath: null, iid, levelId: 0,
      layerDefUid: isObj ? OBJECTS_UID : LAYERS[name].uid, pxOffsetX: 0, pxOffsetY: 0, visible: true, optionalRules: [],
      intGridCsv: isObj ? [] : Array.from(m.layers[name]), autoLayerTiles: [], seed: 1234567, overrideTilesetUid: null,
      gridTiles: [], entityInstances: isObj ? m.entities.map(entityInstance) : [],
    };
  });
  return {
    __header__: { fileType: "LDtk Project JSON", app: "LDtk", doc: "https://ldtk.io/json", schema: "https://ldtk.io/files/JSON_SCHEMA.json",
      appAuthor: "Sebastien 'deepnight' Benard", appVersion: LDTK, url: "https://ldtk.io" },
    tinyTownVersion: VERSION,
    iid: iids.project, jsonVersion: LDTK, appBuildId: 473702, nextUid: 100, identifierStyle: "Capitalize", toc: [],
    worldLayout: "Free", worldGridWidth: 256, worldGridHeight: 256, defaultLevelWidth: m.cols * GRID, defaultLevelHeight: m.rows * GRID,
    defaultPivotX: 0.5, defaultPivotY: 1, defaultGridSize: GRID, defaultEntityWidth: GRID, defaultEntityHeight: GRID,
    bgColor: "#40465B", defaultLevelBgColor: "#b4d566", minifyJson: false, externalLevels: false, exportTiled: false,
    simplifiedExport: false, imageExportMode: "None", exportLevelBg: true, pngFilePattern: null, backupOnSave: false,
    backupLimit: 10, backupRelPath: null, levelNamePattern: "%world_Level_%idx", customCommands: [], flags: [],
    defs: { layers: layerDefs(), entities: entityDefs(), tilesets: [], enums: [], externalEnums: [], levelFields: [] },
    levels: [{
      identifier: "Town", iid: iids.level, uid: 0, worldX: 0, worldY: 0, worldDepth: 0, pxWid: m.cols * GRID, pxHei: m.rows * GRID,
      __bgColor: "#b4d566", bgColor: null, useAutoIdentifier: false, bgRelPath: null, bgPos: null, bgPivotX: 0.5, bgPivotY: 0.5,
      __smartColor: "#ADADB5", __bgPos: null, externalRelPath: null, fieldInstances: [], layerInstances, __neighbours: [],
    }],
    worlds: [], dummyWorldIid: iids.world,
  };
}

// The LDtk-style JSON text, with each IntGrid row on its own line so diffs stay readable.
export function stringifyMap(m) {
  const json = buildMap(m);
  let text = JSON.stringify(json, null, 1);
  text = text.replace(/"intGridCsv": \[([\d,\s]*)\]/g, (all, body) => {
    const nums = body.split(",").map((s) => s.trim()).filter(Boolean);
    if (!nums.length) return `"intGridCsv": []`;
    const lines = [];
    for (let i = 0; i < nums.length; i += m.cols) lines.push(nums.slice(i, i + m.cols).join(","));
    return `"intGridCsv": [\n${lines.join(",\n")}\n]`;
  });
  return text;
}
