"""Write tiny-town maps (.ldtk, LDtk 1.5.3 subset) from Python. The same structure as js/format.js buildMap();
keep the uids and values in sync with js/registry.js.

    p = Project(40, 50)
    p.set_intgrid("Terrain", [0, 1, ...])          # cols * rows values, row by row
    p.add_entity("Prop", x, y, {"sprite": "tree-1"})
    p.save("maps/town.ldtk")
"""
import json
import re
import uuid

GRID = 16
LDTK = "1.5.3"
VERSION = 1
OBJECTS_UID = 1
LAYERS = {   # name: (uid, [(value, id, colour)])
    "Height": (5, [(1, "raised", "#8a9a3c")]),
    "Terrain": (4, [(1, "path", "#e2c96a"), (2, "cobbles", "#7a8399"), (3, "water", "#45bddd"), (4, "soil", "#a37a45"), (5, "bridge", "#cfa765")]),
    "Features": (3, [(1, "stairs", "#7a5733")]),
    "Deco": (2, [(1, "fence", "#5a3a32"), (2, "flowers", "#f28fb0"), (3, "tallgrass", "#2f7448"), (4, "gate", "#cfa765")]),
}
ENTITIES = {  # name: (uid, colour, pivot, resizable, {field: (type, uid)})
    "Prop": (10, "#4f9a48", (0.5, 1), False, {"sprite": ("String", 11)}),
    "Character": (20, "#e8673a", (0.5, 1), False, {"id": ("String", 21), "sprite": ("String", 22), "perch": ("Point", 23),
                                                    "flyTo": ("Point", 24), "path": ("Array<Point>", 25)}),
    "Path": (30, "#f2c94c", (0, 0), False, {"name": ("String", 31), "points": ("Array<Point>", 32)}),
    "Region": (40, "#3a76f0", (0, 0), True, {"name": ("String", 41)}),
}
LAYER_ORDER = ["Objects", "Deco", "Features", "Terrain", "Height"]

LAYER_DEF_COMMON = dict(
    doc=None, uiColor=None, gridSize=GRID, guideGridWid=0, guideGridHei=0, displayOpacity=1, inactiveOpacity=1,
    hideInList=False, hideFieldsWhenInactive=True, canSelectWhenInactive=True, renderInWorldView=True,
    pxOffsetX=0, pxOffsetY=0, parallaxFactorX=0, parallaxFactorY=0, parallaxScaling=True,
    requiredTags=[], excludedTags=[], uiFilterTags=[], useAsyncRender=False, autoTilesKilledByOtherLayerUid=None,
    biomeFieldUid=None, intGridValuesGroups=[], autoRuleGroups=[], autoSourceLayerDefUid=None, tilesetDefUid=None,
    tilePivotX=0, tilePivotY=0)


def _uuid():
    return str(uuid.uuid4())


def _layer_defs():
    out = []
    for name in LAYER_ORDER:
        if name == "Objects":
            out.append(dict(LAYER_DEF_COMMON, __type="Entities", type="Entities", identifier=name, uid=OBJECTS_UID, intGridValues=[], inactiveOpacity=0.6))
        else:
            uid, values = LAYERS[name]
            out.append(dict(LAYER_DEF_COMMON, __type="IntGrid", type="IntGrid", identifier=name, uid=uid,
                            intGridValues=[dict(value=v, identifier=i, color=c, tile=None, groupUid=0) for v, i, c in values]))
    return out


def _field_def(identifier, typ, uid):
    point, array = typ != "String", typ.startswith("Array")
    return dict(
        identifier=identifier, doc=None, __type=typ, uid=uid, type="F_Point" if point else "F_String", isArray=array, canBeNull=not array,
        arrayMinLength=None, arrayMaxLength=None, editorDisplayMode="PointPath" if array else "PointStar" if point else "ValueOnly",
        editorDisplayScale=1, editorDisplayPos="Above", editorLinkStyle="ArrowsLine" if array else "StraightArrow",
        editorDisplayColor=None, editorAlwaysShow=False, editorShowInWorld=True, editorCutLongValues=True,
        editorTextSuffix=None, editorTextPrefix=None, useForSmartColor=False, exportToToc=False, searchable=False,
        min=None, max=None, regex=None, acceptFileTypes=None, defaultOverride=None, textLanguageMode=None,
        symmetricalRef=False, autoChainRef=True, allowOutOfLevelRef=True, allowedRefs="OnlySame",
        allowedRefsEntityUid=None, allowedRefTags=[], tilesetUid=None)


def _entity_defs():
    return [dict(
        identifier=name, uid=uid, tags=[], exportToToc=False, allowOutOfBounds=False, doc=None, width=GRID, height=GRID,
        resizableX=res, resizableY=res, minWidth=None, maxWidth=None, minHeight=None, maxHeight=None, keepAspectRatio=False,
        tileOpacity=1, fillOpacity=0.08, lineOpacity=0, hollow=res, color=color, renderMode="Rectangle", showName=True,
        tilesetId=None, tileRenderMode="FitInside", tileRect=None, uiTileRect=None, nineSliceBorders=[], maxCount=0,
        limitScope="PerLevel", limitBehavior="MoveLastOne", pivotX=pivot[0], pivotY=pivot[1],
        fieldDefs=[_field_def(f, t, u) for f, (t, u) in fields.items()])
        for name, (uid, color, pivot, res, fields) in ENTITIES.items()]


