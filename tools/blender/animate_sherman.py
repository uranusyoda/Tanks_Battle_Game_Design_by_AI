"""Animation pass for the M4A1 Sherman: turret traverse, main-gun recoil +
muzzle flash, and a drive forward / reverse with rolling tracks.

Assumes assets/models/m4a1_sherman.blend is open.

    /Applications/Blender.app/Contents/MacOS/Blender -b \
        assets/models/m4a1_sherman.blend --python tools/blender/animate_sherman.py

Timeline (24 fps, 240 frames)
  1-81    drive forward, turret traverses right
  81-100  halt, fire at frame 95 (recoil + muzzle flash)
  100-140 turret returns to centre
  165-237 reverse, tracks roll backwards
"""

import math
import os

import bpy
from mathutils import Matrix, Vector

BASE = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D"
FPS = 24
F_END = 240
FWD_END = 81
F_REV_START = 165
F_REV_END = 237
F_FIRE = 95
STEP = 4                     # frames per track-link pitch
PITCH_M = 0.1668             # one link pitch in metres (= 1 m/s at 24 fps)
SPEED = PITCH_M * FPS / STEP  # m/s

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def srgb(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def material(name, hexcolor, rough=0.7, metal=0.0, emit=None, emit_strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    r, g, b = srgb(hexcolor)
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        er, eg, eb = srgb(emit)
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = (er, eg, eb, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emit_strength
    return mat


def new_object(name, verts, faces, coll, mat=None, parent=None, keep_world=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
        if keep_world:
            obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def box_data(centre, size):
    cx, cy, cz = centre
    sx, sy, sz = (s * 0.5 for s in size)
    verts = [(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz),
             (cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz),
             (cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz),
             (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def merge(*parts):
    verts, faces = [], []
    for v, f in parts:
        off = len(verts)
        verts.extend(v)
        faces.extend(tuple(i + off for i in face) for face in f)
    return verts, faces


# ----------------------------------------------------------------------------
# scene / track setup
# ----------------------------------------------------------------------------
def scene_setup():
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = F_END


def track_poses(n):
    """Evenly spaced link poses around the stadium: (y, z, theta)."""
    # geometry constants mirror build_sherman.py
    sprocket_y, idler_y, R = -2.40, 2.40, 0.40
    turret = bpy.data.objects["Turret_Pivot"]
    dz = turret.location.z - 1.70          # model was dropped onto the ground
    z0 = 0.545 + dz

    pts = []
    seg = 64
    for i in range(seg // 2 + 1):
        a = math.pi / 2 + math.pi * i / (seg // 2)
        pts.append((sprocket_y + R * math.cos(a), z0 + R * math.sin(a)))
    for i in range(seg // 2 + 1):
        a = -math.pi / 2 + math.pi * i / (seg // 2)
        pts.append((idler_y + R * math.cos(a), z0 + R * math.sin(a)))

    seglens, total = [], 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        seglens.append(d)
        total += d
    step = total / n

    poses = []
    for k in range(n):
        s = k * step
        acc, i = 0.0, 0
        while acc + seglens[i] < s and i < len(pts) - 1:
            acc += seglens[i]
            i += 1
        t = (s - acc) / seglens[i] if seglens[i] else 0.0
        a, b = pts[i], pts[(i + 1) % len(pts)]
        py = a[0] + (b[0] - a[0]) * t
        pz = a[1] + (b[1] - a[1]) * t
        theta = math.atan2(b[1] - a[1], b[0] - a[0])
        poses.append((py, pz, theta))
    return poses, total


def build_animated_tracks(coll, root, mat, static_names=("Track_L", "Track_R")):
    for name in static_names:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_viewport = True
            obj.hide_render = True

    half_w, half_l, half_t = 0.21, 0.079, 0.024
    link_v, link_f = merge(
        box_data((0, 0, 0), (half_w * 2, half_l * 2, half_t * 2)),
        box_data((0, 0, 0.062), (0.076, 0.048, 0.068)),
    )

    track_light = material("Sherman_TrackLight", "#4d4e43", 0.5, 0.7)

    n = 73
    poses, total = track_poses(n)
    print(f"[anim] track perimeter {total:.2f} m, {n} links, dz ok")

    sides = {"L": -1.02, "R": 1.02}
    links = {}
    for tag, sx in sides.items():
        objs = []
        for k in range(n):
            lm = track_light if k % 6 == 0 else mat
            obj = new_object(f"AnimLink_{tag}_{k:02d}", link_v, link_f, coll, lm, parent=root)
            obj.rotation_mode = "XYZ"
            objs.append(obj)
        links[tag] = objs
    return links, poses, n


def animate_tracks(links, poses, n):
    fwd_steps = (FWD_END - 1) // STEP            # 20
    rev_steps = round((F_REV_END - F_REV_START) / STEP)  # 18

    for tag, objs in links.items():
        sx = -1.02 if tag == "L" else 1.02
        for k, obj in enumerate(objs):
            # forward keys
            keys = []
            for i in range(fwd_steps + 1):
                f = 1 + i * STEP
                keys.append((f, (k + i) % n))
            # hold
            keys.append((F_REV_START, (k + fwd_steps) % n))
            # reverse keys
            for i in range(1, rev_steps + 1):
                f = F_REV_START + i * STEP
                keys.append((f, (k + fwd_steps - i) % n))
            if keys[-1][0] < F_END:
                keys.append((F_END, keys[-1][1]))

            for f, idx in keys:
                py, pz, theta = poses[idx]
                obj.location = (sx, py, pz)
                obj.rotation_euler = (theta, 0.0, 0.0)
                obj.keyframe_insert("location", frame=f)
                obj.keyframe_insert("rotation_euler", frame=f)

    for tag, objs in links.items():
        for obj in objs:
            set_interpolation(obj, "LINEAR")


def recenter_mesh(obj):
    """Mesh data is in world coordinates with the origin at 0,0,0; move the
    origin to the part's own centre so rotations spin in place."""
    me = obj.data
    if not len(me.vertices):
        return
    lo = [min(v.co[i] for v in me.vertices) for i in range(3)]
    hi = [max(v.co[i] for v in me.vertices) for i in range(3)]
    c = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
    for v in me.vertices:
        v.co -= c
    obj.location = obj.location + c


def add_wheel_bolts(wheel, coll, mat):
    c = wheel.location.copy()
    side = 1 if c.x > 0 else -1
    for i in range(3):
        a = 2 * math.pi * i / 3
        pos = (c.x + side * 0.112, c.y + 0.235 * math.cos(a), c.z + 0.235 * math.sin(a))
        v, f = box_data(pos, (0.02, 0.055, 0.055))
        bolt = new_object(f"{wheel.name}_Bolt{i}", v, f, coll, mat)
        bolt.parent = wheel
        bolt.matrix_parent_inverse = Matrix.Translation(-c)


def animate_wheels():
    turret = bpy.data.objects["Turret_Pivot"]
    dz = turret.location.z - 1.70
    d_fwd = ((FWD_END - 1) / FPS) * SPEED
    d_rev = ((F_REV_END - F_REV_START) / FPS) * SPEED

    radii = {"Tire": 0.325, "Hub": 0.325, "HubCap": 0.325,
             "Sprocket": 0.36, "SprocketTeeth": 0.36,
             "Idler": 0.35, "Roller": 0.085}
    for obj in bpy.data.objects:
        if not obj.name.startswith(("Tire_", "Hub_", "HubCap_", "Sprocket_",
                                    "SprocketTeeth_", "Idler_", "Roller_")):
            continue
        r = next((v for k, v in radii.items() if obj.name.startswith(k)), None)
        if r is None:
            continue
        recenter_mesh(obj)
        if obj.name.startswith("Tire_"):
            add_wheel_bolts(obj, bpy.data.collections["M4A1_76"],
                            bpy.data.materials["Sherman_Metal"])
        obj.rotation_mode = "XYZ"
        base = obj.rotation_euler.x
        obj.rotation_euler.x = base
        obj.keyframe_insert("rotation_euler", index=0, frame=1)
        obj.rotation_euler.x = base + d_fwd / r
        obj.keyframe_insert("rotation_euler", index=0, frame=FWD_END)
        obj.keyframe_insert("rotation_euler", index=0, frame=F_REV_START)
        obj.rotation_euler.x = base + (d_fwd - d_rev) / r
        obj.keyframe_insert("rotation_euler", index=0, frame=F_REV_END)
        obj.keyframe_insert("rotation_euler", index=0, frame=F_END)
        set_interpolation(obj, "LINEAR")


def animate_hull(root):
    d_fwd = ((FWD_END - 1) / FPS) * SPEED
    d_rev = ((F_REV_END - F_REV_START) / FPS) * SPEED
    y0 = root.location.y
    root.keyframe_insert("location", index=1, frame=1)
    root.location.y = y0 - d_fwd
    root.keyframe_insert("location", index=1, frame=FWD_END)
    root.keyframe_insert("location", index=1, frame=F_REV_START)
    root.location.y = y0 - d_fwd + d_rev
    root.keyframe_insert("location", index=1, frame=F_REV_END)
    root.keyframe_insert("location", index=1, frame=F_END)
    set_interpolation(root, "LINEAR")


def animate_turret_and_gun():
    t = bpy.data.objects["Turret_Pivot"]
    t.rotation_mode = "XYZ"
    t.rotation_euler.z = 0.0
    t.keyframe_insert("rotation_euler", index=2, frame=1)
    t.keyframe_insert("rotation_euler", index=2, frame=30)
    t.rotation_euler.z = 0.92
    t.keyframe_insert("rotation_euler", index=2, frame=78)
    t.keyframe_insert("rotation_euler", index=2, frame=112)
    t.rotation_euler.z = 0.0
    t.keyframe_insert("rotation_euler", index=2, frame=140)

    # barrel recoil: translate the gun group backwards along +Y in pivot space
    parts = [bpy.data.objects[n] for n in
             ("GunBarrel", "GunSleeve", "GunMuzzleRing")]
    muzzle = bpy.data.objects.get("GunMuzzle")
    for obj in parts + ([muzzle] if muzzle else []):
        obj.location.y = 0.0
        obj.keyframe_insert("location", index=1, frame=92)
        obj.location.y = 0.26
        obj.keyframe_insert("location", index=1, frame=F_FIRE + 1)
        obj.keyframe_insert("location", index=1, frame=F_FIRE + 3)
        obj.location.y = 0.0
        obj.keyframe_insert("location", index=1, frame=F_FIRE + 14)
    for name in ("GunBarrel", "GunSleeve", "GunMuzzleRing"):
        set_interpolation(bpy.data.objects[name], "BEZIER")


def build_muzzle_flash(coll, gun_pivot):
    flash_mat = material("MuzzleFlash", "#ff9a2e", 0.4, 0.0,
                         emit="#ff6a10", emit_strength=1.1)
    v, f = [], []
    parts = []
    # star of flat wedges around an axis pointing -Y
    for i in range(6):
        a = 2 * math.pi * i / 6
        r_in, r_out = 0.02, 0.21
        wid = 0.07
        y0, y1 = -3.02, -3.38 - 0.07 * (i % 2)
        p1 = (r_in * math.cos(a) - wid * math.sin(a), y0, r_in * math.sin(a) + wid * math.cos(a))
        p2 = (r_in * math.cos(a) + wid * math.sin(a), y0, r_in * math.sin(a) - wid * math.cos(a))
        p3 = (r_out * math.cos(a), y1, r_out * math.sin(a))
        parts.append(([p1, p2, p3], [(0, 1, 2)]))
    v, f = merge(*parts)
    obj = new_object("MuzzleFlash", v, f, coll, flash_mat, parent=gun_pivot,
                     keep_world=False)
    obj.location = (0, 0, 0)
    obj.scale = (0, 0, 0)
    for fr, s in ((1, 0.0), (F_FIRE - 1, 0.0), (F_FIRE, 1.0), (F_FIRE + 2, 0.55),
                  (F_FIRE + 5, 0.0), (F_END, 0.0)):
        obj.scale = (s, s, s)
        obj.keyframe_insert("scale", frame=fr)
    set_interpolation(obj, "CONSTANT")

    light_data = bpy.data.lights.new("MuzzleLightData", "POINT")
    light_data.color = (1.0, 0.72, 0.35)
    light_data.shadow_soft_size = 0.4
    light = bpy.data.objects.new("MuzzleLight", light_data)
    coll.objects.link(light)
    light.parent = gun_pivot
    light.location = (0, -3.2, 0)
    for fr, e in ((1, 0.0), (F_FIRE - 1, 0.0), (F_FIRE, 2200.0),
                  (F_FIRE + 2, 1200.0), (F_FIRE + 5, 0.0), (F_END, 0.0)):
        light_data.energy = e
        light_data.keyframe_insert("energy", frame=fr)


# ----------------------------------------------------------------------------
# studio scene for the preview render
# ----------------------------------------------------------------------------
def studio():
    scene = bpy.context.scene
    engines = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if cand in engines:
            scene.render.engine = cand
            break
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.fps = FPS
    ee = scene.eevee
    for attr, val in (("taa_render_samples", 64), ("use_raytracing", False),
                      ("use_gtao", True)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except Exception:
                pass

    world = bpy.data.worlds.get("AnimWorld") or bpy.data.worlds.new("AnimWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.34, 0.43, 0.55, 1)
    bg.inputs[1].default_value = 0.9
    scene.world = world

    def ensure(name, data):
        obj = bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
        if obj.name not in bpy.context.scene.collection.objects:
            try:
                bpy.context.scene.collection.objects.link(obj)
            except RuntimeError:
                pass
        return obj

    ground_mesh = bpy.data.meshes.new("AnimGround")
    s = 60
    ground_mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [],
                            [(0, 1, 2, 3)])
    ground_mesh.update()
    ground = ensure("AnimGround", ground_mesh)
    gm = material("AnimGroundMat", "#8c7a58", 0.95)
    if not ground.data.materials:
        ground.data.materials.append(gm)

    sun_data = bpy.data.lights.new("AnimSunData", "SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(8)
    sun = ensure("AnimSun", sun_data)
    sun.rotation_euler = (math.radians(52), math.radians(6), math.radians(-38))

    for nm, loc, energy, size in (("AnimFill", (-8.0, -6.0, 5.0), 1200, 6.0),
                                  ("AnimRim", (7.0, 8.0, 6.0), 1500, 5.0)):
        data = bpy.data.lights.new(nm + "Data", "AREA")
        data.energy = energy
        data.size = size
        obj = ensure(nm, data)
        obj.location = loc
        obj.rotation_euler = (Vector((0, -1.7, 1.3)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    cam_data = bpy.data.cameras.new("AnimCamData")
    cam_data.lens = 42
    cam = ensure("AnimCam", cam_data)
    cam.location = (8.8, -11.6, 3.9)
    cam.rotation_euler = (Vector((0.0, -1.7, 1.30)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    # a couple of crates so the movement reads
    crate_mat = material("AnimCrate", "#6b5a3e", 0.85)
    for i, (x, y, sz) in enumerate(((6.5, 3.0, 1.1), (-6.5, -4.5, 0.85), (5.5, -9.0, 0.95))):
        v, f = box_data((x, y, sz / 2), (sz, sz, sz))
        new_object(f"AnimCrate_{i}", v, f, bpy.context.scene.collection, crate_mat)

    if hasattr(scene.render.image_settings, "media_type"):
        scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = os.path.join(BASE, "preview", "sherman_anim.mp4")


def fcurve_list(action):
    """Action.fcurves is gone in Blender 5 (slotted actions)."""
    fcs = getattr(action, "fcurves", None)
    if fcs is not None:
        return list(fcs)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def set_interpolation(obj, mode="LINEAR"):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in fcurve_list(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = mode


def main():
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    scene_setup()
    coll = bpy.data.collections["M4A1_76"]
    root = bpy.data.objects["M4A1_Sherman"]
    track_mat = bpy.data.materials["Sherman_Track"]

    links, poses, n = build_animated_tracks(coll, root, track_mat)
    animate_tracks(links, poses, n)
    animate_wheels()
    animate_hull(root)
    animate_turret_and_gun()
    build_muzzle_flash(coll, bpy.data.objects["Gun_Pivot"])
    studio()

    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(BASE, "assets", "models", "m4a1_sherman_anim.blend"))
    print("[anim] saved animated blend")


main()
