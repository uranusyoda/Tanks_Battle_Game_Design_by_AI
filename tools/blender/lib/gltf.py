"""glTF export: operator arguments are checked against the running Blender's
RNA, so a Blender upgrade that renames or drops a flag degrades to a warning
instead of a TypeError in the middle of a build.
"""

import hashlib
import os

import bpy

from . import scene

DEFAULTS = {
    "export_format": "GLB",
    "use_selection": True,
    "export_apply": True,          # bake modifiers
    "export_yup": True,            # Three.js is Y up
    "export_texcoords": True,
    "export_normals": True,
    "export_materials": "EXPORT",
    "export_cameras": False,
    "export_lights": False,
    "export_extras": True,         # custom props -> node.extras
    "export_animations": False,
    "export_skins": False,
    "export_morph": False,
}


def _operator_props():
    return {p.identifier: p for p in bpy.ops.export_scene.gltf.get_rna_type().properties}


def _validate(settings):
    """Drop unknown keys, reject invalid enum values with a readable message."""
    props = _operator_props()
    accepted, dropped = {}, []
    for key, value in settings.items():
        prop = props.get(key)
        if prop is None:
            dropped.append(key)
            continue
        if prop.type == "ENUM":
            valid = [e.identifier for e in prop.enum_items]
            if valid and value not in valid:
                raise ValueError(
                    "glTF export: %s=%r is not valid in Blender %s; choose one of %s"
                    % (key, value, bpy.app.version_string, valid)
                )
        accepted[key] = value
    if dropped:
        print("[export] ignoring unsupported flags: %s" % ", ".join(sorted(dropped)))
    return accepted


def export_glb(path, objs, settings=None):
    """Export `objs` (with hierarchy) to a .glb. Returns the written path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.select(objs)
    kwargs = dict(DEFAULTS)
    kwargs.update(settings or {})
    kwargs["filepath"] = path
    kwargs = _validate(kwargs)

    # The exporter narrates every primitive at INFO level (and its
    # export_loglevel flag is broken in 5.0: setting it raises KeyError).
    # debug_value 1 == WARNING is the supported way to quieten it.
    previous = bpy.app.debug_value
    try:
        bpy.app.debug_value = 1
        bpy.ops.export_scene.gltf(**kwargs)
    finally:
        bpy.app.debug_value = previous

    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise RuntimeError("glTF export produced no file: %s" % path)
    print("[export] %s (%.2f MB)" % (path, os.path.getsize(path) / 1048576))
    return path


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, check_existing=False)
    print("[save] %s" % path)
    return path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
