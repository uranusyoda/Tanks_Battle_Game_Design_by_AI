// The battlefield: tiles, eagle monument, water animation and tile changes.
// It reads level content and listens to core `tileChanged` events; it never
// changes the grid itself.

import * as THREE from 'three';
import { cx, cz, TILE } from '../core/constants.js';

export function createWorld({ scene, textures, fx }) {
  const staticG = new THREE.Group();
  scene.add(staticG);

  const geoBox = new THREE.BoxGeometry(1, 1, 1);
  const geoPlane = new THREE.PlaneGeometry(1, 1);
  const geoGroundPatch = new THREE.CircleGeometry(0.5, 20);
  const geoBush = new THREE.SphereGeometry(0.3, 10, 8);
  const geoTree = new THREE.ConeGeometry(0.32, 0.95, 8);
  const geoTrunk = new THREE.CylinderGeometry(0.045, 0.065, 0.35, 6);
  const geoEagleBody = new THREE.SphereGeometry(0.26, 16, 12);
  const geoEagleHead = new THREE.SphereGeometry(0.12, 12, 8);
  const geoEagleBase = new THREE.CylinderGeometry(0.5, 0.58, 0.12, 24);
  const geoEagleStep = new THREE.CylinderGeometry(0.38, 0.45, 0.1, 24);
  const geoEagleBand = new THREE.CylinderGeometry(0.4, 0.42, 0.045, 24);
  const geoDeb = new THREE.BoxGeometry(0.14, 0.14, 0.14);

  const brickMat = new THREE.MeshStandardMaterial({
    map: textures.brickMap,
    normalMap: textures.brickNormal,
    normalScale: new THREE.Vector2(0.85, 0.85),
    roughnessMap: textures.brickRough,
    roughness: 1,
    metalness: 0,
    envMapIntensity: 0.4,
  });
  const steelMat = new THREE.MeshStandardMaterial({
    map: textures.steelMap,
    normalMap: textures.steelNormal,
    normalScale: new THREE.Vector2(0.9, 0.9),
    roughnessMap: textures.steelRough,
    roughness: 1,
    metalness: 0.72,
    envMapIntensity: 1.1,
  });
  const waterMat = new THREE.MeshPhysicalMaterial({
    color: 0x123c5c,
    roughness: 0.07,
    metalness: 0,
    normalMap: textures.waterNormal,
    normalScale: new THREE.Vector2(0.55, 0.55),
    transparent: true,
    opacity: 0.86,
    envMapIntensity: 1.35,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    ior: 1.33,
  });
  const iceMat = new THREE.MeshPhysicalMaterial({
    color: 0xd8e8f2,
    roughness: 0.05,
    metalness: 0,
    envMapIntensity: 1.4,
    clearcoat: 0.8,
    clearcoatRoughness: 0.06,
    transparent: true,
    opacity: 0.9,
  });
  const forestMat = new THREE.MeshStandardMaterial({
    map: textures.leafMap, color: 0x9fca7a, roughness: 0.95, metalness: 0, flatShading: true,
  });
  const forestMat2 = new THREE.MeshStandardMaterial({
    map: textures.leafMap, color: 0x6d9c52, roughness: 0.95, metalness: 0, flatShading: true,
  });
  const forestGroundMat = new THREE.MeshStandardMaterial({ color: 0x3d4b2c, roughness: 1, metalness: 0 });
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5a4130, roughness: 0.95, metalness: 0 });
  const plinthMat = new THREE.MeshStandardMaterial({ color: 0x4b4f57, roughness: 0.55, metalness: 0.15, envMapIntensity: 0.7 });
  const waterBedMat = new THREE.MeshStandardMaterial({ color: 0x15251f, roughness: 0.92, metalness: 0 });
  const eagleMat = new THREE.MeshStandardMaterial({ color: 0x8a6535, metalness: 0.55, roughness: 0.45, envMapIntensity: 0.9 });
  const wingMat = new THREE.MeshStandardMaterial({ color: 0xd9a94f, metalness: 0.35, roughness: 0.4, envMapIntensity: 0.8 });
  const goldMat = new THREE.MeshPhysicalMaterial({
    color: 0xffc73f, metalness: 0.55, roughness: 0.3, envMapIntensity: 1.1, clearcoat: 0.6, clearcoatRoughness: 0.12,
  });
  const eagleGlowMat = new THREE.SpriteMaterial({
    map: fx.glowTex, color: 0xffcf82, blending: THREE.AdditiveBlending, transparent: true, opacity: 0.2, depthWrite: false,
  });
  const debrisMat = new THREE.MeshStandardMaterial({ color: 0x5a4636, roughness: 1, metalness: 0 });
  const debrisSteelMat = new THREE.MeshStandardMaterial({ color: 0x9aa3ad, roughness: 0.55, metalness: 0.7, envMapIntensity: 0.8 });

  const blockMeshes = new Map();
  const waters = [];
  let levelRef = null;
  let eagleGlow = null;

  function build(level) {
    clear();
    levelRef = level;
    const tiles = level.grid;
    for (let r = 0; r < tiles.length; r++) {
      for (let c = 0; c < tiles[r].length; c++) {
        const t = tiles[r][c];
        const x = cx(c);
        const z = cz(r);
        if (t === TILE.BRICK || t === TILE.STEEL) {
          addBlock(r, c, t, x, z);
        } else if (t === TILE.WATER) {
          const bed = new THREE.Mesh(geoPlane, waterBedMat);
          bed.rotation.x = -Math.PI / 2;
          bed.position.set(x, 0.03, z);
          bed.scale.set(0.99, 0.99, 1);
          bed.receiveShadow = true;
          staticG.add(bed);

          const m = new THREE.Mesh(geoPlane, waterMat);
          m.rotation.x = -Math.PI / 2;
          m.position.set(x, 0.07, z);
          m.scale.set(0.99, 0.99, 1);
          m.receiveShadow = true;
          m.userData.ph = Math.random() * 6;
          m.userData.baseY = 0.07;
          staticG.add(m);
          waters.push(m);
        } else if (t === TILE.FOREST) {
          const patch = new THREE.Mesh(geoGroundPatch, forestGroundMat);
          patch.rotation.x = -Math.PI / 2;
          patch.position.set(x, 0.012, z);
          patch.scale.setScalar(1.1);
          patch.receiveShadow = true;
          staticG.add(patch);
          for (let i = 0; i < 5; i++) {
            const m = new THREE.Mesh(geoBush, i % 2 ? forestMat : forestMat2);
            const s = 0.28 + Math.random() * 0.24;
            m.scale.set(s, s * 1.15, s);
            m.position.set(x + (Math.random() - 0.5) * 0.58, 0.22 + s * 0.5, z + (Math.random() - 0.5) * 0.58);
            m.castShadow = true;
            m.receiveShadow = true;
            staticG.add(m);
          }
          const trunk = new THREE.Mesh(geoTrunk, trunkMat);
          trunk.position.set(x, 0.17, z);
          trunk.castShadow = true;
          staticG.add(trunk);
          const cone = new THREE.Mesh(geoTree, forestMat2);
          cone.position.set(x, 0.62, z);
          cone.scale.set(1.05, 1, 1.05);
          cone.castShadow = true;
          staticG.add(cone);
          const cone2 = new THREE.Mesh(geoTree, forestMat);
          cone2.position.set(x, 1.0, z);
          cone2.scale.set(0.72, 0.72, 0.72);
          cone2.castShadow = true;
          staticG.add(cone2);
        } else if (t === TILE.ICE) {
          const m = new THREE.Mesh(geoPlane, iceMat);
          m.rotation.x = -Math.PI / 2;
          m.position.set(x, 0.035, z);
          m.scale.set(0.99, 0.99, 1);
          m.receiveShadow = true;
          staticG.add(m);
        } else if (t === TILE.EAGLE) {
          buildEagle(x, z);
        }
      }
    }
  }

  function addBlock(r, c, t, x, z) {
    const m = new THREE.Mesh(geoBox, t === TILE.BRICK ? brickMat : steelMat);
    const h = t === TILE.BRICK ? 0.7 : 0.8;
    m.scale.set(0.96, h, 0.96);
    m.position.set(x, h / 2, z);
    m.castShadow = true;
    m.receiveShadow = true;
    staticG.add(m);
    blockMeshes.set(r * 100 + c, m);
  }

  function buildEagle(x, z) {
    const g = new THREE.Group();
    const base = new THREE.Mesh(geoEagleBase, plinthMat);
    base.position.y = 0.06;
    base.castShadow = true;
    base.receiveShadow = true;
    g.add(base);

    const step = new THREE.Mesh(geoEagleStep, plinthMat);
    step.position.y = 0.16;
    step.castShadow = true;
    step.receiveShadow = true;
    g.add(step);

    const band = new THREE.Mesh(geoEagleBand, goldMat);
    band.position.y = 0.225;
    band.castShadow = true;
    g.add(band);

    const body = new THREE.Mesh(geoEagleBody, eagleMat);
    body.position.y = 0.57;
    body.scale.set(0.62, 0.45, 1.5);
    body.castShadow = true;
    g.add(body);

    const neck = new THREE.Mesh(geoBox, eagleMat);
    neck.scale.set(0.13, 0.2, 0.18);
    neck.position.set(0, 0.68, 0.12);
    neck.rotation.x = -0.25;
    g.add(neck);

    const head = new THREE.Mesh(geoEagleHead, goldMat);
    head.position.set(0, 0.78, 0.15);
    head.scale.set(0.85, 0.85, 0.95);
    head.castShadow = true;
    g.add(head);

    const beak = new THREE.Mesh(geoTree, goldMat);
    beak.scale.set(0.08, 0.16, 0.08);
    beak.rotation.x = Math.PI / 2;
    beak.position.set(0, 0.76, 0.25);
    g.add(beak);

    const tail = new THREE.Mesh(geoBox, wingMat);
    tail.scale.set(0.3, 0.035, 0.26);
    tail.position.set(0, 0.6, -0.3);
    tail.rotation.x = 0.18;
    g.add(tail);

    for (const s of [-1, 1]) {
      for (let k = 0; k < 3; k++) {
        const feather = new THREE.Mesh(geoBox, k === 2 ? goldMat : wingMat);
        feather.scale.set(0.5, 0.04, 0.19);
        feather.position.set(s * (0.3 + k * 0.17), 0.7 - k * 0.012, -0.02 - k * 0.07);
        feather.rotation.y = s * (-0.14 - k * 0.16);
        feather.rotation.z = s * (0.02 + k * 0.02);
        feather.castShadow = true;
        g.add(feather);
      }
      const wing = new THREE.Mesh(geoBox, wingMat);
      wing.scale.set(0.72, 0.055, 0.26);
      wing.position.set(s * 0.38, 0.72, 0.06);
      wing.rotation.y = s * 0.22;
      wing.rotation.z = s * -0.03;
      wing.castShadow = true;
      g.add(wing);
    }

    eagleGlow = new THREE.Sprite(eagleGlowMat);
    eagleGlow.position.set(0, 0.6, 0);
    eagleGlow.scale.setScalar(1.7);
    g.add(eagleGlow);

    g.position.set(x, 0, z + 0.22);
    g.scale.setScalar(1.05);
    staticG.add(g);
  }

  /** React to a core `tileChanged` event. Never mutates core state. */
  function tileChanged(r, c, tile, previous) {
    const key = r * 100 + c;
    const mesh = blockMeshes.get(key);
    const x = cx(c);
    const z = cz(r);

    if (tile === TILE.EMPTY) {
      if (mesh) {
        staticG.remove(mesh);
        blockMeshes.delete(key);
      }
      spawnDebris(x, z, previous === TILE.STEEL);
      for (let i = 0; i < 4; i++) {
        fx.dustPuff(x + (Math.random() - 0.5) * 0.8, z + (Math.random() - 0.5) * 0.8);
      }
      fx.addScorch(x, z, 0.55);
      return;
    }

    if (tile === TILE.BRICK || tile === TILE.STEEL) {
      if (mesh) {
        mesh.material = tile === TILE.BRICK ? brickMat : steelMat;
        const h = tile === TILE.BRICK ? 0.7 : 0.8;
        mesh.scale.y = h;
        mesh.position.y = h / 2;
      } else {
        addBlock(r, c, tile, x, z);
      }
    }
  }

  function spawnDebris(x, z, steel) {
    const group = new THREE.Group();
    const parts = [];
    for (let i = 0; i < 8; i++) {
      const p = new THREE.Mesh(geoDeb, steel ? debrisSteelMat : debrisMat);
      group.add(p);
      parts.push(new THREE.Vector3((Math.random() - 0.5) * 3, 1.5 + Math.random() * 2.5, (Math.random() - 0.5) * 3));
    }
    group.position.set(x, 0.4, z);
    const start = performance.now();
    // Re-use the FX pump through a tiny local tween stored on the group.
    group.userData.tick = (dt) => {
      const t = (performance.now() - start) / 1000;
      group.children.forEach((p, i) => {
        const v = parts[i];
        v.y -= 10 * dt;
        p.position.addScaledVector(v, dt);
        p.rotation.x += dt * 7;
        p.rotation.z += dt * 5;
        if (p.position.y < 0.05) p.position.y = 0.05;
      });
      if (t > 0.65) {
        staticG.remove(group);
        return false;
      }
      return true;
    };
    staticG.add(group);
    debrisGroups.push(group);
  }

  const debrisGroups = [];

  function update(dt, time) {
    for (let i = waters.length - 1; i >= 0; i--) {
      const w = waters[i];
      w.position.y = w.userData.baseY + Math.sin(time * 1.7 + w.userData.ph) * 0.012;
    }
    textures.waterNormal.offset.x = (time * 0.014) % 1;
    textures.waterNormal.offset.y = (time * 0.009) % 1;
    if (eagleGlow) eagleGlow.material.opacity = 0.18 + Math.sin(time * 1.4) * 0.04;
    for (let i = debrisGroups.length - 1; i >= 0; i--) {
      if (!debrisGroups[i].userData.tick(dt)) debrisGroups.splice(i, 1);
    }
  }

  function clear() {
    while (staticG.children.length) staticG.remove(staticG.children[0]);
    blockMeshes.clear();
    waters.length = 0;
    debrisGroups.length = 0;
    eagleGlow = null;
    levelRef = null;
  }

  return { build, tileChanged, update, clear, blockMeshes };
}
