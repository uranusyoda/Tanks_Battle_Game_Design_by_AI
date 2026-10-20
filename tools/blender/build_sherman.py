"""Parametric M4A1(76)W Sherman builder for Blender 5.x.

Run inside Blender via:
    exec(compile(open("<this file>").read(), "<this file>", "exec"))

Conventions
-----------
* Metres, real scale. Front = -Y, up = +Z, ground = Z 0.
* Game-ready hierarchy:
      M4A1_Sherman (empty)
        Hull           (mesh + detail children)
        Turret_Pivot   (empty, ring centre)
          Turret ...   (turret shell + roof details)
          Gun_Pivot    (empty at trunnion, rotates on X for elevation)
            GunBarrel / Mantlet
            GunMuzzle  (empty at barrel tip)
        Track_L / Track_R, wheels, sprockets, idlers
* Everything is rebuilt idempotently into collection "M4A1_76".
"""

import math
import bpy
import bmesh
from mathutils import Vector

# ----------------------------------------------------------------------------
# config
# ----------------------------------------------------------------------------
COLL = "M4A1_76"
ROOT_NAME = "M4A1_Sherman"

TRACK_X = 1.02
TRACK_W = 0.42
WHEEL_R = 0.325
WHEEL_Z = 0.475
WHEEL_Y = [-2.05, -1.23, -0.41, 0.41, 1.23, 2.05]
ROLLER_Z = 0.830
ROLLER_R = 0.085
SPROCKET_Y = -2.40
IDLER_Y = 2.40
PATH_R = 0.40
TRACK_Z = 0.545
BOGIE_Z = 0.58

UPPER_HW = 1.245
SPONSON_Z = 1.00
RING_Z = 1.70
RING_Y = 0.10
TRUNNION = Vector((0.0, -0.95, 1.98))
MUZZLE_Y = -3.98


def srgb(hexstr):
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def glacis_y(z):
    """Y of the sloped front plate for a given height (glacis plane)."""
    return -2.85 + (z - 1.13) * 2.16


# ----------------------------------------------------------------------------
# scene helpers
# ----------------------------------------------------------------------------
def get_collection():
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        coll = bpy.data.collections.new(COLL)
        bpy.context.scene.collection.children.link(coll)
    return coll


def clear_collection(coll):
    for obj in list(coll.objects):
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and data.users == 0 and isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)


def material(name, hexcolor, rough=0.75, metal=0.0):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    r, g, b = srgb(hexcolor)
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = (r, g, b, 1.0)
    return mat


def new_object(name, verts, faces, coll, mat=None, smooth=True, sharp_angle=30.0,
               parent=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], faces)
    mesh.validate(verbose=False)
    mesh.update()

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if smooth:
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < math.radians(sharp_angle)
            else:
                e.smooth = False
        for f in bm.faces:
            f.smooth = True
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, loc, coll, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.25
    obj.location = loc
    coll.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


