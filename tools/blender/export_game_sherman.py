"""Export the animated M4A1 Sherman in the form the game needs.

Source (read only):  assets/models/m4a1_sherman_anim.blend
Output (default):    versions/v3/assets/models/m4a1_sherman_hero.glb
                     versions/v3/assets/models/m4a1_sherman_troop.glb
                     versions/v3/assets/models/manifest.json
Override with the SHERMAN_EXPORT_OUT env var (absolute path).

Why a custom export instead of the stock glTF exporter?

* The demo scene bakes hull translation (drive), turret traverse, gun recoil and
  a muzzle flash into one 240-frame timeline.  A game needs those separated:
  the hull position comes from physics, the turret comes from the player's aim,
  and only the treadmill / recoil are animations.
* Two LODs are produced.  Hero keeps the 146 individually animated track links;
  Troop merges them into two static track meshes (and the running gear into two
  meshes) so four enemy tanks stay cheap to draw.
* Static hull / turret / gun parts are joined per moving group, which drops the
  hero from 304 meshes to ~167 and the troop tank to ~10.

Run:
    /Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
        --factory-startup --python tools/blender/export_game_sherman.py
"""

import hashlib
import json
import math
import os

import bpy
from mathutils import Vector

BASE = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D"
SRC = os.path.join(BASE, "assets", "models", "m4a1_sherman_anim.blend")
OUT_DIR = os.environ.get(
    "SHERMAN_EXPORT_OUT",
    os.path.join(BASE, "versions", "v3", "assets", "models"),
)

GAME_SCALE = 0.22        # the view scales the metre-sized source model by this
FPS = 24
STEP = 4                 # frames per track-link pitch (matches animate_sherman.py)
PITCH_M = 0.1668         # one link pitch in metres
TRACK_N = 73
TRACK_R = 0.40
TRACK_Z0 = 0.545
FWD_END = 81
F_REV_START = 165
F_REV_END = 237

STATIC_GROUP_EXCLUDE = (
    "AnimLink_", "Tire_", "Hub_", "HubCap_", "Sprocket_", "SprocketTeeth_",
    "Idler_", "Roller_",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def fcurves(action):
    """Blender 5 slotted actions."""
    fcs = getattr(action, "fcurves", None)
    if fcs is not None:
        return list(fcs)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in getattr(layer, "strips", []):
            for bag in getattr(strip, "channelbags", []):
                out.extend(bag.fcurves)
    return out


def clear_animation():
    for obj in bpy.data.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)


def deselect_all():
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)


def join_meshes(objs, name):
    objs = [o for o in objs if o and o.type == "MESH"]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    deselect_all()
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    joined.data.name = name
    return joined


def track_poses(n=TRACK_N):
    """Evenly spaced link poses around the stadium: (y, z, theta).

    Copied from tools/blender/animate_sherman.py so the exported loop uses the
    exact same path as the Blender preview.
    """
    sprocket_y, idler_y, R = -2.40, 2.40, TRACK_R
    z0 = TRACK_Z0
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
        while i < len(pts) - 1 and acc + seglens[i] < s:
            acc += seglens[i]
            i += 1
        t = (s - acc) / seglens[i] if seglens[i] else 0.0
        a, b = pts[i], pts[(i + 1) % len(pts)]
        py = a[0] + (b[0] - a[0]) * t
        pz = a[1] + (b[1] - a[1]) * t
        theta = math.atan2(b[1] - a[1], b[0] - a[0])
        poses.append((py, pz, theta))
    return poses, total


def push_nla(obj, action, track_name, start, end):
    ad = obj.animation_data or obj.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, int(start), action)
    strip.frame_start = start
    strip.frame_end = end
    strip.action_frame_start = start
    strip.action_frame_end = end
    # Blender 5: keep the slot that keyframe_insert() created.
    if hasattr(strip, "action_slot") and getattr(action, "slots", None):
        try:
            strip.action_slot = action.slots[0]
        except Exception:
            pass
    ad.action = None
    return track


def bake_action(obj, name, rows, interpolation="LINEAR"):
    """rows: [(frame, location_tuple, rotation_euler_tuple_or_None)]"""
    ad = obj.animation_data or obj.animation_data_create()
    ad.action = None
    for frame, loc, rot in rows:
        if loc is not None:
            obj.location = loc
            obj.keyframe_insert("location", frame=frame)
        if rot is not None:
            obj.rotation_euler = rot
            obj.keyframe_insert("rotation_euler", frame=frame)
    act = ad.action
    act.name = name
    for fc in fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = interpolation
    return act


