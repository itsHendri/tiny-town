"""The look lab: candidate looks for one thing at a time, each drawn by the real renderer on the market village,
plus a picker page with a pick and a note per option: out/lab/<round>/index.html.

    python art/lab.py <round>          # rounds: palette, outline, ground, grass, trees (keep / drop), tree-look, house, cyber
    python art/lab.py <round> <key>    # draw one option (each runs in its own process: drawers cache by palette)
    python art/lab.py house-builder    # every combination of the house switches on a little street, with toggles
    python art/lab.py cyber-builder    # every combination of the cyber items' choices on a neon street
    python art/lab.py chip-builder     # the same for the circuit-board concepts
    python art/lab.py city-builder     # neon city polish: before / after for each change
    python art/lab.py tree-builder     # cyber trees, in a dense wood
    python art/lab.py tech-builder     # tech trees (tech objects that read as trees), in a dense wood

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


def tree_look(crown=None, shadow=None):
    """Setup for the tree round: swap iso_trees.crown and iso.place (the ground shadow)."""
    def setup():
        import iso
        import iso_trees
        import lab_trees as t
        if crown:
            iso_trees.crown = crown
        if shadow:
            t.ORIGINAL = iso.place
            iso.place = t.shadow_place(shadow)
    return setup


def _masses(**kw):
    import lab_trees
    return lab_trees.masses(**kw)


ROUNDS["tree-look"] = {
    "title": "Tree look",
    "lead": "Crowns built from a few big leaf masses with clean light and shadow, instead of many small speckled "
            "clumps. Pick a crown and a ground shadow (they can come from different cards). The Tree lineup view "
            "shows all 12 kinds; pines keep their tiers for now (the scots pine's needle clouds do change).",
    "picks": ["crown", "shadow"],
    "field": True, "field_label": "Tree lineup (3x)", "lineup": True,
    "options": [
        ("today", "Today: small speckled clumps / soft ellipse", "What the village draws now.", None, tree_look()),
        ("masses", "Big masses / cast shadow", "6-8 big masses, each lit top-left, the crown darker to the "
         "bottom-right, a dark line where masses overlap. Shadow falls bottom-right, crown-sized.", None,
         lambda: tree_look(_masses(), "cast")()),
        ("scalloped", "Leafy edges / contact shadow", "The same masses with bumpy, leafy outlines. Small shadow "
         "under the foot.", None, lambda: tree_look(_masses(scallop=0.14), "contact")()),
        ("dabs", "Leaf dabs / pool shadow", "Masses with the lit side broken into small leaf shapes. Shadow with a "
         "darker core.", None, lambda: tree_look(_masses(scallop=0.1, dabs=True), "pool")()),
        ("cel", "Flat bands / cast shadow", "Tone from the whole crown's light only (three flat bands), lines "
         "between masses: graphic, very clean.", None, lambda: tree_look(_masses(cel=True), "cast")()),
        ("fewer", "Fewest, biggest masses / cast", "Only 4-5 masses, bigger still: the boldest silhouettes.",
         None, lambda: tree_look(_masses(count=5.5, grow=2.0, scallop=0.08), "cast")()),
        ("no-rim", "Masses without lines / pool", "Big masses, no dark line between them: softer, rounder.", None,
         lambda: tree_look(_masses(rim=False, scallop=0.1), "pool")()),
    ],
}


def house_look(**kw):
    """Setup for the house round: change the storybook look (iso_props.LOOK keys)."""
    def setup():
        import iso_props
        iso_props.LOOKS["storybook"].update(kw)
    return setup


ALL_HOUSE = dict(ground_shadow=True, eave=6, windows="clean", roof_steps=True)
ROUNDS["house"] = {
    "title": "House look",
    "lead": "Each card changes one thing on the storybook houses (the last two combine them). These add up, so tick "
            "every change you want to keep. The House lineup view shows all five houses up close.",
    "keep": [], "keep_label": "Use this", "picks": ["keep"],
    "field": True, "field_label": "House lineup (3x)", "lineup": "houses",
    "options": [
        ("today", "Today", "The houses as they are.", None, house_look()),
        ("shadow", "Ground shadow", "A thin contact shadow along the wall feet and a short cast shadow off the shaded "
         "side, so houses sit on the ground.", None, house_look(ground_shadow=True)),
        ("eave", "Eave shadow", "The roof overhang shades the top of the walls, deeper and darker.", None,
         house_look(eave=6)),
        ("windows", "Clean windows", "No glazing bars (they eat the glass at this size): solid glass with a light streak; flower boxes kept.",
         None, house_look(windows="clean")),
        ("sills", "Clean windows, sills", "Clean windows with a light sill instead of the flower box.", None,
         house_look(windows="clean", flower_box=False)),
        ("roof", "Roof light steps", "Shingles lighter near the ridge, darker toward the eave, a lit ridge line, "
         "less moss.", None, house_look(roof_steps=True)),
        ("all", "All together", "Ground shadow, eave shadow, clean windows with flower boxes, roof steps.", None,
         house_look(**ALL_HOUSE)),
        ("all-sills", "All together, sills", "As above, with sills instead of flower boxes.", None,
         house_look(**ALL_HOUSE, flower_box=False)),
    ],
}


def cyber_pal(key):
    def pal():
        import theme_cyber
        return theme_cyber.palette(**theme_cyber.LOOKS[key])
    return pal


def cyber_apply():
    import theme_cyber
    theme_cyber.apply()


ROUNDS["cyber"] = {
    "title": "Cyberpunk palette",
    "lead": "The same village as a neon city, drawn by the first cyber versions of the hero items: plaza panels with "
            "glowing seams for grass, a canal for water, a lit walkway for the path, steel grates for cobbles, neon "
            "blocks for houses, neon foliage on the trees. Each card is one palette. Pick the palette; note anything "
            "about the shapes too (they get their own rounds next). The Block lineup shows the five buildings.",
    "field": True, "field_label": "Block lineup (3x)", "lineup": "houses",
    "options": [
        ("neon", "Neon night", "Indigo concrete, hot magenta signs, cyan water and glass, amber walkways.",
         cyber_pal("neon"), cyber_apply),
        ("blade", "Rain and sodium", "Cold blue-grey city, orange signs, teal water: a rainy noir street.",
         cyber_pal("blade"), cyber_apply),
        ("synth", "Synthwave", "Purple ground, pink and violet neon, red-orange light.", cyber_pal("synth"),
         cyber_apply),
        ("acid", "Acid grid", "Deep teal city with green neon, like a terminal screen.", cyber_pal("acid"),
         cyber_apply),
        ("vapor", "Vapor dusk", "Lighter lilac concrete, soft pink and sky blue: friendlier, less night.",
         cyber_pal("vapor"), cyber_apply),
        ("rain", "Wet steel", "Neutral steel grey, red neon, pale cyan: restrained, very readable.",
         cyber_pal("rain"), cyber_apply),
    ],
}


# ---------- the house builder: every combination of the house switches, flipped live on one page ----------

HOUSE_SWITCHES = [   # (key, label, note, LOOK changes when on)
    ("shadow", "Ground shadow", "Contact shadow along the wall feet, a short cast shadow off the shaded side.",
     {"ground_shadow": True}),
    ("eave", "Eave shadow", "The roof overhang shades the top of the walls.", {"eave": 6}),
    ("windows", "Clean windows", "Solid glass with a light streak, no glazing bars.", {"windows": "clean"}),
    ("sills", "Sills, no flower boxes", "A light sill under each clean window instead of the flower box.",
     {"flower_box": False}),
    ("roof", "Roof light steps", "Lighter near the ridge, darker toward the eave, a lit ridge line, less moss.",
     {"roof_steps": True}),
]


def house_street():
    """All five houses on a little street: grass behind, a path in front, a tree for scale. Returns (map, spots)."""
    import preview
    m = preview.Map(25, 7)
    m.fill("terrain", 4, 0, 6, 25, "path")
    spots = [("cottage-red", 2, 3), ("cottage-brown", 6, 3), ("tree-1", 8, 1), ("thatch-house", 12, 3),
             ("townhouse", 16, 3), ("longhouse", 21, 3)]
    return m, spots


def house_builder():
    import itertools
    from PIL import Image
    palettes.use(palettes.DEFAULT)
    import iso
    import iso_props
    from iso_nature import nature
    out = OUT / "house-builder"
    out.mkdir(parents=True, exist_ok=True)
    base = dict(iso_props.LOOKS["storybook"])
    tree = nature()["tree-1"]
    box = None
    for bits in itertools.product((0, 1), repeat=len(HOUSE_SWITCHES)):
        iso_props.LOOKS["storybook"] = dict(base)
        for on, (_, _, _, change) in zip(bits, HOUSE_SWITCHES):
            if on:
                iso_props.LOOKS["storybook"].update(change)
        iso_props.use_look("storybook")
        m, spots = house_street()
        for name, c, r in spots:
            spr = tree if name == "tree-1" else iso_props.house(**iso_props.HOUSES[name])[0]
            m.objects.append((spr, c * 16 + 8, (r + 1) * 16))
        im = iso.render(m, 0, margin=1, woods=False)
        box = box or im.getbbox()
        im.crop(box).save(out / ("".join(map(str, bits)) + ".png"))
    iso_props.LOOKS["storybook"] = base
    switches = [{"key": k, "label": l, "note": n} for k, l, n, _ in HOUSE_SWITCHES]
    (out / "index.html").write_text(BUILDER_PAGE.replace("__SWITCHES__", json.dumps(switches)))
    print("wrote out/lab/house-builder/index.html", 2 ** len(HOUSE_SWITCHES), "combinations")


BUILDER_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>House Builder</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@700&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
:root { --bg: #efe9dc; --panel: #fffaf1; --fg: #26303f; --muted: #5f6672; --line: #ddd2bd; --on: #2f7448; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 "IBM Plex Sans", system-ui, sans-serif; }
.page { max-width: 1400px; margin: 0 auto; padding: 24px 16px 110px; display: grid; gap: 16px; }
h1 { font: 700 32px/1.1 "Pixelify Sans", monospace; margin: 0; }
.lead { color: var(--muted); margin: 0; max-width: 80ch; }
.controls { display: flex; flex-wrap: wrap; gap: 10px; }
.sw { display: flex; gap: 10px; align-items: flex-start; background: var(--panel); border: 1.5px solid var(--line); border-radius: 12px; padding: 10px 12px; cursor: pointer; max-width: 300px; }
.sw:has(input:checked) { border-color: var(--on); box-shadow: 0 0 0 1px var(--on); }
.sw input { margin-top: 4px; accent-color: var(--on); }
.sw b { display: block; font-weight: 600; } .sw span { color: var(--muted); font-size: 13px; }
.bar2 { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.bar2 button { border: 1.5px solid var(--line); background: var(--panel); color: var(--fg); border-radius: 8px; padding: 5px 12px; font: 600 13px inherit; cursor: pointer; }
.bar2 button[aria-pressed=true] { border-color: var(--on); color: var(--on); }
.stage { display: grid; gap: 12px; }
.view { background: var(--panel); border: 1.5px solid var(--line); border-radius: 14px; overflow: hidden; }
.view h2 { font: 600 13px inherit; margin: 0; padding: 8px 12px; color: var(--muted); }
.scroll { overflow: auto; background: #6f8f45; }
.scroll img { display: block; image-rendering: pixelated; max-width: none; }
.bar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; gap: 10px; align-items: center; background: var(--fg); color: var(--panel); padding: 8px 10px 8px 16px; border-radius: 12px; font-size: 13.5px; max-width: calc(100% - 32px); }
.bar button { border: 0; border-radius: 8px; background: var(--panel); color: var(--fg); font: 600 13px inherit; padding: 6px 12px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--on); outline-offset: 2px; }
</style></head><body><div class="page">
<h1>House builder</h1>
<p class="lead">Flip the switches: every house on the street changes together, today's street stays below to compare.
Hold <b>Space</b> (or the Compare button) to flip the top picture back to today.</p>
<div class="controls" id="controls"></div>
<div class="bar2" role="group" aria-label="Zoom">
  <button type="button" data-z="1">1x</button><button type="button" data-z="2">2x</button>
  <button type="button" data-z="3">3x</button><button type="button" data-z="4">4x</button>
  <button type="button" id="cmp">Hold to compare</button>
</div>
<div class="stage">
  <section class="view"><h2 id="mine-t">Your houses</h2><div class="scroll"><img id="mine" alt="The houses with your switches"></div></section>
  <section class="view"><h2>Today</h2><div class="scroll"><img id="today" alt="The houses today"></div></section>
</div>
<textarea id="note" placeholder="Notes (anything to tweak)..." style="width:100%;min-height:40px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:8px;padding:6px 8px;font:13px inherit"></textarea>
</div>
<div class="bar"><span id="status"></span><button id="copy" type="button">Copy picks</button></div>
<script>
const SW = __SWITCHES__, KEY = "tiny-town/house-builder";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
S.on = S.on || {}; S.zoom = S.zoom || 3;
const ctl = document.getElementById("controls");
for (const s of SW) {
  const l = document.createElement("label"); l.className = "sw";
  l.innerHTML = `<input type="checkbox" data-k="${s.key}"><div><b>${s.label}</b><span>${s.note}</span></div>`;
  ctl.append(l);
}
const bits = (on) => SW.map((s) => on[s.key] ? 1 : 0).join("");
const mine = document.getElementById("mine"), today = document.getElementById("today");
let comparing = false;
function draw() {
  mine.src = (comparing ? bits({}) : bits(S.on)) + ".png";
  today.src = bits({}) + ".png";
  document.getElementById("mine-t").textContent = comparing ? "Today (comparing)" : "Your houses";
  for (const img of [mine, today]) img.onload = () => { img.style.width = img.naturalWidth * S.zoom + "px"; };
  for (const b of document.querySelectorAll("[data-z]")) b.setAttribute("aria-pressed", +b.dataset.z === S.zoom);
  const n = SW.filter((s) => S.on[s.key]).length;
  document.getElementById("status").textContent = n ? `${n} switch${n > 1 ? "es" : ""} on` : "All off (today)";
}
for (const i of document.querySelectorAll("[data-k]")) { i.checked = !!S.on[i.dataset.k]; i.addEventListener("change", () => { S.on[i.dataset.k] = i.checked; save(); draw(); }); }
for (const b of document.querySelectorAll("[data-z]")) b.addEventListener("click", () => { S.zoom = +b.dataset.z; save(); draw(); });
const cmp = document.getElementById("cmp");
const hold = (v) => { if (comparing !== v) { comparing = v; draw(); } };
cmp.addEventListener("pointerdown", () => hold(true)); for (const e of ["pointerup", "pointerleave"]) cmp.addEventListener(e, () => hold(false));
addEventListener("keydown", (e) => { if (e.code === "Space" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); hold(true); } });
addEventListener("keyup", (e) => { if (e.code === "Space") hold(false); });
const note = document.getElementById("note"); note.value = S.note || ""; note.addEventListener("input", () => { S.note = note.value; save(); });
draw();
document.getElementById("copy").addEventListener("click", async () => {
  const on = SW.filter((s) => S.on[s.key]).map((s) => s.label);
  const text = `House builder: ${on.length ? on.join(", ") : "all off (today)"}` + (S.note ? `\n  note: ${S.note}` : "");
  try { await navigator.clipboard.writeText(text); document.getElementById("status").textContent = "Copied, paste it to Claude"; } catch { prompt("Copy this:", text); }
});
</script></body></html>
"""


