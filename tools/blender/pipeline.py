"""Tank Battle 3D — asset build pipeline (runs inside Blender).

    blender -b --factory-startup -noaudio -P tools/blender/pipeline.py -- build m4a1_sherman

Commands
    list                        show every asset spec
    build <id|--all> [...]      build -> export glb -> preview -> verify
    validate <id|glb> [...]     re-check an existing glb, no rebuild

Flags (build)
    --all             every spec in tools/blender/specs
    --lod / --no-lod  override the spec's LOD setting
    --preview / --no-preview
    --blend / --no-blend
    --out DIR         override the spec's output directory
    --no-verify       skip the glb re-import check (faster, less evidence)
    --strict          treat warnings as failures
    --json            print a machine-readable summary on the last line

Exit code is 0 only if every requested asset passed every check.
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys
import traceback

import bpy

BLENDER_DIR = os.path.dirname(os.path.abspath(__file__))
if BLENDER_DIR not in sys.path:
    sys.path.insert(0, BLENDER_DIR)

from lib import gltf, preview, proj, scene, validate  # noqa: E402

#: spec["builder"] -> module path (project-relative) and an optional entry
#: function. Without a function the module is expected to populate the scene
#: while it is being imported (the older top-level builder scripts do that).
BUILDERS = {
    "m4_sherman": {"path": "tools/build_sherman.py"},
    "sherman": {"path": "tools/blender/build_sherman.py", "func": "build"},
}

PREVIEW_DIR = "media/models/build"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def log(msg):
    print(msg, flush=True)


def load_builder(name):
    if name not in BUILDERS:
        raise KeyError("unknown builder %r; known: %s"
                       % (name, ", ".join(sorted(BUILDERS))))
    cfg = BUILDERS[name]
    path = proj.resolve(cfg["path"])
    if not os.path.isfile(path):
        raise FileNotFoundError("builder module missing: %s" % path)
    module_name = "tank_builder_" + name
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    func = cfg.get("func")
    if func is None:
        # the module populated the scene while importing
        return lambda params: None
    return getattr(module, func)


def flag(spec, section, key, cli_value, default=False):
    """CLI wins, then the spec, then the default."""
    if cli_value is not None:
        return cli_value
    return (spec.get(section) or {}).get(key, default)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# one asset
# ---------------------------------------------------------------------------
def build_asset(spec, args, manifest):
    rep = validate.Report(spec["id"])
    log("\n=== %s ===" % spec["id"])

    scene.reset()
    builder = load_builder(spec.get("builder", "sherman"))
    builder(spec.get("params") or {})

    coll_name = spec.get("collection")
    objs = scene.objects(coll_name)
    if not objs:
        rep.error("builder produced no objects")
        rep.print()
        return rep, None

    removed = scene.strip(objs, spec.get("strip"))
    if removed:
        log("[strip] %s" % ", ".join(removed))
        objs = scene.objects(coll_name)

    changed = scene.override_materials(spec.get("material_overrides"))
    if changed:
        log("[paint] %s" % ", ".join(changed))

    tags = scene.tag(objs, spec.get("tags"))

    scale = (spec.get("params") or {}).get("scale", 1.0)
    scene.scale_root(objs, scale)

    if (spec.get("params") or {}).get("drop_to_ground"):
        scene.drop_to_ground(objs)

    st = scene.stats(objs, exclude=spec.get("stats_exclude"))
    log("[build] %d objects, %d tris, %d materials"
        % (st["objects"], st["tris"], len(st["materials"])))

    out_dir = proj.resolve(args.out or spec.get("out_dir", "assets/models"))
    basename = spec.get("file") or spec["id"]
    os.makedirs(out_dir, exist_ok=True)
    glb_path = os.path.join(out_dir, basename + ".glb")

    export_settings = dict(spec.get("export") or {})
    gltf.export_glb(glb_path, objs, export_settings)
    validate.check_scene(rep, spec, st, glb_path)
    validate.check_file(rep, spec, glb_path, os.path.getsize(glb_path))

    entry = {
        "id": spec["id"],
        "spec": proj.rel(spec["_spec_path"]),
        "builder": spec.get("builder"),
        "generated_at": now(),
        "blender": bpy.app.version_string,
        "glb": proj.rel(glb_path),
        "bytes": os.path.getsize(glb_path),
        "sha256": gltf.sha256(glb_path),
        "stats": st,
        "tags": tags,
        "files": {},
    }

    # optional .blend copy of the source scene (preview rig not included:
    # the preview camera/lights are added after this point)
    if flag(spec, "blend", "enabled", args.blend, False):
        blend_path = os.path.join(out_dir, basename + ".blend")
        gltf.save_blend(blend_path)
        entry["files"]["blend"] = proj.rel(blend_path)

    # LODs
    lod_cfg = spec.get("lod") or {}
    want_lod = flag(spec, "lod", "enabled", args.lod, False)
    lod_files = []
    if want_lod:
        for i, ratio in enumerate(lod_cfg.get("ratios") or [0.45, 0.2], start=1):
            coll, dup_objs = scene.duplicate(objs, "_%d" % i)
            before = scene.decimate(dup_objs, ratio)
            lod_path = os.path.join(out_dir, "%s_lod%d.glb" % (basename, i))
            gltf.export_glb(lod_path, dup_objs, dict(export_settings, use_selection=True))
            lod_st = scene.stats(dup_objs)
            lod_files.append({
                "file": proj.rel(lod_path),
                "ratio": ratio,
                "tris": lod_st["tris"],
                "bytes": os.path.getsize(lod_path),
            })
            log("[lod%d] %d -> %d tris (ratio %.2f)" % (i, before, lod_st["tris"], ratio))
            scene.remove_objects(dup_objs)
            bpy.data.collections.remove(coll)
        entry["files"]["lod"] = lod_files

    # preview
    want_preview = flag(spec, "preview", "enabled", args.preview, True)
    if want_preview and not rep.errors:
        pv = spec.get("preview") or {}
        try:
            paths = preview.render(
                objs, proj.resolve(PREVIEW_DIR), basename,
                bbox=st.get("bbox"),
                resolution=tuple(pv.get("resolution") or (1280, 880)),
                samples=pv.get("samples", 48),
                views=pv.get("views") or ["hero", "side", "front"],
            )
            entry["files"]["preview"] = [proj.rel(p) for p in paths]
        except Exception:
            traceback.print_exc()
            rep.warn("preview render failed (non-fatal)")

    # round-trip: destroys the scene, so it goes last
    if not args.no_verify and not rep.errors:
        try:
            loaded = validate.measure_glb(glb_path, exclude=spec.get("stats_exclude"))
            validate.check_roundtrip(rep, spec, st, loaded)
            entry["verified"] = {
                "tris": loaded["tris"],
                "materials": len(loaded["materials"]),
                "nodes": len(loaded["nodes"]),
                "bbox": loaded["bbox"],
            }
        except Exception as exc:
            traceback.print_exc()
            rep.error("glb re-import failed: %s" % exc)

    if args.strict:
        rep.errors.extend(rep.warnings)
        rep.warnings = []

    entry["checks"] = rep.as_dict()
    rep.print()
    log("[out] %s" % proj.rel(glb_path))
    return rep, entry


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_list(_args):
    specs = proj.list_specs()
    if not specs:
        log("no specs in %s" % proj.SPECS_DIR)
        return 0
    log("%-18s %-10s %-26s %s" % ("id", "builder", "collection", "output"))
    for name in specs:
        spec = proj.load_spec(name)
        log("%-18s %-10s %-26s %s"
            % (spec["id"], spec.get("builder", "?"), spec.get("collection") or "-",
               (spec.get("out_dir", "assets/models") + "/"
                + (spec.get("file") or spec["id"]) + ".glb")))
    return 0


def cmd_build(args):
    if args.all or not args.assets:
        names = proj.list_specs()
    else:
        names = args.assets
    if not names:
        log("error: nothing to build (no specs found)")
        return 2

    out_dir = args.out or "assets/models"
    manifest = proj.read_manifest(out_dir)
    manifest["blender"] = bpy.app.version_string
    manifest["generated_at"] = now()
    manifest.setdefault("assets", {})

    results = []
    for name in names:
        try:
            spec = proj.load_spec(name)
            rep, entry = build_asset(spec, args, manifest)
        except Exception:
            traceback.print_exc()
            rep = validate.Report(name)
            rep.error("build crashed")
            entry = None
        if entry:
            manifest["assets"][spec["id"]] = entry
        results.append((name, rep))

    manifest_path = proj.write_manifest(out_dir, manifest)

    log("\n=== summary ===")
    failed = 0
    for name, rep in results:
        entry = manifest["assets"].get(name) or {}
        if rep.ok:
            st = entry.get("stats") or {}
            log("[ok]   %-16s %6s tris  %6.2f MB  %s"
                % (name, st.get("tris", "?"), entry.get("bytes", 0) / 1048576,
                   entry.get("glb", "")))
        else:
            failed += 1
            log("[FAIL] %-16s %s" % (name, "; ".join(rep.errors)))
    log("[manifest] %s" % proj.rel(manifest_path))

    if args.json:
        log("JSON " + json.dumps({
            "ok": failed == 0,
            "assets": {n: r.as_dict() for n, r in results},
            "manifest": proj.rel(manifest_path),
        }, ensure_ascii=False))

    return 0 if failed == 0 else 1


def cmd_validate(args):
    failed = 0
    for target in args.targets:
        matches = [p for p in (target,) if p.endswith(".glb") and os.path.isfile(p)]
        if matches:
            path = matches[0]
            spec = {"id": os.path.basename(path)[:-4], "validate": {}}
        else:
            spec = proj.load_spec(target)
            out_dir = proj.resolve(args.out or spec.get("out_dir", "assets/models"))
            path = os.path.join(out_dir, (spec.get("file") or spec["id"]) + ".glb")
        rep = validate.Report(spec["id"])
        if not os.path.isfile(path):
            rep.error("missing file: %s" % path)
        else:
            validate.check_file(rep, spec, path, os.path.getsize(path))
            loaded = validate.measure_glb(path, exclude=spec.get("stats_exclude"))
            for name in (spec.get("validate") or {}).get("require_nodes") or []:
                if name not in loaded["nodes"]:
                    rep.error("required node %r missing" % name)
            st = loaded
            if st["meshes"] == 0:
                rep.error("no geometry in file")
            max_tris = (spec.get("validate") or {}).get("max_tris")
            if max_tris and st["tris"] > max_tris:
                rep.error("tris %d over budget %d" % (st["tris"], max_tris))
            rep.note("%d tris, %d materials, %d nodes, %.2f MB"
                     % (st["tris"], len(st["materials"]), len(st["nodes"]),
                        os.path.getsize(path) / 1048576))
        rep.print()
        if not rep.ok:
            failed += 1
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def parse(argv):
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Tank Battle 3D asset pipeline (run inside Blender).")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="show asset specs")
    p_list.set_defaults(func=cmd_list)

    p_build = sub.add_parser("build", help="build and export assets")
    p_build.add_argument("assets", nargs="*", help="spec ids (default: all)")
    p_build.add_argument("--all", action="store_true")
    p_build.add_argument("--lod", dest="lod", action="store_true", default=None)
    p_build.add_argument("--no-lod", dest="lod", action="store_false")
    p_build.add_argument("--preview", dest="preview", action="store_true", default=None)
    p_build.add_argument("--no-preview", dest="preview", action="store_false")
    p_build.add_argument("--blend", dest="blend", action="store_true", default=None)
    p_build.add_argument("--no-blend", dest="blend", action="store_false")
    p_build.add_argument("--out", default=None, help="override output directory")
    p_build.add_argument("--no-verify", action="store_true")
    p_build.add_argument("--strict", action="store_true")
    p_build.add_argument("--json", action="store_true")
    p_build.set_defaults(func=cmd_build)

    p_val = sub.add_parser("validate", help="check existing glb files")
    p_val.add_argument("targets", nargs="+", help="spec ids or .glb paths")
    p_val.add_argument("--out", default=None)
    p_val.set_defaults(func=cmd_validate)

    return parser.parse_args(argv)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        argv = ["build"]
    try:
        args = parse(argv)
    except SystemExit as exc:  # argparse --help / bad args
        return int(exc.code or 0)
    if not getattr(args, "func", None):
        print("usage: blender -b -P tools/blender/pipeline.py -- {list,build,validate} ...")
        return 2
    return args.func(args)


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    # Blender swallows SystemExit and exits 0; a build tool must not.
    os._exit(0 if code == 0 else (code if isinstance(code, int) else 1))
