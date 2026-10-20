"""Headless build + export + preview render for the M4A1 Sherman.

    /Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
        --factory-startup --python tools/blender/headless.py
"""

import os
import sys
import traceback

import bpy

BASE = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D"
BLENDER_DIR = os.path.join(BASE, "tools", "blender")
MODELS = os.path.join(BASE, "assets", "models")


def run(path, name):
    with open(path) as fh:
        code = fh.read()
    exec(compile(code, path, "exec"), {"__name__": name})


def export_glb():
    os.makedirs(MODELS, exist_ok=True)
    out = os.path.join(MODELS, "m4a1_sherman.glb")
    bpy.ops.object.select_all(action="DESELECT")
    coll = bpy.data.collections["M4A1_76"]
    for obj in coll.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.data.objects["M4A1_Sherman"]
    bpy.ops.export_scene.gltf(
        filepath=out,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    size = os.path.getsize(out) / 1048576
    print(f"[export] {out} ({size:.2f} MB)")

    blend = os.path.join(MODELS, "m4a1_sherman.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print(f"[save] {blend}")


def main():
    # start from a truly empty file: no default cube/camera/light
    bpy.ops.wm.read_factory_settings(use_empty=True)
    run(os.path.join(BLENDER_DIR, "build_sherman.py"), "sherman_build")
    export_glb()
    try:
        run(os.path.join(BLENDER_DIR, "render_preview.py"), "preview")
    except Exception:
        traceback.print_exc()
        print("[render] preview failed (non-fatal)")


main()
