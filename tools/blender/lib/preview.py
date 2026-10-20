"""Studio preview renders for build verification.

Three fixed angles framed from the asset's own bounding box, so any model that
comes out of the pipeline can be eyeballed without opening the GUI.
"""

import math
import os

import bpy
from mathutils import Vector

#: name -> (direction from target towards the camera, distance factor)
VIEWS = {
    "hero": ((-1.0, -1.1, 0.55), 1.00),
    "side": ((-1.0, 0.03, 0.17), 1.06),
    "front": ((-0.38, -1.0, 0.22), 1.03),
}


def fit_distance(cam_data, bbox, resolution, margin=0.95):
    """Camera distance that fits the bbox bounding sphere in frame."""
    radius = 0.5 * math.sqrt(sum(s * s for s in bbox["size"]))
    sensor = cam_data.sensor_width
    aspect = resolution[0] / float(resolution[1])
    fov_x = 2.0 * math.atan(sensor / (2.0 * cam_data.lens))
    fov_y = 2.0 * math.atan((sensor / aspect) / (2.0 * cam_data.lens))
    return radius / math.sin(min(fov_x, fov_y) / 2.0) * margin


def _ensure(name, data):
    obj = bpy.data.objects.get(name)
    if obj:
        return obj
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _pick_engine(scene):
    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        if cand in engines:
            scene.render.engine = cand
            return cand
    return scene.render.engine


def setup(target, resolution=(1280, 880), samples=48):
    scene = bpy.context.scene
    scene.render.engine = _pick_engine(scene)
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    ee = getattr(scene, "eevee", None)
    if ee is not None:
        for attr, val in (("taa_render_samples", samples), ("use_raytracing", True),
                          ("use_gtao", True), ("gtao_distance", 1.2)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception as exc:
                    print("[preview] skip", attr, exc)

    world = bpy.data.worlds.get("PreviewWorld") or bpy.data.worlds.new("PreviewWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.32, 0.40, 0.52, 1.0)
    bg.inputs[1].default_value = 0.9
    scene.world = world

    mesh = bpy.data.meshes.get("PreviewGround")
    if mesh is None:
        mesh = bpy.data.meshes.new("PreviewGround")
        size = 40
        mesh.from_pydata(
            [(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0)],
            [], [(0, 1, 2, 3)])
        mesh.update()
    ground = _ensure("PreviewGround", mesh)
    gm = bpy.data.materials.get("PreviewGroundMat") or bpy.data.materials.new("PreviewGroundMat")
    gm.use_nodes = True
    bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.22, 0.19, 0.14, 1)
    bsdf.inputs["Roughness"].default_value = 0.95
    if not ground.data.materials:
        ground.data.materials.append(gm)

    sun_data = bpy.data.lights.get("PreviewSun") or bpy.data.lights.new("PreviewSun", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(8)
    sun = _ensure("PreviewSun", sun_data)
    sun.rotation_euler = (math.radians(52), math.radians(6), math.radians(-38))

    for name, loc, energy, size in (
        ("PreviewFill", (-7.0, -5.0, 4.5), 900, 6.0),
        ("PreviewRim", (6.5, 7.5, 5.5), 1200, 5.0),
        ("PreviewTop", (0.0, 0.5, 9.0), 500, 8.0),
    ):
        data = bpy.data.lights.get(name) or bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.size = size
        obj = _ensure(name, data)
        obj.location = loc
        obj.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    cam_data = bpy.data.cameras.get("PreviewCam") or bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 62
    cam = _ensure("PreviewCam", cam_data)
    scene.camera = cam
    return cam


def render(objs, out_dir, basename, target=None, bbox=None,
           resolution=(1280, 880), samples=48, views=None, ext="png"):
    """Render the requested views; returns the written file paths."""
    views = views or ["hero", "side", "front"]
    st_bbox = bbox
    if target is None or st_bbox is None:
        from . import scene as scene_mod
        st = scene_mod.stats(objs)
        if not st["bbox"]:
            raise RuntimeError("cannot preview: no geometry")
        st_bbox = st_bbox or st["bbox"]
        target = target or Vector(st_bbox["center"])
    max_dim = max(st_bbox["size"]) if st_bbox else 7.0

    os.makedirs(out_dir, exist_ok=True)
    cam = setup(target, resolution=resolution, samples=samples)
    base_dist = fit_distance(cam.data, st_bbox, resolution)

    written = []
    for name in views:
        if name not in VIEWS:
            raise KeyError("unknown preview view %r; known: %s"
                           % (name, ", ".join(sorted(VIEWS))))
        direction, factor = VIEWS[name]
        dist = base_dist * factor
        unit = Vector(direction).normalized()
        cam.location = target + unit * dist
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(out_dir, "%s_%s.%s" % (basename, name, ext))
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        written.append(path)
        print("[preview] %s" % path)
    return written
