"""The look lab: candidate looks for one thing at a time, each drawn by the real renderer on the market village,
plus a picker page with a pick and a note per option: out/lab/<round>/index.html.

    python art/lab.py <round>          # rounds: palette
    python art/lab.py <round> <key>    # draw one option (each runs in its own process: drawers cache by palette)

Serve the repo (python3 -m http.server 8000) and open http://localhost:8000/out/lab/<round>/.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palettes

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "lab"
DETAIL = (160, 60, 560, 230)          # a house, trees, flowers, the pond and the road, in the full-bleed picture


def earthy(**kw):
    """Today's earthy palette, ramps shifted (see palettes.shift), with any colours overridden. `then` is a list of
    further shifts, each a dict of palettes.shift arguments (use `ramps` to touch only some materials)."""
    extra, then = kw.pop("set", {}), kw.pop("then", [])
    pal = palettes.PALETTES["earthy"]
    for step in ([kw] if kw else []) + then:
        pal = palettes.shift(pal, **step)
    return {**pal, **extra}


NATURE = ["grass", "leaves", "pine", "moss"]
DARKS = ["grass", "leaves", "pine", "trunk", "wood", "roof", "slate", "stone", "moss", "door"]


ROUNDS = {
    "palette": {
        "title": "Palette",
        "lead": "The same village in candidate palettes. Lightness mostly stays as picked; what changes is hue shift "
                "(warm lights, cool shadows), saturation and contrast. Look at the 1x picture first: that's the real size.",
        "options": [
            ("today", "Earthy (today)", "What the village draws now.", lambda: earthy()),
            ("warm-cool", "Warm light, cool shade", "Lights lean yellow, shadows lean blue. Same values, a little more "
             "colour.", lambda: earthy(hue=10, chroma=1.1)),
            ("warm-cool-strong", "Warm/cool, stronger", "Bigger hue shift and a touch more contrast: more depth.",
             lambda: earthy(hue=18, chroma=1.2, spread=1.1)),
            ("shared-dark", "Shared plum shadows", "Every material's darkest step leans toward one deep plum, and the "
             "outline goes plum too, so shadows tie the scene together.",
             lambda: earthy(hue=12, chroma=1.1, then=[dict(dark="#2b2342", dark_mix=0.35, ramps=DARKS)],
                           set={"out": "#2b2236"})),
            ("fresh", "Fresher greens", "Warm/cool shift, but grass and leaves pulled back from olive toward a "
             "clearer green.", lambda: earthy(hue=12, chroma=1.1, then=[dict(tint=(140, 14), chroma=1.15, ramps=NATURE)])),
            ("rich", "Storybook rich", "Saturated and contrasty, like a picture book.",
             lambda: earthy(hue=14, chroma=1.35, spread=1.18)),
            ("soft", "Soft daylight", "Lighter and gentler, lower contrast.",
             lambda: earthy(hue=8, chroma=0.9, spread=0.85, lift=0.03)),
            ("golden", "Golden hour", "Everything pulled a little toward warm gold, cool shadows kept.",
             lambda: earthy(hue=12, chroma=1.15, tint=(70, 6), set={"out": "#2e1c18"})),
            ("cool", "Cool morning", "A fresher, slightly blue light.",
             lambda: earthy(hue=10, chroma=1.05, tint=(230, 8), set={"out": "#1f2230"})),
        ],
    },
}


def draw(round_name, key):
    rd = ROUNDS[round_name]
    opt = next(o for o in rd["options"] if o[0] == key)
    palettes.PALETTES["lab"] = opt[3]()
    palettes.use("lab")
    import iso
    from render_map import load_map
    from reference_town import full_bleed
    m, _ = load_map(ROOT / "maps" / "market-village.ldtk", ROOT / "sprites")
    im = full_bleed(iso.render(m, 0, margin=6, woods=False))
    out = OUT / round_name
    out.mkdir(parents=True, exist_ok=True)
    im.save(out / f"{key}-1x.png")
    d = im.crop(DETAIL)
    d.resize((d.width * 3, d.height * 3), 0).save(out / f"{key}-zoom.png")
    if round_name == "palette":
        swatch(palettes.PALETTES["lab"]).save(out / f"{key}-ramps.png")


def swatch(pal):
    """Every ramp as a row of 8 px squares."""
    from PIL import Image, ImageDraw
    rows = [names for names in palettes.RAMPS.values()] + [["out", "fl_w", "fl_y", "fl_p", "fl_o", "light", "win", "win2"]]
    im = Image.new("RGB", (8 * 8, 8 * len(rows)), "#ffffff")
    d = ImageDraw.Draw(im)
    for j, names in enumerate(rows):
        for i, n in enumerate(names):
            if n in pal:
                d.rectangle((i * 8, j * 8, i * 8 + 7, j * 8 + 7), fill=pal[n])
    return im.resize((im.width * 3, im.height * 3), 0)


def main(round_name):
    rd = ROUNDS[round_name]
    for key, *_ in rd["options"]:
        subprocess.run([sys.executable, __file__, round_name, key], check=True)
        print("drew", key)
    cards = [{"key": k, "name": n, "note": t} for k, n, t, _ in rd["options"]]
    page = PAGE.replace("__TITLE__", rd["title"]).replace("__LEAD__", rd["lead"]) \
        .replace("__ROUND__", round_name).replace("__CARDS__", json.dumps(cards)) \
        .replace("__RAMPS__", "true" if round_name == "palette" else "false")
    (OUT / round_name / "index.html").write_text(page)
    print(f"wrote out/lab/{round_name}/index.html")


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ Lab</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@700&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
:root { --bg: #efe9dc; --panel: #fffaf1; --fg: #26303f; --muted: #5f6672; --line: #ddd2bd; --on: #2f7448; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 "IBM Plex Sans", system-ui, sans-serif; }
.page { max-width: 1640px; margin: 0 auto; padding: 28px 16px 110px; }
h1 { font: 700 32px/1.1 "Pixelify Sans", monospace; margin: 0 0 6px; }
.lead { color: var(--muted); max-width: 80ch; margin: 0 0 14px; }
.tools { display: flex; gap: 8px; margin: 0 0 18px; flex-wrap: wrap; }
.tools button { border: 1.5px solid var(--line); background: var(--panel); color: var(--fg); border-radius: 8px; padding: 5px 12px; font: 600 13px inherit; cursor: pointer; }
.tools button[aria-pressed=true] { border-color: var(--on); color: var(--on); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 780px), 1fr)); gap: 18px; }
.card { background: var(--panel); border: 1.5px solid var(--line); border-radius: 14px; overflow: hidden; display: grid; }
.card.p { border-color: var(--on); box-shadow: 0 0 0 2px var(--on); }
.pic { background: #6f8f45; overflow: auto; }
.pic img { display: block; image-rendering: pixelated; max-width: none; }
.pic.fit img { width: 100%; }
.ramps { padding: 8px 12px 0; } .ramps img { image-rendering: pixelated; display: block; }
.foot { padding: 10px 12px 12px; display: grid; gap: 8px; }
.foot b { font-weight: 600; } .foot p { margin: 0; color: var(--muted); font-size: 13.5px; }
.foot label { display: inline-flex; gap: 6px; align-items: center; font: 600 13px inherit; cursor: pointer; }
textarea { width: 100%; border: 1px solid var(--line); background: var(--bg); color: var(--fg); border-radius: 8px; padding: 6px 8px; font: 13px inherit; min-height: 36px; resize: vertical; }
.bar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; gap: 10px; align-items: center; background: var(--fg); color: var(--panel); padding: 8px 10px 8px 16px; border-radius: 12px; font-size: 13.5px; max-width: calc(100% - 32px); }
.bar button { border: 0; border-radius: 8px; background: var(--panel); color: var(--fg); font: 600 13px inherit; padding: 6px 12px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--on); outline-offset: 2px; }
</style></head><body><div class="page">
<h1>__TITLE__</h1>
<p class="lead">__LEAD__</p>
<div class="tools" role="group" aria-label="View">
  <button type="button" data-v="1x" aria-pressed="true">1x village</button>
  <button type="button" data-v="2x" aria-pressed="false">2x village</button>
  <button type="button" data-v="zoom" aria-pressed="false">Zoomed detail</button>
</div>
<div class="grid" id="grid"></div>
<p><textarea id="general" placeholder="Anything else (mixing two options, a colour to change)..."></textarea></p>
</div>
<div class="bar"><span id="status">Pick one</span><button id="copy" type="button">Copy picks</button></div>
<script>
const CARDS = __CARDS__, RAMPS = __RAMPS__, KEY = "tiny-town/lab/__ROUND__";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
const grid = document.getElementById("grid");
for (const c of CARDS) {
  const a = document.createElement("article"); a.className = "card"; a.dataset.key = c.key;
  a.innerHTML = `<div class="pic"><img alt="${c.name}"></div>${RAMPS ? `<div class="ramps"><img src="${c.key}-ramps.png?v=${Date.now()}" alt="${c.name} ramps"></div>` : ""}
    <div class="foot"><b>${c.name}</b><p>${c.note}</p>
    <label><input type="radio" name="pick" value="${c.key}"> Pick this</label>
    <textarea data-note="${c.key}" placeholder="Note on ${c.name}..."></textarea></div>`;
  grid.append(a);
}
const v0 = Date.now();
function view(v) {
  S.view = v; save();
  for (const b of document.querySelectorAll(".tools button")) b.setAttribute("aria-pressed", b.dataset.v === v);
  for (const a of document.querySelectorAll(".card")) {
    const img = a.querySelector(".pic img");
    img.src = `${a.dataset.key}-${v === "zoom" ? "zoom" : "1x"}.png?v=${v0}`;
    img.style.width = v === "2x" ? "1546px" : "";
    a.querySelector(".pic").classList.toggle("fit", v === "zoom");
  }
}
for (const b of document.querySelectorAll(".tools button")) b.addEventListener("click", () => view(b.dataset.v));
view(S.view || "1x");
for (const r of document.querySelectorAll("input[type=radio]")) { r.checked = S.pick === r.value; r.addEventListener("change", () => { S.pick = r.value; save(); sync(); }); }
for (const t of document.querySelectorAll("textarea")) { const k = t.dataset.note || "general"; t.value = S["note:" + k] || ""; t.addEventListener("input", () => { S["note:" + k] = t.value; save(); }); }
function sync() {
  for (const a of document.querySelectorAll(".card")) a.classList.toggle("p", S.pick === a.dataset.key);
  document.getElementById("status").textContent = S.pick ? "Ready to copy" : "Pick one";
}
sync();
document.getElementById("copy").addEventListener("click", async () => {
  const name = (k) => CARDS.find((c) => c.key === k)?.name || "no pick";
  const lines = [`__TITLE__ pick: ${name(S.pick)}`];
  for (const c of CARDS) if (S["note:" + c.key]) lines.push(`  ${c.name}: ${S["note:" + c.key]}`);
  if (S["note:general"]) lines.push(`  note: ${S["note:general"]}`);
  const text = lines.join("\\n");
  try { await navigator.clipboard.writeText(text); document.getElementById("status").textContent = "Copied, paste it to Claude"; } catch { prompt("Copy this:", text); }
});
</script></body></html>
"""

if __name__ == "__main__":
    if len(sys.argv) > 2:
        draw(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "palette")
