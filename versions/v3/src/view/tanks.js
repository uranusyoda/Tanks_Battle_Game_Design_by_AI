// Bridges simulation state to tank rigs. It creates, poses and removes models,
// but never computes damage, cooldowns or win conditions.

import * as THREE from 'three';
import { createTankRig } from '../assets/tankRig.js';
import { VIEW_TUNING } from '../content/assets.js';

export function createTankLayer({ scene, models, shadowTex }) {
  const rigs = new Map(); // id -> view
  let showcase = null;
  let showcaseLights = [];

  function entryFor(lod) {
    return (
      models.get(lod === 'hero' ? 'sherman_hero' : 'sherman_troop') ||
      models.get('sherman_hero') ||
      models.get('sherman_troop')
    );
  }

  function createView(id, { paint, lod = 'hero', scale = 1 }) {
    const entry = entryFor(lod);
    if (!entry) throw new Error('No tank model loaded');
    const rig = createTankRig(entry, { paint });
    const container = new THREE.Group();
    const baseScale = (entry.def.scale || 0.2) * scale;
    rig.model.scale.setScalar(baseScale);
    container.add(rig.model);

    const shadow = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 1),
      new THREE.MeshBasicMaterial({
        map: shadowTex,
        color: 0x000000,
        transparent: true,
        opacity: VIEW_TUNING.shadow.opacity,
        depthWrite: false,
      }),
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = 0.018;
    shadow.scale.set(VIEW_TUNING.shadow.width * scale, VIEW_TUNING.shadow.length * scale, 1);
    shadow.renderOrder = 2;
    container.add(shadow);

    scene.add(container);
    const view = { id, rig, container, shadow, baseScale, scale };
    rigs.set(id, view);
    return view;
  }

  function removeView(id) {
    const view = rigs.get(id);
    if (!view) return;
    scene.remove(view.container);
    view.rig.dispose();
    view.shadow.material.dispose();
    rigs.delete(id);
  }

  function poseTank(view, t, dt, time) {
    view.container.position.set(t.x, 0, t.z);
    view.container.rotation.y = t.heading;
    view.rig.model.scale.setScalar(view.baseScale * (view.spawnProgress ?? 1));
    view.rig.setTurret(t.turretYaw);
    view.rig.update(dt);
  }

  function syncPlayer(state, dt, time) {
    const p = state.player;
    let view = rigs.get('player');
    if (!view || view.specId !== p.spec.id) {
      if (view) removeView('player');
      view = createView('player', { paint: p.spec.paint, lod: p.spec.model?.lod || 'hero', scale: 1 });
      view.specId = p.spec.id;
    }
    view.container.visible = p.alive && (p.invuln > 0 ? Math.floor(time * 12) % 2 === 0 : true);
    if (!p.alive) return view;

    poseTank(view, p, dt, time);
    view.rig.setDriveSpeed(p.moving ? p.speed : 0);
    view.rig.setOpacity(1);
    view.rig.setFlash('none');
    return view;
  }

  function syncEnemies(state, dt, time) {
    const live = new Set();
    for (const e of state.enemies) {
      live.add(e.id);
      let view = rigs.get(e.id);
      if (!view) {
        view = createView(e.id, { paint: e.prof.paint, lod: 'troop', scale: e.scale });
        view.spawnProgress = 0;
      }
      view.spawnProgress = Math.min(1, e.spawnTimer / 0.5);
      poseTank(view, e, dt, time);
      view.rig.setDriveSpeed(e.moving && e.freezeTimer <= 0 ? e.prof.speed : 0);
      // Forest concealment is presentation; the core already handles detection.
      const hidden = e.inForest && state.player.spec.id !== 't90';
      view.rig.setOpacity(hidden ? 0.22 : 1);
      view.rig.setFlash(e.hitFlash > 0 ? 'hit' : e.freezeTimer > 0 ? 'frozen' : 'none');
      const op = hidden ? 0.22 : 1;
      view.shadow.material.opacity = VIEW_TUNING.shadow.opacity * op;
    }
    for (const id of [...rigs.keys()]) {
      if (id !== 'player' && !live.has(id)) removeView(id);
    }
  }

  function sync(state, dt, time) {
    syncPlayer(state, dt, time);
    syncEnemies(state, dt, time);
  }

  function fire(id) {
    const view = rigs.get(id);
    if (view) view.rig.fire();
  }

  const muzzleOut = new THREE.Vector3();

  /** Returns a world position snapshot; accepts a plain {x,y,z} target. */
  function getMuzzle(id, target) {
    const view = rigs.get(id);
    if (!view) return null;
    view.rig.getMuzzleWorldPosition(muzzleOut);
    if (target) {
      target.x = muzzleOut.x;
      target.y = muzzleOut.y;
      target.z = muzzleOut.z;
      return target;
    }
    return muzzleOut;
  }

  // --------------------------------------------------------------- showcase
  function showShowcase(spec) {
    clear();
    const view = createView('showcase', { paint: spec.paint, lod: 'hero', scale: 1 });
    view.container.position.set(0, 0.12, 1.6);
    view.container.rotation.y = 0.55;

    const plinth = new THREE.Mesh(
      new THREE.CylinderGeometry(0.82, 0.9, 0.12, 40),
      new THREE.MeshStandardMaterial({ color: 0x2e2f33, roughness: 0.8, metalness: 0.05, envMapIntensity: 0.45 }),
    );
    plinth.position.y = -0.06;
    plinth.receiveShadow = true;
    view.container.add(plinth);

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.74, 0.02, 8, 48),
      new THREE.MeshStandardMaterial({ color: 0xffc73f, metalness: 0.6, roughness: 0.3, envMapIntensity: 1.1 }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.002;
    view.container.add(ring);

    const key = new THREE.PointLight(0xffe2b4, 20, 10, 2);
    key.position.set(2.2, 3.8, 5.0);
    scene.add(key);
    showcaseLights = [key];

    view.shadow.visible = false; // the directional light casts the real shadow
    showcase = view;
  }

  function updateShowcase(dt, time) {
    if (!showcase) return;
    showcase.container.rotation.y = 0.55 + Math.sin(time * 0.28) * 0.45;
    showcase.rig.setTurret(Math.sin(time * 0.55) * 0.55);
    showcase.rig.setDriveSpeed(0);
    showcase.rig.update(dt);
  }

  function clear() {
    for (const id of [...rigs.keys()]) removeView(id);
    for (const light of showcaseLights) scene.remove(light);
    showcaseLights = [];
    showcase = null;
  }

  return { sync, fire, getMuzzle, showShowcase, updateShowcase, clear, rigs };
}
