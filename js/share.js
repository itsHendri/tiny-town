// Share codes: a whole map as one line of text you can paste in a chat. The map is packed small (cell layers
// and objects only), compressed with the browser's built-in gzip, and written as base64.

import { newMap } from "./format.js";

const PREFIX = "tinytown1:";

const toB64 = (bytes) => { let s = ""; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); };
const fromB64 = (text) => Uint8Array.from(atob(text.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

async function pipe(bytes, stream) {
  return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer());
}

export async function mapToCode(m) {
  const packed = {
    c: m.cols, r: m.rows,
    L: Object.fromEntries(Object.entries(m.layers).map(([k, v]) => [k, Array.from(v)])),
    E: m.entities.map((e) => ({ t: e.type, x: e.x, y: e.y, w: e.w, h: e.h, f: e.fields })),
  };
  return PREFIX + toB64(await pipe(new TextEncoder().encode(JSON.stringify(packed)), new CompressionStream("gzip")));
}

export async function codeToMap(code) {
  const text = code.trim();
  if (!text.startsWith(PREFIX)) throw new Error("That isn't a tiny-town share code (it should start with tinytown1:).");
  const packed = JSON.parse(new TextDecoder().decode(await pipe(fromB64(text.slice(PREFIX.length)), new DecompressionStream("gzip"))));
  const m = newMap(packed.c, packed.r);
  for (const [k, v] of Object.entries(packed.L)) if (m.layers[k] && v.length === m.cols * m.rows) m.layers[k].set(v);
  m.entities = packed.E.map((e) => ({ type: e.t, x: e.x, y: e.y, w: e.w, h: e.h, fields: e.f }));
  return m;
}
