// Turns a loaded glTF into a game-ready tank rig: named turret/gun/muzzle
// nodes, a drive loop, a one-shot recoil, per-instance paint and opacity.
// Presentation only — speed and turret angles are inputs supplied by the view.

import * as THREE from 'three';
import { VIEW_TUNING } from '../content/assets.js';

const PAINT_MATERIALS = {
  Sherman_Olive: 'olive',
  Sherman_OliveDark: 'oliveDark',
  Sherman_Star: 'star',
};

const NO_CAST_SHADOW = /^(AnimLink_|Tire_|Hub_|HubCap_|Sprocket_|Idler_|Roller_|RunningGear_|Track_)/;

/**
 * @param {{gltf: import('three').GLTF, def: object}} entry
 * @param {{paint?: object}} options
 */
export function createTankRig(entry, { paint = {} } = {}) {
  const { gltf, def } = entry;
  const model = gltf.scene.clone(true);

  const materials = new Set();
  model.traverse((obj) => {
    if (!obj.isMesh) return;
    // Track links and wheels are small; skip their shadow casting to keep the
    // shadow pass cheap. The hull still casts the tank's silhouette.
    obj.castShadow = !NO_CAST_SHADOW.test(obj.name);
    obj.receiveShadow = true;

    const source = Array.isArray(obj.material) ? obj.material : [obj.material];
    const cloned = source.map((mat) => {
      if (!mat) return mat;
      const copy = mat.clone();
      copy.name = mat.name;
      copy.userData.baseColor = copy.color.clone();
      copy.userData.baseEmissive = copy.emissive ? copy.emissive.clone() : null;
      const key = PAINT_MATERIALS[mat.name];
      if (key && paint[key] !== undefined) copy.color.setHex(paint[key]);
      copy.userData.baseColor = copy.color.clone();
      if (key) copy.envMapIntensity = 0.55;
      materials.add(copy);
      return copy;
    });
    obj.material = Array.isArray(obj.material) ? cloned : cloned[0];
  });

  const turret = model.getObjectByName(def.tags.turret) || null;
  const gun = model.getObjectByName(def.tags.gun) || null;
  const muzzle = model.getObjectByName(def.tags.muzzle) || null;

  const mixer = new THREE.AnimationMixer(model);
  const driveClip = def.clips.drive
    ? THREE.AnimationClip.findByName(gltf.animations || [], def.clips.drive)
    : null;
  const fireClip = def.clips.fire
    ? THREE.AnimationClip.findByName(gltf.animations || [], def.clips.fire)
    : null;

  let driveAction = null;
  if (driveClip) {
    driveAction = mixer.clipAction(driveClip);
    driveAction.setLoop(THREE.LoopRepeat, Infinity);
    driveAction.play();
    driveAction.timeScale = 0;
  }

  let fireAction = null;
  if (fireClip) {
    fireAction = mixer.clipAction(fireClip);
    fireAction.setLoop(THREE.LoopOnce, 1);
    fireAction.clampWhenFinished = true;
  }

  let opacity = 1;
  let flashKind = 'none';
  const muzzleWorld = new THREE.Vector3();

  const rig = {
    model,
    turret,
    gun,
    muzzle,
    materials: [...materials],
    hasDrive: !!driveAction,
    hasFire: !!fireAction,

    setTurret(yaw) {
      if (turret) turret.rotation.y = yaw;
    },

    setGunPitch(pitch) {
      if (gun) gun.rotation.x = pitch;
    },

    /** speed is signed world units per second. */
    setDriveSpeed(speed) {
      if (!driveAction) return;
      const magnitude = Math.abs(speed) < 0.05 ? 0 : Math.abs(speed) * VIEW_TUNING.treadRate;
      driveAction.timeScale = Math.sign(speed) * Math.min(magnitude, 2.4);
    },

    fire() {
      if (!fireAction) return;
      fireAction.reset();
      fireAction.play();
    },

    update(dt) {
      mixer.update(dt);
    },

    setOpacity(value) {
      if (Math.abs(value - opacity) < 0.01) return;
      opacity = value;
      for (const mat of materials) {
        mat.transparent = value < 0.999;
        mat.opacity = value;
        mat.depthWrite = value > 0.8;
      }
    },

    setFlash(kind) {
      if (kind === flashKind) return;
      flashKind = kind;
      for (const mat of materials) {
        if (!mat.emissive) continue;
        if (kind === 'hit') {
          mat.emissive.setHex(0x883311);
          mat.emissiveIntensity = 1.0;
        } else if (kind === 'frozen') {
          mat.emissive.setHex(0x114466);
          mat.emissiveIntensity = 1.2;
        } else if (mat.userData.baseEmissive) {
          mat.emissive.copy(mat.userData.baseEmissive);
          mat.emissiveIntensity = 1.0;
        } else {
          mat.emissive.setHex(0x000000);
        }
      }
    },

    getMuzzleWorldPosition(target = muzzleWorld) {
      if (muzzle) {
        muzzle.getWorldPosition(target);
      } else {
        model.getWorldPosition(target);
        target.y += 0.55;
      }
      return target;
    },

    dispose() {
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      for (const mat of materials) mat.dispose();
    },
  };

  return rig;
}
