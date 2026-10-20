// Procedural texture generation. This is asset production code, not rules:
// it may use the DOM canvas and Three.js textures, and it never decides gameplay.

import * as THREE from 'three';
import { mulberry32 } from '../shared/random.js';

const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const clamp255 = (v) => (v < 0 ? 0 : v > 255 ? 255 : v);
const smoothstep = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};

// tileable value-noise fbm field, returns Float32Array in [0,1]
function fbm(size, freq, octaves, seed, gain = 0.5) {
  const rand = mulberry32(seed);
  const out = new Float32Array(size * size);
  let amp = 1;
  let total = 0;
  for (let o = 0; o < octaves; o++) {
    const f = freq << o;
    const grid = new Float32Array(f * f);
    for (let i = 0; i < grid.length; i++) grid[i] = rand();
    for (let y = 0; y < size; y++) {
      const fy = ((y + 0.5) / size) * f;
      const y0 = Math.floor(fy);
      const ty = fy - y0;
      const sy = ty * ty * (3 - 2 * ty);
      const y1 = (y0 + 1) % f;
      const row0 = y0 * f;
      const row1 = y1 * f;
      for (let x = 0; x < size; x++) {
        const fx = ((x + 0.5) / size) * f;
        const x0 = Math.floor(fx);
        const tx = fx - x0;
        const sx = tx * tx * (3 - 2 * tx);
        const x1 = (x0 + 1) % f;
        const a = grid[row0 + x0];
        const b = grid[row0 + x1];
        const c = grid[row1 + x0];
        const d = grid[row1 + x1];
        out[y * size + x] += amp * ((a + (b - a) * sx) * (1 - sy) + (c + (d - c) * sx) * sy);
      }
    }
    total += amp;
    amp *= gain;
  }
  for (let i = 0; i < out.length; i++) out[i] /= total;
  return out;
}

function rawTex(size, paint, srgb, maxAniso) {
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  const img = ctx.createImageData(size, size);
  const d = img.data;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const o = (y * size + x) << 2;
      const c = paint(x, y);
      d[o] = c[0];
      d[o + 1] = c[1];
      d[o + 2] = c[2];
      d[o + 3] = c.length > 3 ? c[3] : 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = maxAniso;
  return t;
}

function normalFromH(h, size, strength, maxAniso) {
  return rawTex(
    size,
    (x, y) => {
      const xl = (x - 1 + size) % size;
      const xr = (x + 1) % size;
      const yu = (y - 1 + size) % size;
      const yd = (y + 1) % size;
      const gx = h[y * size + xr] - h[y * size + xl];
      const gy = h[yd * size + x] - h[yu * size + x];
      const nx = -gx * strength;
      const ny = gy * strength;
      const l = Math.hypot(nx, ny, 1);
      return [((nx / l) * 0.5 + 0.5) * 255, ((ny / l) * 0.5 + 0.5) * 255, ((1 / l) * 0.5 + 0.5) * 255];
    },
    false,
    maxAniso,
  );
}

function radialTex(size, stops, srgb, maxAniso) {
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const s of stops) g.addColorStop(s[0], s[1]);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = srgb === false ? THREE.NoColorSpace : THREE.SRGBColorSpace;
  t.anisotropy = maxAniso;
  return t;
}

