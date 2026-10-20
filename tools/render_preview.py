"""Render preview stills / animation segments for the animated Sherman.

Usage (headless):
  Blender -b assets/models/m4_sherman.blend -P tools/render_preview.py -- --stills
  Blender -b assets/models/m4_sherman.blend -P tools/render_preview.py -- --anim
"""

import bpy
import math
import os
import sys
from mathutils import Vector

C = bpy.context
D = bpy.data
scene = C.scene

TRACK_MAT_NT = None
for mat in D.materials:
    if mat.name == "Sherman_TrackTex":
        TRACK_MAT_NT = mat.node_tree

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STILLS_ONLY = "--stills" in ARGS

ROOT_DIR = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D"
PREVIEW = os.path.join(ROOT_DIR, "media", "models")
FRAMES = "/tmp/sherman_anim"
os.makedirs(PREVIEW, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)

# --------------------------------------------------------------------------- #
# set
# --------------------------------------------------------------------------- #

# remember the rest pose (frame 1) so clip switching never leaks transforms
BASE = {}
for o in D.objects:
    BASE[o.name] = (o.location.copy(), o.rotation_euler.copy(), o.scale.copy())


def reset_pose():
    for name, (loc, rot, sca) in BASE.items():
        o = D.objects.get(name)
        if not o:
            continue
        o.location = loc
        o.rotation_euler = rot
        o.scale = sca
    if TRACK_MAT_NT:
        mp = next((n for n in TRACK_MAT_NT.nodes if n.type == "MAPPING"), None)
        if mp:
            mp.inputs["Location"].default_value[0] = 0.0


bpy.ops.mesh.primitive_plane_add(size=90, location=(0, 0, 0))
floor = C.object
floor.name = "RenderFloor"
m = D.materials.new("FloorSand")
m.use_nodes = True
bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (0.48, 0.42, 0.32, 1)
bsdf.inputs["Roughness"].default_value = 0.95
floor.data.materials.append(m)

bpy.ops.object.camera_add(location=(9.6, -10.6, 5.2))
cam = C.object
cam.data.lens = 50
cam.rotation_euler = (Vector((0, -1.1, 1.35)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

bpy.ops.object.light_add(type="SUN", location=(6, -4, 12))
sun = C.object
sun.data.energy = 3.6
sun.data.angle = math.radians(4)
sun.rotation_euler = (math.radians(48), 0, math.radians(-40))

bpy.ops.object.light_add(type="SUN", location=(-8, 6, 8))
fill = C.object
fill.data.energy = 1.1
fill.rotation_euler = (math.radians(60), 0, math.radians(150))

w = scene.world or D.worlds.new("World")
scene.world = w
w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.60, 0.68, 0.78, 1)
bg.inputs[1].default_value = 0.9

scene.render.engine = "BLENDER_EEVEE"
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = -0.25
except Exception:
    pass
try:
    scene.eevee.taa_render_samples = 32
except Exception:
    pass
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False

# --------------------------------------------------------------------------- #
# NLA solo
# --------------------------------------------------------------------------- #



def solo(clip):
    for o in D.objects:
        ad = o.animation_data
        if not ad:
            continue
        for tr in ad.nla_tracks:
            tr.mute = (tr.name != clip)
    if TRACK_MAT_NT and TRACK_MAT_NT.animation_data:
        for tr in TRACK_MAT_NT.animation_data.nla_tracks:
            tr.mute = (tr.name != clip)


CAMS = {
    "TurretTurn": ((9.6, -10.6, 5.2), (0, -1.1, 1.35), 50),
    "Fire": ((8.2, -9.2, 4.4), (0, -2.2, 1.9), 55),
    "Drive": ((8.8, 9.4, 4.6), (0, 0.6, 1.25), 48),
}


def set_cam(clip):
    loc, target, lens = CAMS[clip]
    cam.location = loc
    cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


CLIPS = [("TurretTurn", 40, "turretturn"), ("Fire", 13, "fire"),
         ("Fire", 22, "fire_smoke"), ("Drive", 46, "drive")]

# --------------------------------------------------------------------------- #
# stills
# --------------------------------------------------------------------------- #

scene.render.resolution_x = 1280
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
try:
    scene.eevee.taa_render_samples = 32
except Exception:
    pass

for clip, frame, label in CLIPS:
    reset_pose()
    solo(clip)
    set_cam(clip)
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(PREVIEW, "anim_%s.png" % label)
    bpy.ops.render.render(write_still=True)
    print("STILL", clip, frame)

if not STILLS_ONLY:
    scene.render.resolution_x = 640
    scene.render.resolution_y = 400
    try:
        scene.eevee.taa_render_samples = 12
    except Exception:
        pass
    ranges = {"TurretTurn": (1, 96), "Fire": (1, 60), "Drive": (1, 120)}
    for clip, (start, end) in ranges.items():
        reset_pose()
        solo(clip)
        set_cam(clip)
        out = os.path.join(FRAMES, clip)
        os.makedirs(out, exist_ok=True)
        for f in range(start, end + 1):
            scene.frame_set(f)
            scene.render.filepath = os.path.join(out, "f%04d.png" % f)
            bpy.ops.render.render(write_still=True)
        print("SEGMENT", clip, "done")

print("RENDER_DONE")
