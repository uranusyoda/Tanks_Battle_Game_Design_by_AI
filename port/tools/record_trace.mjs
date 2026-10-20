import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const SRC = path.resolve(process.argv[2] ?? 'versions/v3');
const OUT = path.resolve(process.argv[3] ?? 'port/traces');
const CONTENT_JSON = path.resolve(process.argv[4] ?? 'port/contract/content.json');
const load = (rel) => import(pathToFileURL(path.join(SRC, rel)).href);

const [{ createBattle }, { TANKS }, { ENEMY_TYPES }, { LEVEL }, { POWERUPS }] =
  await Promise.all([
    load('src/core/battle.js'),
    load('src/content/tanks.js'),
    load('src/content/enemies.js'),
    load('src/content/levels.js'),
    load('src/content/powerups.js'),
  ]);

const DT = 1 / 60;

function emptyLevel() {
  const grid = Array.from({ length: 13 }, () => Array(13).fill(0));
  grid[12][6] = 9;
  return {
    name: 'Trace Arena',
    grid,
    waves: [{ t: 0, list: ['line'] }],
    spawnCols: [6],
    maxOnField: 1,
    bunker: [],
  };
}

const SCENARIOS = [
  {
    id: 'drive_into_brick',
    tankId: 'sherman',
    seed: 7,
    steps: 120,
    level: LEVEL,
    commands: [{ step: 0, op: 'setMove', args: [1, 0] }],
  },
  {
    id: 'fire_brick',
    tankId: 'sherman',
    seed: 7,
    steps: 120,
    level: LEVEL,
    commands: [
      { step: 0, op: 'aimAt', args: [0, 3] },
      { step: 5, op: 'setTrigger', args: [true] },
      { step: 8, op: 'setTrigger', args: [false] },
    ],
  },
  {
    id: 'hit_enemy',
    tankId: 'sherman',
    seed: 7,
    steps: 300,
    level: emptyLevel(),
    commands: [
      { step: 0, op: 'aimAt', args: [0, -6] },
      { step: 0, op: 'setTrigger', args: [true] },
    ],
  },
  {
    id: 'eagle_fail',
    tankId: 'sherman',
    seed: 7,
    steps: 120,
    level: LEVEL,
    commands: [
      { step: 0, op: 'aimAt', args: [0, 6] },
      { step: 0, op: 'setTrigger', args: [true] },
      { step: 2, op: 'setTrigger', args: [false] },
    ],
    // Source unit test aligns the hull directly at the eagle.
    initial: { x: 0, z: 5, heading: 0, turretYaw: 0, invuln: 0 },
  },
  {
    id: 'skill_smoke',
    tankId: 'sherman',
    seed: 7,
    steps: 180,
    level: LEVEL,
    commands: [{ step: 0, op: 'useSkill', args: [] }],
  },
];

const snap = (battle) => {
  const s = battle.state;
  return {
    t: s.time, phase: s.phase, score: s.score, wave: s.wave, killed: s.killed,
    skillCd: s.skillCd,
    player: {
      x: s.player.x, z: s.player.z, heading: s.player.heading,
      turretYaw: s.player.turretYaw, hp: s.player.hp, lives: s.player.lives,
      alive: s.player.alive, invuln: s.player.invuln, smoke: s.player.smoke,
    },
    enemies: s.enemies.map((e) => ({
      id: e.id, x: e.x, z: e.z, heading: e.heading, turretYaw: e.turretYaw, hp: e.hp,
    })),
    bullets: s.bullets.map((b) => ({ id: b.id, x: b.x, z: b.z, from: b.from })),
    pickups: s.pickups.map((p) => ({ id: p.id, x: p.x, z: p.z, powerupId: p.def.id })),
    eagle: s.eagle.alive,
  };
};

const canonical = (v) => Array.isArray(v)
  ? v.map(canonical)
  : v && typeof v === 'object'
    ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canonical(v[k])]))
    : v;

const contentRaw = await fs.readFile(CONTENT_JSON, 'utf8');
const contentHash = crypto.createHash('sha256').update(contentRaw).digest('hex');

await fs.mkdir(OUT, { recursive: true });

for (const sc of SCENARIOS) {
  const battle = createBattle({
    tankId: sc.tankId, tanks: TANKS, enemyTypes: ENEMY_TYPES,
    level: sc.level, powerups: POWERUPS, seed: sc.seed,
  });
  if (sc.initial) Object.assign(battle.state.player, sc.initial);

  const events = [];
  const samples = [];
  for (let step = 0; step < sc.steps; step++) {
    for (const c of sc.commands.filter((c) => c.step === step)) {
      battle.commands[c.op](...c.args);
    }
    battle.update(DT);
    for (const e of battle.drainEvents()) events.push({ step, ...e });
    if (step % 5 === 0) samples.push({ step, state: snap(battle) });
  }
  const final = snap(battle);
  const digest = crypto.createHash('sha256')
    .update(JSON.stringify(canonical({ samples, final, events }))).digest('hex');
  const trace = {
    schema: 1, scenario: sc.id, source: { root: 'versions/v3', version: '3.0.0' },
    seed: sc.seed, dt: DT, dt_num: 1, dt_den: 60, steps: sc.steps, tankId: sc.tankId,
    contentHash, level: sc.level, initial: sc.initial ?? null,
    commands: sc.commands, events, samples, final, digest,
  };
  await fs.writeFile(path.join(OUT, `${sc.id}.json`), JSON.stringify(trace, null, 2) + '\n');
  console.log(`${sc.id}: ${events.length} events, ${samples.length} samples, digest=${digest.slice(0, 12)}`);
}
