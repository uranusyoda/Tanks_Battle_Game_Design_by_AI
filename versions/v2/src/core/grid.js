import { ROWS, COLS, TILE, SOLID_TILES, cx, cz, tc, tr } from './constants.js';

/**
 * The board is a pure data structure: tiles + geometry queries.
 * It owns no meshes and knows nothing about rendering.
 */
export function createGrid(level) {
  const tiles = level.grid.map((row) => row.slice());
  const solid = new Set(SOLID_TILES);

  const grid = {
    rows: ROWS,
    cols: COLS,
    tiles,

    tile(r, c) {
      if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return TILE.STEEL;
      return tiles[r][c];
    },

    isSolid(t) {
      return solid.has(t);
    },

    center(r, c) {
      return { x: cx(c), z: cz(r) };
    },

    /** True if a circle of radius rad at (x,z) overlaps a solid tile. */
    circleHitsSolid(x, z, rad) {
      const rr = tr(z);
      const cc = tc(x);
      for (let r = rr - 1; r <= rr + 1; r++) {
        for (let c = cc - 1; c <= cc + 1; c++) {
          if (!solid.has(grid.tile(r, c))) continue;
          const nx = Math.max(cx(c) - 0.5, Math.min(x, cx(c) + 0.5));
          const nz = Math.max(cz(r) - 0.5, Math.min(z, cz(r) + 0.5));
          if ((x - nx) ** 2 + (z - nz) ** 2 < rad * rad) return true;
        }
      }
      return false;
    },

    /** Axis-separated slide. Mutates entity.x / entity.z. Returns moved. */
    tryMove(entity, dx, dz, rad) {
      let moved = false;
      if (dx !== 0 && !grid.circleHitsSolid(entity.x + dx, entity.z, rad)) {
        entity.x += dx;
        moved = true;
      }
      if (dz !== 0 && !grid.circleHitsSolid(entity.x, entity.z + dz, rad)) {
        entity.z += dz;
        moved = true;
      }
      return moved;
    },

    lineOfSight(x1, z1, x2, z2) {
      const d = Math.hypot(x2 - x1, z2 - z1);
      const steps = Math.max(1, Math.ceil(d * 3));
      for (let i = 1; i < steps; i++) {
        const t = i / steps;
        const t2 = grid.tile(tr(z1 + (z2 - z1) * t), tc(x1 + (x2 - x1) * t));
        if (solid.has(t2) && t2 !== TILE.WATER) return false;
      }
      return true;
    },

    /** Remove a destructible tile. Returns the previous tile code. */
    destroy(r, c) {
      const t = grid.tile(r, c);
      if (t !== TILE.BRICK && t !== TILE.STEEL) return t;
      tiles[r][c] = TILE.EMPTY;
      return t;
    },

    set(r, c, t) {
      if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return;
      tiles[r][c] = t;
    },
  };

  return grid;
}
