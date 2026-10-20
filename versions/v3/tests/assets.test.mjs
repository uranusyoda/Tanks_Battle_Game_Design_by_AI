import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import { MODEL_ASSETS } from '../src/content/assets.js';

const ROOT = process.cwd();
const manifest = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets/models/manifest.json'), 'utf8'));

function readGlb(url) {
  const file = fileURLToPath(url);
  const bytes = fs.readFileSync(file);
  const magic = bytes.readUInt32LE(0);
  assert.equal(magic, 0x46546c67, `${file} is a GLB`);
  let offset = 12;
  let json = null;
  while (offset < bytes.length) {
    const length = bytes.readUInt32LE(offset);
    const type = bytes.readUInt32LE(offset + 4);
    const chunk = bytes.subarray(offset + 8, offset + 8 + length);
    if (type === 0x4e4f534a) json = JSON.parse(chunk.toString('utf8'));
    offset += 8 + length;
  }
  assert.ok(json, 'GLB has a JSON chunk');
  return { bytes, json };
}

for (const [id, def] of Object.entries(MODEL_ASSETS)) {
  test(`asset contract: ${id}`, () => {
    const { bytes, json } = readGlb(def.url);
    const entry = manifest.models[id];
    assert.ok(entry, `${id} is in the build manifest`);

    // integrity
    assert.equal(bytes.length, entry.bytes);
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), entry.sha256);

    // self contained
    assert.equal(json.images?.length ?? 0, 0, 'no external textures');
    assert.ok(json.meshes.length > 0);
    assert.ok(json.materials.length >= 7);

    // names used by the rig
    const names = new Set((json.nodes || []).map((n) => n.name));
    for (const tag of Object.values(def.tags)) {
      assert.ok(names.has(tag), `${id} has node ${tag}`);
    }
    assert.ok(names.has('M4A1_Sherman'), 'root named M4A1_Sherman');

    // animation clips
    const clips = new Map((json.animations || []).map((a) => [a.name, a]));
    for (const clipName of Object.values(def.clips)) {
      assert.ok(clips.has(clipName), `${id} has clip ${clipName}`);
    }
    if (def.lod === 'hero') {
      assert.ok(clips.get('Drive'), 'hero has the Drive loop');
      const drive = clips.get('Drive');
      assert.ok(drive.channels.length > 300, 'Drive animates every track link');
      const input = json.accessors[drive.samplers[0].input];
      assert.ok(input.max[0] > 10, 'Drive is a long loop');
      assert.ok(clips.get('Fire'));
    }
    if (def.lod === 'troop') {
      assert.equal(clips.has('Drive'), false, 'troop uses merged static tracks');
      assert.ok(clips.get('Fire'));
    }

    // every animation channel points at a real node
    for (const animation of json.animations || []) {
      for (const channel of animation.channels) {
        assert.ok(Number.isInteger(channel.target.node));
        assert.ok(json.nodes[channel.target.node], `${animation.name} targets a node`);
      }
    }
  });
}

test('asset manifest: LOD split is explicit', () => {
  assert.equal(manifest.models.sherman_hero.lod, 'hero');
  assert.equal(manifest.models.sherman_troop.lod, 'troop');
  assert.ok(manifest.models.sherman_hero.bytes > manifest.models.sherman_troop.bytes);
});
