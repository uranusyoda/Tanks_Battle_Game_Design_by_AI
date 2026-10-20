"""Validation: cheap assertions on the built scene, plus a glTF round-trip.

The round-trip is the part that matters: it re-imports the exported .glb into a
fresh file and measures that, so the numbers describe what the game will load
rather than what Blender happens to hold in memory.
"""

import bpy

from . import scene


class Report:
    def __init__(self, label):
        self.label = label
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.info.append(msg)

    @property
    def ok(self):
        return not self.errors

    def as_dict(self):
        return {
            "label": self.label,
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def print(self):
        tag = "OK  " if self.ok else "FAIL"
        print("[check:%s] %s" % (tag, self.label))
        for msg in self.info:
            print("        · %s" % msg)
        for msg in self.warnings:
            print("        ! %s" % msg)
        for msg in self.errors:
            print("        × %s" % msg)


def check_scene(rep, spec, st, path):
    """Assertions that do not need the file on disk."""
    rules = spec.get("validate") or {}

    if st["meshes"] == 0:
        rep.error("scene has no mesh objects")

    max_tris = rules.get("max_tris")
    if max_tris and st["tris"] > max_tris:
        rep.error("tris %d over budget %d" % (st["tris"], max_tris))
    elif max_tris:
        rep.note("tris %d / %d" % (st["tris"], max_tris))

    for name in rules.get("require_nodes") or []:
        if bpy.data.objects.get(name) is None:
            rep.error("required node %r missing" % name)

    max_materials = rules.get("max_materials")
    if max_materials and len(st["materials"]) > max_materials:
        rep.error("%d materials, budget %d" % (len(st["materials"]), max_materials))

    bbox = st.get("bbox")
    if not bbox:
        return
    limit = rules.get("bbox_max_m")
    if limit:
        for axis, value, cap in zip("xyz", bbox["size"], limit):
            if value > cap + 1e-6:
                rep.error("bbox %s=%.3f m over %s cap %.3f" % (axis, value, axis, cap))

    tol = rules.get("ground_tolerance")
    if tol is not None and abs(bbox["min"][2]) > tol:
        rep.error("model does not sit on the ground: lowest z=%.4f (tol %.3f)"
                  % (bbox["min"][2], tol))


def check_file(rep, spec, path, size):
    rules = spec.get("validate") or {}
    if size <= 0:
        rep.error("exported file is empty: %s" % path)
        return
    max_bytes = rules.get("max_bytes")
    if max_bytes and size > max_bytes:
        rep.error("file is %.2f MB, budget %.2f MB"
                  % (size / 1048576, max_bytes / 1048576))
    else:
        rep.note("file %.2f MB" % (size / 1048576))


def measure_glb(path, exclude=None):
    """Import a .glb into an empty file and measure it. Destroys the scene."""
    scene.reset()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = list(bpy.context.scene.objects)
    st = scene.stats(objs, exclude=exclude)
    st["nodes"] = sorted(ob.name for ob in objs)
    return st


def _close(a, b, rel=0.01, abs_=1e-3):
    return abs(a - b) <= max(abs_, abs(b) * rel)


def check_roundtrip(rep, spec, built, loaded):
    """The exported file must contain the same thing the scene had."""
    rules = spec.get("validate") or {}

    if loaded["tris"] == 0:
        rep.error("re-imported glb has no geometry")
        return
    if not _close(loaded["tris"], built["tris"], rel=0.02):
        rep.error("tri count changed through export: %d -> %d"
                  % (built["tris"], loaded["tris"]))

    for name in rules.get("require_nodes") or []:
        if name not in loaded["nodes"]:
            rep.error("required node %r did not survive export" % name)

    names = set(loaded["nodes"])
    for node in (spec.get("tags") or {}):
        if node not in names:
            rep.error("tagged node %r did not survive export" % node)

    b, l = built.get("bbox"), loaded.get("bbox")
    if b and l:
        for axis, (bv, lv) in enumerate(zip(b["size"], l["size"])):
            if not _close(lv, bv, rel=0.02, abs_=2e-3):
                rep.error("bbox %s changed through export: %.4f -> %.4f"
                          % ("xyz"[axis], bv, lv))

    extra = set(loaded["materials"]) - set(built["materials"])
    if extra:
        rep.warn("materials added by exporter: %s" % ", ".join(sorted(extra)))

    rep.note("round-trip: %d tris, %d materials, %d nodes"
             % (loaded["tris"], len(loaded["materials"]), len(loaded["nodes"])))
