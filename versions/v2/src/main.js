// Boot: create the presentation layer, load assets, wire the game, run frames.

import { createStage } from './view/stage.js';
import { createWorld } from './view/world.js';
import { createFx } from './view/fx.js';
import { createTankLayer } from './view/tanks.js';
import { createProjectileLayer } from './view/projectiles.js';
import { createHud } from './view/hud.js';
import { createCameraRig } from './view/camera.js';
import { createInput } from './platform/input.js';
import { loadHighScore } from './platform/storage.js';
import { loadModelAssets } from './assets/modelStore.js';
import { createGame } from './app/game.js';
import { TANKS } from './content/tanks.js';

async function boot() {
  const canvas = document.getElementById('c');
  const hud = createHud({ tanks: TANKS });
  hud.showLoading('正在装载 M4A1 Sherman…');
  hud.setHighScore(loadHighScore());

  // Let the loading panel paint before the procedural texture pass blocks.
  await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 30)));

  const stage = createStage(canvas);

  // FX needs the camera for shake; wire the sink after both exist.
  const shakeSink = { add: () => {} };
  const fx = createFx({
    scene: stage.scene,
    textures: stage.fxTextures,
    onShake: (amount) => shakeSink.add(amount),
  });
  const world = createWorld({ scene: stage.scene, textures: stage.surfaceTextures, fx });

  hud.showLoading('正在装载 M4A1 Sherman…');
  const { models, failures } = await loadModelAssets();
  if (failures.length) console.warn('[boot] asset failures', failures);

  const tanks = createTankLayer({ scene: stage.scene, models, shadowTex: stage.fxTextures.shadowTex });
  const projectiles = createProjectileLayer({ scene: stage.scene, textures: stage.fxTextures });
  const camera = createCameraRig(stage.camera);
  shakeSink.add = (amount) => camera.addShake(amount);
  const input = createInput(canvas);

  const game = createGame({ stage, world, fx, tanks, projectiles, hud, camera, input });
  game.showGarage();

  // Debug/testing hooks. The production game never reads these.
  window.__game = game;
  window.__stage = stage;
  window.__models = models;
  window.__tanks = tanks;
  window.__projectiles = projectiles;
  window.__world = world;
  window.__fx = fx;
  window.__camera = camera;

  const params = new URLSearchParams(location.search);
  const autoTank = params.get('tank');
  if (autoTank && TANKS[autoTank]) {
    setTimeout(() => game.startBattle(autoTank), 250);
  }

  let last = performance.now();
  let elapsed = 0;
  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    elapsed += dt;
    game.update(dt, elapsed);
    game.render();
  }
  requestAnimationFrame(frame);
}

boot().catch((error) => {
  console.error(error);
  const overlay = document.getElementById('overlay');
  if (overlay) {
    overlay.style.display = 'flex';
    overlay.innerHTML = `<div class="panel"><h1>装载失败</h1>
      <div class="sub">${String(error.message || error)}<br>请通过本地 HTTP 服务打开（不要直接双击 HTML）。</div></div>`;
  }
});
