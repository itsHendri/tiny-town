"""The look lab: candidate looks for one thing at a time, each drawn by the real renderer on the market village,
plus a picker page with a pick and a note per option: out/lab/<round>/index.html.

    python art/lab.py <round>          # rounds: palette, outline, ground, grass
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


def outlines(style="solid", double=True, beam=None):
    """Setup for the outline round: Sprite.outline's style, 2 px or 1 px on buildings, the storybook timber colour."""
    def setup():
        import iso_props
        from sprites import OUTLINE
        OUTLINE.update(style=style, double=double)
        if beam:
            iso_props.LOOKS["storybook"]["beam"] = beam
    return setup


OUTLINE_ROUND = {
    "title": "Outlines",
    "lead": "The same village in the new palette, with different outlines on houses, trees, stalls and props. "
            "Selective outline: the lit sides (top, left) get a dark shade of the colour inside instead of the "
            "dark line, so shapes look lit rather than drawn. Compare at 1x and in the zoomed detail.",
    "options": [
        ("today", "Solid, 2 px on houses (today)", "Dark line all round; houses get a double line.", None, outlines()),
        ("thin", "Solid, 1 px", "The same line, single on houses too. Lighter, crisper buildings.", None,
         outlines(double=False)),
        ("selout", "Selective, 2 px on houses", "Dark line on the shadow sides, a dark local colour on the lit "
         "sides.", None, outlines("selout")),
        ("selout-thin", "Selective, 1 px", "Selective outline, single line everywhere.", None,
         outlines("selout", False)),
        ("selout-wood", "Selective, 1 px, wood timbers", "As above, and the house timbers in dark wood instead "
         "of the outline colour, so the walls read lighter.", None, outlines("selout", False, "k3")),
        ("soft", "Soft, 1 px", "A dark local colour all round; the dark line only along the bottom, where things "
         "meet the ground.", None, outlines("soft", False)),
        ("soft-wood", "Soft, 1 px, wood timbers", "Soft outline plus dark wood timbers: the gentlest look.", None,
         outlines("soft", False, "k3")),
        ("thin-wood", "Solid, 1 px, wood timbers", "Today's line but single, with wood timbers.", None,
         outlines(double=False, beam="k3")),
    ],
}


ROUNDS["outline"] = OUTLINE_ROUND


def with_deep_water():
    """The default palette plus w4: a deeper water shade for the bank's shadow."""
    pal = dict(palettes.PALETTES[palettes.DEFAULT])
    L, C, H = palettes.oklch(pal["w3"])
    pal["w4"] = palettes.hexof(L - 0.12, C * 0.9, H + 6)
    return pal


def ground(grass, water, grass_n=None):
    def setup():
        import iso
        import lab_ground as g
        if grass_n:
            import ground as gr
            gr.GRASS_N = grass_n
        if grass:
            iso.grass_px = getattr(g, "grass_" + grass)
        if water:
            iso.SETS["water"] = getattr(g, "water_" + water)
    return setup


def with_close_greens():
    """The default palette plus g1l / g1d: greens a small step lighter / darker than g1, for faint patches."""
    pal = dict(palettes.PALETTES[palettes.DEFAULT])
    L, C, H = palettes.oklch(pal["g1"])
    pal["g1l"] = palettes.hexof(L + 0.03, C * 1.02, H - 3)
    pal["g1d"] = palettes.hexof(L - 0.025, C, H + 3)
    return pal


