// Deterministic RNG wrapper. The raw generator lives in shared/ so asset
// generation can use it without depending on the rules layer.

import { mulberry32 } from '../shared/random.js';

export { mulberry32 };

export function createRng(seed = 1) {
  const next = mulberry32(seed);
  return {
    next,
    range: (a, b) => a + (b - a) * next(),
    int: (a, b) => Math.floor(a + (b - a + 1) * next()),
    chance: (p) => next() < p,
    pick: (arr) => arr[Math.floor(next() * arr.length)],
    /** Weighted pick: items are [{ w, ... }]. */
    weighted(items) {
      const total = items.reduce((s, it) => s + it.w, 0);
      let r = next() * total;
      for (const it of items) {
        if ((r -= it.w) <= 0) return it;
      }
      return items[items.length - 1];
    },
  };
}
