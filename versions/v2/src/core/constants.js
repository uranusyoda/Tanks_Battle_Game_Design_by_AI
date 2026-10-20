// Mechanical constants shared by the rules core.
// Nothing in this folder imports Three.js, the DOM or any asset file.

export const ROWS = 13;
export const COLS = 13;

/** Collision radius of a tank, in board units (one tile = 1 unit). */
export const TANK_R = 0.4;

/** Radius used for bullet-vs-tank hits. */
export const BULLET_R = 0.14;

/** tile codes: 0 empty, 1 brick, 2 steel, 3 water, 4 forest, 5 ice, 9 eagle */
export const TILE = Object.freeze({
  EMPTY: 0,
  BRICK: 1,
  STEEL: 2,
  WATER: 3,
  FOREST: 4,
  ICE: 5,
  EAGLE: 9,
});

/** Water is solid for movement but does not block line of sight. */
export const SOLID_TILES = Object.freeze([TILE.BRICK, TILE.STEEL, TILE.WATER, TILE.EAGLE]);

export const cx = (col) => col - 6;
export const cz = (row) => row - 6;
export const tc = (x) => Math.round(x + 6);
export const tr = (z) => Math.round(z + 6);

export const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);

/** Shortest signed angle in (-PI, PI]. */
export function wrapAngle(a) {
  while (a > Math.PI) a -= Math.PI * 2;
  while (a <= -Math.PI) a += Math.PI * 2;
  return a;
}
