import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const SRC = path.resolve(process.argv[2] ?? 'versions/v3');
const OUT = path.resolve(process.argv[3] ?? 'port/contract');

const load = (rel) => import(pathToFileURL(path.join(SRC, rel)).href);

const [
  { TANKS },
  { ENEMY_TYPES },
  { LEVEL, SHOWROOM },
  { POWERUPS },
  { MODEL_ASSETS, VIEW_TUNING },
] = await Promise.all([
  load('src/content/tanks.js'),
  load('src/content/enemies.js'),
  load('src/content/levels.js'),
  load('src/content/powerups.js'),
  load('src/content/assets.js'),
]);

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortKeys(value[k])]));
  }
  return value;
}

const content = sortKeys({
  meta: { source: 'versions/v3', version: '3.0.0' },
  tanks: TANKS,
  enemies: ENEMY_TYPES,
  levels: { LEVEL, SHOWROOM },
  powerups: POWERUPS,
  assets: MODEL_ASSETS,
  viewTuning: VIEW_TUNING,
});

await fs.mkdir(OUT, { recursive: true });
const json = JSON.stringify(content, null, 2) + '\n';
await fs.writeFile(path.join(OUT, 'content.json'), json);

const hash = crypto.createHash('sha256').update(json).digest('hex');
await fs.writeFile(path.join(OUT, 'content.sha256'), hash + '\n');
console.log(`wrote ${path.join(OUT, 'content.json')} (${json.length} bytes)`);
console.log(`sha256 ${hash}`);