ROUNDS["grass"] = {
    "title": "Clean grass",
    "lead": "Round 2 for grass, water stays as today. All options keep Clean flat's tiny tufts; what changes is the "
            "light patches, which made a blob pattern when tiles join up. Check the Open field view: a plain meadow "
            "is where repeats show.",
    "field": True,
    "options": [
        ("clean", "Clean flat (round 1 pick)", "Soft light patches in gh: the blobs you saw.", None,
         ground("clean", None)),
        ("bare", "No patches", "Just the base green and the tiny tufts.", None, ground("bare", None)),
        ("faint", "Faint patches", "Same patches, in a green only a small step lighter than the base.",
         with_close_greens, ground("faint", None)),
        ("flecks", "Small flecks", "Many small ragged light flecks instead of big patches.", with_close_greens,
         ground("flecks", None)),
        ("lit-tufts", "Lit tufts", "No filled patches; tufts get denser and lighter where a patch would be.",
         None, ground("lit_tufts", None)),
        ("diagonal", "Diagonal swells", "Faint patches stretched along the iso diagonals, like gentle swells.",
         with_close_greens, ground("diagonal", None)),
        ("two-tone", "Two close greens", "The base split into two close greens, no light patches.",
         with_close_greens, ground("two_tone", None)),
        ("patches-big", "Clean flat, big repeat", "Round 1's patches exactly, but the grass repeats every 16 cells "
         "instead of 4, so they stop lining up into dots.", None, ground("patches_big", None, 16)),
        ("faint-big", "Faint patches, big repeat", "Faint patches with the 16-cell repeat.", with_close_greens,
         ground("faint_big", None, 16)),
        ("swells-big", "Soft swells, big repeat", "Light and shade swells in three close greens, 16-cell repeat.",
         with_close_greens, ground("swells_big", None, 16)),
    ],
}


ROUNDS["ground"] = {
    "title": "Grass and water",
    "lead": "Grass is most of the screen, so it sets how clean the whole map feels. Each card pairs one grass with "
            "one water; pick a grass and a water separately (they can come from different cards). Today's grass is "
            "per-pixel speckle; the new ones use soft light/shade patches and drawn tufts instead.",
    "picks": ["grass", "water"],
    "options": [
        ("today", "Today: speckle / flat water", "What the village draws now.", None, ground(None, None)),
        ("calm", "Calm patches / depth bands", "Grass: big soft light and shade patches, a few tufts. Water: foam "
         "line, then shallow, mid and deep bands.", with_deep_water, ground("calm", "depth")),
        ("tufted", "Tufted / bank shadow", "Grass: one flat green with lots of sunlit tufts. Water: depth plus the "
         "bank's shadow along the top shore.", with_deep_water, ground("tufted", "shade")),
        ("lush", "Lush meadow / deep", "Grass: three-tone patches, tufts, the odd flower. Water: dark and deep with "
         "a bright edge.", with_deep_water, ground("lush", "deep")),
        ("blades", "Combed blades / still pond", "Grass: short slanted blades, a fine even texture. Water: no foam, "
         "a light rim and long soft streaks.", with_deep_water, ground("blades", "calm")),
        ("clean", "Clean flat / clear shallows", "Grass: nearly flat with soft light patches, the cleanest. Water: "
         "wide pale rim, sparkles.", with_deep_water, ground("clean", "clear")),
        ("clover", "Clover clumps / bank shadow", "Grass: rounded clumps lit from the top-left. Water: as Tufted.",
         with_deep_water, ground("clover", "shade")),
    ],
}


def draw(round_name, key):
    """An option is (key, name, note, palette, setup): palette() returns a palette dict (None: the default),
    setup() then changes drawing settings before anything is drawn."""
    rd = ROUNDS[round_name]
    key, _, _, pal, *setup = next(o for o in rd["options"] if o[0] == key)
    palettes.PALETTES["lab"] = pal() if pal else palettes.PALETTES[palettes.DEFAULT]
    palettes.use("lab")
    for fn in setup:
        fn()
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
    if rd.get("field"):
        import preview
        f = preview.Map(34, 34)
        f.fill("terrain", 16, 0, 18, 34, "path")
        f.fill("terrain", 9, 19, 13, 24, "water")
        fi = iso.render(f, 0, objects=False, margin=0, woods=False)
        cx, cy = fi.width // 2, fi.height // 2
        fi.crop((cx - 300, cy - 130, cx + 300, cy + 130)).resize((1200, 520), 0).save(out / f"{key}-field.png")
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
    cards = [{"key": k, "name": n, "note": t} for k, n, t, *_ in rd["options"]]
    page = PAGE.replace("__TITLE__", rd["title"]).replace("__LEAD__", rd["lead"]) \
        .replace("__PICKS__", json.dumps(rd.get("picks", ["pick"]))).replace("__ROUND__", round_name).replace("__CARDS__", json.dumps(cards)) \
        .replace("__RAMPS__", "true" if round_name == "palette" else "false") \
        .replace("__FIELD__", "true" if rd.get("field") else "false")
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
.picks { display: flex; gap: 14px; flex-wrap: wrap; }
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
  <button type="button" data-v="field" aria-pressed="false" hidden>Open field (2x)</button>
