// Asset loading boundary. Everything that knows a file path lives here or in
// content/assets.js. The rules core never sees any of this.

import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MODEL_ASSETS } from '../content/assets.js';

const loader = new GLTFLoader();

function loadOne(def, onProgress) {
  return new Promise((resolve, reject) => {
    loader.load(
      def.url,
      (gltf) => resolve({ gltf, def, ok: true }),
      (event) => {
        if (onProgress && event.total) onProgress(def.id, event.loaded / event.total);
      },
      (error) => reject(new Error(`${def.id}: ${error.message || error}`)),
    );
  });
}

/**
 * Load every model in the manifest. A failed hero falls back to the troop LOD
 * so the game still boots; the returned map records `fellBackFrom` for the HUD.
 */
export async function loadModelAssets({ onProgress } = {}) {
  const models = new Map();
  const failures = [];

  for (const [id, def] of Object.entries(MODEL_ASSETS)) {
    try {
      models.set(id, await loadOne(def, onProgress));
    } catch (error) {
      failures.push({ id, error: String(error) });
      console.error('[assets]', error);
    }
  }

  for (const [id, def] of Object.entries(MODEL_ASSETS)) {
    if (models.has(id) || !def.fallback) continue;
    const fallback = models.get(def.fallback);
    if (fallback) {
      models.set(id, { ...fallback, fellBackFrom: id });
      console.warn(`[assets] ${id} missing, using ${def.fallback}`);
    }
  }

  if (!models.size) throw new Error('No tank model could be loaded');
  return { models, failures };
}
