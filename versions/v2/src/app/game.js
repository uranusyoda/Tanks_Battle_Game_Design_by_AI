// Composition root for one play session. It wires intents -> rules -> events ->
// view. This is the only file that knows about all the layers at once.

import { createBattle } from '../core/battle.js';
import { TANKS } from '../content/tanks.js';
import { ENEMY_TYPES } from '../content/enemies.js';
import { LEVEL, SHOWROOM } from '../content/levels.js';
import { POWERUPS } from '../content/powerups.js';
import { unlockAudio, sfx } from '../platform/audio.js';
import { loadHighScore, saveHighScore } from '../platform/storage.js';

const MODE = Object.freeze({ GARAGE: 'garage', BATTLE: 'battle', OVER: 'over' });

export function createGame({ stage, world, fx, tanks, projectiles, hud, camera, input }) {
  let mode = MODE.GARAGE;
  let battle = null;
  let state = null;
  const aim = { x: 0, z: 3 };

  function showGarage() {
    mode = MODE.GARAGE;
    battle = null;
    state = null;
    world.build(SHOWROOM);
    fx.clear();
    projectiles.clear();
    tanks.showShowcase(TANKS.sherman);
    hud.showGarage();
    hud.setHighScore(loadHighScore());
    unlockAudio();
  }

  function startBattle(tankId) {
    const spec = TANKS[tankId];
    if (!spec) return;
    unlockAudio();
    world.build(LEVEL);
    fx.clear();
    projectiles.clear();
    tanks.clear();
    battle = createBattle({
      tankId,
      tanks: TANKS,
      enemyTypes: ENEMY_TYPES,
      level: LEVEL,
      powerups: POWERUPS,
      seed: (Date.now() ^ (Math.random() * 0xffffffff)) >>> 0,
    });
    state = battle.state;
    window.__battle = battle; // debug/testing hook
    hud.hide();
    hud.initIcons(state.totalEnemies);
    hud.flash('守住鹰徽 · 消灭全部敌军');
    mode = MODE.BATTLE;
    camera.updateBattle(state, 1); // snap the chase camera to the spawn
  }

  // ------------------------------------------------------------------ events
  const muzzle = { x: 0, y: 0, z: 0 };

  function handleEvent(event) {
    switch (event.type) {
      case 'fire': {
        sfx('fire');
        tanks.fire(event.shooterId);
        const m = tanks.getMuzzle(event.shooterId, muzzle);
        if (m) {
          fx.flash(m.x, m.y, m.z, event.ap ? 0xffe8a8 : 0xffd48a, 0.5, 0.12);
          fx.muzzleSmoke(m.x, m.z);
        } else {
          fx.flash(event.x, 0.66, event.z, 0xffd48a, 0.45, 0.12);
          fx.muzzleSmoke(event.x, event.z);
        }
        break;
      }
      case 'explosion':
        sfx('boom');
        fx.explosion(event.x, event.z, event.scale);
        break;
      case 'impact':
        fx.spark(event.x, event.z);
        break;
      case 'spark':
        fx.spark(event.x, event.z);
        break;
      case 'tileChanged':
        world.tileChanged(event.r, event.c, event.tile, event.previous);
        break;
      case 'spawn':
        fx.spawnFx(event.x, event.z);
        break;
      case 'respawn':
        fx.spawnFx(event.x, event.z);
        break;
      case 'pickupDropped':
        fx.flash(event.x, 0.7, event.z, event.color, 0.5, 0.3);
        break;
      case 'pickup':
        sfx('pick');
        fx.flash(state.player.x, 0.8, state.player.z, 0xfff0b0, 0.7, 0.35);
        break;
      case 'playerHit':
        camera.addShake(0.18);
        fx.flash(event.x, 0.7, event.z, 0xffaa66, 0.4, 0.15);
        break;
      case 'shieldBlock':
        fx.flash(event.x, 0.6, event.z, 0x6f9fe8, 0.8, 0.2);
        break;
      case 'reactiveBlock':
        fx.flash(event.x, 0.6, event.z, 0xff8844, 0.7, 0.25);
        break;
      case 'skill':
        if (event.kind === 'smoke') fx.smokeCloud(event.x, event.z);
        if (event.kind === 'reactive') fx.flash(event.x, 0.7, event.z, 0xff8844, 0.9, 0.4);
        if (event.kind === 'ap') fx.flash(event.x, 0.8, event.z, 0xffe8a8, 0.6, 0.3);
        break;
      case 'message':
        hud.flash(event.text);
        break;
      case 'gameover': {
        const hi = Math.max(loadHighScore(), state.score);
        saveHighScore(state.score);
        hud.setHighScore(hi);
        hud.showGameOver({ win: event.win, reason: event.reason, score: state.score, hi });
        mode = MODE.OVER;
        battle.commands.stop();
        break;
      }
      default:
        break;
    }
  }

  // ------------------------------------------------------------------- input
  function readInput() {
    const keys = input.keys;
    const throttle = (keys.KeyW ? 1 : 0) - (keys.KeyS ? 1 : 0);
    const turn = (keys.KeyA ? 1 : 0) - (keys.KeyD ? 1 : 0);
    battle.commands.setMove(throttle, turn);
    battle.commands.setTrigger(!!(keys.Space || input.isMouseDown()));
    if (stage.pickGround(input.mouseNdc, aim)) battle.commands.aimAt(aim.x, aim.z);
  }

  input.onKey('KeyE', () => {
    if (mode === MODE.BATTLE && battle) battle.commands.useSkill();
  });
  input.onKey('KeyC', () => {
    if (mode === MODE.BATTLE || mode === MODE.OVER) camera.toggleMode();
  });
  input.onKey('KeyR', () => {
    if (mode !== MODE.GARAGE) showGarage();
  });

  hud.onPick((tankId) => startBattle(tankId));
  hud.onGarage(() => showGarage());

  // ------------------------------------------------------------------- frame
  function update(dt, time) {
    stage.update(dt, time);

    if (mode === MODE.GARAGE) {
      tanks.updateShowcase(dt, time);
      fx.update(dt, time);
      camera.updateGarage(time);
      hud.update(null, dt);
      return;
    }

    if (mode === MODE.BATTLE) {
      readInput();
      battle.update(dt);
      for (const event of battle.drainEvents()) handleEvent(event);
      tanks.sync(state, dt, time);
      projectiles.sync(state.bullets);
      fx.updateTreadMarks(dt, state.player);
      fx.syncPickups(state.pickups, time, dt);
      fx.syncShield(state.player, time);
      hud.update(state, dt);
    } else {
      // Game over: let explosions and particles finish, keep the camera put.
      tanks.sync(state, dt, time);
      projectiles.sync(state.bullets);
      fx.syncPickups(state.pickups, time, dt);
      fx.syncShield(state.player, time);
      hud.update(null, dt);
    }

    world.update(dt, time);
    fx.update(dt, time);
    camera.updateBattle(state, dt);
  }

  function render() {
    stage.render();
  }

  return { startBattle, showGarage, update, render, get mode() { return mode; }, get state() { return state; } };
}