# ----------------------------------------------------------------------------
# primitives
# ----------------------------------------------------------------------------
def rounded_rect_2d(hw, hh, r, segs=4):
    r = max(0.0, min(r, hw * 0.98, hh * 0.98))
    pts = []
    corners = [
        (hw - r, hh - r, 0.0, 90.0),
        (-hw + r, hh - r, 90.0, 180.0),
        (-hw + r, -hh + r, 180.0, 270.0),
        (hw - r, -hh + r, 270.0, 360.0),
    ]
    for cx, cy, a0, a1 in corners:
        for i in range(segs + 1):
            a = math.radians(a0 + (a1 - a0) * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    out = []
    for p in pts:
        if not out or (abs(p[0] - out[-1][0]) > 1e-6 or abs(p[1] - out[-1][1]) > 1e-6):
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-6 and abs(out[0][1] - out[-1][1]) < 1e-6:
        out.pop()
    return out


def loft(rings, cap_start=True, cap_end=True):
    n = len(rings[0])
    verts = [p for ring in rings for p in ring]
    faces = []
    for i in range(len(rings) - 1):
        a, b = i * n, (i + 1) * n
        for j in range(n):
            k = (j + 1) % n
            faces.append((a + j, a + k, b + k, b + j))
    if cap_start:
        faces.append(tuple(range(n - 1, -1, -1)))
    if cap_end:
        base = (len(rings) - 1) * n
        faces.append(tuple(base + j for j in range(n)))
    return verts, faces


def cylinder(axis, centre, radius, length, segs=16, r2=None):
    r2 = radius if r2 is None else r2
    cx, cy, cz = centre
    verts, faces = [], []
    for side, r in ((-0.5, radius), (0.5, r2)):
        for i in range(segs):
            t = 2 * math.pi * i / segs
            if axis == "x":
                verts.append((cx + side * length, cy + r * math.cos(t), cz + r * math.sin(t)))
            elif axis == "y":
                verts.append((cx + r * math.cos(t), cy + side * length, cz + r * math.sin(t)))
            else:
                verts.append((cx + r * math.cos(t), cy + r * math.sin(t), cz + side * length))
    for i in range(segs):
        j = (i + 1) % segs
        faces.append((i, j, segs + j, segs + i))
    faces.append(tuple(range(segs - 1, -1, -1)))
    faces.append(tuple(segs + i for i in range(segs)))
    return verts, faces


def merge(*parts):
    verts, faces = [], []
    for v, f in parts:
        off = len(verts)
        verts.extend(v)
        faces.extend(tuple(i + off for i in face) for face in f)
    return verts, faces


def box(centre, size, rot_z=0.0, rot_x=0.0):
    cx, cy, cz = centre
    sx, sy, sz = (s * 0.5 for s in size)
    raw = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
           (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    cxr, sxr = math.cos(rot_x), math.sin(rot_x)
    raw = [(x, y * cxr - z * sxr, y * sxr + z * cxr) for x, y, z in raw]
    c, s = math.cos(rot_z), math.sin(rot_z)
    verts = [(cx + x * c - y * s, cy + x * s + y * c, cz + z) for x, y, z in raw]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return verts, faces


def star_2d(radius, inner=0.42):
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * inner
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def decal_star(centre, radius, axis="x"):
    """Flat, triangulated 5-point star on the plane normal to `axis`."""
    pts = star_2d(radius)
    cx, cy, cz = centre
    if axis == "x":
        v = [(cx, cy + u, cz + w) for u, w in pts]
    elif axis == "y":
        v = [(cx + u, cy, cz + w) for u, w in pts]
    else:
        v = [(cx + u, cy + w, cz) for u, w in pts]
    v = [(cx, cy, cz)] + v
    f = [(0, 1 + i, 1 + (i + 1) % 10) for i in range(10)]
    return v, f


# ----------------------------------------------------------------------------
# hull
# ----------------------------------------------------------------------------
def build_lower_hull(coll, mat):
    # (y, half width, z bottom, z top, corner radius)
    stations = [
        (-2.92, 0.47, 0.70, 1.02, 0.10),
        (-2.86, 0.61, 0.57, 1.04, 0.12),
        (-2.74, 0.71, 0.49, 1.06, 0.12),
        (-2.50, 0.775, 0.46, 1.07, 0.09),
        (-2.10, 0.80, 0.46, 1.08, 0.07),
        (-1.00, 0.80, 0.45, 1.08, 0.06),
        (0.80, 0.80, 0.45, 1.08, 0.06),
        (2.20, 0.79, 0.46, 1.07, 0.07),
        (2.70, 0.735, 0.52, 1.05, 0.10),
        (2.92, 0.60, 0.64, 1.00, 0.12),
    ]
    rings = []
    for y, hw, z0, z1, r in stations:
        hh = (z1 - z0) * 0.5
        cz = (z1 + z0) * 0.5
        rings.append([(x, y, cz + z) for x, z in rounded_rect_2d(hw, hh, r, 4)])
    v, f = loft(rings)
    return new_object("Hull_Lower", v, f, coll, mat, sharp_angle=26)


def build_upper_hull(coll, mat):
    # (y, half width, deck z, corner radius)
    stations = [
        (-2.90, 0.62, 1.045, 0.06),
        (-2.84, 0.94, 1.105, 0.09),
        (-2.70, 1.13, 1.215, 0.10),
        (-2.45, 1.215, 1.375, 0.09),
        (-2.05, 1.245, 1.545, 0.07),
        (-1.62, 1.245, 1.665, 0.06),
        (-0.40, 1.245, 1.735, 0.05),
        (1.30, 1.245, 1.735, 0.05),
        (2.30, 1.235, 1.715, 0.05),
        (2.72, 1.175, 1.655, 0.06),
        (2.92, 1.00, 1.555, 0.08),
    ]
    rings = []
    for y, hw, z1, r in stations:
        hh = (z1 - SPONSON_Z) * 0.5
        cz = (z1 + SPONSON_Z) * 0.5
        rings.append([(x, y, cz + z) for x, z in rounded_rect_2d(hw, hh, r, 4)])
    v, f = loft(rings)
    return new_object("Hull_Upper", v, f, coll, mat, sharp_angle=24)


def cast_from_front(upper, x, z):
    """First hit of a ray fired at the front plate, in object space."""
    hit, loc, nor, _ = upper.ray_cast(Vector((x, -12.0, z)), Vector((0, 1, 0)))
    return (loc, nor) if hit else (None, None)


def put(verts, loc, nor, lift=0.0):
    """Place geometry built around the origin (+Z = outward) onto a surface."""
    q = nor.to_track_quat("Z", "Y")
    base = loc + nor * lift
    return [tuple(base + q @ Vector(v)) for v in verts]


def build_glacis_details(coll, root, upper, mats):
    olive, dark, metal, glass, star_mat = mats
    objs = []

    def add(name, v, f, mat, smooth=True):
        objs.append(new_object(name, v, f, coll, mat, smooth=smooth, parent=root))

    def surface(x, z):
        return cast_from_front(upper, x, z)

    # driver + co-driver hatches, flush on the sloped plate
    for i, hx in enumerate((-0.42, 0.42)):
        loc, nor = surface(hx, 1.55)
        if loc:
            v, f = cylinder("z", (0, 0, 0), 0.255, 0.045, 20)
            add(f"Hatch_{i}", put(v, loc, nor, 0.008), f, olive)
            v, f = cylinder("z", (0, 0, 0), 0.212, 0.018, 20)
            add(f"HatchRim_{i}", put(v, loc, nor, 0.040), f, dark)

    # periscope blocks
    for i, hx in enumerate((-0.63, 0.63)):
        loc, nor = surface(hx, 1.635)
        if loc:
            v, f = box((0, 0, 0.035), (0.17, 0.13, 0.07))
            add(f"Periscope_{i}", put(v, loc, nor, 0.006), f, dark, smooth=False)

    # bow MG ball mount + barrel
    loc, nor = surface(0.60, 1.27)
    if loc:
        v, f = cylinder("z", (0, 0, 0.03), 0.145, 0.11, 16)
        add("BowMG_Ball", put(v, loc, nor, 0.0), f, metal)
        v, f = cylinder("y", (loc.x, loc.y - 0.20, loc.z + 0.02), 0.042, 0.34, 12)
        add("BowMG_Barrel", v, f, metal)

    # headlights on the front corners, facing forward
    for i, hx in enumerate((-0.99, 0.99)):
        loc, nor = surface(hx, 1.40)
        if loc:
            cy = loc.y - 0.10
            v, f = merge(cylinder("y", (hx, cy, loc.z), 0.070, 0.13, 14),
                         cylinder("y", (hx, cy - 0.08, loc.z), 0.080, 0.03, 14))
            add(f"LightBody_{i}", v, f, metal)
            v, f = cylinder("y", (hx, cy - 0.098, loc.z), 0.055, 0.015, 14)
            add(f"LightLens_{i}", v, f, glass)
            v, f = box((hx, cy - 0.09, loc.z + 0.085), (0.15, 0.018, 0.05))
            add(f"LightGuard_{i}", v, f, dark, smooth=False)

    # spare track links bolted to the glacis
    for i in range(3):
        loc, nor = surface(0.0, 1.33 + i * 0.085)
        if loc:
            v, f = box((0, 0, 0.03), (0.31, 0.075, 0.055))
            add(f"SpareLink_{i}", put(v, loc, nor, 0.004), f, dark, smooth=False)

    # tow hooks
    for i, hx in enumerate((-0.66, 0.66)):
        v, f = box((hx, -2.90, 0.76), (0.10, 0.18, 0.14))
        add(f"TowHook_{i}", v, f, dark, smooth=False)

    # rounded final-drive housing on the nose
    fd = []
    for y, hw, z0, z1, r in ((-2.88, 0.34, 0.60, 0.98, 0.13),
                             (-2.925, 0.34, 0.62, 0.96, 0.14),
                             (-2.95, 0.24, 0.70, 0.90, 0.11)):
        hh = (z1 - z0) * 0.5
        cz = (z1 + z0) * 0.5
        fd.append([(x, y, cz + z) for x, z in rounded_rect_2d(hw, hh, r, 5)])
    v, f = loft(fd)
    add("FinalDrive", v, f, olive)

    # glacis star
    loc, nor = surface(0.0, 1.47)
    if loc:
        v, f = decal_star((0, 0, 0), 0.20, axis="z")
        add("Star_Glacis", put(v, loc, nor, 0.012), f, star_mat, smooth=False)

    # hull side stars
    for side, sx in ((-1, -12.0), (1, 12.0)):
        hit, loc, nor, _ = upper.ray_cast(Vector((sx, -0.30, 1.36)),
                                          Vector((-1 if sx > 0 else 1, 0, 0)))
        if hit:
            v, f = decal_star((0, 0, 0), 0.20, axis="z")
            add(f"Star_{'L' if side < 0 else 'R'}",
                put(v, loc, nor, 0.008), f, star_mat, smooth=False)
    return objs


def build_deck_details(coll, root, mats):
    olive, dark, metal, glass, star_mat = mats
    objs = []

    def add(name, v, f, mat, smooth=True):
        objs.append(new_object(name, v, f, coll, mat, smooth=smooth, parent=root))

    v, f = box((0.0, 1.95, 1.752), (1.52, 0.95, 0.05))
    add("EnginePanel", v, f, olive)
    for i in range(7):
        v, f = box((0.0, 1.55 + i * 0.13, 1.787), (1.28, 0.035, 0.03))
        add(f"Grille_{i}", v, f, dark, smooth=False)
    v, f = box((0.0, 2.875, 1.10), (1.28, 0.06, 0.55))
    add("RearPlate", v, f, dark, smooth=False)
    for i, hx in enumerate((-0.58, 0.58)):
        v, f = cylinder("y", (hx, 2.92, 1.18), 0.09, 0.16, 12)
        add(f"Exhaust_{i}", v, f, metal)
    for i, hx in enumerate((-0.55, 0.55)):
        v, f = box((hx, 2.46, 1.755), (0.06, 0.16, 0.09))
        add(f"LiftEye_{i}", v, f, dark, smooth=False)
    v, f = box((0.0, 2.70, 1.58), (1.10, 0.12, 0.20))
    add("StowageBox", v, f, olive)
    return objs


# ----------------------------------------------------------------------------
# turret + gun
# ----------------------------------------------------------------------------
def turret_ring(z, hw, hl_f, hl_b, r):
    hh = max(hl_f, hl_b)
    pts = rounded_rect_2d(hw, hh, r, 5)
    out = []
    for x, y in pts:
        y = y * (hl_b / hh) if y > 0 else y * (hl_f / hh)
        out.append((x, y + RING_Y, z))
    return out


def build_turret(coll, mat, dark):
    R = RING_Z
    rings = [
        turret_ring(R + 0.005, 0.760, 0.80, 0.84, 0.28),
        turret_ring(R + 0.10, 0.875, 0.90, 0.97, 0.36),
        turret_ring(R + 0.38, 0.895, 0.915, 1.04, 0.38),
        turret_ring(R + 0.60, 0.885, 0.885, 1.02, 0.38),
        turret_ring(R + 0.665, 0.845, 0.845, 0.965, 0.35),
        turret_ring(R + 0.705, 0.720, 0.720, 0.830, 0.31),
        turret_ring(R + 0.735, 0.570, 0.570, 0.660, 0.25),
    ]
    v, f = loft(rings)
    body = new_object("Turret_Body", v, f, coll, mat, sharp_angle=34)

    v, f = cylinder("z", (0.0, RING_Y, RING_Z + 0.015), 1.02, 0.07, 32)
    collar = new_object("Turret_Ring", v, f, coll, dark, sharp_angle=60)

    # mantlet: cast wedge in front of the trunnion
    mt = []
    for y, hw, hh, r in ((-0.62, 0.300, 0.280, 0.20),
                         (-0.80, 0.335, 0.310, 0.22),
                         (-1.00, 0.325, 0.300, 0.22),
                         (-1.16, 0.250, 0.225, 0.18)):
        mt.append([(x, y, 1.98 + z) for x, z in rounded_rect_2d(hw, hh, r, 6)])
    v, f = loft(mt)
    mantlet = new_object("Mantlet", v, f, coll, mat, sharp_angle=40)

    return [body, collar, mantlet]


def build_turret_roof(coll, mats):
    olive, dark, metal, glass, star_mat = mats
    R = RING_Z
    objs = []

    def add(name, v, f, mat, smooth=True):
        objs.append(new_object(name, v, f, coll, mat, smooth=smooth))

    # raised roof plate with a visible seam
    v, f = box((0.0, RING_Y + 0.04, R + 0.775), (1.10, 1.30, 0.025))
    add("RoofPlate", v, f, olive)
    for i, (hx, hy, sx, sy) in enumerate(((-0.55, 0.40, 0.03, 1.30),
                                          (0.55, 0.40, 0.03, 1.30),
                                          (0.0, -0.24, 1.10, 0.03))):
        v, f = box((hx, RING_Y + hy, R + 0.788), (sx, sy, 0.02))
        add(f"RoofSeam_{i}", v, f, dark, smooth=False)

    # commander cupola
    v, f = merge(cylinder("z", (-0.33, RING_Y + 0.30, R + 0.90), 0.30, 0.26, 20),
                 cylinder("z", (-0.33, RING_Y + 0.30, R + 0.80), 0.33, 0.06, 20))
    add("Cupola", v, f, olive)
    v, f = cylinder("z", (-0.33, RING_Y + 0.30, R + 1.035), 0.275, 0.045, 20)
    add("CupolaHatch", v, f, dark)
    for i in range(6):
        a = 2 * math.pi * i / 6
        v, f = box((-0.33 + 0.285 * math.cos(a), RING_Y + 0.30 + 0.285 * math.sin(a), R + 0.92),
                   (0.07, 0.07, 0.10), rot_z=a)
        add(f"CupolaVision_{i}", v, f, dark, smooth=False)

    # loader hatch
    v, f = cylinder("z", (0.47, RING_Y + 0.02, R + 0.795), 0.255, 0.05, 20)
    add("LoaderHatch", v, f, dark)
    v, f = cylinder("z", (0.47, RING_Y + 0.02, R + 0.77), 0.31, 0.03, 20)
    add("LoaderRing", v, f, olive)

    # pintle socket (no MG fitted, matches the reference tank)
    v, f = cylinder("z", (0.04, RING_Y + 0.60, R + 0.80), 0.07, 0.06, 10)
    add("Pintle", v, f, dark)

    # antenna
    v, f = cylinder("z", (0.84, RING_Y + 0.50, R + 1.35), 0.012, 1.30, 6)
    add("Antenna", v, f, metal)
    # lifting eyes
    for i, hx in enumerate((-0.60, 0.60)):
        v, f = box((hx, RING_Y - 0.22, R + 0.79), (0.07, 0.11, 0.09))
        add(f"TurretLift_{i}", v, f, dark, smooth=False)
    return objs


def build_gun(coll, mats):
    olive, dark, metal, glass, star_mat = mats
    objs = []

    def add(name, v, f, mat, smooth=True):
        objs.append(new_object(name, v, f, coll, mat, smooth=smooth))

    v, f = cylinder("y", (0.0, -2.45, 1.98), 0.098, 2.95, 16, r2=0.082)
    add("GunBarrel", v, f, olive)
    v, f = cylinder("y", (0.0, -1.30, 1.98), 0.125, 0.60, 16)
    add("GunSleeve", v, f, dark)
    v, f = cylinder("y", (0.0, -3.93, 1.98), 0.098, 0.09, 16)
    add("GunMuzzleRing", v, f, metal)
    return objs


# ----------------------------------------------------------------------------
# running gear
# ----------------------------------------------------------------------------
def track_path():
    """Closed stadium: front arc over the sprocket, rear arc over the idler."""
    pts = []
    seg = 64
    R = PATH_R
    for i in range(seg // 2 + 1):          # front, top -> bottom (wraps the sprocket)
        a = math.pi / 2 + math.pi * i / (seg // 2)
        pts.append((SPROCKET_Y + R * math.cos(a), TRACK_Z + R * math.sin(a)))
    for i in range(seg // 2 + 1):          # rear, bottom -> top (wraps the idler)
        a = -math.pi / 2 + math.pi * i / (seg // 2)
        pts.append((IDLER_Y + R * math.cos(a), TRACK_Z + R * math.sin(a)))
    return pts


def build_tracks(coll, mat):
    path = track_path()
    seglens, total = [], 0.0
    n = len(path)
    for i in range(n):
        a, b = path[i], path[(i + 1) % n]
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        seglens.append(d)
        total += d
    pitch = 0.166
    count = max(8, round(total / pitch))
    step = total / count

    objs = []
    for side, sx in ((-1, -TRACK_X), (1, TRACK_X)):
        parts = []
        for k in range(count):
            s = k * step
            acc, i = 0.0, 0
            while acc + seglens[i] < s and i < n - 1:
                acc += seglens[i]
                i += 1
            t = (s - acc) / seglens[i] if seglens[i] else 0.0
            a, b = path[i], path[(i + 1) % n]
            py = a[0] + (b[0] - a[0]) * t
            pz = a[1] + (b[1] - a[1]) * t
            ty, tz = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(ty, tz) or 1.0
            ty, tz = ty / ln, tz / ln
            ny, nz = -tz, ty
            if py * ny + (pz - TRACK_Z) * nz < 0:
                ny, nz = -ny, -nz

            def place(off_n, half_t, half_n, half_x):
                cy = py + ny * off_n
                cz = pz + nz * off_n
                corners = []
                for ox in (-half_x, half_x):
                    for st in (-1, 1):
                        for sn in (-1, 1):
                            corners.append((
                                sx + ox,
                                cy + ty * st * half_t + ny * sn * half_n,
                                cz + tz * st * half_t + nz * sn * half_n,
                            ))
                idx = lambda a_, b_, c_: a_ * 4 + b_ * 2 + c_
                quads = [
                    (idx(0, 0, 0), idx(0, 0, 1), idx(0, 1, 1), idx(0, 1, 0)),
                    (idx(1, 0, 0), idx(1, 1, 0), idx(1, 1, 1), idx(1, 0, 1)),
                    (idx(0, 0, 0), idx(1, 0, 0), idx(1, 0, 1), idx(0, 0, 1)),
                    (idx(0, 1, 0), idx(0, 1, 1), idx(1, 1, 1), idx(1, 1, 0)),
                    (idx(0, 0, 0), idx(0, 1, 0), idx(1, 1, 0), idx(1, 0, 0)),
                    (idx(0, 0, 1), idx(1, 0, 1), idx(1, 1, 1), idx(0, 1, 1)),
                ]
                return corners, quads

            parts.append(place(-0.018, 0.079, 0.024, TRACK_W * 0.5))
            parts.append(place(-0.062, 0.024, 0.034, 0.032))
        v, f = merge(*parts)
        objs.append(new_object(f"Track_{'L' if side < 0 else 'R'}", v, f, coll, mat,
                               smooth=False))
    return objs


def build_running_gear(coll, mats):
    rubber, metal, olive = mats
    objs = []

    def add(name, v, f, mat, smooth=True):
        objs.append(new_object(name, v, f, coll, mat, smooth=smooth))

    for side, sx in ((-1, -TRACK_X), (1, TRACK_X)):
        tag = "L" if side < 0 else "R"
        for i, wy in enumerate(WHEEL_Y):
            v, f = cylinder("x", (sx, wy, WHEEL_Z), WHEEL_R, 0.20, 24)
            add(f"Tire_{tag}_{i}", v, f, rubber)
            v, f = cylinder("x", (sx, wy, WHEEL_Z), 0.185, 0.215, 20)
            add(f"Hub_{tag}_{i}", v, f, olive)
            v, f = cylinder("x", (sx + (0.11 if side > 0 else -0.11), wy, WHEEL_Z), 0.065, 0.03, 12)
            add(f"HubCap_{tag}_{i}", v, f, metal)
        for i, ry in enumerate((-1.55, 0.0, 1.55)):
            v, f = cylinder("x", (sx, ry, ROLLER_Z), ROLLER_R, 0.15, 12)
            add(f"Roller_{tag}_{i}", v, f, metal)
        v, f = box((sx, 0.0, BOGIE_Z), (0.09, 4.35, 0.16))
        add(f"Beam_{tag}", v, f, olive, smooth=False)
        v, f = cylinder("x", (sx, SPROCKET_Y, TRACK_Z), 0.360, 0.17, 20)
        add(f"Sprocket_{tag}", v, f, metal)
        parts = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            parts.append(box((sx, SPROCKET_Y + 0.360 * math.cos(a), TRACK_Z + 0.360 * math.sin(a)),
                             (0.17, 0.10, 0.10), rot_x=a))
        v, f = merge(*parts)
        add(f"SprocketTeeth_{tag}", v, f, metal, smooth=False)
        v, f = cylinder("x", (sx, IDLER_Y, TRACK_Z), 0.350, 0.17, 18)
        add(f"Idler_{tag}", v, f, metal)
    return objs


def build_fenders(coll, mat, dark):
    objs = []

    def add(name, v, f, mat_, smooth=True):
        objs.append(new_object(name, v, f, coll, mat_, smooth=smooth))

    for side, sx in ((-1, -TRACK_X), (1, TRACK_X)):
        tag = "L" if side < 0 else "R"
        # narrow fender lip along the sponson underside, over the track
        v, f = box((sx + 0.02, -0.05, 1.00), (0.30, 4.70, 0.03))
        add(f"Fender_{tag}", v, f, mat)
    return objs


# ----------------------------------------------------------------------------
# build
# ----------------------------------------------------------------------------
PALETTE = {
    "olive": "#4e5733",
    "oliveDark": "#343b23",
    "metal": "#55554d",
    "rubber": "#191919",
    "track": "#3a3b32",
    "glass": "#b9c8c4",
    "star": "#ddd8c6",
}


def build(params=None):
    """Build the tank into the scene.

    `params` comes from the asset spec (tools/blender/specs/*.json) and may
    override `palette`. Geometry stays parameterised by this file's constants.
    """
    palette = dict(PALETTE)
    palette.update((params or {}).get("palette") or {})

    coll = get_collection()
    clear_collection(coll)

    olive = material("Sherman_Olive", palette["olive"], 0.70, 0.05)
    olive_d = material("Sherman_OliveDark", palette["oliveDark"], 0.78, 0.05)
    metal = material("Sherman_Metal", palette["metal"], 0.42, 0.85)
    rubber = material("Sherman_Rubber", palette["rubber"], 0.93, 0.0)
    track = material("Sherman_Track", palette["track"], 0.55, 0.65)
    glass = material("Sherman_Glass", palette["glass"], 0.28, 0.0)
    star_mat = material("Sherman_Star", palette["star"], 0.88, 0.0)
    mats = (olive, olive_d, metal, glass, star_mat)

    root = empty(ROOT_NAME, (0, 0, 0), coll)

    lower = build_lower_hull(coll, olive)
    upper = build_upper_hull(coll, olive)
    for o in (lower, upper):
        o.parent = root

    build_glacis_details(coll, root, upper, mats)
    build_deck_details(coll, root, mats)

    turret_pivot = empty("Turret_Pivot", (0.0, RING_Y, RING_Z), coll, parent=root)
    gun_pivot = empty("Gun_Pivot", (TRUNNION.x, TRUNNION.y - RING_Y, TRUNNION.z - RING_Z),
                      coll, parent=turret_pivot)
    bpy.context.view_layer.update()

    for o in build_turret(coll, olive, olive_d) + build_turret_roof(coll, mats):
        o.parent = turret_pivot
        o.matrix_parent_inverse = turret_pivot.matrix_world.inverted()

    empty("GunMuzzle", (0.0, MUZZLE_Y - TRUNNION.y, 0.0), coll, parent=gun_pivot)
    for o in build_gun(coll, mats):
        o.parent = gun_pivot
        o.matrix_parent_inverse = gun_pivot.matrix_world.inverted()

    build_running_gear(coll, (rubber, metal, olive))
    build_tracks(coll, track)
    build_fenders(coll, olive, olive_d)

    # drop the model onto z = 0 (tracks touching the ground)
    bpy.context.view_layer.update()
    lows = []
    for o in coll.objects:
        if o.type == "MESH":
            lows.append(min((o.matrix_world @ v.co).z for v in o.data.vertices))
    dz = -min(lows) if lows else 0.0
    if abs(dz) > 1e-6:
        for o in coll.objects:
            if o.type == "MESH":
                for v in o.data.vertices:
                    v.co.z += dz
        turret = bpy.data.objects.get("Turret_Pivot")
        if turret and turret.parent is root:
            turret.location.z += dz
        bpy.context.view_layer.update()

    # keep the whole tank under one root so the game gets a single node
    for o in coll.objects:
        if o is not root and o.parent is None:
            o.parent = root
    bpy.context.view_layer.update()

    for o in coll.objects:
        o.select_set(False)

    tris = 0
    for o in coll.objects:
        if o.type == "MESH":
            o.data.calc_loop_triangles()
            tris += len(o.data.loop_triangles)
    bpy.context.view_layer.update()
    print(f"[sherman] built {len(coll.objects)} objects in '{COLL}', tris={tris}")


if __name__ == "__main__":
    build()