def _field_instance(name, typ, uid, v):
    base = dict(__identifier=name, __type=typ, __tile=None, defUid=uid)
    if typ == "Point":
        if not v:
            return dict(base, __value=None, realEditorValues=[])
        return dict(base, __value=dict(cx=v[0], cy=v[1]), realEditorValues=[dict(id="V_String", params=[f"{v[0]},{v[1]}"])])
    if typ == "Array<Point>":
        pts = v or []
        return dict(base, __value=[dict(cx=p[0], cy=p[1]) for p in pts], realEditorValues=[dict(id="V_String", params=[f"{p[0]},{p[1]}"]) for p in pts])
    if v is None:
        return dict(base, __value=None, realEditorValues=[])
    return dict(base, __value=str(v), realEditorValues=[dict(id="V_String", params=[str(v)])])


def _entity_instance(typ, x, y, fields, w, h):
    uid, color, pivot, _, defs = ENTITIES[typ]
    return dict(
        __identifier=typ, __grid=[int(x // GRID), int(y // GRID)], __pivot=list(pivot), __tags=[], __tile=None,
        __smartColor=color, iid=_uuid(), width=w, height=h, defUid=uid, px=[int(x), int(y)], __worldX=int(x), __worldY=int(y),
        fieldInstances=[_field_instance(f, t, u, fields.get(f)) for f, (t, u) in defs.items()])


def _project_json(cols, rows, grids, entities):
    layers = []
    for name in LAYER_ORDER:
        obj = name == "Objects"
        layers.append(dict(
            __identifier=name, __type="Entities" if obj else "IntGrid", __cWid=cols, __cHei=rows, __gridSize=GRID,
            __opacity=1, __pxTotalOffsetX=0, __pxTotalOffsetY=0, __tilesetDefUid=None, __tilesetRelPath=None, iid=_uuid(),
            levelId=0, layerDefUid=OBJECTS_UID if obj else LAYERS[name][0], pxOffsetX=0, pxOffsetY=0, visible=True,
            optionalRules=[], intGridCsv=[] if obj else grids[name], autoLayerTiles=[], seed=1234567,
            overrideTilesetUid=None, gridTiles=[], entityInstances=entities if obj else []))
    W, H = cols * GRID, rows * GRID
    return dict(
        __header__=dict(fileType="LDtk Project JSON", app="LDtk", doc="https://ldtk.io/json", schema="https://ldtk.io/files/JSON_SCHEMA.json",
                        appAuthor="Sebastien 'deepnight' Benard", appVersion=LDTK, url="https://ldtk.io"),
        tinyTownVersion=VERSION,
        iid=_uuid(), jsonVersion=LDTK, appBuildId=473702, nextUid=100, identifierStyle="Capitalize", toc=[],
        worldLayout="Free", worldGridWidth=256, worldGridHeight=256, defaultLevelWidth=W, defaultLevelHeight=H,
        defaultPivotX=0.5, defaultPivotY=1, defaultGridSize=GRID, defaultEntityWidth=GRID, defaultEntityHeight=GRID,
        bgColor="#40465B", defaultLevelBgColor="#b4d566", minifyJson=False, externalLevels=False, exportTiled=False,
        simplifiedExport=False, imageExportMode="None", exportLevelBg=True, pngFilePattern=None, backupOnSave=False,
        backupLimit=10, backupRelPath=None, levelNamePattern="%world_Level_%idx", customCommands=[], flags=[],
        defs=dict(layers=_layer_defs(), entities=_entity_defs(), tilesets=[], enums=[], externalEnums=[], levelFields=[]),
        levels=[dict(
            identifier="Town", iid=_uuid(), uid=0, worldX=0, worldY=0, worldDepth=0, pxWid=W, pxHei=H, __bgColor="#b4d566",
            bgColor=None, useAutoIdentifier=False, bgRelPath=None, bgPos=None, bgPivotX=0.5, bgPivotY=0.5,
            __smartColor="#ADADB5", __bgPos=None, externalRelPath=None, fieldInstances=[], layerInstances=layers, __neighbours=[])],
        worlds=[], dummyWorldIid=_uuid())


class Project:
    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.grids = {name: [0] * (cols * rows) for name in LAYERS}
        self.entities = []

    def set_intgrid(self, name, values):
        assert len(values) == self.cols * self.rows, f"{name}: expected {self.cols * self.rows} values"
        self.grids[name] = list(values)

    def add_entity(self, typ, x, y, fields, w=GRID, h=GRID):
        self.entities.append(_entity_instance(typ, x, y, fields, w, h))

    def to_json(self):
        return _project_json(self.cols, self.rows, self.grids, self.entities)

    def save(self, path):
        text = json.dumps(self.to_json(), indent=1)
        # one IntGrid row per line, like js/format.js stringifyMap()

        def rows(match):
            nums = [n.strip() for n in match.group(1).split(",") if n.strip()]
            if not nums:
                return '"intGridCsv": []'
            lines = [",".join(nums[i:i + self.cols]) for i in range(0, len(nums), self.cols)]
            return '"intGridCsv": [\n' + ",\n".join(lines) + "\n]"
        text = re.sub(r'"intGridCsv": \[([\d,\s]*)\]', rows, text)
        with open(path, "w") as f:
            f.write(text + "\n")
