"""Studio preview render for the Sherman (EEVEE, 3 fixed views)."""

import math
import os
import bpy
from mathutils import Vector

OUT = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D/media/models/build"
TARGET = Vector((0.0, 0.0, 1.35))


def ensure(name, data):
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def setup_scene():
    scene = bpy.context.scene
    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if cand in engines:
            scene.render.engine = cand
            break
    print("engine:", scene.render.engine, engines)

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 880
    scene.render.film_transparent = False
    ee = scene.eevee
    for attr, val in (("taa_render_samples", 64), ("use_raytracing", True),
                      ("use_gtao", True), ("gtao_distance", 1.2)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception as exc:
                print("skip", attr, exc)

    # world
    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.40, 0.52, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.world = world

    # ground
    mesh = bpy.data.meshes.get("PreviewGround")
    if mesh is None:
        mesh = bpy.data.meshes.new("PreviewGround")
        size = 40
        verts = [(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)]
        mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
        mesh.update()
    ground = ensure("PreviewGround", mesh)
    gm = bpy.data.materials.get("PreviewGroundMat") or bpy.data.materials.new("PreviewGroundMat")
    gm.use_nodes = True
    bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.22, 0.19, 0.14, 1)
    bsdf.inputs["Roughness"].default_value = 0.95
    if not ground.data.materials:
        ground.data.materials.append(gm)

    # lights
    sun_data = bpy.data.lights.get("PreviewSun") or bpy.data.lights.new("PreviewSun", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(8)
    sun = ensure("PreviewSun", sun_data)
    sun.rotation_euler = (math.radians(52), math.radians(6), math.radians(-38))

    for name, loc, energy, size in (
        ("PreviewFill", (-7.0, -5.0, 4.5), 900, 6.0),
        ("PreviewRim", (6.5, 7.5, 5.5), 1200, 5.0),
        ("PreviewTop", (0.0, 0.5, 9.0), 500, 8.0),
    ):
        data = bpy.data.lights.get(name) or bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        obj = ensure(name, data)
        obj.location = loc
        direction = TARGET - Vector(loc)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    cam_data = bpy.data.cameras.get("PreviewCam") or bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 62
    cam = ensure("PreviewCam", cam_data)
    scene.camera = cam
    return cam


def aim(cam, loc, target=TARGET):
    cam.location = loc
    cam.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def render(name):
    scene = bpy.context.scene
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)


def main():
    os.makedirs(OUT, exist_ok=True)
    cam = setup_scene()
    views = {
        "m4a1_hero.png": (-7.6, -8.4, 4.3),
        "m4a1_side.png": (-13.0, 0.4, 2.2),
        "m4a1_front.png": (-4.6, -12.0, 2.6),
    }
    for name, loc in views.items():
        aim(cam, loc)
        render(name)


main()
