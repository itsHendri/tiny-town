"""Themes: the same maps in another look. A theme is a palette plus drawers swapped for its own (art/theme_*.py),
built into its own tile folder; terrain values and prop names keep their meaning, so any map can switch.

    python art/iso_tiles.py --theme cyberpunk      -> tiles/themes/cyberpunk/iso/
    python art/tiles.py --theme cyberpunk          -> tiles/themes/cyberpunk/

The default theme (cottage) is built into tiles/ and tiles/iso/ as always. js/editor.js lists the same themes.
"""
import palettes

THEMES = ["cottage", "cyberpunk"]


def folder(theme):
    """Where a theme's top-down sheet goes (its isometric sheet goes in <folder>/iso)."""
    return "tiles" if theme in (None, "cottage") else f"tiles/themes/{theme}"


def use(theme, palette=None):
    """Switch the colours for a theme (before importing the art modules). Returns a function that swaps the
    drawers, to call once the art modules are imported."""
    if theme in (None, "cottage"):
        palettes.use(palette or palettes.DEFAULT)
        return lambda: None
    if theme == "cyberpunk":
        import theme_cyber
        palettes.PALETTES["cyber"] = theme_cyber.tweak(theme_cyber.palette(**theme_cyber.LOOKS[theme_cyber.PICK]))
        palettes.use("cyber")
        return theme_cyber.apply
    raise ValueError(f"no theme {theme!r} (themes: {', '.join(THEMES)})")


def palette_name(theme, palette=None):
    return palette or ("cyber" if theme == "cyberpunk" else palettes.DEFAULT)


def args(argv):
    """(palette, theme) from command-line arguments: [palette] [--theme NAME]."""
    rest, theme = list(argv), None
    if "--theme" in rest:
        i = rest.index("--theme")
        theme = rest[i + 1]
        del rest[i:i + 2]
    return (rest[0] if rest else None), theme