def make_drive_clip(link_objs, wheel_objs, poses, perimeter):
    loop_end = 1 + TRACK_N * STEP          # 293
    sides = {"L": -1.02, "R": 1.02}

    for tag, objs in link_objs.items():
        sx = sides[tag]
        for k, obj in enumerate(objs):
            rows = []
            for i in range(TRACK_N + 1):
                py, pz, theta = poses[(k + i) % TRACK_N]
                rows.append((1 + i * STEP, (sx, py, pz), (theta, 0.0, 0.0)))
            act = bake_action(obj, f"Drive_Link_{tag}_{k:02d}", rows)
            push_nla(obj, act, "Drive", 1, loop_end)

    # A wheel must turn a whole number of revolutions per loop, otherwise the
    # seamless loop would visibly jump.  Snap the rate to the nearest turn.
    distances = {"Tire": 0.325, "Hub": 0.325, "HubCap": 0.325,
                 "Sprocket": 0.36, "SprocketTeeth": 0.36,
                 "Idler": 0.35, "Roller": 0.085}
    for obj in wheel_objs:
        radius = next((v for k, v in distances.items() if obj.name.startswith(k)), None)
        if radius is None:
            continue
        turns = max(1, int(round(perimeter / (2 * math.pi * radius))))
        rows = []
        for i in range(TRACK_N + 1):
            rows.append((1 + i * STEP, None, (2 * math.pi * turns * i / TRACK_N, 0.0, 0.0)))
        act = bake_action(obj, f"Drive_Wheel_{obj.name}", rows)
        push_nla(obj, act, "Drive", 1, loop_end)


def make_fire_clip(gun_objs):
    for obj in gun_objs:
        base = obj.location.y          # GunMuzzle sits at the barrel tip
        rows = [
            (1,  (obj.location.x, base, obj.location.z), None),
            (5,  (obj.location.x, base + 0.26, obj.location.z), None),
            (7,  (obj.location.x, base + 0.26, obj.location.z), None),
            (18, (obj.location.x, base, obj.location.z), None),
        ]
        act = bake_action(obj, f"Fire_{obj.name}", rows, interpolation="BEZIER")
        push_nla(obj, act, "Fire", 1, 18)


