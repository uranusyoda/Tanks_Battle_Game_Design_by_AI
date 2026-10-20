"""Build an animated, game-ready M4 Sherman (75mm) in Blender.

Run inside Blender (via MCP execute_blender_code):
    exec(compile(open("/path/to/build_sherman.py").read(), "build_sherman.py", "exec"))

Conventions:
  X = width, Y = length (front = -Y), Z = up. Metres.
  Root "M4_Sherman" at the ground centre.

Animation clips (24 fps, every clip starts at frame 1):
  TurretTurn  1-96   turret yaw sweep
  Fire        1-60   recoil + muzzle flash + smoke
  Drive       1-120  forward/back, wheel spin, scrolling track texture, exhaust

Track motion uses a tiling tread texture on the track band (UV u runs along
the loop); scroll map.offset.x in three.js for runtime movement.
"""

import bpy
import bmesh
import math
import os
from mathutils import Vector

OUT_DIR = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D/assets/models"

C = bpy.context
D = bpy.data

FPS = 24
LINK = 0.27          # metres per tread link (one texture repeat)
TRACK_X = 1.12
TRACK_W = 0.44
TRACK_R = 0.50
TRACK_T = 0.10
CY1, CY2 = -2.02, 2.02
Z0 = 0.56
WHEEL_YS = (-1.92, -1.26, -0.34, 0.34, 1.26, 1.92)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def srgb(c):
    v = c / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def material(name, rgb, rough=0.7, metal=0.0):
    m = D.materials.get(name)
    if m:
        return m
    m = D.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    col = (srgb(rgb[0]), srgb(rgb[1]), srgb(rgb[2]), 1.0)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    m.diffuse_color = col
    m.roughness = rough
    m.metallic = metal
    return m


def activate(o):
    if C.object and C.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    C.view_layer.objects.active = o


def bevel(o, width=0.03, segments=2, angle=40):
    md = o.modifiers.new("bev", "BEVEL")
    md.width = width
    md.segments = segments
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    activate(o)
    bpy.ops.object.modifier_apply(modifier=md.name)


