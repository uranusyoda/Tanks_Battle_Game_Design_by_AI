"""Project paths and asset-spec loading.

Every path is derived from this file's location, so the pipeline works from any
cwd and survives the project being moved or cloned.

    tools/blender/lib/proj.py  ->  this file
    tools/blender/             ->  BLENDER_DIR
    <project>/                 ->  PROJ
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(_HERE)
PROJ = os.path.dirname(os.path.dirname(BLENDER_DIR))
SPECS_DIR = os.path.join(BLENDER_DIR, "specs")

#: Override the project root (useful in CI or when running from a copy).
ROOT_ENV = "TANK_PROJ_ROOT"


def proj_root():
    return os.path.abspath(os.environ.get(ROOT_ENV, PROJ))


def resolve(path):
    """Make `path` absolute, relative to the project root."""
    return path if os.path.isabs(path) else os.path.join(proj_root(), path)


def rel(path):
    """Project-relative path with forward slashes, as written into the manifest."""
    try:
        return os.path.relpath(os.path.abspath(path), proj_root()).replace(os.sep, "/")
    except ValueError:
        return os.path.abspath(path)


def spec_file(ident):
    if ident.endswith(".json") and os.path.isfile(ident):
        return os.path.abspath(ident)
    if os.path.isfile(ident):
        return os.path.abspath(ident)
    return os.path.join(SPECS_DIR, ident + ".json")


def load_spec(ident):
    path = spec_file(ident)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "no spec %r; available: %s" % (ident, ", ".join(list_specs()) or "(none)")
        )
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    spec.setdefault("id", os.path.splitext(os.path.basename(path))[0])
    spec["_spec_path"] = path
    return spec


def list_specs():
    if not os.path.isdir(SPECS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(SPECS_DIR) if f.endswith(".json"))


def read_manifest(out_dir):
    path = os.path.join(resolve(out_dir), "manifest.json")
    if not os.path.isfile(path):
        return {"assets": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(out_dir, manifest):
    path = os.path.join(resolve(out_dir), "manifest.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
    return path