# ---------------------------------------------------------------------------
# scene surgery
# ---------------------------------------------------------------------------
def prepare_scene():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    scene = bpy.context.scene
    scene.render.fps = FPS

    # Drop the preview studio (camera, lights, ground, crates).
    keep = {o.name for o in bpy.data.collections["M4A1_76"].objects}
    for obj in list(bpy.data.objects):
        if obj.name not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)

    # The static track meshes were only kept as a fallback; the game uses links.
    for name in ("Track_L", "Track_R"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Muzzle flash and muzzle light are spawned by the engine, not the asset.
    for name in ("MuzzleFlash", "MuzzleLight"):
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    root = bpy.data.objects["M4A1_Sherman"]
    turret = bpy.data.objects["Turret_Pivot"]
    gun = bpy.data.objects["Gun_Pivot"]

    clear_animation()
    scene.frame_set(1)
    root.location = (0.0, 0.0, 0.0)
    root.rotation_euler = (0.0, 0.0, 0.0)
    turret.rotation_euler = (0.0, 0.0, 0.0)
    # Put the muzzle marker at the real barrel tip (the source blend's empty
    # sits at the breech, which would spawn muzzle flash inside the turret).
    muzzle = bpy.data.objects.get("GunMuzzle")
    if muzzle:
        inv = gun.matrix_world.inverted()
        tips = []
        for name in ("GunBarrel", "GunMuzzleRing"):
            obj = bpy.data.objects.get(name)
            if not obj:
                continue
            for corner in obj.bound_box:
                tips.append((inv @ (obj.matrix_world @ Vector(corner))).y)
        muzzle.location = (0.0, min(tips), 0.0)
        print(f"[export] muzzle tip local y={muzzle.location.y:.4f}")

    return root, turret, gun


def collect_parts(root, turret, gun):
    prefixes = STATIC_GROUP_EXCLUDE
    links = {"L": [], "R": []}
    wheels = []
    hull = []
    turret_parts = []
    gun_parts = []

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        name = obj.name
        if name.startswith("AnimLink_"):
            links[name[9]].append(obj)
        elif obj.parent is root:
            if name.startswith(prefixes):
                wheels.append(obj)
            else:
                hull.append(obj)
        elif obj.parent is turret:
            turret_parts.append(obj)
        elif obj.parent is gun:
            gun_parts.append(obj)

    for side in links:
        links[side].sort(key=lambda o: o.name)
    return links, wheels, hull, turret_parts, gun_parts


def join_static(hull, turret_parts):
    """One mesh each for hull and turret. Gun parts stay separate: they recoil."""
    hull_obj = join_meshes(hull, "Hull")
    turret_obj = join_meshes(turret_parts, "Turret")
    return hull_obj, turret_obj


def join_wheels(root):
    """Join each wheel with its own bolt children, keep wheels separate."""
    prefixes = ("Tire_", "Hub_", "HubCap_", "Sprocket_", "SprocketTeeth_",
                "Idler_", "Roller_")
    candidates = [o for o in bpy.data.objects
                  if o.type == "MESH" and o.parent is root
                  and o.name.startswith(prefixes) and "_Bolt" not in o.name]
    out = []
    for obj in candidates:
        children = [c for c in obj.children if c.type == "MESH"]
        out.append(join_meshes([obj] + children, obj.name))
    return out


def glb_stats(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def triangle_count():
    total = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def export_glb(path, animations=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=False,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_materials="EXPORT",
        export_animations=animations,
        export_animation_mode="NLA_TRACKS",
        export_merge_animation="NLA_TRACK",
        export_force_sampling=False,
        export_optimize_animation_size=True,
        export_anim_slide_to_zero=True,
        export_bake_animation=False,
        export_nla_strips=True,
    )
    print("[export] wrote", path, os.path.getsize(path), "bytes")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    root, turret, gun = prepare_scene()
    links, wheels, hull, turret_parts, gun_parts = collect_parts(root, turret, gun)
    print(f"[export] parts: links={len(links['L'])+len(links['R'])} wheels={len(wheels)} "
          f"hull={len(hull)} turret={len(turret_parts)} gun={len(gun_parts)}")

    join_static(hull, turret_parts)
    wheels = join_wheels(root)
    print(f"[export] after join: wheels={len(wheels)}")

    poses, perimeter = track_poses()
    print(f"[export] track perimeter {perimeter:.4f} m, pitch {perimeter/TRACK_N:.4f} m")
    make_drive_clip(links, wheels, poses, perimeter)
    make_fire_clip([bpy.data.objects[n] for n in ("GunBarrel", "GunSleeve",
                                                   "GunMuzzleRing", "GunMuzzle")])

    scene = bpy.context.scene
    scene.frame_set(1)

    hero_path = os.path.join(OUT_DIR, "m4a1_sherman_hero.glb")
    hero_tris = triangle_count()
    export_glb(hero_path)
    hero_stats = glb_stats(hero_path)

    # ---- troop LOD -------------------------------------------------------
    # Freeze the track links at frame 1 and merge each side into one mesh.
    for side, objs in links.items():
        for obj in objs:
            if obj.animation_data:
                obj.animation_data_clear()
        join_meshes(objs, f"Track_{side}")

    # Merge the running gear per side as well.
    def is_left(name):
        return name.endswith("_L") or "_L_" in name
    left = [o for o in wheels if is_left(o.name)]
    right = [o for o in wheels if not is_left(o.name)]
    join_meshes(left, "RunningGear_L")
    join_meshes(right, "RunningGear_R")

    # Only the gun recoil animation is kept for troops.
    for obj in bpy.data.objects:
        if obj.animation_data:
            for track in list(obj.animation_data.nla_tracks):
                if track.name != "Fire":
                    obj.animation_data.nla_tracks.remove(track)

    troop_path = os.path.join(OUT_DIR, "m4a1_sherman_troop.glb")
    troop_tris = triangle_count()
    export_glb(troop_path)
    troop_stats = glb_stats(troop_path)

    # ---- manifest --------------------------------------------------------
    manifest = {
        "generated_at": "2026-10-20",
        "path_base": "repository root",
        "source_blend": "assets/models/m4a1_sherman_anim.blend",
        "exporter": "tools/blender/export_game_sherman.py",
        "blender": bpy.app.version_string,
        "units": f"metres (source); game scale {GAME_SCALE}",
        "game_scale": GAME_SCALE,
        "orientation": "glTF +Z forward, +Y up, origin at track contact",
        "clips": {"drive": "Drive", "fire": "Fire"},
        "tags": {"turret": "Turret_Pivot", "gun": "Gun_Pivot", "muzzle": "GunMuzzle"},
        "models": {
            "sherman_hero": {
                "file": "m4a1_sherman_hero.glb",
                "lod": "hero",
                "has_drive_animation": True,
                "tris": hero_tris,
                "bytes": hero_stats["bytes"],
                "sha256": hero_stats["sha256"],
            },
            "sherman_troop": {
                "file": "m4a1_sherman_troop.glb",
                "lod": "troop",
                "has_drive_animation": False,
                "tris": troop_tris,
                "bytes": troop_stats["bytes"],
                "sha256": troop_stats["sha256"],
            },
        },
    }
    with open(os.path.join(OUT_DIR, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print("[export] manifest written")


main()