def box(name, size, loc, rot=(0, 0, 0), mat=None, bev=0.0, seg=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = C.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    activate(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bev > 0:
        bevel(o, bev, seg)
    if mat:
        o.data.materials.append(mat)
    return o


def cyl(name, r, depth, loc, axis="Z", verts=16, mat=None, bev=0.0, r2=None):
    rot = {"Z": (0, 0, 0), "X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0)}[axis]
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(
            vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = C.object
    o.name = name
    if bev > 0:
        bevel(o, bev, 3, 30)
    if mat:
        o.data.materials.append(mat)
    return o


def sphere(name, r, loc, mat=None, subdiv=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = C.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    return o


def star(name, loc, radius, depth, facing="X", mat=None):
    verts = []
    for i in range(10):
        a = math.radians(90 + i * 36)
        rr = radius if i % 2 == 0 else radius * 0.42
        verts.append((0.0, rr * math.cos(a), rr * math.sin(a)))
    verts.append((0.0, 0.0, 0.0))
    faces = [(10, (i + 1) % 10, i) for i in range(10)]
    me = D.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = D.objects.new(name, me)
    C.collection.objects.link(o)
    o.location = loc
    if facing == "-X":
        o.rotation_euler = (0, 0, math.pi)
    for p in me.polygons:
        p.use_smooth = False
    if mat:
        me.materials.append(mat)
    return o


def parent_to(o, p):
    o.parent = p
    o.matrix_parent_inverse = p.matrix_world.inverted()


def empty(name, loc):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=loc)
    e = C.object
    e.name = name
    e.empty_display_size = 0.4
    return e


def mesh_object(name, bm, mat=None):
    me = D.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = D.objects.new(name, me)
    C.collection.objects.link(o)
    if mat:
        me.materials.append(mat)
    return o


def apply_transforms(o):
    """Bake rotation/scale so local axes match world (joined cylinders carry a 90 deg rotation)."""
    activate(o)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


def join_meshes(objs, name, origin=None):
    objs = [o for o in objs if o and o.type == "MESH"]
    if not objs:
        return None
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    C.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = C.object
    o.name = name
    if origin is not None:
        C.scene.cursor.location = origin
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    return o


# --------------------------------------------------------------------------- #
# reset
# --------------------------------------------------------------------------- #

if C.object and C.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=True)
for coll in (D.meshes, D.curves, D.materials):
    for b in list(coll):
        if b.users == 0:
            coll.remove(b)

C.scene.render.fps = FPS
C.scene.frame_start = 1
C.scene.frame_end = 120


# --------------------------------------------------------------------------- #
# materials
# --------------------------------------------------------------------------- #

OLIVE = material("Sherman_Olive", (74, 80, 48), 0.75)
OLIVE_D = material("Sherman_OliveDark", (56, 61, 37), 0.80)
RUBBER = material("Sherman_Rubber", (28, 28, 26), 0.95)
METAL = material("Sherman_Metal", (110, 110, 100), 0.38, 0.85)
STAR = material("Sherman_Star", (225, 224, 208), 0.8)
LENS = material("Sherman_Lens", (150, 152, 132), 0.25, 0.3)
TRACK = material("Sherman_Track", (38, 38, 34), 0.85, 0.25)


def make_track_image():
    w, h = 128, 64
    img = D.images.new("TrackTread", w, h, alpha=False)
    px = [0.0] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            v = 0.10
            if 6 <= x < 122:
                v = 0.26
            if y < 8 or y >= h - 8:
                v = 0.40
            if 14 <= y < 20 or 44 <= y < 50:
                v = 0.17
            if 22 <= y < 42 and 18 <= x < 110:
                v = 0.33
            if x < 6 or x >= 122:
                v = 0.05
            for bx, by in ((26, 16), (26, 48), (102, 16), (102, 48)):
                if (x - bx) ** 2 + (y - by) ** 2 <= 9:
                    v = 0.55
            i = (y * w + x) * 4
            px[i] = v
            px[i + 1] = v
            px[i + 2] = v * 0.97
            px[i + 3] = 1.0
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(px)
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        img.filepath_raw = os.path.join(OUT_DIR, "track_tread.png")
        img.file_format = "PNG"
        img.save()
        img.source = "FILE"
        img.reload()
        img.pack()
        print("TRACK_TEX packed", bool(img.packed_file))
    except Exception as e:
        print("TRACK_TEX pack failed", e)
    return img


def track_material(img):
    m = D.materials.new("Sherman_TrackTex")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.15
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.extension = "REPEAT"
    tx.location = (-380, 0)
    mp.location = (-620, 0)
    uv.location = (-840, 0)
    nt.links.new(uv.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    return m, mp


TRACK_IMG = make_track_image()
TRACK_MAT, TRACK_MAP = track_material(TRACK_IMG)

SMOKE = material("Sherman_Smoke", (80, 80, 80), 1.0)
_smoke_bsdf = next(n for n in SMOKE.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_smoke_bsdf.inputs["Alpha"].default_value = 0.16
for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED"),
                  ("shadow_method", "NONE"), ("use_transparent_shadow", False)):
    try:
        setattr(SMOKE, attr, val)
    except Exception:
        pass
SMOKE.show_transparent_back = False

FLASH = D.materials.new("Sherman_Flash")
FLASH.use_nodes = True
_fb = next(n for n in FLASH.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_fb.inputs["Base Color"].default_value = (1.0, 0.45, 0.08, 1)
_fb.inputs["Roughness"].default_value = 0.6
try:
    _fb.inputs["Emission Color"].default_value = (1.0, 0.28, 0.03, 1)
    _fb.inputs["Emission Strength"].default_value = 2.0
except Exception:
    pass


# --------------------------------------------------------------------------- #
# hierarchy
# --------------------------------------------------------------------------- #

ROOT = empty("M4_Sherman", (0, 0, 0))
ROOT.empty_display_size = 0.8
TURRET = empty("Turret_Pivot", (0, -0.05, 1.62))
parent_to(TURRET, ROOT)
GUN_PIVOT = empty("Gun_Pivot", (0, -1.35, 2.05))
parent_to(GUN_PIVOT, TURRET)


def hull(o):
    parent_to(o, ROOT)
    return o


def turret(o):
    parent_to(o, TURRET)
    return o


def gun(o):
    parent_to(o, GUN_PIVOT)
    return o


# --------------------------------------------------------------------------- #
# hull
# --------------------------------------------------------------------------- #

HULL_W = 2.34
HULL_LOW_W = 2.02


def extruded_hull(name, profile, width, mat, bev=0.035):
    bm = bmesh.new()
    left = [bm.verts.new((-width / 2, y, z)) for y, z in profile]
    right = [bm.verts.new((width / 2, y, z)) for y, z in profile]
    bm.faces.new(left[::-1])
    bm.faces.new(right)
    for i in range(len(profile)):
        j = (i + 1) % len(profile)
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_object(name, bm, mat)
    bevel(o, bev, 2)
    return o


LOW_PROFILE = [
    (-2.42, 0.50),
    (-2.74, 0.53),
    (-2.76, 0.84),
    (-2.70, 1.08),
    (2.58, 1.08),
    (2.58, 0.66),
    (2.42, 0.50),
]
hull(extruded_hull("Hull_Lower", LOW_PROFILE, HULL_LOW_W, OLIVE))

UP_PROFILE = [
    (-2.70, 1.06),
    (-2.08, 1.58),
    (2.24, 1.58),
    (2.60, 1.16),
    (2.60, 1.06),
]
hull(extruded_hull("Hull_Upper", UP_PROFILE, HULL_W, OLIVE))

hull(box("Nose", (1.70, 0.46, 0.56), (0, -2.76, 0.82), mat=OLIVE, bev=0.16, seg=3))
for x in (-0.82, 0.82):
    hull(box("FinalDrive_%s" % x, (0.46, 0.20, 0.34), (x, -2.66, 0.78), mat=OLIVE, bev=0.08))
hull(box("Belly", (2.0, 4.75, 0.06), (0, 0.0, 0.49), mat=OLIVE_D))

for x in (-0.54, 0.54):
    side = "L" if x < 0 else "R"
    hull(box("Hatch_%s" % side, (0.52, 0.46, 0.08),
             (x, -2.30, 1.40), rot=(math.radians(45), 0, 0), mat=OLIVE, bev=0.035))
    hull(box("Periscope_%s" % side, (0.16, 0.10, 0.07),
             (x, -2.56, 1.46), rot=(math.radians(45), 0, 0), mat=OLIVE_D))

hull(sphere("BowMG", 0.14, (0.62, -2.42, 1.20), METAL))
hull(cyl("BowMG_Barrel", 0.035, 0.34, (0.62, -2.56, 1.22), axis="Y", verts=10, mat=METAL))

for x in (-0.82, 0.82):
    hull(cyl("Light_%s" % x, 0.075, 0.12, (x, -2.26, 1.52), axis="Y", verts=12, mat=LENS))
    hull(cyl("LightBase_%s" % x, 0.11, 0.08, (x, -2.17, 1.50), axis="Y", verts=12, mat=METAL))
    hull(box("LightGuard_%s" % x, (0.26, 0.26, 0.03), (x, -2.22, 1.62), mat=OLIVE_D))

for x in (-0.64, 0.64):
    hull(box("TowHook_%s" % x, (0.11, 0.30, 0.13), (x, -2.88, 0.63), mat=OLIVE_D, bev=0.02))

for i in range(3):
    hull(box("SpareLink_%d" % i, (0.60, 0.11, 0.11),
             (0, -2.38 + i * 0.03, 1.26 - i * 0.10),
             rot=(math.radians(45), 0, 0), mat=TRACK, bev=0.015))

hull(box("EngineDeck", (2.02, 1.45, 0.12), (0, 1.66, 1.63), mat=OLIVE, bev=0.03))
for i in range(5):
    hull(box("Grille_%d" % i, (1.78, 0.07, 0.05),
             (0, 1.14 + i * 0.26, 1.70), mat=OLIVE_D))
for x in (-0.58, 0.58):
    hull(cyl("Exhaust_%s" % x, 0.085, 0.32, (x, 2.68, 1.30), axis="Y", verts=10, mat=METAL))
hull(box("RearPlate", (1.40, 0.08, 0.42), (0, 2.62, 0.92), mat=OLIVE_D))

for x in (-1.14, 1.14):
    hull(box("FenderF_%s" % x, (0.38, 0.85, 0.045), (x, -2.30, 1.12),
             rot=(math.radians(-6), 0, 0), mat=OLIVE, bev=0.015))
    hull(box("FenderR_%s" % x, (0.38, 0.70, 0.045), (x, 2.28, 1.12),
             rot=(math.radians(6), 0, 0), mat=OLIVE, bev=0.015))

hull(star("Star_L", (-HULL_W / 2 - 0.003, 0.15, 1.30), 0.22, 0.004, facing="-X", mat=STAR))
hull(star("Star_R", (HULL_W / 2 + 0.003, 0.15, 1.30), 0.22, 0.004, facing="X", mat=STAR))


# --------------------------------------------------------------------------- #
# turret
# --------------------------------------------------------------------------- #

turret(cyl("TurretRing", 0.95, 0.10, (0, -0.05, 1.62), verts=24, mat=OLIVE_D))
body = cyl("TurretBody", 0.98, 0.80, (0, -0.05, 2.05), verts=12, mat=OLIVE, r2=0.88)
bevel(body, 0.12, 3, 30)
turret(body)
turret(cyl("TurretRoof", 0.80, 0.05, (0, -0.05, 2.44), verts=16, mat=OLIVE))

turret(cyl("Cupola", 0.31, 0.20, (0.34, 0.21, 2.54), verts=12, mat=OLIVE))
turret(cyl("CupolaHatch", 0.22, 0.05, (0.34, 0.21, 2.65), verts=12, mat=OLIVE_D))
turret(box("LoaderHatch", (0.44, 0.44, 0.05), (-0.40, -0.07, 2.47), mat=OLIVE_D, bev=0.02))

turret(cyl("GunMount", 0.52, 0.50, (0, -1.20, 2.05), axis="Y", verts=12, mat=OLIVE, r2=0.40))
turret(box("Mantlet", (0.92, 0.50, 0.70), (0, -1.50, 2.05), mat=OLIVE, bev=0.14, seg=4))
turret(cyl("CoaxMG", 0.045, 0.30, (0.28, -1.78, 2.14), axis="Y", verts=10, mat=METAL))
for x in (-0.52, 0.52):
    turret(box("LiftingEye_%s" % x, (0.16, 0.06, 0.05), (x, 0.44, 2.47), mat=OLIVE_D))

turret(cyl("MG_Mount", 0.07, 0.18, (-0.58, 0.29, 2.40), verts=10, mat=METAL))
turret(box("MG_Body", (0.10, 0.42, 0.11), (-0.58, 0.21, 2.51), mat=METAL, bev=0.012))
turret(cyl("MG_Barrel", 0.024, 0.60, (-0.58, -0.19, 2.51), axis="Y", verts=8, mat=METAL))

turret(cyl("Antenna", 0.012, 0.90, (0.66, 0.63, 2.86), verts=6, mat=METAL))

for i in range(2):
    turret(box("TurretLink_%d" % i, (0.10, 0.26, 0.28), (-0.98, -0.27 + i * 0.30, 2.10),
               mat=TRACK, bev=0.01))


# --------------------------------------------------------------------------- #
# main gun
# --------------------------------------------------------------------------- #

gun(cyl("GunBarrel", 0.105, 1.85, (0, -2.40, 2.05), axis="Y", verts=14, mat=OLIVE, r2=0.075))
gun(cyl("GunMuzzle", 0.11, 0.24, (0, -3.32, 2.05), axis="Y", verts=14, mat=OLIVE_D))
gun(cyl("GunBreech", 0.17, 0.44, (0, -1.40, 2.05), axis="Y", verts=12, mat=OLIVE_D))


# --------------------------------------------------------------------------- #
# tracks + running gear
# --------------------------------------------------------------------------- #

def capsule_path(cy1, cy2, z0, r, seg=12, step=0.27):
    pts = []
    for i in range(seg + 1):
        a = math.radians(90 + 180 * i / seg)
        pts.append(((cy1 + r * math.cos(a), z0 + r * math.sin(a)),
                    (math.cos(a), math.sin(a))))
    n = max(1, round((cy2 - cy1) / step))
    for i in range(1, n):
        pts.append(((cy1 + (cy2 - cy1) * i / n, z0 - r), (0.0, -1.0)))
    for i in range(seg + 1):
        a = math.radians(270 + 180 * i / seg)
        pts.append(((cy2 + r * math.cos(a), z0 + r * math.sin(a)),
                    (math.cos(a), math.sin(a))))
    for i in range(1, n):
        pts.append(((cy2 - (cy2 - cy1) * i / n, z0 + r), (0.0, 1.0)))
    return pts


def make_track(name, xc):
    outer = capsule_path(CY1, CY2, Z0, TRACK_R)
    inner = capsule_path(CY1, CY2, Z0, TRACK_R - TRACK_T)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    w2 = TRACK_W / 2
    loops = {}
    for tag, path in (("ol", outer), ("il", inner)):
        for side, xs in (("l", xc - w2), ("r", xc + w2)):
            loops[tag + "_" + side] = [bm.verts.new((xs, p[0][0], p[0][1])) for p in path]
    n = len(outer)
    s = [0.0]
    for i in range(1, n + 1):
        a = outer[i - 1][0]
        b = outer[i % n][0]
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    U = [x / LINK for x in s]

    def set_uv(face, coords):
        for lp, co in zip(face.loops, coords):
            lp[uv].uv = co

    for i in range(n):
        j = (i + 1) % n
        ui, uj = U[i], U[i + 1]
        f = bm.faces.new((loops["ol_l"][i], loops["ol_l"][j], loops["ol_r"][j], loops["ol_r"][i]))
        set_uv(f, [(ui, 0), (uj, 0), (uj, 1), (ui, 1)])
        f = bm.faces.new((loops["il_l"][i], loops["il_r"][i], loops["il_r"][j], loops["il_l"][j]))
        set_uv(f, [(ui, 1), (ui, 0), (uj, 0), (uj, 1)])
        f = bm.faces.new((loops["ol_l"][i], loops["il_l"][i], loops["il_l"][j], loops["ol_l"][j]))
        set_uv(f, [(ui, 0), (ui, 0.3), (uj, 0.3), (uj, 0)])
        f = bm.faces.new((loops["ol_r"][i], loops["ol_r"][j], loops["il_r"][j], loops["il_r"][i]))
        set_uv(f, [(ui, 0), (uj, 0), (uj, 0.3), (ui, 0.3)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_object(name, bm, TRACK_MAT)
    return o


TRACKS = []
for side, xc in (("L", -TRACK_X), ("R", TRACK_X)):
    t = make_track("Track_" + side, xc)
    parent_to(t, ROOT)
    TRACKS.append(t)

AXLES = []   # (object, radius)
for i, y in enumerate(WHEEL_YS):
    parts = []
    for side, xc in (("L", -TRACK_X), ("R", TRACK_X)):
        parts.append(cyl("Wheel_%s_%d" % (side, i), 0.31, 0.17, (xc, y, 0.47),
                         axis="X", verts=16, mat=RUBBER))
        parts.append(cyl("Hub_%s_%d" % (side, i), 0.14, 0.185, (xc, y, 0.47),
                         axis="X", verts=12, mat=METAL))
    o = join_meshes(parts, "Axle_%d" % i, origin=(0, y, 0.47))
    apply_transforms(o)
    parent_to(o, ROOT)
    AXLES.append((o, 0.31))

# bogie brackets stay on the hull
for side, xc in (("L", -TRACK_X), ("R", TRACK_X)):
    for i, y in enumerate(WHEEL_YS):
        hull(box("Bogie_%s_%d" % (side, i), (0.10, 0.40, 0.15), (xc - 0.02, y, 0.82),
                 mat=OLIVE_D, bev=0.02))

# drive sprocket (front) + teeth
parts = []
for side, xc in (("L", -TRACK_X), ("R", TRACK_X)):
    parts.append(cyl("Sprocket_%s" % side, 0.35, 0.19, (xc, -2.16, 0.58),
                     axis="X", verts=16, mat=METAL))
    for k in range(10):
        a = 2 * math.pi * k / 10
        y = -2.16 + 0.38 * math.cos(a)
        z = 0.58 + 0.38 * math.sin(a)
        parts.append(box("Tooth_%s_%d" % (side, k), (0.20, 0.10, 0.10), (xc, y, z),
                         rot=(a + math.pi / 2, 0, 0), mat=METAL))
sp = join_meshes(parts, "Sprocket", origin=(0, -2.16, 0.58))
apply_transforms(sp)
parent_to(sp, ROOT)
AXLES.append((sp, 0.35))

# idler (rear)
parts = [cyl("Idler_%s" % side, 0.33, 0.17, (xc, 2.16, 0.56), axis="X", verts=16, mat=METAL)
         for side, xc in (("L", -TRACK_X), ("R", TRACK_X))]
idl = join_meshes(parts, "Idler", origin=(0, 2.16, 0.56))
apply_transforms(idl)
parent_to(idl, ROOT)
AXLES.append((idl, 0.33))

# return rollers (one object per axle line)
for k, y in enumerate((-0.95, 0.95)):
    parts = [cyl("Roller_%s_%d" % (side, k), 0.10, 0.15, (xc, y, 1.01), axis="X", verts=10, mat=OLIVE_D)
             for side, xc in (("L", -TRACK_X), ("R", TRACK_X))]
    ro = join_meshes(parts, "Roller_%d" % k, origin=(0, y, 1.01))
    apply_transforms(ro)
    parent_to(ro, ROOT)
    AXLES.append((ro, 0.10))


# --------------------------------------------------------------------------- #
# ground, join hull, gun under turret
# --------------------------------------------------------------------------- #

zmin = min((o.matrix_world @ v.co).z for o in D.objects if o.type == "MESH" for v in o.data.vertices)
ROOT.location.z -= zmin

SKIP = {o.name for o in D.objects
        if o.type == "MESH" and (o.name.startswith("Track_") or o.name.startswith("Axle_")
                                 or o.name in ("Sprocket", "Idler", "Roller_0", "Roller_1"))}
Hull = join_meshes([o for o in ROOT.children if o.type == "MESH" and o.name not in SKIP], "Hull")
TurretObj = join_meshes([o for o in TURRET.children if o.type == "MESH"], "Turret")
GunObj = join_meshes([o for o in GUN_PIVOT.children if o.type == "MESH"], "Gun")
apply_transforms(GunObj)

parent_to(GUN_PIVOT, TurretObj)

# The gun meshes get joined into one "Gun" object, which would leave the game
# without a muzzle reference: add an empty at the barrel tip, in world space,
# parented so it follows traverse and recoil.
MUZZLE = empty("GunMuzzle", (0.0, -3.44, 2.05))
parent_to(MUZZLE, GunObj)


# --------------------------------------------------------------------------- #
# FX: muzzle flash, gun smoke, exhaust
# --------------------------------------------------------------------------- #

FLASH_OBJ = None
FIRE_PUFFS = []
EXHAUST_PUFFS = []

cone = cyl("FlashCone", 0.30, 0.85, (0, 0, 0), axis="Y", verts=12, mat=FLASH, r2=0.02)
core = sphere("FlashCore", 0.16, (0, -0.30, 0), FLASH, subdiv=1)
FLASH_OBJ = join_meshes([cone, core], "MuzzleFlash")
apply_transforms(FLASH_OBJ)
FLASH_OBJ.parent = GunObj
try:
    FLASH_OBJ.visible_shadow = False
except Exception:
    pass
FLASH_OBJ.location = (0, -1.10, 0)
FLASH_OBJ.scale = (0.001, 0.001, 0.001)

for i in range(7):
    p = sphere("FireSmoke_%d" % i, 0.28, (0, 0, 0), SMOKE, subdiv=2)
    for poly in p.data.polygons:
        poly.use_smooth = True
    p.parent = GunObj
    try:
        p.visible_shadow = False
    except Exception:
        pass
    p.location = ((i % 3 - 1) * 0.34, -1.02 - (i // 3) * 0.16, 0.02 + (i % 2) * 0.22)
    p.scale = (0.001, 0.001, 0.001)
    FIRE_PUFFS.append(p)

for i in range(8):
    p = sphere("Exhaust_%d" % i, 0.28, (0, 0, 0), SMOKE, subdiv=2)
    for poly in p.data.polygons:
        poly.use_smooth = True
    p.parent = ROOT
    try:
        p.visible_shadow = False
    except Exception:
        pass
    p.location = ((-1) ** i * 0.62, 2.92 + i * 0.05, 1.32 + i * 0.02)
    p.scale = (0.001, 0.001, 0.001)
    EXHAUST_PUFFS.append(p)


# --------------------------------------------------------------------------- #
# animation helpers
# --------------------------------------------------------------------------- #

CUR_NAME = ""
CUR_ACTIONS = []


def anim(obj):
    for o, a in CUR_ACTIONS:
        if o == obj:
            return a
    ad = obj.animation_data_create()
    act = D.actions.new("%s_%s" % (CUR_NAME, obj.name))
    act.use_fake_user = True
    ad.action = act
    CUR_ACTIONS.append((obj, act))
    return act


def key_rot(obj, axis, frame, value):
    obj.rotation_euler[axis] = value
    obj.keyframe_insert("rotation_euler", index=axis, frame=frame)


def key_loc(obj, axis, frame, value):
    obj.location[axis] = value
    obj.keyframe_insert("location", index=axis, frame=frame)


def key_scale(obj, frame, value):
    obj.scale = (value, value, value)
    obj.keyframe_insert("scale", frame=frame)


def set_new_key_interp(interp):
    """New keyframes follow this preference (Blender 5 actions have no .fcurves)."""
    try:
        C.preferences.edit.keyframe_new_interpolation_type = interp
    except Exception:
        pass


def start_clip(name, interp="BEZIER"):
    global CUR_NAME, CUR_ACTIONS
    CUR_NAME = name
    CUR_ACTIONS = []
    set_new_key_interp(interp)


def end_clip():
    for obj, act in CUR_ACTIONS:
        ad = obj.animation_data
        ad.action = None
        tr = ad.nla_tracks.new()
        tr.name = CUR_NAME
        st = tr.strips.new(CUR_NAME, 1, act)
        st.name = CUR_NAME


# --- clip: turret turn ----------------------------------------------------- #

start_clip("TurretTurn")
act = anim(TURRET)
for f, a in [(1, 0.0), (10, 0.0), (42, -0.95), (58, -0.95), (94, 0.0), (96, 0.0)]:
    key_rot(TURRET, 2, f, a)
end_clip()


# --- clip: fire ------------------------------------------------------------ #

start_clip("Fire")

act = anim(GunObj)
for f, y in [(1, -2.40), (9, -2.40), (11, -2.12), (13, -2.12), (26, -2.40), (60, -2.40)]:
    key_loc(GunObj, 1, f, y)

act = anim(GUN_PIVOT)
for f, a in [(1, 0.0), (10, 0.0), (11, 0.02), (18, 0.0), (60, 0.0)]:
    key_rot(GUN_PIVOT, 0, f, a)

act = anim(FLASH_OBJ)
for f, s in [(1, 0.001), (10, 0.001), (11, 1.0), (13, 1.3), (16, 0.001), (60, 0.001)]:
    key_scale(FLASH_OBJ, f, s)

for i, p in enumerate(FIRE_PUFFS):
    act = anim(p)
    t0 = 11 + i * 0.6
    base = tuple(p.location)
    key_scale(p, 1, 0.001)
    key_scale(p, t0, 0.001)
    key_scale(p, t0 + 3, 0.85 + 0.10 * i)
    key_scale(p, t0 + 12, 1.5)
    key_scale(p, t0 + 24, 0.001)
    key_loc(p, 1, t0, base[1])
    key_loc(p, 1, t0 + 24, base[1] - 1.1)
    key_loc(p, 2, t0, base[2])
    key_loc(p, 2, t0 + 24, base[2] + 0.7)
    key_loc(p, 0, t0, base[0])
    key_loc(p, 0, t0 + 24, base[0] * 2.6)

end_clip()


# --- clip: drive ----------------------------------------------------------- #

start_clip("Drive", "LINEAR")

act = anim(ROOT)
for f, y in [(1, 0.0), (8, 0.0), (48, -3.2), (60, -3.2), (104, 0.0), (120, 0.0)]:
    key_loc(ROOT, 1, f, y)

for obj, radius in AXLES:
    act = anim(obj)
    angle = 3.2 / radius
    for f, a in [(1, 0.0), (8, 0.0), (48, angle), (60, angle), (104, 0.0), (120, 0.0)]:
        key_rot(obj, 0, f, a)

for i, p in enumerate(EXHAUST_PUFFS):
    act = anim(p)
    base = tuple(p.location)
    for cyc in range(2):
        t0 = 8 + i * 7 + cyc * 52
        key_scale(p, 1, 0.001)
        key_scale(p, t0, 0.001)
        key_scale(p, t0 + 4, 0.6 + 0.06 * i)
        key_scale(p, t0 + 11, 1.05)
        key_scale(p, t0 + 20, 0.001)
        key_loc(p, 2, t0, base[2])
        key_loc(p, 2, t0 + 20, base[2] + 0.55)
        key_loc(p, 1, t0, base[1])
        key_loc(p, 1, t0 + 20, base[1] + 0.95)

end_clip()


# --- track texture scroll (Blender playback only) -------------------------- #

nt = TRACK_MAT.node_tree
ad = nt.animation_data_create()
act = D.actions.new("Drive_TrackScroll")
act.use_fake_user = True
ad.action = act
set_new_key_interp("LINEAR")
loc = TRACK_MAP.inputs["Location"]
for f, v in [(1, 0.0), (8, 0.0), (48, -3.2 / LINK), (60, -3.2 / LINK), (104, 0.0), (120, 0.0)]:
    loc.default_value[0] = v
    loc.keyframe_insert("default_value", index=0, frame=f)
ad.action = None
tr = ad.nla_tracks.new()
tr.name = "Drive"
tr.strips.new("Drive", 1, act)


# --------------------------------------------------------------------------- #
# save + export
# --------------------------------------------------------------------------- #
def save_and_export(out_dir=None):
    """Standalone export. The pipeline imports this module instead and runs its
    own exporter (tools/blender/pipeline.py), so this only fires when the file
    is run directly."""
    out_dir = out_dir or OUT_DIR
    C.scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")

    tris = 0
    for o in D.objects:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)

    print("OBJECTS", len(D.objects), "MESHES", sum(1 for o in D.objects if o.type == "MESH"), "TRIS", tris)

    os.makedirs(out_dir, exist_ok=True)
    blend_path = os.path.join(out_dir, "m4_sherman.blend")
    glb_path = os.path.join(out_dir, "m4_sherman.glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        export_apply=True,
        export_yup=True,
        use_selection=False,
        export_extras=True,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
    )
    print("SAVED", blend_path)
    print("EXPORTED", glb_path, os.path.getsize(glb_path), "bytes")
    return glb_path


if __name__ == "__main__":
    save_and_export()

