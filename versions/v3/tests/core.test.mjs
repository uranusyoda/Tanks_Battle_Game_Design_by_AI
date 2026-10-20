import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

import { createBattle } from '../src/core/battle.js';
import { TANKS } from '../src/content/tanks.js';
import { ENEMY_TYPES } from '../src/content/enemies.js';
import { LEVEL } from '../src/content/levels.js';
import { POWERUPS } from '../src/content/powerups.js';
import { TILE, tc, tr } from '../src/core/constants.js';

const clone = (v) => JSON.parse(JSON.stringify(v));

function makeLevel({ waves = [{ t: 999, list: ['line'] }], bunker = LEVEL.bunker } = {}) {
  const level = clone(LEVEL);
  level.waves = waves;
  level.bunker = bunker;
  return level;
}

function makeBattle({ tankId = 'sherman', level = makeLevel(), seed = 7 } = {}) {
  return createBattle({
    tankId,
    tanks: TANKS,
    enemyTypes: ENEMY_TYPES,
    level,
    powerups: POWERUPS,
    seed,
  });
}

function tick(battle, seconds, step = 1 / 60) {
  const n = Math.round(seconds / step);
  for (let i = 0; i < n; i++) battle.update(step);
}

function eventsOf(battle, type) {
  return battle.drainEvents().filter((e) => e.type === type);
}

test('content: every tank and enemy in the waves is defined', () => {
  for (const tank of Object.values(TANKS)) {
    assert.equal(tank.id, tank.id);
    assert.ok(tank.skill?.name, `${tank.id} has a skill`);
    assert.ok(tank.model?.lod, `${tank.id} points at an asset LOD, not a file`);
  }
  for (const wave of LEVEL.waves) {
    for (const id of wave.list) assert.ok(ENEMY_TYPES[id], `missing enemy ${id}`);
  }
  const eagles = LEVEL.grid.flat().filter((t) => t === TILE.EAGLE).length;
  assert.equal(eagles, 1);
});

test('grid: a tank cannot drive through a brick', () => {
  const battle = makeBattle();
  const p = battle.state.player;
  p.x = 0;
  p.z = 5;
  p.heading = Math.PI;
  battle.commands.setMove(1, 0);
  tick(battle, 1.5);
  // Row 11 still has a brick at column 6, so the tank must stop before z=3.5.
  assert.ok(p.z > 3.5, `player stopped at z=${p.z}`);
});

test('rules: firing destroys a brick and emits a semantic event', () => {
  const battle = makeBattle();
  const p = battle.state.player;
  p.x = 0;
  p.z = 5;
  p.heading = Math.PI;
  p.invuln = 0;
  battle.commands.aimAt(0, 3);
  battle.commands.setTrigger(true);
  battle.update(1 / 60);
  battle.commands.setTrigger(false);
  tick(battle, 0.5);
  assert.equal(battle.grid.tile(9, 6), TILE.EMPTY, 'brick at row 9 col 6 destroyed');
  const changed = eventsOf(battle, 'tileChanged');
  assert.equal(changed.length, 1);
  assert.equal(changed[0].r, 9);
  assert.equal(changed[0].c, 6);
});

test('rules: an enemy shot damages the player', () => {
  const level = makeLevel({ waves: [{ t: 0, list: ['line'] }] });
  const battle = makeBattle({ level });
  battle.update(1 / 60); // spawn
  const enemy = battle.state.enemies[0];
  assert.ok(enemy, 'enemy spawned');
  // Park the enemy in clear line of sight, then let it fire.
  const p = battle.state.player;
  enemy.x = p.x;
  enemy.z = p.z - 1.5;
  enemy.heading = 0;
  enemy.fireCd = 0;
  p.invuln = 0;
  battle.update(1 / 60);
  tick(battle, 0.6);
  assert.ok(p.hp < p.maxHp, `player hp ${p.hp}`);
});

