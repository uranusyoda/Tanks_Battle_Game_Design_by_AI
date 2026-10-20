// Presentation effects: explosions, smoke, muzzle flash, tread marks, scorch
// decals, power-up pickups and the energy shield. Pure output — feeding any of
// this back into the rules would be a bug.

import * as THREE from 'three';

export function createFx({ scene, textures, onShake = () => {} }) {
  const { glowTex, smokeTex, shadowTex, scorchTex, trackTex } = textures;

  const geoPlane = new THREE.PlaneGeometry(1, 1);
  const geoDeb = new THREE.BoxGeometry(0.14, 0.14, 0.14);
  const geoOct = new THREE.OctahedronGeometry(0.24);
  const geoRing = new THREE.TorusGeometry(0.32, 0.02, 6, 20);
  const geoShield = new THREE.SphereGeometry(0.85, 18, 12);

  const debrisMat = new THREE.MeshStandardMaterial({ color: 0x5a4636, roughness: 1, metalness: 0 });
  const debrisSteelMat = new THREE.MeshStandardMaterial({
    color: 0x9aa3ad, roughness: 0.55, metalness: 0.7, envMapIntensity: 0.8,
  });
  const smokeMat2 = new THREE.MeshBasicMaterial({ color: 0x8a8a8a, transparent: true, opacity: 0.8 });

  // ambient flash pool
  const flashLights = [];
  for (let i = 0; i < 3; i++) {
    const light = new THREE.PointLight(0xffa252, 0, 13, 2);
    scene.add(light);
    flashLights.push({ light, power: 0, t: 0, dur: 0.35 });
  }
  let flashIdx = 0;

  function flashLight(x, z, power) {
    const f = flashLights[flashIdx++ % flashLights.length];
    f.light.position.set(x, 0.9, z);
    f.power = 16 * power;
    f.t = 0;
    f.dur = 0.38;
    f.light.intensity = f.power;
  }

  const fx = [];
  function addFx(mesh, dur, fn) {
    scene.add(mesh);
    fx.push({ mesh, dur, t: 0, fn });
  }

  function spriteFx(map, color, opacity, blend) {
    return new THREE.Sprite(
      new THREE.SpriteMaterial({
        map,
        color,
        transparent: true,
        opacity,
        depthWrite: false,
        blending: blend === undefined ? THREE.NormalBlending : blend,
      }),
    );
  }

  function flash(x, y, z, color, size, dur) {
    const m = spriteFx(glowTex, color, 1, THREE.AdditiveBlending);
    m.position.set(x, y, z);
    m.scale.setScalar(size);
    addFx(m, dur, (mm, k) => {
      mm.scale.setScalar(size * (0.55 + k * 1.5));
      mm.material.opacity = Math.pow(1 - k, 1.5);
    });
  }

  function dustPuff(x, z) {
    const m = spriteFx(smokeTex, 0xcbb28a, 0.3);
    m.position.set(x + (Math.random() - 0.5) * 0.3, 0.16, z + (Math.random() - 0.5) * 0.3);
    m.scale.setScalar(0.5);
    addFx(m, 0.55 + Math.random() * 0.35, (mm, k, dt) => {
      mm.position.y += dt * 0.5;
      mm.scale.setScalar(0.5 + k * 1.2);
      mm.material.opacity = 0.3 * (1 - k);
    });
  }

  function muzzleSmoke(x, z) {
    for (let i = 0; i < 3; i++) {
      const m = spriteFx(smokeTex, 0x8a8a86, 0.42);
      m.position.set(x + (Math.random() - 0.5) * 0.22, 0.66, z + (Math.random() - 0.5) * 0.22);
      m.scale.setScalar(0.34);
      addFx(m, 0.45 + Math.random() * 0.3, (mm, k, dt) => {
        mm.position.y += dt * 0.45;
        mm.scale.setScalar(0.34 + k * 0.95);
        mm.material.opacity = 0.42 * (1 - k);
      });
    }
  }

  function spark(x, z) {
    flash(x, 0.62, z, 0xfff0b0, 0.32, 0.14);
    for (let i = 0; i < 3; i++) {
      flash(
        x + (Math.random() - 0.5) * 0.3,
        0.55 + Math.random() * 0.35,
        z + (Math.random() - 0.5) * 0.3,
        0xffa860,
        0.14,
        0.2 + Math.random() * 0.15,
      );
    }
  }

  function spawnFx(x, z) {
    const m = spriteFx(glowTex, 0xfff2d0, 1, THREE.AdditiveBlending);
    m.position.set(x, 0.35, z);
    m.scale.setScalar(0.6);
    addFx(m, 0.5, (mm, k) => {
      mm.scale.setScalar(0.6 + 2.2 * k);
      mm.material.opacity = (1 - k) * 0.9;
    });
    for (let i = 0; i < 4; i++) dustPuff(x + (Math.random() - 0.5) * 0.6, z + (Math.random() - 0.5) * 0.6);
  }

  function smokeCloud(x, z) {
    for (let i = 0; i < 16; i++) {
      const sm = spriteFx(smokeTex, i % 2 ? 0x7f858c : 0x5d626a, 0.72);
      const a = Math.random() * 6.283;
      const r = Math.random() * 1.5;
      sm.position.set(x + Math.cos(a) * r, 0.3 + Math.random() * 0.3, z + Math.sin(a) * r);
      const rise = 0.28 + Math.random() * 0.32;
      addFx(sm, 5, (m, k, dt) => {
        m.position.y += dt * rise;
        m.position.x += Math.cos(a) * dt * 0.22;
        m.position.z += Math.sin(a) * dt * 0.22;
        m.scale.setScalar(1.3 + k * 2.8);
        const fade = k < 0.72 ? 1 : (1 - k) / 0.28;
        m.material.opacity = 0.72 * fade * (0.8 + 0.2 * Math.sin(k * 9 + i));
      });
    }
  }

  function explosion(x, z, s) {
    onShake(0.3 * s);
    flashLight(x, z, Math.min(1.4, s));

    const fl = spriteFx(glowTex, 0xffc070, 1, THREE.AdditiveBlending);
    fl.position.set(x, 0.5 * s + 0.2, z);
    fl.scale.setScalar(1.1 * s);
    addFx(fl, 0.42, (m, k) => {
      m.scale.setScalar((1.1 + 3.2 * k) * s);
      m.material.opacity = Math.pow(1 - k, 2);
    });

    for (let i = 0; i < 7; i++) {
      const sm = spriteFx(smokeTex, i % 3 ? 0x4d4842 : 0x6d655c, 0.6);
      const a = Math.random() * 6.283;
      const r = Math.random() * 0.55 * s;
      sm.position.set(x + Math.cos(a) * r, 0.25 + Math.random() * 0.45, z + Math.sin(a) * r);
      const rise = 0.55 + Math.random() * 0.7;
      const drift = 0.35 + Math.random() * 0.5;
      addFx(sm, 0.9 + Math.random() * 0.7, (m, k, dt) => {
        m.position.y += dt * rise;
        m.position.x += Math.cos(a) * dt * drift;
        m.position.z += Math.sin(a) * dt * drift;
        m.scale.setScalar((0.55 + 1.9 * k) * s);
        m.material.opacity = 0.6 * (1 - k) * (1 - k * 0.4);
      });
    }

    const group = new THREE.Group();
    const parts = [];
    for (let i = 0; i < 14; i++) {
      const p = new THREE.Mesh(geoDeb, i % 3 ? debrisMat : smokeMat2);
      group.add(p);
      parts.push(new THREE.Vector3((Math.random() - 0.5) * 4 * s, (2 + Math.random() * 3) * s, (Math.random() - 0.5) * 4 * s));
    }
    group.position.set(x, 0.4, z);
    addFx(group, 0.7, (g, k, d) => {
      g.children.forEach((p, i) => {
        const v = parts[i];
        v.y -= 11 * d;
        p.position.addScaledVector(v, d);
        p.rotation.x += d * 6;
        p.rotation.y += d * 5;
        if (p.position.y < 0.05) p.position.y = 0.05;
      });
    });

    addScorch(x, z, s);
  }

  // ------------------------------------------------------------ tread marks
  const trackGroup = new THREE.Group();
  scene.add(trackGroup);
  const tracks = [];
  let trackCd = 0;

  function addTrack(x, z, heading) {
    const m = new THREE.Mesh(
      geoPlane,
      new THREE.MeshBasicMaterial({
        map: trackTex,
        color: 0x4a3620,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
        polygonOffset: true,
        polygonOffsetFactor: -1,
      }),
    );
    m.rotation.x = -Math.PI / 2;
    m.rotation.z = -heading;
    m.position.set(x, 0.006, z);
    m.scale.set(0.98, 0.62, 1);
    m.renderOrder = 1;
    trackGroup.add(m);
    tracks.push({ m, life: 8 });
    if (tracks.length > 70) {
      const t0 = tracks.shift();
      trackGroup.remove(t0.m);
      t0.m.material.dispose();
    }
  }

  /** Called by the app each frame; emits a mark every 0.1s while moving. */
  function updateTreadMarks(dt, player) {
    if (!player || !player.alive || !player.moving) return;
    trackCd -= dt;
    if (trackCd <= 0) {
      addTrack(player.x, player.z, player.heading);
      trackCd = 0.1;
    }
  }

  // ---------------------------------------------------------------- scorches
  const decalGroup = new THREE.Group();
  scene.add(decalGroup);
  const decals = [];

  function addScorch(x, z, s) {
    const m = new THREE.Mesh(
      geoPlane,
      new THREE.MeshBasicMaterial({
        map: scorchTex,
        color: 0x2a1d13,
        transparent: true,
        opacity: 0.55,
        depthWrite: false,
        polygonOffset: true,
        polygonOffsetFactor: -2,
      }),
    );
    m.rotation.x = -Math.PI / 2;
    m.rotation.z = Math.random() * 6.283;
    m.position.set(x, 0.014, z);
    m.scale.setScalar((1.5 + Math.random() * 0.8) * s);
    decalGroup.add(m);
    decals.push(m);
    if (decals.length > 26) {
      const d0 = decals.shift();
      decalGroup.remove(d0);
      d0.material.dispose();
    }
  }

  // ---------------------------------------------------------------- pickups
  const pickupMap = new Map();

  function syncPickups(list, time, dt = 1 / 60) {
    const live = new Set();
    for (const p of list) {
      live.add(p.id);
      let view = pickupMap.get(p.id);
      if (!view) {
        const mesh = new THREE.Mesh(
          geoOct,
          new THREE.MeshStandardMaterial({
            color: p.def.color,
            emissive: p.def.color,
            emissiveIntensity: 0.45,
            roughness: 0.4,
          }),
        );
        mesh.position.set(p.x, 0.55, p.z);
        const ring = new THREE.Mesh(
          geoRing,
          new THREE.MeshBasicMaterial({ color: p.def.color, transparent: true, opacity: 0.7 }),
        );
        ring.rotation.x = Math.PI / 2;
        ring.position.set(p.x, 0.08, p.z);
        scene.add(mesh);
        scene.add(ring);
        view = { mesh, ring, life: p.life };
        pickupMap.set(p.id, view);
      }
      view.mesh.rotation.y += 2.5 * dt;
      view.mesh.position.y = 0.55 + Math.sin(time * 3 + p.x) * 0.08;
      const blink = p.life < 3 && Math.floor(time * 8) % 2 === 0;
      view.mesh.visible = !blink;
      view.ring.visible = !blink;
    }
    for (const [id, view] of pickupMap) {
      if (live.has(id)) continue;
      scene.remove(view.mesh);
      scene.remove(view.ring);
      view.mesh.material.dispose();
      view.ring.material.dispose();
      pickupMap.delete(id);
    }
  }

  // ----------------------------------------------------------------- shield
  let shieldGroup = null;

  function ensureShield() {
    if (shieldGroup) return shieldGroup;
    shieldGroup = new THREE.Group();
    const inner = new THREE.Mesh(
      new THREE.SphereGeometry(0.82, 24, 16),
      new THREE.MeshBasicMaterial({
        color: 0x7db4ff,
        transparent: true,
        opacity: 0.13,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide,
      }),
    );
    const wire = new THREE.Mesh(
      geoShield,
      new THREE.MeshBasicMaterial({ color: 0xa9d4ff, wireframe: true, transparent: true, opacity: 0.34, depthWrite: false }),
    );
    shieldGroup.add(inner, wire);
    scene.add(shieldGroup);
    return shieldGroup;
  }

  function syncShield(player, time) {
    const visible = !!player && player.alive && player.shield > 0;
    const group = ensureShield();
    group.visible = visible;
    if (!visible) return;
    group.position.set(player.x, 0.5, player.z);
    group.rotation.y = time * 0.8;
    group.scale.setScalar(1 + Math.sin(time * 6) * 0.05);
  }

  // ----------------------------------------------------------------- update
  function update(dt, time) {
    for (let i = fx.length - 1; i >= 0; i--) {
      const f = fx[i];
      f.t += dt;
      const k = f.t / f.dur;
      if (k >= 1) {
        scene.remove(f.mesh);
        if (f.mesh.isSprite && f.mesh.material) f.mesh.material.dispose();
        fx.splice(i, 1);
      } else {
        f.fn(f.mesh, k, dt);
      }
    }

    for (let i = tracks.length - 1; i >= 0; i--) {
      const t = tracks[i];
      t.life -= dt;
      if (t.life <= 0) {
        trackGroup.remove(t.m);
        t.m.material.dispose();
        tracks.splice(i, 1);
      } else {
        t.m.material.opacity = 0.22 * Math.min(1, t.life / 2.5);
      }
    }

    for (const f of flashLights) {
      if (f.t < f.dur) {
        f.t += dt;
        const k = Math.min(1, f.t / f.dur);
        f.light.intensity = f.power * (1 - k) * (1 - k);
      } else if (f.light.intensity !== 0) {
        f.light.intensity = 0;
      }
    }
  }

  function clear() {
    for (let i = fx.length - 1; i >= 0; i--) {
      scene.remove(fx[i].mesh);
      if (fx[i].mesh.isSprite) fx[i].mesh.material.dispose();
    }
    fx.length = 0;
    for (const t of tracks) {
      trackGroup.remove(t.m);
      t.m.material.dispose();
    }
    tracks.length = 0;
    for (const d of decals) {
      decalGroup.remove(d);
      d.material.dispose();
    }
    decals.length = 0;
    for (const [id, view] of pickupMap) {
      scene.remove(view.mesh);
      scene.remove(view.ring);
      view.mesh.material.dispose();
      view.ring.material.dispose();
      pickupMap.delete(id);
    }
    for (const f of flashLights) {
      f.t = f.dur;
      f.power = 0;
      f.light.intensity = 0;
    }
    if (shieldGroup) shieldGroup.visible = false;
    trackCd = 0;
  }

  return {
    glowTex,
    smokeTex,
    shadowTex,
    explosion,
    flash,
    spark,
    muzzleSmoke,
    dustPuff,
    smokeCloud,
    spawnFx,
    addTrack,
    addScorch,
    syncPickups,
    syncShield,
    updateTreadMarks,
    update,
    clear,
  };
}
