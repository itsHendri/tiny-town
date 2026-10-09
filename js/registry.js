// What can be painted and placed. Add a terrain or an object kind here and the editor and renderer pick it up.

// IntGrid layers: one small number per cell (0 = nothing). `color` is how the editor shows the raw grid.
// `uid`s are LDtk's ids for the definitions; keep them in sync with art/ldtk.py.
export const LAYERS = {
  Height: {
    uid: 5,
    label: "Height",
    values: [
      { v: 1, id: "level-1", label: "Level 1", color: "#8a9a3c" },
      { v: 2, id: "level-2", label: "Level 2", color: "#6f8a34" },
      { v: 3, id: "level-3", label: "Level 3", color: "#55752c" },
      { v: 4, id: "level-4", label: "Level 4", color: "#3d5f25" },
    ],
  },
  Terrain: {
    uid: 4,
    label: "Ground",
    values: [
      { v: 1, id: "path", label: "Path", color: "#e2c96a" },
      { v: 2, id: "cobbles", label: "Cobbles", color: "#7a8399" },
      { v: 3, id: "water", label: "Water", color: "#45bddd" },
      { v: 4, id: "soil", label: "Crops", color: "#a37a45" },
      { v: 5, id: "bridge", label: "Bridge", color: "#cfa765" },
      { v: 6, id: "dirt", label: "Dirt", color: "#a88d5c" },
    ],
  },
  Features: { uid: 3, label: "Features", values: [{ v: 1, id: "stairs", label: "Stairs", color: "#7a5733" }] },
  Deco: {
    uid: 2,
    label: "Decoration",
    values: [
      { v: 1, id: "fence", label: "Fence", color: "#5a3a32" },
      { v: 2, id: "flowers", label: "Flowers", color: "#f28fb0" },
      { v: 3, id: "tallgrass", label: "Tall grass", color: "#2f7448" },
      { v: 4, id: "gate", label: "Gate", color: "#cfa765" },
    ],
  },
};

export const value = (layer, id) => LAYERS[layer].values.find((x) => x.id === id).v;

export const MAX_LEVEL = LAYERS.Height.values.length;

// The ground overlays, drawn on every level in this order. Each is a dual-grid set in the tile sheet, fed by
// the cells holding one of `ids` on that level.
export const OVERLAYS = [
  { name: "dirt", ids: ["dirt"] },
  { name: "water", ids: ["water", "bridge"] },
  { name: "soil", ids: ["soil"] },
  { name: "path", ids: ["path"] },
  { name: "cobbles", ids: ["cobbles"] },
];

// Entity kinds, on the Objects layer (uid 1). Fields are typed like LDtk's: String, Point (a cell), Array<Point>.
export const OBJECTS_UID = 1;
export const ENTITIES = {
  Prop: { uid: 10, label: "Prop", color: "#4f9a48", pivot: [0.5, 1], fields: { sprite: ["String", 11] } },
  Character: { uid: 20, label: "Character", color: "#e8673a", pivot: [0.5, 1],
    fields: { id: ["String", 21], sprite: ["String", 22], perch: ["Point", 23], flyTo: ["Point", 24], path: ["Array<Point>", 25] } },
  Path: { uid: 30, label: "Path", color: "#f2c94c", pivot: [0, 0], fields: { name: ["String", 31], points: ["Array<Point>", 32] } },
  Region: { uid: 40, label: "Region", color: "#3a76f0", pivot: [0, 0], resizable: true, fields: { name: ["String", 41] } },
};
export const LAYER_ORDER = ["Objects", "Deco", "Features", "Terrain", "Height"];   // top first, like LDtk