# ---------- the cyber builder: a choice per item, every combination pre-rendered on a neon street ----------

CYBER_GROUPS = [   # (key, label, [(value, label, note)]); the first is v0
    ("plaza", "Plaza (grass)", [("panels", "Panels", "2 x 2 dark panels per cell, some seams glowing."),
                                ("slabs", "Big slabs", "One slab per cell, fewer glowing seams."),
                                ("puddles", "Puddles", "Panels with neon puddles reflecting the signs."),
                                ("quiet", "Quiet", "Panels, no glowing seams.")]),
    ("canal", "Canal (water)", [("neon", "Neon reflections", "Short reflections of the signs drifting."),
                                ("calm", "Calm", "Dark water, the edge glow, the odd sparkle."),
                                ("bands", "Bands", "Long bright bands of reflected light.")]),
    ("walkway", "Walkway (path)", [("tiles", "Tiles", "Small tiles, a glowing amber curb."),
                                   ("hazard", "Hazard curb", "Tiles, the curb striped like a warning."),
                                   ("road", "Glowing road", "Dark asphalt, glowing dashes on the cell lines.")]),
    ("windows", "Windows", [("random", "Random", "Every window a random neon colour."),
                            ("one", "One per building", "Each building lit in its sign's colour."),
                            ("warm", "Warm", "Warm light in the windows; neon only on signs and trims."),
                            ("sparse", "Sparse", "Most windows dark, a few lit.")]),
    ("trees", "Trees", [("neon", "Neon foliage", "The tree shapes in neon pink, pines in cyan."),
                        ("rim", "Dark, neon rim", "Dark crowns, a cyan rim of light on the lit side."),
                        ("holo", "Holo", "Cyan hologram trees.")]),
]


