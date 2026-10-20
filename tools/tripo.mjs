#!/usr/bin/env node
// Tripo openapi connector for 钢铁防线3D.
// Auth: TRIPO_API_KEY env var, else ./.secrets/tripo.key
// Base: TRIPO_BASE env var, else https://api.tripo3d.com/v2/openapi
//   NOTE api.tripo3d.ai is SNI-blocked on this network; .com (国内站) serves the same v2 routes.
//
// usage:
//   node tools/tripo.mjs check
//   node tools/tripo.mjs gen "low poly ww2 medium tank, olive green"
//   node tools/tripo.mjs wait <task_id>
//   node tools/tripo.mjs get  <task_id>
//   node tools/tripo.mjs dl   <task_id> [outdir]

import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const BASE = (process.env.TRIPO_BASE || 'https://api.tripo3d.com/v2/openapi').replace(/\/$/, '');

function apiKey() {
  if (process.env.TRIPO_API_KEY) return process.env.TRIPO_API_KEY.trim();
  try {
    return readFileSync(join(ROOT, '.secrets', 'tripo.key'), 'utf8').trim();
  } catch {
    throw new Error('no API key: set TRIPO_API_KEY or write ./.secrets/tripo.key');
  }
}

async function call(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      Authorization: `Bearer ${apiKey()}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(30_000),
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text.slice(0, 400) }; }
  if (!res.ok || json.code !== 0) {
    const err = new Error(`${json.message || 'request failed'} (code ${json.code ?? res.status})`);
    err.suggestion = json.suggestion;
    err.http = res.status;
    throw err;
  }
  return json.data;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function check() {
  const bal = await call('GET', '/user/balance');
  console.log(`key ok   balance=${bal.balance}  frozen=${bal.frozen ?? 0}`);
  if (!bal.balance) console.log('WARN: zero credit — creating a task will fail with code 2010');
  return bal;
}

async function gen(prompt) {
  const data = await call('POST', '/task', {
    type: 'text_to_model',
    prompt,
    model_version: process.env.TRIPO_MODEL || undefined,
    face_limit: process.env.TRIPO_FACE_LIMIT ? Number(process.env.TRIPO_FACE_LIMIT) : undefined,
    texture: true,
    pbr: true,
  });
  console.log(data.task_id);
  return data.task_id;
}

async function wait(taskId) {
  const started = Date.now();
  for (;;) {
    const t = await call('GET', `/task/${taskId}`);
    const secs = ((Date.now() - started) / 1000).toFixed(0);
    console.log(`[${secs}s] ${t.status} ${t.progress ?? 0}%`);
    if (t.status === 'success') return t;
    if (['failed', 'banned', 'expired', 'cancelled', 'unknown'].includes(t.status)) {
      throw new Error(`task ${t.status}: ${JSON.stringify(t)}`);
    }
    await sleep(5000);
  }
}

function urls(task) {
  const out = {};
  for (const k of ['pbr_model', 'base_model', 'model']) {
    const v = task.output?.[k];
    if (v) out[k] = typeof v === 'string' ? v : v.url;
  }
  return out;
}

async function get(taskId) {
  const t = await call('GET', `/task/${taskId}`);
  console.log(`status=${t.status} progress=${t.progress ?? 0}%`);
  for (const [k, v] of Object.entries(urls(t))) console.log(`${k}: ${v}`);
  return t;
}

async function dl(taskId, outdir = join(ROOT, 'vendor/models')) {
  const t = await call('GET', `/task/${taskId}`);
  const u = urls(t);
  const target = u.pbr_model || u.base_model || u.model;
  if (!target) throw new Error(`task ${taskId} has no model url (status=${t.status})`);
  const res = await fetch(target, { signal: AbortSignal.timeout(120_000) });
  if (!res.ok) throw new Error(`download failed: HTTP ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  mkdirSync(outdir, { recursive: true });
  const file = join(outdir, `${taskId}.glb`);
  writeFileSync(file, buf);
  console.log(`${file}  ${(buf.length / 1024).toFixed(0)} KB`);
  return file;
}

const [cmd, ...args] = process.argv.slice(2);
const run = { check, gen, wait, get, dl }[cmd];
if (!run) {
  console.error('usage: check | gen <prompt> | wait <id> | get <id> | dl <id> [outdir]');
  process.exit(2);
}
try {
  await run(...args);
} catch (e) {
  console.error(`ERR ${e.message}`);
  if (e.suggestion) console.error(`     -> ${e.suggestion}`);
  process.exit(1);
}
