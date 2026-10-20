#!/usr/bin/env python3
"""Generate seamless PBR-ish textures for the Godot port.

No external assets: albedo/height are procedural, normals are derived from height
with wrap-around Sobel. Outputs go to godot/assets/textures/.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "godot" / "assets" / "textures"
OUT.mkdir(parents=True, exist_ok=True)


def smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def value_noise(size: int, fx: int, fy: int, rng: np.random.Generator) -> np.ndarray:
    grid = rng.random((fy, fx)).astype(np.float32)
    xs = np.linspace(0.0, float(fx), size, endpoint=False, dtype=np.float32)
    ys = np.linspace(0.0, float(fy), size, endpoint=False, dtype=np.float32)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    tx = xs - x0
    ty = ys - y0
    x0 %= fx
    y0 %= fy
    x1 = (x0 + 1) % fx
    y1 = (y0 + 1) % fy
    sx = smoothstep(tx)
    sy = smoothstep(ty)
    g00 = grid[np.ix_(y0, x0)]
    g10 = grid[np.ix_(y0, x1)]
    g01 = grid[np.ix_(y1, x0)]
    g11 = grid[np.ix_(y1, x1)]
    top = g00 * (1.0 - sx) + g10 * sx
    bottom = g01 * (1.0 - sx) + g11 * sx
    return top * (1.0 - sy) + bottom * sy


def fbm(size: int, base: int, octaves: int, rng: np.random.Generator, gain: float = 0.5) -> np.ndarray:
    total = np.zeros((size, size), dtype=np.float32)
    amp = 1.0
    norm = 0.0
    freq = base
    for _ in range(octaves):
        total += value_noise(size, freq, freq, rng) * amp
        norm += amp
        amp *= gain
        freq *= 2
    out = total / max(norm, 1e-6)
    out -= out.min()
    out /= max(out.max(), 1e-6)
    return out.astype(np.float32)


def normal_from_height(height: np.ndarray, strength: float = 2.0) -> np.ndarray:
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(height)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= length
    ny /= length
    nz /= length
    return ((np.stack([nx, ny, nz], axis=-1) * 0.5 + 0.5) * 255.0).clip(0, 255).astype(np.uint8)


def save_rgb(arr: np.ndarray, name: str) -> None:
    img = Image.fromarray((arr.clip(0.0, 1.0) * 255.0).astype(np.uint8), "RGB")
    img.save(OUT / name, optimize=True)
    print("wrote", name, img.size)


def save_gray(arr: np.ndarray, name: str) -> None:
    img = Image.fromarray((arr.clip(0.0, 1.0) * 255.0).astype(np.uint8), "L")
    img.save(OUT / name, optimize=True)
    print("wrote", name, img.size)


def save_normal(height: np.ndarray, name: str, strength: float = 2.0) -> None:
    img = Image.fromarray(normal_from_height(height, strength), "RGB")
    img.save(OUT / name, optimize=True)
    print("wrote", name, img.size)


def mix(a: np.ndarray, b: np.ndarray, t: np.ndarray | float) -> np.ndarray:
    if isinstance(t, np.ndarray) and t.ndim == 2:
        t = t[..., None]
    return a * (1.0 - t) + b * t


def ground() -> None:
    size = 1024
    rng = np.random.default_rng(11)
    broad = fbm(size, 4, 7, rng)
    mid = fbm(size, 16, 5, rng)
    fine = fbm(size, 64, 3, rng)

    dark = np.array([0.15, 0.19, 0.12], np.float32)
    green = np.array([0.30, 0.34, 0.20], np.float32)
    dirt = np.array([0.34, 0.27, 0.18], np.float32)

    albedo = mix(dark, green, smoothstep(np.clip((broad - 0.30) / 0.42, 0, 1)))
    dirt_amount = np.clip((mid - 0.56) * 3.2, 0, 1) * 0.75
    albedo = mix(albedo, dirt, dirt_amount)
    albedo *= (0.84 + 0.32 * fine)[..., None]

    height = broad * 0.55 + mid * 0.30 + fine * 0.15
    yy, xx = np.mgrid[0:size, 0:size]

    # Small stones / pebbles: keep away from the edges so the texture stays seamless.
    for _ in range(220):
        cx = int(rng.integers(10, size - 10))
        cy = int(rng.integers(10, size - 10))
        radius = int(rng.integers(2, 8))
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius * radius
        shade = float(rng.uniform(0.30, 0.52))
        albedo[mask] = albedo[mask] * 0.45 + np.array([shade, shade * 0.94, shade * 0.82]) * 0.55
        height[mask] += 0.10 + float(rng.uniform(0.0, 0.08))

    # Dry grass specks.
    for _ in range(900):
        x = int(rng.integers(0, size))
        y = int(rng.integers(0, size))
        shade = float(rng.uniform(0.26, 0.44))
        albedo[y, x] = albedo[y, x] * 0.3 + np.array([shade * 1.05, shade, shade * 0.55]) * 0.7

    save_rgb(albedo, "ground_albedo.png")
    save_normal(height, "ground_normal.png", 3.2)
    save_gray(0.74 + 0.20 * fine, "ground_roughness.png")


def brick() -> None:
    size = 512
    rows, cols = 4, 2
    bh, bw = size // rows, size // cols
    mortar = 5
    rng = np.random.default_rng(22)
    yy, xx = np.mgrid[0:size, 0:size]
    row = yy // bh
    offset = (row % 2) * (bw // 2)
    xshift = (xx + offset) % size
    col = xshift // bw
    lx = xshift % bw
    ly = yy % bh
    edge = np.minimum(np.minimum(lx, ly), np.minimum(bw - 1 - lx, bh - 1 - ly))
    is_mortar = edge < mortar

    palette = np.array([
        [0.50, 0.24, 0.14], [0.58, 0.29, 0.17], [0.44, 0.20, 0.12],
        [0.55, 0.31, 0.19], [0.48, 0.26, 0.15], [0.61, 0.34, 0.21],
    ], np.float32)
    ids = (row * cols + col) % len(palette)
    fine = fbm(size, 32, 4, rng)
    coarse = fbm(size, 8, 4, rng)

    albedo = palette[ids] * (0.78 + 0.36 * fine)[..., None]
    shade = 0.82 + 0.18 * np.clip(edge / 8.0, 0, 1)
    albedo *= shade[..., None]
    # Pits and wear.
    wear = np.clip((coarse - 0.64) * 4.0, 0, 1) * 0.35
    albedo = mix(albedo, np.array([0.26, 0.18, 0.12], np.float32), wear)

    mortar_color = np.array([0.53, 0.49, 0.40], np.float32)
    mortar_noise = (0.80 + 0.35 * fine)[..., None]
    albedo = np.where(is_mortar[..., None], mortar_color * mortar_noise, albedo)

    height = np.where(is_mortar, 0.18, 0.82) + fine * 0.08
    height += np.clip(edge / 10.0, 0, 1) * 0.05
    save_rgb(albedo, "brick_albedo.png")
    save_normal(height, "brick_normal.png", 4.0)
    save_gray(np.where(is_mortar, 0.94, 0.78 + 0.12 * fine), "brick_roughness.png")


def steel() -> None:
    size = 512
    rng = np.random.default_rng(33)
    fine = fbm(size, 48, 4, rng)
    broad = fbm(size, 4, 5, rng)
    brushed = value_noise(size, 6, 96, rng)

    base = np.array([0.38, 0.40, 0.43], np.float32)
    albedo = base * (0.82 + 0.30 * brushed)[..., None]
    albedo *= (0.90 + 0.18 * fine)[..., None]

    rust = np.clip((broad - 0.62) * 3.6, 0, 1) * 0.35
    albedo = mix(albedo, np.array([0.38, 0.22, 0.13], np.float32), rust)

    height = brushed * 0.35 + fine * 0.15
    yy, xx = np.mgrid[0:size, 0:size]

    # Rivets.
    for y in range(32, size, 64):
        for x in range(32, size, 64):
            mask = (xx - x) ** 2 + (yy - y) ** 2 <= 7 ** 2
            height[mask] += 0.55
            albedo[mask] = albedo[mask] * 0.65 + np.array([0.55, 0.56, 0.58], np.float32) * 0.35

    # Scratches.
    img = Image.fromarray((albedo.clip(0, 1) * 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    for _ in range(40):
        x0 = int(rng.integers(0, size))
        y0 = int(rng.integers(0, size))
        length = int(rng.integers(8, 90))
        draw.line([(x0, y0), (x0 + length, y0 + int(rng.integers(-3, 4)))],
                  fill=tuple(int(v) for v in (rng.uniform(0.55, 0.8) * 255, rng.uniform(0.55, 0.8) * 255, rng.uniform(0.55, 0.8) * 255)),
                  width=1)
    img = img.filter(ImageFilter.GaussianBlur(0.35))
    albedo = np.asarray(img, dtype=np.float32) / 255.0

    save_rgb(albedo, "steel_albedo.png")
    save_normal(height, "steel_normal.png", 4.2)
    save_gray(0.32 + 0.24 * brushed + 0.08 * fine, "steel_roughness.png")


def water_normal() -> None:
    size = 512
    rng = np.random.default_rng(44)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    height = (
        np.sin((xx * 3.0 + yy * 1.5) / size * math.tau) * 0.35
        + np.sin((xx * -1.0 + yy * 4.0) / size * math.tau + 1.7) * 0.25
        + np.sin((xx * 2.0 - yy * 2.0) / size * math.tau + 0.4) * 0.18
        + fbm(size, 8, 4, rng) * 0.22
    )
    height -= height.min()
    height /= max(height.max(), 1e-6)
    save_normal(height, "water_normal.png", 1.6)
    # A second, finer normal map for the shader to blend.
    height2 = fbm(size, 24, 4, rng) * 0.6 + fbm(size, 64, 3, rng) * 0.4
    save_normal(height2, "water_normal_b.png", 1.2)


def ice() -> None:
    size = 512
    rng = np.random.default_rng(55)
    fine = fbm(size, 32, 5, rng)
    base = np.array([0.58, 0.76, 0.86], np.float32)
    albedo = base * (0.86 + 0.24 * fine)[..., None]

    height = fine * 0.35
    img = Image.fromarray((albedo.clip(0, 1) * 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(img)
    for _ in range(28):
        x, y = rng.integers(0, size), rng.integers(0, size)
        points = [(int(x), int(y))]
        for _ in range(int(rng.integers(3, 8))):
            x = (x + rng.integers(-60, 61)) % size
            y = (y + rng.integers(-60, 61)) % size
            points.append((int(x), int(y)))
        brightness = int(rng.uniform(0.75, 0.98) * 255)
        draw.line(points, fill=(brightness, brightness, 255), width=int(rng.integers(1, 3)))
    albedo = np.asarray(img.filter(ImageFilter.GaussianBlur(0.4)), dtype=np.float32) / 255.0
    save_rgb(albedo, "ice_albedo.png")
    save_normal(height, "ice_normal.png", 1.8)
    save_gray(0.10 + 0.15 * fine, "ice_roughness.png")


def foliage() -> None:
    size = 512
    rng = np.random.default_rng(66)
    mottle = fbm(size, 8, 6, rng)
    fine = fbm(size, 48, 4, rng)
    dark = np.array([0.05, 0.16, 0.06], np.float32)
    mid = np.array([0.13, 0.34, 0.13], np.float32)
    light = np.array([0.26, 0.48, 0.17], np.float32)
    albedo = mix(dark, mid, smoothstep(np.clip((mottle - 0.25) / 0.5, 0, 1)))
    albedo = mix(albedo, light, np.clip((fine - 0.55) * 2.0, 0, 1) * 0.5)
    save_rgb(albedo, "foliage_albedo.png")
    save_normal(mottle * 0.7 + fine * 0.3, "foliage_normal.png", 2.2)
    save_gray(0.82 + 0.14 * fine, "foliage_roughness.png")

    # Bark.
    b = fbm(size, 8, 4, rng)
    streak = value_noise(size, 8, 64, rng)
    bark = np.array([0.20, 0.13, 0.08], np.float32) * (0.70 + 0.55 * streak)[..., None]
    bark *= (0.85 + 0.30 * b)[..., None]
    save_rgb(bark, "bark_albedo.png")
    save_normal(streak * 0.8 + b * 0.2, "bark_normal.png", 2.5)


def tank_grunge() -> None:
    size = 512
    rng = np.random.default_rng(77)
    broad = fbm(size, 4, 6, rng)
    fine = fbm(size, 32, 4, rng)
    streak = value_noise(size, 8, 96, rng)
    light = np.array([0.86, 0.85, 0.80], np.float32)
    dark = np.array([0.46, 0.45, 0.42], np.float32)
    albedo = mix(dark, light, smoothstep(np.clip((broad - 0.25) / 0.6, 0, 1)))
    albedo *= (0.82 + 0.30 * streak)[..., None]
    albedo *= (0.90 + 0.20 * fine)[..., None]
    save_rgb(albedo, "tank_grunge_albedo.png")
    save_normal(streak * 0.5 + fine * 0.5, "tank_grunge_normal.png", 1.0)
    save_gray(0.42 + 0.36 * broad + 0.10 * fine, "tank_grunge_roughness.png")


def rock() -> None:
    size = 256
    rng = np.random.default_rng(88)
    broad = fbm(size, 6, 5, rng)
    fine = fbm(size, 32, 4, rng)
    base = np.array([0.34, 0.32, 0.28], np.float32)
    albedo = base * (0.72 + 0.50 * broad)[..., None] * (0.85 + 0.25 * fine)[..., None]
    save_rgb(albedo, "rock_albedo.png")
    save_normal(broad * 0.7 + fine * 0.3, "rock_normal.png", 3.0)
    save_gray(0.80 + 0.15 * fine, "rock_roughness.png")


def grass_tuft() -> None:
    size = 256
    rng = np.random.default_rng(99)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for _ in range(18):
        bx = size * 0.5 + rng.uniform(-45, 45)
        tipx = bx + rng.uniform(-55, 55)
        tipy = rng.uniform(18, 100)
        ctrlx = bx + rng.uniform(-25, 25)
        ctrly = rng.uniform(120, 210)
        points = []
        for t in np.linspace(0.0, 1.0, 12):
            x = (1 - t) ** 2 * bx + 2 * (1 - t) * t * ctrlx + t * t * tipx
            y = (1 - t) ** 2 * size + 2 * (1 - t) * t * ctrly + t * t * tipy
            points.append((float(x), float(y)))
        for i in range(len(points) - 1):
            t = i / max(len(points) - 2, 1)
            color = (
                int(40 + 30 * t),
                int(95 + 65 * t),
                int(35 + 30 * t),
                int(180 + 60 * t),
            )
            draw.line([points[i], points[i + 1]], fill=color, width=int(2 + 2 * (1 - t)))
    img = img.filter(ImageFilter.GaussianBlur(0.3))
    img.save(OUT / "grass_tuft.png", optimize=True)
    print("wrote grass_tuft.png", img.size)


def contact_sheet() -> None:
    names = [
        "ground_albedo.png", "brick_albedo.png", "steel_albedo.png", "ice_albedo.png",
        "foliage_albedo.png", "tank_grunge_albedo.png", "ground_normal.png", "brick_normal.png",
    ]
    thumbs = []
    for name in names:
        img = Image.open(OUT / name).convert("RGB").resize((256, 256))
        thumbs.append((name, img))
    sheet = Image.new("RGB", (256 * 4, 256 * 2), (30, 30, 30))
    for i, (_, img) in enumerate(thumbs):
        sheet.paste(img, ((i % 4) * 256, (i // 4) * 256))
    sheet.save(OUT / "textures_preview.png")
    print("wrote textures_preview.png")


if __name__ == "__main__":
    ground()
    brick()
    steel()
    water_normal()
    ice()
    foliage()
    tank_grunge()
    rock()
    grass_tuft()
    contact_sheet()