</div>
<div class="grid" id="grid"></div>
<p><textarea id="general" placeholder="Anything else (mixing two options, a colour to change)..."></textarea></p>
</div>
<div class="bar"><span id="status">Pick one</span><button id="copy" type="button">Copy picks</button></div>
<script>
const CARDS = __CARDS__, RAMPS = __RAMPS__, PICKS = __PICKS__, FIELD = __FIELD__, KEY = "tiny-town/lab/__ROUND__";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
const grid = document.getElementById("grid");
for (const c of CARDS) {
  const a = document.createElement("article"); a.className = "card"; a.dataset.key = c.key;
  a.innerHTML = `<div class="pic"><img alt="${c.name}"></div>${RAMPS ? `<div class="ramps"><img src="${c.key}-ramps.png?v=${Date.now()}" alt="${c.name} ramps"></div>` : ""}
    <div class="foot"><b>${c.name}</b><p>${c.note}</p>
    <div class="picks">${PICKS.map((p) => `<label><input type="radio" name="${p}" value="${c.key}"> ${PICKS.length > 1 ? "Use for " + p : "Pick this"}</label>`).join("")}</div>
    <textarea data-note="${c.key}" placeholder="Note on ${c.name}..."></textarea></div>`;
  grid.append(a);
}
const v0 = Date.now();
function view(v) {
  S.view = v; save();
  for (const b of document.querySelectorAll(".tools button")) b.setAttribute("aria-pressed", b.dataset.v === v);
  for (const a of document.querySelectorAll(".card")) {
    const img = a.querySelector(".pic img");
    img.src = `${a.dataset.key}-${v === "zoom" || v === "field" ? v : "1x"}.png?v=${v0}`;
    img.style.width = v === "2x" ? "1546px" : "";
    a.querySelector(".pic").classList.toggle("fit", v === "zoom" || v === "field");
  }
}
if (FIELD) document.querySelector("[data-v=field]").hidden = false;
for (const b of document.querySelectorAll(".tools button")) b.addEventListener("click", () => view(b.dataset.v));
view(S.view || "1x");
for (const r of document.querySelectorAll("input[type=radio]")) { r.checked = S[r.name] === r.value; r.addEventListener("change", () => { S[r.name] = r.value; save(); sync(); }); }
for (const t of document.querySelectorAll("textarea")) { const k = t.dataset.note || "general"; t.value = S["note:" + k] || ""; t.addEventListener("input", () => { S["note:" + k] = t.value; save(); }); }
function sync() {
  for (const a of document.querySelectorAll(".card")) a.classList.toggle("p", PICKS.some((p) => S[p] === a.dataset.key));
  const left = PICKS.filter((p) => !S[p]);
  document.getElementById("status").textContent = left.length ? (PICKS.length > 1 ? "Pick a " + left.join(" and a ") : "Pick one") : "Ready to copy";
}
sync();
document.getElementById("copy").addEventListener("click", async () => {
  const name = (k) => CARDS.find((c) => c.key === k)?.name || "no pick";
  const lines = PICKS.map((p) => `__TITLE__ ${p === "pick" ? "pick" : p}: ${name(S[p])}`);
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
