/**
 * Asset manifest — the contract between the asset layer and everything else.
 *
 * Only the view/asset layers read `url`, `scale` and `clips`. Gameplay reads
 * `paint`/`model.lod` from content, never the file path. Swapping a model means
 * changing this file, not the rules.
 */
const MODEL_BASE = new URL('../../assets/models/', import.meta.url);

export const MODEL_ASSETS = {
  sherman_hero: {
    id: 'sherman_hero',
    file: 'm4a1_sherman_hero.glb',
    url: new URL('m4a1_sherman_hero.glb', MODEL_BASE).href,
    source: 'assets/models/m4a1_sherman_anim.blend',
    licence: 'project asset (procedurally built)',
    scale: 0.22,
    lod: 'hero',
    clips: { drive: 'Drive', fire: 'Fire' },
    tags: { turret: 'Turret_Pivot', gun: 'Gun_Pivot', muzzle: 'GunMuzzle' },
    fallback: 'sherman_troop',
  },
  sherman_troop: {
    id: 'sherman_troop',
    file: 'm4a1_sherman_troop.glb',
    url: new URL('m4a1_sherman_troop.glb', MODEL_BASE).href,
    source: 'assets/models/m4a1_sherman_anim.blend',
    licence: 'project asset (procedurally built)',
    scale: 0.22,
    lod: 'troop',
    clips: { fire: 'Fire' },
    tags: { turret: 'Turret_Pivot', gun: 'Gun_Pivot', muzzle: 'GunMuzzle' },
  },
};

/** Presentation tuning, safe to change without touching rules. */
export const VIEW_TUNING = {
  treadRate: 0.9, // drive clip timeScale per world unit/second of tank speed
  shadow: { width: 0.95, length: 1.55, opacity: 0.42 },
};