// ---------------------------------------------------------------------------
// surface maps
// ---------------------------------------------------------------------------
export function createSurfaceTextures(maxAniso = 8) {
  // ground
  const GS = 512;
  const gA = fbm(GS, 3, 4, 101);
  const gB = fbm(GS, 8, 4, 202);
  const gC = fbm(GS, 36, 3, 303);

  const groundMap = rawTex(
    GS,
    (x, y) => {
      const i = y * GS + x;
      const l = gA[i];
      const m = gB[i];
      const f = gC[i];
      let r = 198;
      let g = 174;
      let b = 136;
      const patch = (l - 0.5) * 28 + (m - 0.5) * 15 + (f - 0.5) * 9;
      r += patch;
      g += patch * 0.93;
      b += patch * 0.82;
      const warm = m - 0.5;
      r += warm * 7;
      g += warm * 3;
      b -= warm * 6;
      if (f > 0.7) {
        const k = (f - 0.7) * 7;
        r += k * 11;
        g += k * 9;
        b += k * 7;
      }
      if (f < 0.28) {
        const k = (0.28 - f) * 7;
        r -= k * 13;
        g -= k * 13;
        b -= k * 12;
      }
      if (m < 0.28) {
        const k = (0.28 - m) * 70;
        r -= k * 0.5;
        g -= k * 0.58;
        b -= k * 0.55;
      }
      if (m > 0.87) {
        const k = (m - 0.87) * 420;
        r += k * 0.11;
        g += k * 0.1;
        b += k * 0.08;
      }
      return [clamp255(r), clamp255(g), clamp255(b)];
    },
    true,
    maxAniso,
  );

  const groundRough = rawTex(
    GS,
    (x, y) => {
      const i = y * GS + x;
      const v = 232 + (gC[i] - 0.5) * 42 - (gB[i] > 0.87 ? 30 : 0);
      return [clamp255(v), clamp255(v), clamp255(v)];
    },
    false,
    maxAniso,
  );

  const groundH = new Float32Array(GS * GS);
  for (let i = 0; i < groundH.length; i++) {
    groundH[i] = gB[i] * 0.32 + gC[i] * 0.55 + Math.max(0, gB[i] - 0.87) * 1.7;
  }
  const groundNormal = normalFromH(groundH, GS, 2.4, maxAniso);
  groundMap.repeat.set(26, 26);
  groundRough.repeat.set(26, 26);
  groundNormal.repeat.set(26, 26);

  // brick
  const BS = 512;
  const bA = fbm(BS, 14, 4, 211);
  const bB = fbm(BS, 52, 3, 222);
  const BCOLS = 4;
  const BROWS = 4;
  const MORTAR = 0.042;

  function brickAt(x, y) {
    const bu = ((x + 0.5) / BS) * BCOLS;
    const bv = ((y + 0.5) / BS) * BROWS;
    const row = Math.floor(bv);
    const cu = bu + (row & 1) * 0.5;
    const col = Math.floor(cu);
    const fu = cu - col;
    const fv = bv - row;
    return { row, col, edge: Math.min(fu, 1 - fu, fv, 1 - fv) };
  }
  function brickHash(r, c) {
    const h = Math.sin(r * 127.1 + c * 311.7) * 43758.5453;
    return h - Math.floor(h);
  }

  const brickMap = rawTex(
    BS,
    (x, y) => {
      const i = y * BS + x;
      const b = brickAt(x, y);
      const n = (bA[i] - 0.5) * 22 + (bB[i] - 0.5) * 9;
      if (b.edge < MORTAR) {
        const v = 88 + n * 0.4;
        return [v, v + 1, v + 5];
      }
      const h = brickHash(b.row, b.col);
      let r = 163 + h * 26;
      let g = 94 + h * 17;
      let b2 = 76 + h * 10;
      r += n;
      g += n * 0.7;
      b2 += n * 0.6;
      const wear = 1 - smoothstep(MORTAR, MORTAR + 0.06, b.edge);
      const k = wear * wear * 24;
      r -= k;
      g -= k;
      b2 -= k;
      const grime = smoothstep(0.5, 0.9, bA[i]) * 17;
      r -= grime * 0.9;
      g -= grime;
      b2 -= grime * 0.8;
      return [clamp255(r), clamp255(g), clamp255(b2)];
    },
    true,
    maxAniso,
  );

  const brickH = new Float32Array(BS * BS);
  for (let y = 0; y < BS; y++) {
    for (let x = 0; x < BS; x++) {
      const b = brickAt(x, y);
      const i = y * BS + x;
      brickH[i] = smoothstep(MORTAR, MORTAR + 0.055, b.edge) + (bA[i] - 0.5) * 0.1 + (bB[i] - 0.5) * 0.05;
    }
  }
  const brickNormal = normalFromH(brickH, BS, 4.6, maxAniso);
  const brickRough = rawTex(
    BS,
    (x, y) => {
      const i = y * BS + x;
      const b = brickAt(x, y);
      const v = (b.edge < MORTAR ? 248 : 222) + (bB[i] - 0.5) * 28;
      return [clamp255(v), clamp255(v), clamp255(v)];
    },
    false,
    maxAniso,
  );

  // riveted steel
  const SS = 512;
  const sA = fbm(SS, 10, 4, 311);
  const sB = fbm(SS, 48, 3, 322);
  const rivets = [];
  for (let k = 0; k < 5; k++) {
    const t = 0.09 + k * 0.205;
    rivets.push([t, 0.045], [t, 0.955], [0.045, t], [0.955, t]);
  }
  const steelMap = rawTex(
    SS,
    (x, y) => {
      const i = y * SS + x;
      const u = (x + 0.5) / SS;
      const v = (y + 0.5) / SS;
      let base = 118 + (sA[i] - 0.5) * 26 + (sB[i] - 0.5) * 12;
      base += Math.sin(y * 1.3 + sA[i] * 10) * 1.8;
      const e = Math.min(u, 1 - u, v, 1 - v);
      const border = 1 - smoothstep(0.016, 0.034, e);
      base -= border * 40;
      const seam = Math.max(
        1 - smoothstep(0.003, 0.012, Math.abs(u - 0.5)),
        1 - smoothstep(0.003, 0.012, Math.abs(v - 0.5)),
      );
      base -= seam * 24;
      let rd = 9;
      for (const r of rivets) rd = Math.min(rd, Math.hypot(u - r[0], v - r[1]));
      if (rd < 0.026) {
        const k = 1 - rd / 0.026;
        base += k * k * 30 - 8;
      }
      if (sB[i] > 0.72 && sA[i] > 0.5) base += 8;
      return [clamp255(base), clamp255(base + 4), clamp255(base + 12)];
    },
    true,
    maxAniso,
  );

  const steelH = new Float32Array(SS * SS);
  for (let y = 0; y < SS; y++) {
    for (let x = 0; x < SS; x++) {
      const i = y * SS + x;
      const u = (x + 0.5) / SS;
      const v = (y + 0.5) / SS;
      const e = Math.min(u, 1 - u, v, 1 - v);
      let h = 0.5 + (sA[i] - 0.5) * 0.06 + (sB[i] - 0.5) * 0.03;
      h -= (1 - smoothstep(0.016, 0.034, e)) * 0.5;
      h -= Math.max(
        1 - smoothstep(0.003, 0.012, Math.abs(u - 0.5)),
        1 - smoothstep(0.003, 0.012, Math.abs(v - 0.5)),
      ) * 0.24;
      let rd = 9;
      for (const r of rivets) rd = Math.min(rd, Math.hypot(u - r[0], v - r[1]));
      if (rd < 0.026) h += (1 - rd / 0.026) * 0.42;
      steelH[i] = h;
    }
  }
  const steelNormal = normalFromH(steelH, SS, 3.0, maxAniso);
  const steelRough = rawTex(
    SS,
    (x, y) => {
      const i = y * SS + x;
      const u = (x + 0.5) / SS;
      const v = (y + 0.5) / SS;
      let vv = 124 + (sB[i] - 0.5) * 38;
      const e = Math.min(u, 1 - u, v, 1 - v);
      vv += (1 - smoothstep(0.016, 0.034, e)) * 46;
      vv += Math.max(
        1 - smoothstep(0.003, 0.012, Math.abs(u - 0.5)),
        1 - smoothstep(0.003, 0.012, Math.abs(v - 0.5)),
      ) * 22;
      let rd = 9;
      for (const r of rivets) rd = Math.min(rd, Math.hypot(u - r[0], v - r[1]));
      if (rd < 0.026) vv -= 34;
      return [clamp255(vv), clamp255(vv), clamp255(vv)];
    },
    false,
    maxAniso,
  );

  // foliage
  const FS = 256;
  const fA = fbm(FS, 10, 4, 711);
  const fB = fbm(FS, 42, 3, 722);
  const leafMap = rawTex(
    FS,
    (x, y) => {
      const i = y * FS + x;
      const n = (fA[i] - 0.5) * 38 + (fB[i] - 0.5) * 18;
      return [clamp255(112 + n * 0.5), clamp255(154 + n), clamp255(86 + n * 0.4)];
    },
    true,
    maxAniso,
  );

  // water ripples
  const WS = 256;
  const wA = fbm(WS, 6, 4, 611);
  const wB = fbm(WS, 18, 3, 622);
  const waterH = new Float32Array(WS * WS);
  for (let i = 0; i < waterH.length; i++) waterH[i] = wA[i] * 0.62 + wB[i] * 0.38;
  const waterNormal = normalFromH(waterH, WS, 4.2, maxAniso);
  waterNormal.repeat.set(2, 2);

  return {
    groundMap, groundRough, groundNormal,
    brickMap, brickNormal, brickRough,
    steelMap, steelNormal, steelRough,
    leafMap, waterNormal,
  };
}

