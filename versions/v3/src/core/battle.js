import { TANK_R, BULLET_R, TILE, clamp, wrapAngle, tc, tr } from './constants.js';
import { createGrid } from './grid.js';
import { createRng } from './rng.js';

const PLAYER_SPAWN = { x: 0, z: 5, heading: Math.PI };
const ENEMY_BULLET_SPEED = 7.5;
const BULLET_LIFE = 2.6;
const ICE_ACCEL = 3;
const ENEMY_TURRET_SPEED = 4.0;

/**
 * Create one battle. Pure simulation: no DOM, no Three.js, no asset loading.
 * Dependencies (tank stats, enemy profiles, level, power-up table) are passed in
 * so content and rules stay separate.
 *
 * Read `state` for a snapshot, call the command methods for intents, and
 * `drainEvents()` for the semantic events the view may react to. Nothing in
 * the view is allowed to feed results back into this module.
 */
export function createBattle({
  tankId,
  tanks,
  enemyTypes,
  level,
  powerups,
  seed = 1,
  rng,
  startLives = 3,
}) {
  const rand = rng || createRng(seed);
  const grid = createGrid(level);
  const spec = tanks[tankId];
  if (!spec) throw new Error(`Unknown tank id: ${tankId}`);

  const events = [];
  const emit = (type, data = {}) => events.push({ type, ...data });

  const eagleTile = findEagle(level.grid);
  const state = {
    phase: 'battle', // battle | won | lost
    tankId,
    time: 0,
    score: 0,
    killed: 0,
    totalEnemies: level.waves.reduce((n, w) => n + w.list.length, 0),
    wave: 0,
    spawnQueue: [],
    spawnTimer: 0,
    spawnIndex: 0,
    respawnTimer: 0,
    skillCd: 0,
    fortTimer: 0,
    eagle: {
      r: eagleTile.r,
      c: eagleTile.c,
      x: eagleTile.c - 6,
      z: eagleTile.r - 6,
      alive: true,
    },
    player: {
      id: 'player',
      spec,
      x: PLAYER_SPAWN.x,
      z: PLAYER_SPAWN.z,
      heading: PLAYER_SPAWN.heading,
      turretYaw: 0,
      hp: spec.hp,
      maxHp: spec.hp,
      fireInterval: spec.fire,
      fireCd: 0,
      damage: spec.dmg,
      bulletSpeed: spec.bspd,
      lives: startLives,
      invuln: 2,
      shield: 0,
      smoke: 0,
      ap: false,
      reactiveLeft: 0,
      reactiveTimer: 0,
      repair: 0,
      alive: true,
      vel: { x: 0, z: 0 },
      throttle: 0,
      turn: 0,
      speed: 0,
      moving: false,
    },
    enemies: [],
    bullets: [],
    pickups: [],
  };

  const waves = level.waves.map((w) => ({ t: w.t, list: [...w.list] }));
  const input = { throttle: 0, turn: 0, trigger: false };
  const aim = { x: 0, z: 0, active: false };
  let enemySeq = 0;
  let bulletSeq = 0;
  let pickupSeq = 0;

  // ------------------------------------------------------------------ input
  const commands = {
    setMove(throttle, turn) {
      input.throttle = clamp(throttle, -1, 1);
      input.turn = clamp(turn, -1, 1);
    },
    setTrigger(on) {
      input.trigger = !!on;
    },
    aimAt(x, z) {
      aim.x = x;
      aim.z = z;
      aim.active = true;
    },
    useSkill() {
      if (state.phase !== 'battle' || state.skillCd > 0 || !state.player.alive) return false;
      return activateSkill();
    },
    stop() {
      input.throttle = 0;
      input.turn = 0;
      input.trigger = false;
    },
  };

  // ------------------------------------------------------------------ skill
  function activateSkill() {
    const p = state.player;
    const id = p.spec.id;
    if (id === 'sherman') {
      p.smoke = 5;
      state.skillCd = 20;
      emit('skill', { kind: 'smoke', x: p.x, z: p.z });
      emit('message', { text: '烟幕释放!' });
    } else if (id === 'tiger') {
      p.ap = true;
      state.skillCd = 15;
      emit('skill', { kind: 'ap' });
      emit('message', { text: '穿甲弹已装填' });
    } else {
      p.reactiveLeft = 3;
      p.reactiveTimer = 30;
      state.skillCd = 25;
      emit('skill', { kind: 'reactive' });
      emit('message', { text: '反应装甲启动 x3' });
    }
    return true;
  }

  // ----------------------------------------------------------------- player
  function playerFire() {
    const p = state.player;
    const yaw = p.heading + p.turretYaw;
    const muzzle = p.spec.muzzle ?? 0.82;
    const x = p.x + Math.sin(yaw) * muzzle;
    const z = p.z + Math.cos(yaw) * muzzle;
    const ap = p.ap;
    if (ap) p.ap = false;
    spawnBullet({
      x,
      z,
      yaw,
      speed: p.bulletSpeed,
      damage: p.damage,
      from: 'player',
      ownerId: p.id,
      ap,
      apLeft: ap ? 2 : 0,
    });
    p.fireCd = p.fireInterval;
    emit('fire', { from: 'player', shooterId: p.id, x, z, yaw, ap });
  }

  function updatePlayer(dt) {
    const p = state.player;
    p.invuln = Math.max(0, p.invuln - dt);
    p.shield = Math.max(0, p.shield - dt);
    p.smoke = Math.max(0, p.smoke - dt);

    if (p.reactiveTimer > 0) {
      p.reactiveTimer -= dt;
      if (p.reactiveTimer <= 0) p.reactiveLeft = 0;
    }
    if (p.repair > 0) {
      p.repair -= dt;
      p.hp = Math.min(p.maxHp, p.hp + 2 * dt);
    }

    if (!p.alive) {
      if (state.respawnTimer > 0) {
        state.respawnTimer -= dt;
        if (state.respawnTimer <= 0) respawnPlayer();
      }
      return;
    }

    p.heading += input.turn * p.spec.turn * dt;
    p.turn = input.turn;

    const dx = Math.sin(p.heading);
    const dz = Math.cos(p.heading);
    const onIce = grid.tile(tr(p.z), tc(p.x)) === TILE.ICE;
    const throttle = input.throttle;

    if (onIce) {
      const targetX = dx * throttle * p.spec.speed;
      const targetZ = dz * throttle * p.spec.speed;
      p.vel.x += (targetX - p.vel.x) * ICE_ACCEL * dt;
      p.vel.z += (targetZ - p.vel.z) * ICE_ACCEL * dt;
      const moved = grid.tryMove(p, p.vel.x * dt, p.vel.z * dt, TANK_R);
      if (!moved) {
        p.vel.x *= 0.6;
        p.vel.z *= 0.6;
      }
      p.speed = Math.hypot(p.vel.x, p.vel.z) * Math.sign(throttle || 1);
      p.moving = Math.abs(p.speed) > 0.05;
    } else {
      p.vel.x = 0;
      p.vel.z = 0;
      p.speed = throttle * p.spec.speed;
      p.moving = false;
      if (throttle !== 0) {
        p.moving = grid.tryMove(p, dx * throttle * p.spec.speed * dt, dz * throttle * p.spec.speed * dt, TANK_R);
      }
    }
    p.throttle = throttle;

    if (aim.active) {
      const desired = wrapAngle(Math.atan2(aim.x - p.x, aim.z - p.z) - p.heading);
      const maxStep = (p.spec.turretSpeed ?? 6) * dt;
      const delta = wrapAngle(desired - p.turretYaw);
      p.turretYaw = wrapAngle(p.turretYaw + clamp(delta, -maxStep, maxStep));
    }

    p.fireCd -= dt;
    if (input.trigger && p.fireCd <= 0) playerFire();
  }

  function respawnPlayer() {
    const p = state.player;
    p.alive = true;
    p.x = PLAYER_SPAWN.x;
    p.z = PLAYER_SPAWN.z;
    p.heading = PLAYER_SPAWN.heading;
    p.turretYaw = 0;
    p.hp = p.maxHp;
    p.invuln = 2.5;
    p.vel.x = 0;
    p.vel.z = 0;
    p.speed = 0;
    emit('respawn', { id: p.id, x: p.x, z: p.z });
  }

  function damagePlayer(damage) {
    const p = state.player;
    if (!p.alive || p.invuln > 0) return;
    if (p.shield > 0) {
      emit('shieldBlock', { x: p.x, z: p.z });
      return;
    }
    if (p.reactiveLeft > 0) {
      p.reactiveLeft--;
      emit('reactiveBlock', { x: p.x, z: p.z, left: p.reactiveLeft });
      return;
    }
    if (p.spec.id === 'tiger') damage *= 0.8;
    p.hp -= damage;
    emit('playerHit', { x: p.x, z: p.z, damage });
    if (p.hp <= 0) {
      p.hp = 0;
      killPlayer();
    }
  }

  function killPlayer() {
    const p = state.player;
    emit('explosion', { x: p.x, z: p.z, scale: 1.4 });
    p.alive = false;
    p.lives--;
    emit('lifeLost', { lives: p.lives });
    if (p.lives <= 0) endBattle(false, '全部坦克损毁');
    else state.respawnTimer = 1.5;
  }

  // ------------------------------------------------------------------ waves
  function spawnEnemy(typeId) {
    const prof = enemyTypes[typeId];
    const cols = level.spawnCols;
    const col = cols[state.spawnIndex++ % cols.length];
    const hp = prof.hp * 25;
    const enemy = {
      id: `e${enemySeq++}`,
      type: typeId,
      prof,
      x: col - 6,
      z: -6,
      heading: 0,
      turretYaw: 0,
      hp,
      maxHp: hp,
      scale: prof.scale,
      fireCd: 1.2 + rand.next(),
      aimTimer: 0,
      stuck: 0,
      jitterTimer: 0,
      jitterYaw: 0,
      freezeTimer: 0,
      hitFlash: 0,
      spawnTimer: 0,
      seed: rand.range(0, 10),
      alive: true,
    };
    state.enemies.push(enemy);
    emit('spawn', {
      id: enemy.id,
      type: typeId,
      x: enemy.x,
      z: enemy.z,
      scale: enemy.scale,
    });
  }

  function updateWaves(dt) {
    while (state.wave < waves.length && waves[state.wave].t <= state.time) {
      state.spawnQueue.push(...waves[state.wave].list);
      state.wave++;
      emit('message', { text: `第 ${state.wave} 波来袭` });
    }
    state.spawnTimer -= dt;
    if (state.spawnQueue.length && state.enemies.length < level.maxOnField && state.spawnTimer <= 0) {
      spawnEnemy(state.spawnQueue.shift());
      state.spawnTimer = 1;
    }
  }

  // ----------------------------------------------------------------- enemies
  function enemyFire(enemy, error) {
    const p = state.player;
    const yaw = Math.atan2(p.x - enemy.x, p.z - enemy.z) + (rand.next() - 0.5) * 2 * error;
    const muzzle = 0.85 * enemy.scale;
    const x = enemy.x + Math.sin(yaw) * muzzle;
    const z = enemy.z + Math.cos(yaw) * muzzle;
    spawnBullet({
      x,
      z,
      yaw,
      speed: ENEMY_BULLET_SPEED,
      damage: enemy.prof.dmg,
      from: 'enemy',
      ownerId: enemy.id,
    });
    emit('fire', { from: 'enemy', shooterId: enemy.id, x, z, yaw });
  }

  function enemyThink(enemy, dt) {
    const prof = enemy.prof;
    const p = state.player;
    const pd = Math.hypot(p.x - enemy.x, p.z - enemy.z);

    let canSee = false;
    if (p.alive && p.smoke <= 0) {
      const hidden = grid.tile(tr(p.z), tc(p.x)) === TILE.FOREST && pd > 3;
      canSee = !hidden && pd < prof.range + 4 && grid.lineOfSight(enemy.x, enemy.z, p.x, p.z);
    }

    let tx = state.eagle.x;
    let tz = state.eagle.z;
    let hold = false;
    if (canSee) {
      if (prof.id === 'sniper') {
        if (pd < 4.2) {
          tx = enemy.x * 2 - p.x;
          tz = enemy.z * 2 - p.z;
        } else if (pd < prof.range) {
          hold = true;
        } else {
          tx = p.x;
          tz = p.z;
        }
      } else {
        tx = p.x;
        tz = p.z;
      }
    }

    let desired = Math.atan2(tx - enemy.x, tz - enemy.z);
    if (enemy.jitterTimer > 0) {
      enemy.jitterTimer -= dt;
      desired = enemy.jitterYaw;
    } else if (prof.id === 'scout' && !canSee) {
      desired += Math.sin(state.time * 2.3 + enemy.seed) * 0.5;
    }

    const delta = wrapAngle(desired - enemy.heading);
    enemy.heading += Math.sign(delta) * Math.min(Math.abs(delta), 3.2 * dt);
    enemy.heading = wrapAngle(enemy.heading);

    const moving = !(hold && enemy.jitterTimer <= 0);
    let moved = false;
    if (moving && Math.abs(delta) < 0.9) {
      moved = grid.tryMove(
        enemy,
        Math.sin(enemy.heading) * prof.speed * dt,
        Math.cos(enemy.heading) * prof.speed * dt,
        TANK_R * enemy.scale,
      );
    }
    if (!moving || !moved) {
      enemy.stuck += dt;
      if (enemy.stuck > 0.35 && enemy.jitterTimer <= 0) {
        enemy.stuck = 0;
        enemy.jitterTimer = 0.7;
        enemy.jitterYaw = wrapAngle(enemy.heading + (rand.chance(0.5) ? 1 : -1) * Math.PI / 2);
      }
    } else {
      enemy.stuck = 0;
    }
    enemy.moving = moving && moved;
    enemy.inForest = grid.tile(tr(enemy.z), tc(enemy.x)) === TILE.FOREST;

    if (p.alive) {
      const ddx = enemy.x - p.x;
      const ddz = enemy.z - p.z;
      const dd = Math.hypot(ddx, ddz);
      if (dd < TANK_R * 1.7 && dd > 0.001) {
        const push = TANK_R * 1.7 - dd;
        grid.tryMove(enemy, (ddx / dd) * push, (ddz / dd) * push, TANK_R * enemy.scale);
      }
    }

    if (canSee) {
      const desiredTurret = wrapAngle(Math.atan2(p.x - enemy.x, p.z - enemy.z) - enemy.heading);
      const step = ENEMY_TURRET_SPEED * dt;
      enemy.turretYaw = wrapAngle(
        enemy.turretYaw + clamp(wrapAngle(desiredTurret - enemy.turretYaw), -step, step),
      );
      enemy.fireCd -= dt;
      if (enemy.fireCd <= 0 && pd <= prof.range + 1) {
        if (prof.id === 'sniper') {
          enemy.aimTimer += dt;
          if (enemy.aimTimer >= 0.55) {
            enemyFire(enemy, 0.03);
            enemy.aimTimer = 0;
            enemy.fireCd = prof.fire;
          }
        } else {
          enemyFire(enemy, 0.14);
          enemy.fireCd = prof.fire * (0.8 + rand.next() * 0.4);
        }
      }
    } else {
      enemy.turretYaw = wrapAngle(enemy.turretYaw * Math.max(0, 1 - 3 * dt));
      enemy.aimTimer = 0;
      enemy.fireCd = Math.max(enemy.fireCd, 0.6);
    }
  }

  function updateEnemies(dt) {
    for (const enemy of state.enemies) {
      enemy.spawnTimer += dt;
      if (enemy.hitFlash > 0) enemy.hitFlash -= dt;
      if (enemy.freezeTimer > 0) {
        enemy.freezeTimer -= dt;
        continue;
      }
      enemyThink(enemy, dt);
    }
  }

  function hitEnemy(enemy, damage) {
    enemy.hp -= damage;
    enemy.hitFlash = 0.12;
    emit('enemyHit', { id: enemy.id, x: enemy.x, z: enemy.z, damage });
    if (enemy.hp <= 0) killEnemy(enemy, true);
  }

  function killEnemy(enemy, allowDrop) {
    const idx = state.enemies.indexOf(enemy);
    if (idx < 0) return;
    state.enemies.splice(idx, 1);
    emit('explosion', { x: enemy.x, z: enemy.z, scale: enemy.scale * 1.2 });
    emit('enemyKilled', {
      id: enemy.id,
      x: enemy.x,
      z: enemy.z,
      score: enemy.prof.score,
    });
    state.score += enemy.prof.score;
    state.killed++;
    if (allowDrop && rand.chance(0.22)) dropPickup(enemy.x, enemy.z);
  }

  // ----------------------------------------------------------------- bullets
  function spawnBullet({ x, z, yaw, speed, damage, from, ownerId, ap = false, apLeft = 0 }) {
    state.bullets.push({
      id: `b${bulletSeq++}`,
      x,
      z,
      yaw,
      speed,
      damage,
      from,
      ownerId,
      ap,
      apLeft,
      life: BULLET_LIFE,
    });
  }

  function updateBullets(dt) {
    for (let i = state.bullets.length - 1; i >= 0; i--) {
      const b = state.bullets[i];
      const step = b.speed * dt;
      b.x += Math.sin(b.yaw) * step;
      b.z += Math.cos(b.yaw) * step;
      b.life -= dt;

      let dead = b.life <= 0 || Math.abs(b.x) > 7.5 || Math.abs(b.z) > 7.5;
      const r = tr(b.z);
      const c = tc(b.x);
      const tile = grid.tile(r, c);

      if (!dead) {
        if (tile === TILE.BRICK) {
          const prev = grid.destroy(r, c);
          emit('tileChanged', { r, c, tile: TILE.EMPTY, previous: prev });
          emit('impact', { x: b.x, z: b.z, kind: 'brick' });
          if (!b.ap) dead = true;
        } else if (tile === TILE.STEEL) {
          if (b.ap) {
            const prev = grid.destroy(r, c);
            emit('tileChanged', { r, c, tile: TILE.EMPTY, previous: prev });
            emit('impact', { x: b.x, z: b.z, kind: 'steel' });
          } else {
            emit('spark', { x: b.x, z: b.z });
            dead = true;
          }
        } else if (tile === TILE.EAGLE) {
          destroyEagle();
          emit('impact', { x: b.x, z: b.z, kind: 'eagle' });
          dead = true;
        }
      }

      if (!dead) {
        if (b.from === 'enemy') {
          const p = state.player;
          if (p.alive && Math.hypot(b.x - p.x, b.z - p.z) < TANK_R + BULLET_R) {
            damagePlayer(b.damage);
            dead = true;
          }
        } else {
          for (const enemy of state.enemies) {
            if (Math.hypot(b.x - enemy.x, b.z - enemy.z) < TANK_R * enemy.scale + BULLET_R) {
              hitEnemy(enemy, b.damage);
              if (b.ap && b.apLeft > 0) {
                b.apLeft--;
                if (b.apLeft <= 0) dead = true;
              } else {
                dead = true;
              }
              break;
            }
          }
        }
      }

      if (dead) state.bullets.splice(i, 1);
    }
  }

  function destroyEagle() {
    if (!state.eagle.alive) return;
    state.eagle.alive = false;
    emit('explosion', { x: state.eagle.x, z: state.eagle.z, scale: 2.2 });
    endBattle(false, '鹰徽被毁，防线崩溃');
  }

  // ---------------------------------------------------------------- powerups
  function dropPickup(x, z) {
    const def = rand.weighted(powerups);
    state.pickups.push({
      id: `p${pickupSeq++}`,
      def,
      x,
      z,
      life: 12,
    });
    emit('pickupDropped', { id: `p${pickupSeq - 1}`, x, z, powerupId: def.id, color: def.color });
  }

  function applyPowerup(def) {
    const p = state.player;
    switch (def.id) {
      case 'star':
        p.fireInterval = Math.max(0.22, p.fireInterval * 0.7);
        state.score += 500;
        emit('message', { text: '火力升级!' });
        break;
      case 'grenade':
        for (const enemy of [...state.enemies]) killEnemy(enemy, false);
        emit('message', { text: '全体歼灭!' });
        break;
      case 'shovel':
        fortify();
        state.score += 500;
        emit('message', { text: '鹰徽加固 15 秒' });
        break;
      case 'clock':
        for (const enemy of state.enemies) enemy.freezeTimer = 8;
        state.score += 500;
        emit('message', { text: '敌军冻结 8 秒!' });
        break;
      case 'helmet':
        p.shield = 10;
        state.score += 500;
        emit('message', { text: '能量护盾 10 秒' });
        break;
      case 'tank':
        p.lives++;
        emit('message', { text: '备用坦克 +1' });
        break;
      default:
        break;
    }
    if (p.spec.id === 'sherman') p.repair = 5;
    emit('pickup', { powerupId: def.id, x: p.x, z: p.z, label: def.label });
  }

  function fortify() {
    const bunker = level.bunker || [];
    for (const [r, c] of bunker) {
      if (grid.tile(r, c) === TILE.BRICK) {
        grid.set(r, c, TILE.STEEL);
        emit('tileChanged', { r, c, tile: TILE.STEEL, previous: TILE.BRICK });
      }
    }
    state.fortTimer = 15;
  }

  function updateFortify(dt) {
    if (state.fortTimer <= 0) return;
    state.fortTimer -= dt;
    if (state.fortTimer > 0) return;
    const bunker = level.bunker || [];
    for (const [r, c] of bunker) {
      if (grid.tile(r, c) === TILE.STEEL) {
        grid.set(r, c, TILE.BRICK);
        emit('tileChanged', { r, c, tile: TILE.BRICK, previous: TILE.STEEL });
      }
    }
    emit('message', { text: '加固失效' });
  }

  function updatePickups(dt) {
    const p = state.player;
    for (let i = state.pickups.length - 1; i >= 0; i--) {
      const pickup = state.pickups[i];
      pickup.life -= dt;
      if (pickup.life <= 0) {
        state.pickups.splice(i, 1);
        emit('pickupExpired', { id: pickup.id });
        continue;
      }
      if (p.alive && Math.hypot(pickup.x - p.x, pickup.z - p.z) < 0.62) {
        state.pickups.splice(i, 1);
        applyPowerup(pickup.def);
      }
    }
  }

  // -------------------------------------------------------------------- flow
  function endBattle(win, reason) {
    if (state.phase !== 'battle') return;
    state.phase = win ? 'won' : 'lost';
    emit('gameover', { win, reason, score: state.score });
  }

  function checkWin() {
    if (
      state.phase === 'battle' &&
      state.wave >= waves.length &&
      state.spawnQueue.length === 0 &&
      state.enemies.length === 0
    ) {
      endBattle(true, '全部敌军歼灭');
    }
  }

  function update(dt) {
    if (state.phase !== 'battle') return;
    dt = Math.min(Math.max(dt, 0), 0.05);
    state.time += dt;
    state.skillCd = Math.max(0, state.skillCd - dt);

    updatePlayer(dt);
    updateWaves(dt);
    updateEnemies(dt);
    updateBullets(dt);
    updatePickups(dt);
    updateFortify(dt);
    checkWin();
  }

  function drainEvents() {
    if (!events.length) return [];
    return events.splice(0, events.length);
  }

  return { state, grid, commands, update, drainEvents };
}

function findEagle(grid) {
  for (let r = 0; r < grid.length; r++) {
    const c = grid[r].indexOf(TILE.EAGLE);
    if (c >= 0) return { r, c };
  }
  throw new Error('Level has no eagle tile (9)');
}
