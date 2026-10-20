// Visible shells. Their position and lifetime come from the rules core; this
// layer only draws them.

import * as THREE from 'three';

export function createProjectileLayer({ scene, textures }) {
  const geo = new THREE.SphereGeometry(0.085, 10, 8);
  const playerMat = new THREE.MeshBasicMaterial({ color: 0xffe8a8, toneMapped: false });
  const enemyMat = new THREE.MeshBasicMaterial({ color: 0xff9a70, toneMapped: false });
  const views = new Map();

  function sync(bullets) {
    const live = new Set();
    for (const bullet of bullets) {
      live.add(bullet.id);
      let view = views.get(bullet.id);
      if (!view) {
        const mesh = new THREE.Mesh(geo, bullet.from === 'enemy' ? enemyMat : playerMat);
        const glow = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: textures.glowTex,
            color: bullet.from === 'enemy' ? 0xff8a60 : 0xffdc90,
            blending: THREE.AdditiveBlending,
            transparent: true,
            depthWrite: false,
            opacity: 0.95,
          }),
        );
        glow.scale.setScalar(0.5);
        mesh.add(glow);
        scene.add(mesh);
        view = { mesh };
        views.set(bullet.id, view);
      }
      view.mesh.position.set(bullet.x, 0.52, bullet.z);
    }
    for (const [id, view] of views) {
      if (live.has(id)) continue;
      view.mesh.children.forEach((child) => {
        if (child.isSprite) child.material.dispose();
      });
      scene.remove(view.mesh);
      views.delete(id);
    }
  }

  function clear() {
    for (const [id, view] of views) {
      view.mesh.children.forEach((child) => {
        if (child.isSprite) child.material.dispose();
      });
      scene.remove(view.mesh);
      views.delete(id);
    }
  }

  return { sync, clear };
}
