#!/usr/bin/env python3
"""Tripo3D v3 text-to-model helper (submit -> poll -> download GLB).

Docs: https://developers.tripo3d.com/en/docs/quick-start

Usage:
  export TRIPO_API_KEY="tsk_..."          # or pass --api-key
  python3 tools/tripo3d.py "a cute cat" --face-limit 20000
  python3 tools/tripo3d.py --task task_abc123        # resume an existing task
  python3 tools/tripo3d.py "..." --no-wait           # submit only, print task_id

Notes:
  * Generation is async: submit returns task_id, then poll GET /tasks/{task_id}.
  * output.model_url expires ~5 min after success, so we download immediately.
  * The key is never written to disk or logged.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

API_BASE = os.environ.get("TRIPO_API_BASE", "https://openapi.tripo3d.com/v3")
DEFAULT_MODEL = "v3.1-20260211"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "assets" / "models"


def api_key(cli_value: str | None) -> str:
    key = cli_value or os.environ.get("TRIPO_API_KEY", "")
    key = key.strip()
    if not key:
        sys.exit(
            "Missing API key. Export TRIPO_API_KEY=... (create one at "
            "https://developers.tripo3d.com/en/keys) or pass --api-key."
        )
    return key


def request(method: str, path: str, key: str, payload: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    resp = requests.request(method, url, headers=headers, json=payload, timeout=60)
    try:
        body = resp.json()
    except ValueError:
        resp.raise_for_status()
        raise SystemExit(f"Non-JSON response from {url}: {resp.text[:300]}")

    code = body.get("code")
    if resp.status_code >= 400 or code not in (None, 0):
        msg = body.get("message") or body.get("msg") or json.dumps(body)[:500]
        hint = ""
        if code == 1004:
            hint = " (invalid/conflicting parameters)"
        elif code == 2002:
            hint = " (insufficient credits)"
        elif code == 2001:
            hint = " (unauthorized — check the API key)"
        raise SystemExit(f"API error {code} / HTTP {resp.status_code}: {msg}{hint}")
    return body.get("data", {})


def balance(key: str) -> float | None:
    """Best-effort credit check; returns None if the endpoint is unavailable."""
    try:
        data = request("GET", "/account/balance", key)
        return float(data.get("balance"))
    except (SystemExit, ValueError, TypeError):
        return None


def build_payload(args: argparse.Namespace) -> dict:
    payload: dict = {"prompt": args.prompt, "model": args.model}
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt
    if args.face_limit:
        payload["face_limit"] = args.face_limit
    if args.seed is not None:
        payload["model_seed"] = args.seed
    if args.no_texture:
        payload["texture"] = False
        payload["pbr"] = False
    else:
        payload["pbr"] = not args.no_pbr
        if args.pbr and not args.texture:
            payload["texture"] = True
        if args.texture_quality:
            payload["texture_quality"] = args.texture_quality
    if args.quality:
        payload["geometry_quality"] = args.quality
    if args.compress:
        payload["compress"] = "geometry"
    if args.parts:
        # generate_parts is incompatible with texture; the API rejects it otherwise.
        payload["generate_parts"] = True
        payload["texture"] = False
        payload["pbr"] = False
    if args.quad:
        payload["quad"] = True
    return payload


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:limit].rstrip("-") or "model")


def poll(task_id: str, key: str, timeout: float, interval: float) -> dict:
    started = time.time()
    last = None
    while True:
        data = request("GET", f"/tasks/{task_id}", key)
        status = data.get("status")
        progress = data.get("progress", 0)
        if (status, progress) != last:
            print(f"  [{progress:>3}%] {status}", flush=True)
            last = (status, progress)

        if status == "success":
            return data
        if status in ("failed", "cancelled", "banned", "expired"):
            raise SystemExit(
                f"Task {task_id} {status}: "
                f"{data.get('error_message') or data.get('error_code') or 'no detail'}"
            )
        if time.time() - started > timeout:
            raise SystemExit(
                f"Timed out after {timeout:.0f}s; task {task_id} still {status}. "
                f"Resume later with: --task {task_id}"
            )
        time.sleep(interval)


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    size = tmp.stat().st_size
    if size == 0:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Downloaded 0 bytes from {url}")
    tmp.replace(dest)
    print(f"  saved {dest} ({size / 1048576:.2f} MB)")
    return dest


def main() -> None:
    p = argparse.ArgumentParser(description="Tripo3D v3 text-to-model -> GLB")
    p.add_argument("prompt", nargs="?", help="text prompt describing the model")
    p.add_argument("--task", help="resume/download an existing task_id instead of submitting")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"model version (default {DEFAULT_MODEL})")
    p.add_argument("--api-key", help="API key (default: $TRIPO_API_KEY)")
    p.add_argument("--negative-prompt", help="what to avoid")
    p.add_argument("--face-limit", type=int, help="max triangles, e.g. 30000 for web game assets")
    p.add_argument("--seed", type=int, help="geometry seed for reproducibility")
    p.add_argument("--texture-quality", choices=["fast", "standard", "detailed", "extreme"])
    p.add_argument("--quality", choices=["standard", "detailed"], help="geometry quality")
    p.add_argument("--no-texture", action="store_true", help="bare geometry only (no texture)")
    p.add_argument("--no-pbr", action="store_true", help="texture but no PBR maps")
    p.add_argument("--pbr", action="store_true", help="force PBR maps (default when textured)")
    p.add_argument("--parts", action="store_true", help="segmented parts (implies no texture)")
    p.add_argument("--quad", action="store_true", help="quad mesh, forces FBX output")
    p.add_argument("--compress", action="store_true", help="meshopt geometry compression")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output dir (default {DEFAULT_OUT})")
    p.add_argument("--name", help="output basename (default: slug of prompt)")
    p.add_argument("--no-wait", action="store_true", help="submit only")
    p.add_argument("--timeout", type=float, default=600, help="poll timeout seconds")
    p.add_argument("--interval", type=float, default=2.0, help="poll interval seconds")
    args = p.parse_args()

    key = api_key(args.api_key)

    if args.task:
        task_id = args.task
        print(f"Resuming task {task_id}")
    else:
        if not args.prompt:
            p.error("prompt is required unless --task is given")
        payload = build_payload(args)
        bal = balance(key)
        if bal is not None:
            print(f"Credits balance: {bal:.2f}")
            if bal <= 0:
                raise SystemExit(
                    "No credits on this key (balance 0.00). Top up at "
                    "https://developers.tripo3d.com/en/billing/recharge — "
                    "text-to-3D with texture costs 20 credits (1 credit = ¥0.07)."
                )
        print(f"Submitting to {API_BASE}/generation/text-to-model")
        print(f"  model={payload['model']} prompt={payload['prompt']!r}"
              + (f" face_limit={payload.get('face_limit')}" if payload.get("face_limit") else ""))
        data = request("POST", "/generation/text-to-model", key, payload)
        task_id = data.get("task_id")
        if not task_id:
            raise SystemExit(f"No task_id in response: {data}")
        print(f"  task_id={task_id}")
        if args.no_wait:
            print(f"Poll later with: python3 {Path(__file__).name} --task {task_id}")
            return

    data = poll(task_id, key, args.timeout, args.interval)

    out = data.get("output") or {}
    model_url = out.get("model_url")
    image_url = out.get("rendered_image_url")
    slug = args.name or slugify(args.prompt or task_id)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = args.out / f"{slug}-{stamp}"

    print("Downloading:")
    if model_url:
        ext = Path(model_url.split("?")[0]).suffix or ".glb"
        download(model_url, base.with_suffix(ext))
    else:
        print("  ! no model_url in output:", list(out))
    if image_url:
        try:
            download(image_url, base.with_suffix(".preview.png"))
        except Exception as exc:  # preview is nice-to-have only
            print(f"  ! preview download failed: {exc}")

    meta = dict(data)
    meta["prompt"] = args.prompt
    meta["requested_model"] = args.model
    base.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"Task {task_id} done; credits_consumed={data.get('credits_consumed')}")


if __name__ == "__main__":
    main()