def cyber_street():
    """A little neon street: plaza, a canal with a bridge, a walkway along it, a grated square, three blocks,
    trees, weeds and lamps."""
    import preview
    m = preview.Map(18, 12)
    m.fill("terrain", 6, 0, 8, 18, "water")
    m.fill("terrain", 6, 9, 8, 11, "bridge")
    m.fill("terrain", 4, 0, 6, 18, "path")
    m.fill("terrain", 8, 9, 12, 11, "path")
    m.fill("terrain", 9, 12, 12, 17, "cobbles")
    for r in range(9, 12):
        for c in range(1, 5):
            m.deco[r][c] = "tallgrass"
    spots = [("cottage-red", 3, 3), ("townhouse", 8, 3), ("longhouse", 14, 3), ("tree-1", 11, 2), ("pine-3", 1, 1),
             ("tree-2-d2", 6, 10), ("birch-2", 16, 8), ("lamp-iso", 5, 4), ("lamp-iso", 12, 4), ("oak-3", 13, 10),
             ("willow-1", 4, 10), ("cypress-2", 17, 1), ("blossom-1", 8, 8), ("tree-6", 12, 8), ("maple-1", 0, 8)]
    return m, spots


CHIP_GROUPS = [
    ("plaza", "Board (grass)", [("panels", "Neon panels", "Today's pick: dark panels, some seams glowing."),
                                ("pcb", "Circuit board", "Dark solder mask, faint traces along the grid, vias."),
                                ("pcb-green", "Green board", "The classic green circuit board."),
                                ("silicon", "Silicon die", "A fine grid of cells, the odd one lit.")]),
    ("walkway", "Traces (path)", [("tiles", "Tiles", "Today's pick: small tiles, a glowing amber curb."),
                                  ("copper", "Copper", "Copper traces with a bright edge and solder pads."),
                                  ("glow", "Glowing edge", "Dark traces outlined in neon.")]),
    ("canal", "Water", [("neon", "Neon reflections", "Today's pick: a canal reflecting the signs."),
                        ("databus", "Data bus", "Fine lines with light pulses racing along."),
                        ("coolant", "Coolant", "Glowing cyan coolant, bubbles rising."),
                        ("fiber", "Fiber optics", "Optical fibres along the grid, coloured pulses.")]),
    ("trees", "Trees", [("holo", "Holo trees", "Today's pick: cyan hologram trees."),
                        ("capacitors", "Capacitors", "Every tree a capacitor, sizes and colours varied."),
                        ("mixed", "Mixed parts", "Capacitors, a transformer, LEDs, a coil, pylons."),
                        ("stalks", "LED stalks", "LEDs on poles of different heights, glowing."),
                        ("pylons", "Pylons", "Power pylons with glowing insulators.")]),
    ("buildings", "Buildings", [("blocks", "Neon blocks", "Today's buildings."),
                                ("chips", "Chips", "Black chips with silver pins; the tower is a heatsink.")]),
]
CITY_GROUPS = [   # neon city polish: before / after for each change
    ("parts", "Tree parts", [("v1", "As now", "Capacitors, a transformer, LEDs, a coil, pylons."),
                             ("city", "City-scale", "Storage tanks, a transformer station, LED street poles, a ring "
                              "monument, radio masts, pylons.")]),
    ("windows", "Windows", [("random", "Random", "As now: every window a random colour."),
                            ("calm", "Calmer", "One colour per floor, about half the windows dark.")]),
    ("signs", "Signs", [("one", "One sign", "As now: one sign on the front."),
                        ("varied", "Varied", "Blade signs sticking out from the corners, rooftop billboards.")]),
    ("glow", "Neon glow", [("off", "Off", "As now."),
                           ("on", "On", "A soft halo round signs, trims and lamps; light spilling onto the ground.")]),
    ("roofs", "Roofs", [("plain", "Plain", "As now."),
                        ("busy", "Busy", "Rows of AC units, satellite dishes, lit antennas.")]),
]
TREE_GROUPS = [   # cyber trees: trees stay trees, judged in a dense wood
    ("trees", "Broadleaf trees", [("neon", "Neon", "As before the parts: the tree shapes in neon pink."),
                                  ("holo", "Holo", "Cyan holograms."),
                                  ("biolum", "Bioluminescent", "Dark crowns with glowing specks."),
                                  ("outline", "Neon outline", "Dark silhouettes, a neon rim on the lit edge."),
                                  ("cable", "Cable trees", "Crowns of cable bundles, coloured wires, LEDs.")]),
    ("pines", "Pines", [("neon", "Neon", "Cyan tiers."), ("holo", "Holo", "Cyan holograms."),
                        ("biolum", "Bioluminescent", "Dark tiers with glowing specks."),
                        ("outline", "Neon outline", "Dark tiers, a neon rim.")]),
    ("planter", "Planters", [("no", "None", "Trees straight on the plaza."),
                             ("yes", "Lit planters", "Broadleaf trees in concrete boxes with a lit rim.")]),
    ("glow", "Glow", [("on", "On", "Neon pixels get a soft halo."), ("off", "Off", "No halo.")]),
]
TECH_GROUPS = [   # tech trees: tech objects that read as trees (after Hendri's references)
    ("trees", "Tech trees", [("outline", "Neon outline", "The last round's best: dark trees with a neon rim."),
                             ("tech-data", "Data tree", "Dark crown, glowing cubes, light dropping from them, a lit "
                              "pedestal."),
                             ("tech-circuit", "Circuit tree", "Angular crown, traces fanning out from a chip, gold "
                              "vias, a neon outline."),
                             ("tech-wire", "Wireframe hologram", "See-through crown with scanlines over a projector."),
                             ("tech-voxel", "Voxel tree", "A crown of little glowing iso cubes."),
                             ("tech-fibre", "Fibre tree", "Straight fibres fanning up, glowing tips.")]),
    ("glow", "Glow", [("on", "On", "Neon pixels get a soft halo."), ("off", "Off", "No halo.")]),
]
BUILDERS = {"cyber-builder": ("Cyber builder", CYBER_GROUPS), "chip-builder": ("Circuit builder", CHIP_GROUPS),
            "city-builder": ("Neon city polish", CITY_GROUPS), "tree-builder": ("Cyber trees", TREE_GROUPS, "park"),
            "tech-builder": ("Tech trees", TECH_GROUPS, "park")}


