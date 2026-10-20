/**
 * Level content: tile grid, wave table, spawn columns, bunker coordinates.
 * Tile codes: 0 empty, 1 brick, 2 steel, 3 water, 4 forest, 5 ice, 9 eagle.
 */
export const LEVEL = {
  name: 'Training Grounds',
  grid: [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 2, 1, 0, 1, 2, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 0, 1, 0, 0, 0, 4, 0, 0, 0, 1, 0, 2],
    [0, 0, 0, 0, 4, 4, 4, 4, 4, 0, 0, 0, 0],
    [2, 0, 1, 0, 0, 0, 4, 0, 0, 0, 1, 0, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 2, 1, 1, 2, 0, 1, 0, 1],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 1, 1, 9, 1, 1, 0, 0, 0, 0],
  ],
  waves: [
    { t: 0, list: ['scout', 'scout', 'line'] },
    { t: 15, list: ['line', 'line', 'scout'] },
    { t: 30, list: ['line', 'sniper', 'scout', 'scout'] },
  ],
  spawnCols: [1, 4, 8, 11],
  maxOnField: 4,
  bunker: [
    [12, 4],
    [12, 5],
    [12, 7],
    [12, 8],
  ],
};


/** Empty arena used by the garage/showroom so the model is never occluded. */
export const SHOWROOM = {
  name: 'Garage',
  grid: Array.from({ length: 13 }, () => Array(13).fill(0)),
  waves: [],
  spawnCols: [0],
  maxOnField: 0,
  bunker: [],
};
