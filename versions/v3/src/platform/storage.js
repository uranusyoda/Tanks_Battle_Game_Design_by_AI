// Persistence port. Swap this file to change storage; nothing else knows the key.

const KEY = 'sb3d_sherman_hi';

export function loadHighScore() {
  try {
    return Number(localStorage.getItem(KEY)) || 0;
  } catch (error) {
    return 0;
  }
}

export function saveHighScore(score) {
  try {
    if (score > loadHighScore()) localStorage.setItem(KEY, String(score));
  } catch (error) {
    /* private mode */
  }
}
