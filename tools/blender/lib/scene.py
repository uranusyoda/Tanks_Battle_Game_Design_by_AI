"""Scene operations used by the pipeline: reset, post-process, measure.

Everything here is builder-agnostic. A builder only has to leave its result in
the scene (optionally inside a named collection) with Z up and metres scale.
"""

import fnmatch

import bpy
from mathutils import Vector


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------
def reset():
    """Truly empty file: no default cube, camera or light."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------------------
# selection / collections
# ---------------------------------------------------------------------------
def collection(name=None):
    if name:
        coll = bpy.data.collections.get(name)
        if coll is None:
            raise LookupError("collection %r not found after build" % name)
        return coll
    return None


def objects(name=None):
    """Every object of a collection, or the whole scene when name is None."""
    coll = collection(name)
    if coll is not None:
        return list(coll.all_objects)
    return list(bpy.context.scene.objects)


def select(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def remove_objects(objs):
    for ob in list(objs):
        bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------------------
# post-process steps (driven by the spec)
# ---------------------------------------------------------------------------
def strip(objs, patterns):
    """Delete objects whose name matches any glob pattern. Returns removed names."""
    if not patterns:
        return []
    doomed = [ob for ob in objs if any(fnmatch.fnmatch(ob.name, p) for p in patterns)]
    removed = sorted(ob.name for ob in doomed)
    if not removed:
        return []
    # children of a stripped part would be orphaned mid-air; reparent to nothing
    for ob in doomed:
        for child in list(ob.children):
            child.parent = ob.parent
            if ob.parent is not None:
                child.matrix_parent_inverse = ob.parent.matrix_world.inverted()
    remove_objects(doomed)
    bpy.context.view_layer.update()
    return removed


def override_materials(overrides):
    """Retint existing materials by name: {material_name: "#rrggbb"}.

    Works on the Principled BSDF, which is what the glTF exporter reads;
    diffuse_color is only the viewport fallback and is set too.
    """
    if not overrides:
        return []
    changed = []
    for name, hexcolor in overrides.items():
        mat = bpy.data.materials.get(name)
        if mat is None:
            print("[warn] material override: %r not found" % name)
            continue
        rgba = hex_to_linear_rgba(hexcolor)
        mat.diffuse_color = rgba
        if mat.use_nodes and mat.node_tree:
            bsdf = next(
                (n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None
            )
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = rgba
        changed.append(name)
    return changed


def hex_to_linear_rgba(hexcolor):
    h = hexcolor.lstrip("#")
    if len(h) == 8:
        h = h[:6]
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def tag(objs, tags):
    """Write game-facing custom properties; glTF carries them as node extras."""
    if not tags:
        return {}
    written = {}
    for obj_name, value in tags.items():
        ob = bpy.data.objects.get(obj_name)
        if ob is None:
            print("[warn] tag target %r not found" % obj_name)
            continue
        ob["game_node"] = value
        written[obj_name] = value
    return written


def scale_root(objs, factor):
    """Uniform scale about the model root (applied to top-level objects only)."""
    if not factor or abs(factor - 1.0) < 1e-9:
        return
    roots = [ob for ob in objs if ob.parent is None]
    for ob in roots:
        ob.scale = (ob.scale.x * factor, ob.scale.y * factor, ob.scale.z * factor)
    bpy.context.view_layer.update()


def drop_to_ground(objs, tol=1e-6):
    """Translate so the lowest mesh vertex sits at z = 0."""
    lowest = None
    for ob in objs:
        if ob.type != "MESH":
            continue
        mw = ob.matrix_world
        for v in ob.data.vertices:
            z = (mw @ v.co).z
            if lowest is None or z < lowest:
                lowest = z
    if lowest is None or abs(lowest) <= tol:
        return 0.0
    for ob in objs:
        if ob.parent is None:
            ob.location.z -= lowest
    bpy.context.view_layer.update()
    return -lowest


# ---------------------------------------------------------------------------
# LOD
# ---------------------------------------------------------------------------
def duplicate(objs, suffix):
    """Copy objects (and their hierarchy) into a new collection."""
    coll = bpy.data.collections.new("LOD" + suffix)
    bpy.context.scene.collection.children.link(coll)
    mapping = {}
    for ob in objs:
        dup = ob.copy()
        if ob.data is not None:
            dup.data = ob.data.copy()
        coll.objects.link(dup)
        mapping[ob] = dup
    for src, dup in mapping.items():
        if src.parent in mapping:
            dup.parent = mapping[src.parent]
            dup.matrix_parent_inverse = src.matrix_parent_inverse.copy()
    bpy.context.view_layer.update()
    return coll, list(coll.all_objects)


def decimate(objs, ratio):
    """Collapse-decimate every mesh in `objs` in place. Returns tri count before."""
    before = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objs:
        if ob.type != "MESH":
            continue
        before += count_tris(ob)
        mod = ob.modifiers.new("LODDecimate", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = max(0.01, min(1.0, ratio))
        mod.use_collapse_triangulate = True
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        new_mesh = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        old = ob.data
        ob.modifiers.clear()
        ob.data = new_mesh
        if old.users == 0:
            bpy.data.meshes.remove(old)
    bpy.context.view_layer.update()
    return before


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------
def count_tris(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def stats(objs, exclude=None):
    """Triangle/vertex counts, material list and world bounding box.

    `exclude` is a list of glob patterns (muzzle flash, smoke, ...) that are
    part of the export but must not influence size or ground checks.
    """
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    tris = verts = 0
    meshes = 0
    materials = set()
    for ob in objs:
        if ob.type != "MESH":
            continue
        if exclude and any(fnmatch.fnmatch(ob.name, p) for p in exclude):
            continue
        meshes += 1
        tris += count_tris(ob)
        verts += len(ob.data.vertices)
        for slot in ob.material_slots:
            if slot.material:
                materials.add(slot.material.name)
        mw = ob.matrix_world
        for v in ob.data.vertices:
            co = mw @ v.co
            for i in range(3):
                lo[i] = min(lo[i], co[i])
                hi[i] = max(hi[i], co[i])
    if meshes == 0:
        return {
            "objects": len(objs), "meshes": 0, "tris": 0, "verts": 0,
            "materials": [], "bbox": None,
        }
    return {
        "objects": len(objs),
        "meshes": meshes,
        "tris": tris,
        "verts": verts,
        "materials": sorted(materials),
        "bbox": {
            "min": [round(v, 4) for v in lo],
            "max": [round(v, 4) for v in hi],
            "size": [round(hi[i] - lo[i], 4) for i in range(3)],
            "center": [round((hi[i] + lo[i]) / 2, 4) for i in range(3)],
        },
    }


def world_center(objs):
    s = stats(objs)
    if not s["bbox"]:
        return Vector((0, 0, 0))
    return Vector(s["bbox"]["center"])
