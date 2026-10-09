"""A small isometric village scene for comparing looks (houses, later stalls and props).

    python art/iso_village.py <out.png> [palette] [house look]
"""
import sys

import palettes


def scene(palette="earthy", look="cosy"):
    palettes.use(palette)
    import iso
    import iso_props
    import preview
    from sprites import bush, pine, tree
    iso_props.use_look(look)
    m = preview.Map(18, 15)
    m.fill("terrain", 7, 0, 9, 18, "path")                   # the high street
    m.fill("terrain", 0, 8, 15, 10, "path")                  # the cross street
    m.fill("terrain", 11, 1, 14, 5, "water")                 # a pond
    m.fill("height", 0, 13, 4, 18, 1)                        # a little rise in the back corner
    m.fill("terrain", 1, 1, 4, 4, "soil")
    houses = [("cottage-red", 4, 5), ("thatch-house", 14, 5), ("townhouse", 6, 13), ("longhouse", 15, 13), ("cottage-brown", 16, 2)]
    for name, c, r in houses:
        spr, _, _ = iso_props.house(**iso_props.HOUSES[name])
        m.objects.append((spr, c * 16 + 8, (r + 1) * 16))
    for k, (c, r) in enumerate([(0, 5), (1, 12), (11, 2), (12, 1), (2, 14), (17, 9), (10, 14), (0, 9), (16, 11)]):
        spr = pine(f"p{k}") if k % 3 == 0 else bush(f"b{k}") if k % 3 == 2 else tree(f"t{k}", 1.0)
        m.objects.append((spr, c * 16 + 8, (r + 1) * 16))
    return iso.render(m, 0)


if __name__ == "__main__":
    im = scene(sys.argv[2] if len(sys.argv) > 2 else "earthy", sys.argv[3] if len(sys.argv) > 3 else "cosy")
    im.save(sys.argv[1])
    print("wrote", sys.argv[1], im.size)