def cyber_park():
    """A dense wood beside a street: is it a glowing park or a mess? Plus street trees and two blocks."""
    import preview
    from iso_trees import TREE_ALIASES  # noqa: F401
    from dualgrid import h
    kinds = ["tree-1", "tree-2-d2", "oak-3", "maple-1", "blossom-1", "tree-6", "birch-2", "poplar-1", "willow-1",
             "pine-2", "pine-3", "cypress-2"]
    m = preview.Map(20, 15)
    m.fill("terrain", 6, 0, 8, 20, "path")
    m.fill("terrain", 0, 15, 6, 17, "water")
    spots = [("townhouse", 13, 3), ("cottage-red", 9, 3), ("lamp-iso", 4, 5), ("tree-1", 2, 5), ("birch-2", 6, 5),
             ("tree-6", 18, 8)]
    for r in range(9, 15):
        for c in range(0, 15):
            if h("wood", c, r) < 0.8:
                spots.append((kinds[int(h("kind", c, r) * len(kinds))], c, r))
    return m, spots


def cyber_builder(name="cyber-builder"):
    import itertools
    import subprocess as sp
    title, groups_ = BUILDERS[name][:2]
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(*[range(len(g[2])) for g in groups_]))
    procs = 8                                                    # split over processes (drawers cache per look)
    jobs = [sp.Popen([sys.executable, __file__, "builder-part", name, str(k), str(procs)]) for k in range(procs)]
    for j in jobs:
        j.wait()
    groups = [{"key": k, "label": l, "options": [{"value": v, "label": vl, "note": n} for v, vl, n in opts]}
              for k, l, opts in groups_]
    page = CYBER_PAGE.replace("__GROUPS__", json.dumps(groups)).replace("Cyber builder", title) \
        .replace("Cyber Builder", title.title()).replace("tiny-town/cyber-builder", "tiny-town/" + name)
    (out / "index.html").write_text(page)
    print(f"wrote out/lab/{name}/index.html", len(combos), "combinations")