// ---------------------------------------------------------------------------
// FX sprites and decals
// ---------------------------------------------------------------------------
export function createFxTextures(maxAniso = 8) {
  const glowTex = radialTex(
    128,
    [
      [0, 'rgba(255,255,255,1)'],
      [0.22, 'rgba(255,255,255,.66)'],
      [0.55, 'rgba(255,255,255,.17)'],
      [1, 'rgba(255,255,255,0)'],
    ],
    true,
    maxAniso,
  );
  const smokeTex = radialTex(
    128,
    [
      [0, 'rgba(255,255,255,.78)'],
      [0.45, 'rgba(255,255,255,.3)'],
      [1, 'rgba(255,255,255,0)'],
    ],
    true,
    maxAniso,
  );
  const shadowTex = radialTex(
    128,
    [
      [0, 'rgba(0,0,0,.66)'],
      [0.42, 'rgba(0,0,0,.34)'],
      [0.75, 'rgba(0,0,0,.08)'],
      [1, 'rgba(0,0,0,0)'],
    ],
    false,
    maxAniso,
  );
  const scorchTex = radialTex(
    128,
    [
      [0, 'rgba(0,0,0,.92)'],
      [0.3, 'rgba(0,0,0,.6)'],
      [0.68, 'rgba(0,0,0,.2)'],
      [1, 'rgba(0,0,0,0)'],
    ],
    false,
    maxAniso,
  );

  // tread marks impressed into the sand
  const cv = document.createElement('canvas');
  cv.width = cv.height = 64;
  const ctx = cv.getContext('2d');
  for (const cxp of [20, 44]) {
    const g = ctx.createRadialGradient(cxp, 32, 0, cxp, 32, 13);
    g.addColorStop(0, 'rgba(0,0,0,.8)');
    g.addColorStop(0.55, 'rgba(0,0,0,.35)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.ellipse(cxp, 32, 11, 29, 0, 0, 6.2832);
    ctx.fill();
  }
  const trackTex = new THREE.CanvasTexture(cv);

  return { glowTex, smokeTex, shadowTex, scorchTex, trackTex };
}

// ---------------------------------------------------------------------------
// sky
// ---------------------------------------------------------------------------
export function makeSkyEquirect(sunDir) {
  const W = 1024;
  const H = 512;
  const cv = document.createElement('canvas');
  cv.width = W;
  cv.height = H;
  const ctx = cv.getContext('2d');
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0.0, '#1f4a7d');
  g.addColorStop(0.2, '#3f6f9e');
  g.addColorStop(0.36, '#7ea9c8');
  g.addColorStop(0.46, '#c6cfd2');
  g.addColorStop(0.5, '#ecd8b4');
  g.addColorStop(0.56, '#c7a678');
  g.addColorStop(0.78, '#a3825b');
  g.addColorStop(1.0, '#7a6042');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  const su = (Math.atan2(sunDir.z, sunDir.x) / (Math.PI * 2) + 0.5) * W;
  const sv = (0.5 - Math.asin(sunDir.y) / Math.PI) * H;
  for (const ox of [-W, 0, W]) {
    const rg = ctx.createRadialGradient(su + ox, sv, 0, su + ox, sv, H * 0.42);
    rg.addColorStop(0, 'rgba(255,250,232,1)');
    rg.addColorStop(0.045, 'rgba(255,238,198,.95)');
    rg.addColorStop(0.18, 'rgba(255,218,160,.4)');
    rg.addColorStop(0.55, 'rgba(255,206,146,.11)');
    rg.addColorStop(1, 'rgba(255,200,140,0)');
    ctx.fillStyle = rg;
    ctx.beginPath();
    ctx.arc(su + ox, sv, H * 0.42, 0, Math.PI * 2);
    ctx.fill();
  }
  const hz = ctx.createLinearGradient(0, H * 0.4, 0, H * 0.56);
  hz.addColorStop(0, 'rgba(255,228,190,0)');
  hz.addColorStop(0.55, 'rgba(255,228,190,.32)');
  hz.addColorStop(1, 'rgba(255,228,190,0)');
  ctx.fillStyle = hz;
  ctx.fillRect(0, H * 0.4, W, H * 0.16);
  return cv;
}
