// Camera rig. Reads the player position/heading for framing and owns only
// presentation concerns (lerp, shake, garage orbit).

import * as THREE from 'three';

export function createCameraRig(camera) {
  const camPos = new THREE.Vector3(0, 10, 10);
  const desired = new THREE.Vector3();
  const look = new THREE.Vector3();
  let mode = 'chase';
  let shake = 0;
  let frozen = false;

  function toggleMode() {
    mode = mode === 'chase' ? 'top' : 'chase';
    return mode;
  }

  function addShake(amount) {
    shake = Math.max(shake, amount);
  }

  function updateGarage(time) {
    if (frozen) return;
    const a = time * 0.16;
    const cx = 0;
    const cz = 1.6;
    camera.position.set(cx + Math.sin(a) * 4.3, 2.7, cz + Math.cos(a) * 4.3);
    // Look a little left of the tank so it sits on the right, clear of the
    // garage cards.
    camera.lookAt(cx - 0.75, 0.78, cz);
    camPos.copy(camera.position);
  }

  function updateBattle(state, dt) {
    if (frozen) return;
    const p = state.player;
    const k = 1 - Math.exp(-6 * dt);
    if (mode === 'chase') {
      const fx = Math.sin(p.heading);
      const fz = Math.cos(p.heading);
      // Slight over-the-shoulder offset so the eagle monument at the spawn
      // does not sit directly between the camera and the player's tank.
      const sx = Math.cos(p.heading);
      const sz = -Math.sin(p.heading);
      desired.set(p.x - fx * 5.8 + sx * 1.35, 4.8, p.z - fz * 5.8 + sz * 1.35);
      camPos.lerp(desired, k);
      camera.position.copy(camPos);
      if (shake > 0) {
        shake -= dt;
        camera.position.x += (Math.random() - 0.5) * shake * 0.9;
        camera.position.y += (Math.random() - 0.5) * shake * 0.5;
        camera.position.z += (Math.random() - 0.5) * shake * 0.9;
      }
      look.set(p.x + fx * 4.2, 1.0, p.z + fz * 4.2);
      camera.lookAt(look);
    } else {
      desired.set(p.x, 14.5, p.z + 4.5);
      camPos.lerp(desired, k);
      camera.position.copy(camPos);
      camera.lookAt(p.x, 0, p.z - 0.8);
    }
    shake = Math.max(0, shake - dt);
  }

  return {
    toggleMode,
    addShake,
    updateGarage,
    updateBattle,
    freeze() {
      frozen = true;
    },
    unfreeze() {
      frozen = false;
    },
    get mode() {
      return mode;
    },
  };
}
