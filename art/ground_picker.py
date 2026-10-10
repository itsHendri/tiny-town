"""Candidate looks for the isometric Path and Cobbles, each drawn by the real renderer on a small scene (a road, a
square, a patch of Dirt beside them for contrast), plus a picker page: out/ground-picker/index.html.

    python art/ground_picker.py
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palettes

palettes.use("earthy")
import iso
import preview
from iso import h

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "ground-picker"


def uv(gx, gy):
    """Map pixels (u along a row, v down a column) of a screen pixel, wrapped to the 32 px the tiles repeat over."""
    return ((gx + 2 * gy) // 2) % 32, ((2 * gy - gx) // 2) % 32


def edge(sh, x, y, gx, gy, curb=None):
    """Shared edge: grass tufts creep over the rim (or a curb colour), None outside."""
    if not sh.inside(x, y):
        return "out"
    d = sh.dist(x, y, 3)
    if d <= 1.0:
        return curb or ("g3" if h("tuft", gx % 64, gy % 32) < 0.45 else None)
    if d <= 2.0 and h("tuft2", gx % 64, gy % 32) < 0.15:
        return "g2"
    return None


def current(sh, x, y, gx, gy):
    return iso.cobble_px(sh, x, y, gx, gy)


def packed_earth(sh, x, y, gx, gy):
    e = edge(sh, x, y, gx, gy)
    if e == "out":
        return None
    if e:
        return e
    gx, gy = gx % 64, gy % 32
    patch, k = h("pe", gx // 8, gy // 4), h("pk", gx // 2, gy)
    if h("peb", gx, gy) < 0.025:
        return (150, 118, 74)
    if patch > 0.72 and k > 0.4:
        return (236, 212, 160)
    return (214, 186, 128) if k < 0.62 else (196, 165, 108)


def gravel(sh, x, y, gx, gy):
    if not sh.inside(x, y):
        return (196, 188, 170) if sh.dist(x, y, 3) <= 2.0 and h("loose", gx % 64, gy % 32) < 0.12 else None
    e = edge(sh, x, y, gx, gy)
    if e:
        return e
    k = h("gr", gx % 64, gy % 32)
    return (230, 224, 208) if k < 0.3 else (204, 196, 178) if k < 0.72 else (170, 161, 142) if k < 0.93 else (118, 110, 96)


def flagstones(sh, x, y, gx, gy):
    """Big flat stones with grass in the joints."""
    e = edge(sh, x, y, gx, gy)
    if e == "out":
        return None
    if e:
        return e
    i0, j0 = gx // 16, gy // 8
    best = second = 99.0
    sid = off = None
    for j in range(j0 - 1, j0 + 2):
        for i in range(i0 - 1, i0 + 2):
            key = (i % 4, j % 4)
            cx = i * 16 + 3 + h("fx", *key) * 10 + (8 if j % 2 else 0)
            cy = j * 8 + 1 + h("fy", *key) * 6
            d = math.hypot(gx + 0.5 - cx, (gy + 0.5 - cy) * 1.8)
            if d < best:
                second, best, sid, off = best, d, key, (gx + 0.5 - cx, gy + 0.5 - cy)
            elif d < second:
                second = d
    if second - best < 1.2:
        return "g3" if h("joint", gx % 64, gy % 32) < 0.6 else "g2"
    tone = h("ft", *sid)
    base = [(214, 208, 192), (198, 192, 176), (186, 180, 164)][int(tone * 3)]
    if off[0] + off[1] * 1.8 < -5:
        return tuple(min(255, c + 16) for c in base)
    if off[0] + off[1] * 1.8 > 5:
        return tuple(c - 18 for c in base)
    return base


def worn_track(sh, x, y, gx, gy):
    """A path worn into the grass: earth in the middle, grass showing through towards the sides."""
    if not sh.inside(x, y):
        return None
    d = sh.dist(x, y, 6)
    gx, gy = gx % 64, gy % 32
    grassy = h("wt", gx // 2, gy) < (0.75 if d <= 2 else 0.4 if d <= 4 else 0.1)
    if grassy:
        return "g2" if h("wg", gx, gy) < 0.5 else "g3"
    return (186, 150, 98) if h("wk", gx // 2, gy) < 0.6 else (166, 130, 82)


def sand(sh, x, y, gx, gy):
    e = edge(sh, x, y, gx, gy)
    if e == "out":
        return None
    if e:
        return e
    u, v = uv(gx, gy)
    ripple = (v + 2 * math.sin(u / 5)) % 8 < 1
    k = h("sd", gx % 64, gy % 32)
    if ripple:
        return (214, 188, 130)
    return (244, 228, 178) if k < 0.35 else (234, 214, 158)


def bricks(colours, mortar, curb):
    """Blocks laid in rows along the map's columns, each row shifted half a block (running bond)."""
    def px(sh, x, y, gx, gy):
        e = edge(sh, x, y, gx, gy, curb=curb)
        if e == "out":
            return None
        if e:
            return e
        u, v = uv(gx, gy)
        row = v // 4
        uu = (u + (4 if row % 2 else 0)) % 32
        if v % 4 == 0 or uu % 8 == 0:
            return mortar
        base = colours[int(h("bk", uu // 8, row % 8) * len(colours))]
        if v % 4 == 1 or uu % 8 == 1:
            return tuple(min(255, c + 18) for c in base)          # lit top-left lip
        return base
    return px


GREY = {"cb0": (220, 214, 202), "cb1": (182, 176, 166), "cb2": (146, 140, 132), "cb3": (96, 92, 88)}


def grey_cobbles(sh, x, y, gx, gy):
    c = iso.cobble_px(sh, x, y, gx, gy)
    return GREY.get(c, c) if isinstance(c, str) else c


LOOKS = [
    ("current", "Bright cobbles (today)", "What both Path and Cobbles draw now: rounded pale-gold stones.", current),
    ("earth", "Packed earth", "Sandy trodden earth with the odd pebble. Warmer and lighter than Dirt.", packed_earth),
    ("gravel", "Gravel", "Pale crunchy gravel; loose bits spill onto the grass.", gravel),
    ("flags", "Flagstones", "Big flat stones with grass in the joints, like a garden walk.", flagstones),
    ("track", "Worn track", "Earth worn into the grass, grass showing through at the sides.", worn_track),
    ("sand", "Sand", "Pale sand with soft ripples, a seaside or desert road.", sand),
    ("setts", "Grey setts", "Square-cut grey-blue blocks in rows, like the top-down Cobbles swatch.",
     bricks([(150, 160, 178), (136, 146, 166), (166, 174, 190)], (88, 94, 110), (88, 94, 110))),
    ("brick", "Red brick", "Warm brick paving with light mortar, a smart town square.",
     bricks([(178, 86, 62), (160, 74, 54), (192, 104, 76)], (214, 190, 156), (120, 60, 46))),
    ("grey", "Grey cobbles", "Today's rounded stones in cool grey: an old-town street.", grey_cobbles),
]


def scene():
    m = preview.Map(10, 8)
    m.fill("terrain", 3, 0, 5, 10, "path")       # rows first: a road across
    m.fill("terrain", 5, 4, 8, 8, "path")        # and a square off it
    m.fill("terrain", 0, 2, 2, 5, "dirt")        # dirt beside it, to compare
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = scene()
    for key, *_ , fn in LOOKS:
        iso.SETS["path"] = lambda sh, x, y, gx, gy, f, fn=fn: fn(sh, x, y, gx, gy)
        iso.iso_tile.cache_clear()
        im = iso.render(m, 0, objects=False, margin=2)
        im = im.crop(im.getbbox())
        cx, cy = im.width // 2, im.height // 2 + 6               # the middle of the map: road, square and dirt
        im = im.crop((cx - 120, cy - 66, cx + 120, cy + 66))
        im.resize((im.width * 3, im.height * 3), 0).save(OUT / f"{key}.png")
        print("drew", key)
    cards = json.dumps([{"key": k, "name": n, "note": t} for k, n, t, _ in LOOKS])
    (OUT / "index.html").write_text(PAGE.replace("__CARDS__", cards))
    print("wrote out/ground-picker/index.html")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Path Look Picker</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@700&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono&display=swap">
<style>
:root { --bg: #efe9dc; --panel: #fffaf1; --fg: #26303f; --muted: #5f6672; --line: #ddd2bd; --accent: #c4482c; --on: #2f7448; --on-bg: #e3f1d2; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --accent: #f08a62; --on: #9ad86f; --on-bg: #29371f; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --accent: #f08a62; --on: #9ad86f; --on-bg: #29371f; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 "IBM Plex Sans", system-ui, sans-serif; }
.page { max-width: 1240px; margin: 0 auto; padding: 28px 16px 110px; }
h1 { font: 700 32px/1.1 "Pixelify Sans", monospace; margin: 0 0 6px; }
.lead { color: var(--muted); max-width: 72ch; margin: 0 0 18px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 360px), 1fr)); gap: 16px; }
.card { background: var(--panel); border: 1.5px solid var(--line); border-radius: 14px; overflow: hidden; display: grid; }
.card.p { border-color: var(--on); box-shadow: 0 0 0 2px var(--on); }
.card.c { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
.card.p.c { box-shadow: 0 0 0 2px var(--on), 0 0 0 5px var(--accent); }
.pic { background: #6f8f45; display: grid; place-items: center; padding: 8px; }
.pic img { width: 100%; image-rendering: pixelated; display: block; }
.foot { padding: 10px 12px 12px; display: grid; gap: 8px; }
.foot b { font-weight: 600; }
.foot p { margin: 0; color: var(--muted); font-size: 13.5px; }
.picks { display: flex; gap: 8px; flex-wrap: wrap; }
.picks label { display: inline-flex; gap: 6px; align-items: center; border: 1.5px solid var(--line); border-radius: 7px; padding: 3px 10px; font: 600 13px inherit; cursor: pointer; }
.picks input:checked + span { color: var(--on); }
textarea { width: 100%; border: 1px solid var(--line); background: var(--bg); color: var(--fg); border-radius: 8px; padding: 6px 8px; font: 13px inherit; min-height: 36px; resize: vertical; }
.bar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; gap: 10px; align-items: center; background: var(--fg); color: var(--panel); padding: 8px 10px 8px 16px; border-radius: 12px; font-size: 13.5px; max-width: calc(100% - 32px); }
.bar button { border: 0; border-radius: 8px; background: var(--panel); color: var(--fg); font: 600 13px inherit; padding: 6px 12px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
</style></head><body><div class="page">
<h1>Path and Cobbles</h1>
<p class="lead">In isometric, Path and Cobbles draw the same tiles today. Each picture is the real renderer: a road and a square in that look, with Dirt top left to compare. Pick one look for <b>Path</b> and one for <b>Cobbles</b> (they can't be the same), add notes, then Copy picks.</p>
<div class="grid" id="grid"></div>
<p><textarea id="general" placeholder="Anything else (colours, mixing two looks)..."></textarea></p>
</div>
<div class="bar"><span id="status">Pick a Path and a Cobbles look</span><button id="copy" type="button">Copy picks</button></div>
<script>
const CARDS = __CARDS__, KEY = "tiny-town/ground-picker";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
const grid = document.getElementById("grid");
for (const c of CARDS) {
  const a = document.createElement("article"); a.className = "card"; a.dataset.key = c.key;
  a.innerHTML = `<div class="pic"><img src="${c.key}.png" alt="${c.name}: a road and a square"></div><div class="foot"><b>${c.name}</b><p>${c.note}</p>
    <div class="picks"><label><input type="radio" name="path" value="${c.key}"><span>Use for Path</span></label><label><input type="radio" name="cobbles" value="${c.key}"><span>Use for Cobbles</span></label></div>
    <textarea data-note="${c.key}" placeholder="Note on ${c.name}..."></textarea></div>`;
  grid.append(a);
}
for (const r of document.querySelectorAll("input[type=radio]")) { r.checked = S[r.name] === r.value; r.addEventListener("change", () => { S[r.name] = r.value; save(); sync(); }); }
for (const t of document.querySelectorAll("textarea")) { const k = t.dataset.note || "general"; t.value = S["note:" + k] || ""; t.addEventListener("input", () => { S["note:" + k] = t.value; save(); }); }
function sync() {
  for (const a of document.querySelectorAll(".card")) { a.classList.toggle("p", S.path === a.dataset.key); a.classList.toggle("c", S.cobbles === a.dataset.key); }
  document.getElementById("status").textContent = S.path && S.cobbles ? (S.path === S.cobbles ? "Path and Cobbles are the same look" : "Ready to copy") : "Pick a Path and a Cobbles look";
}
sync();
document.getElementById("copy").addEventListener("click", async () => {
  const name = (k) => CARDS.find((c) => c.key === k)?.name || "no pick";
  const lines = [`Path: ${name(S.path)}`, `Cobbles: ${name(S.cobbles)}`];
  for (const c of CARDS) if (S["note:" + c.key]) lines.push(`  ${c.name}: ${S["note:" + c.key]}`);
  if (S["note:general"]) lines.push(`  note: ${S["note:general"]}`);
  const text = lines.join("\\n");
  try { await navigator.clipboard.writeText(text); document.getElementById("status").textContent = "Copied, paste it to Claude"; } catch { prompt("Copy this:", text); }
});
</script></body></html>
"""

if __name__ == "__main__":
    main()