def cyber_builder_part(name, k, n):
    """Draw every n-th combination starting at k, each in a fresh process (the drawers are cached)."""
    import itertools
    combos = list(itertools.product(*[range(len(g[2])) for g in BUILDERS[name][1]]))[k::n]
    for combo in combos:
        subprocess.run([sys.executable, __file__, "builder-one", name, "-".join(map(str, combo))], check=True)


def cyber_builder_one(name, key):
    import theme_cyber
    combo = list(map(int, key.split("-")))
    for (gk, _, opts), i in zip(BUILDERS[name][1], combo):
        theme_cyber.CYBER[gk] = opts[i][0]
    if name == "tech-builder" and theme_cyber.CYBER["trees"] == "outline":
        theme_cyber.CYBER["pines"] = "outline"
    palettes.PALETTES["cyber"] = theme_cyber.tweak(theme_cyber.palette(**theme_cyber.LOOKS[theme_cyber.PICK]))
    palettes.use("cyber")
    import iso
    import iso_props
    from render_map import props
    theme_cyber.apply()
    P = props()
    m, spots = cyber_park() if BUILDERS[name][2:] == ("park",) else cyber_street()
    for nm, c, r in spots:
        spr = iso_props.house(**iso_props.HOUSES[nm])[0] if nm in iso_props.HOUSES else P[nm]
        m.objects.append((spr, c * 16 + 8, (r + 1) * 16))
    im = iso.render(m, 0, margin=1, woods=False)
    im.crop(im.getbbox()).save(OUT / name / f"{key}.png")