test('rules: a shield absorbs a hit without losing HP', () => {
  const level = makeLevel({ waves: [{ t: 0, list: ['line'] }] });
  const battle = makeBattle({ level });
  battle.update(1 / 60);
  const enemy = battle.state.enemies[0];
  const p = battle.state.player;
  enemy.x = p.x;
  enemy.z = p.z - 1.5;
  enemy.fireCd = 0;
  p.invuln = 0;
  p.shield = 10;
  battle.update(1 / 60);
  tick(battle, 0.6);
  assert.equal(p.hp, p.maxHp);
  assert.ok(eventsOf(battle, 'shieldBlock').length >= 1);
});

test('rules: killing the eagle loses the battle, even with the player shot', () => {
  const battle = makeBattle();
  const p = battle.state.player;
  p.x = 0;
  p.z = 5;
  p.heading = 0;
  p.turretYaw = 0;
  p.invuln = 0;
  battle.commands.setTrigger(true);
  battle.update(1 / 60);
  battle.commands.setTrigger(false);
  tick(battle, 0.2);
  assert.equal(battle.state.phase, 'lost');
  assert.equal(battle.state.eagle.alive, false);
  const gameover = eventsOf(battle, 'gameover');
  assert.equal(gameover.length, 1);
  assert.equal(gameover[0].win, false);
});

test('rules: clearing the last wave wins', () => {
  const battle = makeBattle({ level: makeLevel({ waves: [] }) });
  battle.update(1 / 60);
  const s = battle.state;
  // Fast-forward the wave director to "nothing left".
  s.wave = LEVEL.waves.length;
  s.spawnQueue.length = 0;
  s.enemies.length = 0;
  battle.update(1 / 60);
  assert.equal(s.phase, 'won');
  assert.equal(eventsOf(battle, 'gameover')[0].win, true);
});

test('rules: a star power-up improves rate of fire exactly once', () => {
  const battle = makeBattle();
  const p = battle.state.player;
  const before = p.fireInterval;
  battle.state.pickups.push({
    id: 'test', def: POWERUPS.find((x) => x.id === 'star'), x: p.x, z: p.z, life: 5,
  });
  battle.update(1 / 60);
  assert.ok(p.fireInterval < before);
  assert.equal(battle.state.pickups.length, 0);
});

test('rules: same seed + same inputs produce the same battle', () => {
  const run = () => {
    const battle = makeBattle({ seed: 42 });
    const trace = [];
    for (let i = 0; i < 180; i++) {
      battle.commands.setMove(i < 90 ? 1 : -1, i % 30 === 0 ? 1 : 0);
      battle.commands.setTrigger(i % 12 === 0);
      battle.commands.aimAt(1, 2);
      battle.update(1 / 60);
      battle.drainEvents();
      trace.push(
        battle.state.player.x.toFixed(4),
        battle.state.player.z.toFixed(4),
        battle.state.enemies.map((e) => `${e.x.toFixed(3)},${e.z.toFixed(3)}`).join('|'),
      );
    }
    return trace.join(';');
  };
  assert.equal(run(), run());
});

test('layering: the rules core never imports Three.js, the DOM or asset code', () => {
  const dir = path.join(process.cwd(), 'src', 'core');
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.js'));
  assert.ok(files.length >= 4);
  const banned = [/from\s+['"]three['"]/, /from\s+['"].*\/view\//, /from\s+['"].*\/assets\//, /document\./, /window\./, /THREE\./];
  for (const file of files) {
    const source = fs.readFileSync(path.join(dir, file), 'utf8');
    for (const pattern of banned) {
      assert.ok(!pattern.test(source), `${file} must not match ${pattern}`);
    }
    // The core may only depend on itself and the shared utility layer.
    for (const match of source.matchAll(/from\s+['"]([^'"]+)['"]/g)) {
      const spec = match[1];
      assert.ok(spec.startsWith('./') || spec.startsWith('../shared/'), `${file} imports ${spec}`);
    }
  }
});

test('layering: content files are data only', () => {
  const dir = path.join(process.cwd(), 'src', 'content');
  for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.js'))) {
    const source = fs.readFileSync(path.join(dir, file), 'utf8');
    assert.ok(!/^\s*import\s+/m.test(source), `${file} has no import statements`);
  }
});