TREE_NAMES = r"^(tree|oak|birch|poplar|willow|maple|blossom|fruit|pine|spruce|cypress)"
# one tree per distinct silhouette (the suggestion pre-checked on the page)
TREE_KEEP = ["oak-3", "tree-1", "maple-1", "birch-2", "blossom-1", "tree-6", "poplar-1", "willow-1", "pine-3",
             "cypress-2", "pine-2"]


def cull_round(title, lead, pattern, keep):
    """A keep / drop round over props already in tiles/iso/ (no rendering: each card is the sprite)."""
    import re
    meta = json.loads((ROOT / "tiles" / "iso" / "props.json").read_text())["props"]
    names = [n for n in sorted(meta) if re.match(pattern, n) and not meta[n].get("alias")]
    return {"title": title, "lead": lead, "cull": True, "keep": keep, "picks": ["keep"],
            "options": [(n, n, "", None) for n in names]}


def draw_cull(round_name):
    from PIL import Image
    rd, out = ROUNDS[round_name], OUT / round_name
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT / "tiles" / "iso" / "props.json").read_text())["props"]
    sheet = Image.open(ROOT / "tiles" / "iso" / "props.png")
    W = max(meta[k]["w"] for k, *_ in rd["options"]) + 8
    H = max(meta[k]["h"] for k, *_ in rd["options"]) + 8
    for key, *_ in rd["options"]:
        q = meta[key]
        spr = sheet.crop((q["x"], q["y"], q["x"] + q["w"], q["y"] + q["h"]))
        im = Image.new("RGBA", (W, H), palettes.PAL["g1"])
        im.alpha_composite(spr, ((W - q["w"]) // 2, H - 4 - q["h"]))
        im.save(out / f"{key}-1x.png")
        im.resize((W * 4, H * 4), 0).save(out / f"{key}-zoom.png")


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
    if rd.get("lineup"):
        from PIL import Image
        if rd["lineup"] == "houses":
            import iso_props
            iso_props.use_look("storybook")
            ts = [iso_props.house(**kw)[0] for kw in iso_props.HOUSES.values()]
        else:
            import iso_trees
            ts = list(iso_trees.trees().values())
        W, H = sum(t.w for t in ts) + 6 * len(ts) + 6, max(t.h for t in ts) + 10
        im2 = Image.new("RGBA", (W, H), palettes.PAL["g1"])
        x = 6
        for t in ts:
            im2.alpha_composite(t.im, (x, H - 5 - t.h))
            x += t.w + 6
        im2.resize((W * 3, H * 3), 0).save(out / f"{key}-field.png")
    elif rd.get("field"):
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
    if rd.get("cull"):
        palettes.use(palettes.DEFAULT)
        draw_cull(round_name)
    else:
        for key, *_ in rd["options"]:
            subprocess.run([sys.executable, __file__, round_name, key], check=True)
            print("drew", key)
    cards = [{"key": k, "name": n, "note": t} for k, n, t, *_ in rd["options"]]
    page = PAGE.replace("__TITLE__", rd["title"]).replace("__LEAD__", rd["lead"]) \
        .replace("__PICKS__", json.dumps(rd.get("picks", ["pick"]))).replace("__ROUND__", round_name).replace("__CARDS__", json.dumps(cards)) \
        .replace("__RAMPS__", "true" if round_name == "palette" else "false") \
        .replace("__FIELD__", "true" if rd.get("field") else "false").replace("__CULL__", "true" if rd.get("cull") else "false") \
        .replace("__KEEP__", json.dumps(rd.get("keep"))).replace("__KEEP_LABEL__", json.dumps(rd.get("keep_label", "Keep"))) \
        .replace("Open field (2x)", rd.get("field_label", "Open field (2x)"))
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
.grid.small { grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); }
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
const CARDS = __CARDS__, RAMPS = __RAMPS__, PICKS = __PICKS__, FIELD = __FIELD__, KEEP = __KEEP__, KEEP_LABEL = __KEEP_LABEL__, KEY = "tiny-town/lab/__ROUND__";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
const grid = document.getElementById("grid");
if (KEEP && __CULL__) grid.classList.add("small");
for (const c of CARDS) {
  const a = document.createElement("article"); a.className = "card"; a.dataset.key = c.key;
  a.innerHTML = `<div class="pic"><img alt="${c.name}"></div>${RAMPS ? `<div class="ramps"><img src="${c.key}-ramps.png?v=${Date.now()}" alt="${c.name} ramps"></div>` : ""}
    <div class="foot"><b>${c.name}</b><p>${c.note}</p>
    <div class="picks">${KEEP ? `<label><input type="checkbox" name="keep" value="${c.key}"> ${KEEP_LABEL}</label>` : PICKS.map((p) => `<label><input type="radio" name="${p}" value="${c.key}"> ${PICKS.length > 1 ? "Use for " + p : "Pick this"}</label>`).join("")}</div>
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
view(S.view || (KEEP && __CULL__ ? "zoom" : "1x"));
if (KEEP && !S.keep) S.keep = KEEP.slice();
for (const r of document.querySelectorAll("input[type=checkbox]")) { r.checked = S.keep.includes(r.value); r.addEventListener("change", () => { S.keep = S.keep.filter((k) => k !== r.value); if (r.checked) S.keep.push(r.value); save(); sync(); }); }
for (const r of document.querySelectorAll("input[type=radio]")) { r.checked = S[r.name] === r.value; r.addEventListener("change", () => { S[r.name] = r.value; save(); sync(); }); }
for (const t of document.querySelectorAll("textarea")) { const k = t.dataset.note || "general"; t.value = S["note:" + k] || ""; t.addEventListener("input", () => { S["note:" + k] = t.value; save(); }); }
function sync() {
  for (const a of document.querySelectorAll(".card")) a.classList.toggle("p", KEEP ? S.keep.includes(a.dataset.key) : PICKS.some((p) => S[p] === a.dataset.key));
  if (KEEP) { document.getElementById("status").textContent = __CULL__ ? `Keeping ${S.keep.length} of ${CARDS.length}` : `${S.keep.length} ticked`; return; }
  const left = PICKS.filter((p) => !S[p]);
  document.getElementById("status").textContent = left.length ? (PICKS.length > 1 ? "Pick a " + left.join(" and a ") : "Pick one") : "Ready to copy";
}
sync();
document.getElementById("copy").addEventListener("click", async () => {
  const name = (k) => CARDS.find((c) => c.key === k)?.name || "no pick";
  const lines = KEEP ? [`__TITLE__ ${__CULL__ ? "keep" : "use"} (${S.keep.length}): ${CARDS.filter((c) => S.keep.includes(c.key)).map((c) => __CULL__ ? c.key : c.name).join(", ")}`]
    : PICKS.map((p) => `__TITLE__ ${p === "pick" ? "pick" : p}: ${name(S[p])}`);
  for (const c of CARDS) if (S["note:" + c.key]) lines.push(`  ${c.name}: ${S["note:" + c.key]}`);
  if (S["note:general"]) lines.push(`  note: ${S["note:general"]}`);
  const text = lines.join("\\n");
  try { await navigator.clipboard.writeText(text); document.getElementById("status").textContent = "Copied, paste it to Claude"; } catch { prompt("Copy this:", text); }
});
</script></body></html>
"""

ROUNDS["trees"] = cull_round(
    "Trees", "36 trees today, many near-duplicates (six round trees in three shades each, two cypresses). Keep the ones "
    "worth refining; dropped names will point at the closest kept tree, so old maps still open. Pre-checked: one per "
    "distinct shape. Variety within a kind comes back in the refine round (each placed tree drawn a little "
    "differently). Pines now sit in Trees.", TREE_NAMES, TREE_KEEP)


CYBER_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cyber Builder</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@700&family=IBM+Plex+Sans:wght@400;600&display=swap">
<style>
:root { --bg: #efe9dc; --panel: #fffaf1; --fg: #26303f; --muted: #5f6672; --line: #ddd2bd; --on: #2f7448; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #191d24; --panel: #222731; --fg: #eef0f4; --muted: #a9b0bc; --line: #353c4a; --on: #9ad86f; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.5 "IBM Plex Sans", system-ui, sans-serif; }
.page { max-width: 1500px; margin: 0 auto; padding: 24px 16px 110px; display: grid; gap: 14px; }
h1 { font: 700 32px/1.1 "Pixelify Sans", monospace; margin: 0; }
.lead { color: var(--muted); margin: 0; max-width: 80ch; }
.groups { display: grid; gap: 10px; }
.group { display: grid; grid-template-columns: 150px 1fr; gap: 10px; align-items: start; }
.group > b { font-weight: 600; padding-top: 6px; }
.opts { display: flex; flex-wrap: wrap; gap: 6px; }
.opt { border: 1.5px solid var(--line); background: var(--panel); color: var(--fg); border-radius: 8px; padding: 5px 12px; font: 600 13px inherit; cursor: pointer; }
.opt[aria-pressed=true] { border-color: var(--on); color: var(--on); box-shadow: 0 0 0 1px var(--on); }
.hint { color: var(--muted); font-size: 13px; min-height: 20px; }
.bar2 { display: flex; gap: 8px; flex-wrap: wrap; }
.bar2 button { border: 1.5px solid var(--line); background: var(--panel); color: var(--fg); border-radius: 8px; padding: 5px 12px; font: 600 13px inherit; cursor: pointer; }
.bar2 button[aria-pressed=true] { border-color: var(--on); color: var(--on); }
.view { background: var(--panel); border: 1.5px solid var(--line); border-radius: 14px; overflow: hidden; }
.view h2 { font: 600 13px inherit; margin: 0; padding: 8px 12px; color: var(--muted); }
.scroll { overflow: auto; background: #1c1d2b; }
.scroll img { display: block; image-rendering: pixelated; max-width: none; }
.bar { position: fixed; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; gap: 10px; align-items: center; background: var(--fg); color: var(--panel); padding: 8px 10px 8px 16px; border-radius: 12px; font-size: 13.5px; max-width: calc(100% - 32px); }
.bar button { border: 0; border-radius: 8px; background: var(--panel); color: var(--fg); font: 600 13px inherit; padding: 6px 12px; cursor: pointer; }
:focus-visible { outline: 2px solid var(--on); outline-offset: 2px; }
@media (max-width: 600px) { .group { grid-template-columns: 1fr; } }
</style></head><body><div class="page">
<h1>Cyber builder</h1>
<p class="lead">Pick one look per item; the street redraws with your mix (every combination is the real renderer).
Hold <b>Space</b> (or Compare) to flip to the first version of everything.</p>
<div class="groups" id="groups"></div>
<div class="hint" id="hint"></div>
<div class="bar2" role="group" aria-label="Zoom">
  <button type="button" data-z="1">1x</button><button type="button" data-z="2">2x</button>
  <button type="button" data-z="3">3x</button><button type="button" id="cmp">Hold to compare</button>
</div>
<section class="view"><h2 id="t">Your street</h2><div class="scroll"><img id="img" alt="The neon street with your choices"></div></section>
<textarea id="note" placeholder="Notes (anything to tweak)..." style="width:100%;min-height:40px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:8px;padding:6px 8px;font:13px inherit"></textarea>
</div>
<div class="bar"><span id="status">Pick a look per item</span><button id="copy" type="button">Copy picks</button></div>
<script>
const G = __GROUPS__, KEY = "tiny-town/cyber-builder";
let S = {}; try { S = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { S = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch {} };
S.pick = S.pick || {}; S.zoom = S.zoom || 2;
const box = document.getElementById("groups"), hint = document.getElementById("hint"), img = document.getElementById("img");
for (const g of G) {
  const row = document.createElement("div"); row.className = "group";
  row.innerHTML = `<b>${g.label}</b><div class="opts" role="group" aria-label="${g.label}">${g.options.map((o, i) => `<button type="button" class="opt" data-g="${g.key}" data-i="${i}" title="${o.note}">${o.label}</button>`).join("")}</div>`;
  box.append(row);
}
let comparing = false;
function draw() {
  const key = G.map((g) => comparing ? 0 : (S.pick[g.key] || 0)).join("-");
  img.src = key + ".png"; img.onload = () => { img.style.width = img.naturalWidth * S.zoom + "px"; };
  document.getElementById("t").textContent = comparing ? "First version (comparing)" : "Your street";
  for (const b of document.querySelectorAll(".opt")) b.setAttribute("aria-pressed", (S.pick[b.dataset.g] || 0) === +b.dataset.i);
  for (const b of document.querySelectorAll("[data-z]")) b.setAttribute("aria-pressed", +b.dataset.z === S.zoom);
}
for (const b of document.querySelectorAll(".opt")) {
  b.addEventListener("click", () => { S.pick[b.dataset.g] = +b.dataset.i; save(); draw(); });
  b.addEventListener("pointerenter", () => { hint.textContent = b.title; });
  b.addEventListener("focus", () => { hint.textContent = b.title; });
}
for (const b of document.querySelectorAll("[data-z]")) b.addEventListener("click", () => { S.zoom = +b.dataset.z; save(); draw(); });
const cmp = document.getElementById("cmp"), hold = (v) => { if (comparing !== v) { comparing = v; draw(); } };
cmp.addEventListener("pointerdown", () => hold(true)); for (const e of ["pointerup", "pointerleave"]) cmp.addEventListener(e, () => hold(false));
addEventListener("keydown", (e) => { if (e.code === "Space" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); hold(true); } });
addEventListener("keyup", (e) => { if (e.code === "Space") hold(false); });
const note = document.getElementById("note"); note.value = S.note || ""; note.addEventListener("input", () => { S.note = note.value; save(); });
draw();
document.getElementById("copy").addEventListener("click", async () => {
  const text = "Cyber builder: " + G.map((g) => `${g.label}: ${g.options[S.pick[g.key] || 0].label}`).join("; ") + (S.note ? `\n  note: ${S.note}` : "");
  try { await navigator.clipboard.writeText(text); document.getElementById("status").textContent = "Copied, paste it to Claude"; } catch { prompt("Copy this:", text); }
});
</script></body></html>
"""


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "house-builder":
        house_builder()
    elif len(sys.argv) > 1 and sys.argv[1] in BUILDERS:
        cyber_builder(sys.argv[1])
    elif len(sys.argv) > 1 and sys.argv[1] == "builder-part":
        cyber_builder_part(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif len(sys.argv) > 1 and sys.argv[1] == "builder-one":
        cyber_builder_one(sys.argv[2], sys.argv[3])
    elif len(sys.argv) > 2:
        draw(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else "palette")
