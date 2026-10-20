# M4 Sherman 3D Model — Pre-Research Report (For 坦克大战3D / Steel Bastion 3D)
*Generated: 2026-10-15 | Sources: 15+ | Confidence: High (free sources verified on official pages; paid-pack price for one itch.io item unverified)*

## Executive Summary

Real M4 Sherman models exist and are immediately usable. The strongest free option is **Dezryelle's low-poly Sherman series on Sketchfab (CC BY 4.0, free download, 25k–40k triangles, historically accurate, untextured)** — three variants cover our GDD eras. The strongest **structural** fit is the paid **Lowpoly Tank Pack 01 (itch.io)**: every tank ships pre-split into **body / turret / barrel** — exactly the hierarchy our Three.js demo needs — and includes Tiger II + T-34-76, covering two more tanks in our roster. For a zero-attribution, zero-cost, stylized path, **Quaternius' Animated Tanks Pack (CC0)** matches the GDD's "chunky toy-like" art direction. Meshy (API already integrated in our toolbox) is a viable fallback but outputs single-mesh models that require manual turret separation.

**Bottom line: start with the free Sketchfab CC-BY Sherman, verify turret separation after download; buy the itch pack (~$5 class) if we want the perfect 3-part hierarchy plus Tiger/T-34 coverage.**

## 1. Free Downloadable M4 Models (Sketchfab, CC BY)

The author **Dezryelle** publishes a historically accurate low-poly Sherman family, all free and downloadable:

| Model | Tris | License | Notes |
|---|---|---|---|
| Low Poly M4 Early (75) | 30k | CC BY 4.0 | mid-war, "suitable for FPS games", untextured/unrigged |
| Low Poly M4A3(75)W | 25k | CC BY 4.0 | late war; 309 downloads; OBJ confirmed by author; UV-unwrapped |
| Low Poly M4A3(76) HVSS | 34.6k | CC BY 4.0 | late-war 76mm — closest to our Sherman's 75mm-era look |
| M4A3E8 "Easy Eight" (Latin Tiro) | 40.8k | CC BY 4.0 | 2024 model, second-ever by author |

- Strengths: free, immediate, real Sherman silhouettes, web-friendly tri counts ([Sketchfab model pages](https://sketchfab.com/3d-models/low-poly-m4a375w-sherman-tank-0d5533e114bf4849bc8c9213e4ee9cf9))
- Weaknesses: **untextured** (we must add materials — but flat/olive PBR in Blender is quick), **turret separation not stated on the page** (must download and inspect the scene hierarchy in Blender; a Blender-authored model very likely has separate hull/turret objects)
- License cost: credit line in game credits (CC BY requires attribution)
- Other Sketchfab CC-BY options exist (e.g., [Destroyed M4A1E9 Sherman](https://sketchfab.com/3d-models/destroyed-m4a1e9-sherman-931f910486234ea683ce9fde5f9d008e), fully textured in Substance Painter — a destroyed variant, useful for the GDD's "persistent wreck/crater" juice, not as the player tank)

## 2. Game-Ready Packs with the Right Structure

**Best structural match — Lowpoly Tank Pack 01 (IsolatedSoulStudio, itch.io, paid):**
- 6 WWII tanks: **M4 Sherman, Tiger II, Panzer IV, IS2, KV-2, T34-76** — covers Sherman (player) + Tiger (roster tank #2) + a T-34 stand-in for the modern slot
- **"Each model separated into three parts (body, turret, barrel)"** — exactly our control scheme (hull heading + independent turret yaw + muzzle point)
- 10k tris each, 1024×1024 color texture, FBX/DAE (Blender converts to GLB in one step)
- 1 free sample (Panzer IV) to evaluate before buying; exact price must be confirmed on the itch page (fetch failed during research; rating page shows low review count — try the sample first)
- ([itch.io listing](https://itch.io/game-assets/tag-low-poly/tag-tanks), [pack page](https://itch.io/jam/procjam/rate/514467))

**Free + CC0 + animated — Quaternius Animated Tanks Pack:**
- 4 stylized animated tank models, FBX/OBJ/Blend, **CC0** (no attribution, commercial OK) ([pack page](https://quaternius.com/packs/animatedtanks.html), [FAQ confirms CC0](https://quaternius.com/faq.html))
- ~6.5k tris per tank with 4 animation tracks ([model details](https://www.get3dmodels.com/vehicles/tank/))
- Not historically a Sherman — but matches the GDD's LOCKED art direction: "chunky toy-like proportions"
- Also mirrored on Poly Pizza ([Animated Tank Pack, 4 models](https://poly.pizza/u/Quaternius/Lists))

**Other itch.io options:** Toy Tanks 3D pack (Artisau, stylized), Tank & War Tactic Assets (monogon, Advance-Wars-like), Stylized Low Poly Tank Pack (Retgun, free, GLB included, credit required, no-AI-training clause), WW2 Tanks and Tank Crews PSX (rigged, retro style, €15).

## 3. Paid Premium Models (Reference Price Points)

| Model | Price | Tris | Fit for web demo |
|---|---|---|---|
| CGTrader "Sherman M4 Gameready Rigged" (CG-cut) | paid | 55k (5 objects: Body/Equipment/**Tower**/Wheels/Tracks) | Good: turret is its own object; 4K PBR; suspension rig; file 144MB → needs heavy optimization |
| TurboSquid "Combat M4 Sherman" (3D Molier) | **$149** | 470k | Overkill: offline/render grade, too heavy for web |
| Fab "M4 Sherman Tank Challenger" | paid | 10k, GLB native | Light and web-native; single mesh, would need turret split |
| CGTrader M4A1 Sherman (ELR-) | **$74** | 271k | Rigged (turret rotation, gun elevation) but SubD-heavy; over budget |

([CGTrader listing](https://www.cgtrader.com/3d-models/military/military-vehicle/sherman-m4-gameready-rigged), [TurboSquid listing](https://www.brand.turbosquid.com/3d-models/m4-sherman-tank-2264775), [Fab listing](https://www.fab.com/listings/f222237e-931e-4e2a-88b7-094113f0d830?lang=en), [M4A1 listing](https://cghub.one/item/m4a1-sherman-3d-model-149585))

Verdict: premium market exists ($74–$149 band) but is unnecessary at demo stage; web constraints favor ≤30k tris.

## 4. AI Generation Path (Meshy — API already in our toolbox)

- Meshy 6: text/image → textured mesh in ~1 minute; **hard-surface accuracy 80–90%** — tanks/vehicles are its strength ([3D Next review](https://3dnext.com/reviews/meshy-ai-3d-generation/), [AIToolApp review](https://aitoolapp.com/meshy-ai))
- Exports GLB directly; polygon budget controllable (3k–100k) via remeshing
- Real case: Stradion Studios cut tank-combat asset pipeline from ~4h to ~4min ([IJERT comparison](https://www.ijert.org/best-ai-3d-model-generators-for-game-developers-creators-2026))
- **Limitations that matter to us:** output is typically a single merged mesh — the turret is NOT a separate node, so hull/turret split must be done manually in Blender; free tier = CC BY 4.0, commercial needs paid plan ([Meshy review](https://www.suxiaodh.com/sites/504.html), [ToolMango review](https://toolmango.com/tools/meshy))
- Since the 飞叔 AI toolbox already integrates the Meshy API, this is the cheapest experiment path: image-to-3D from a Sherman reference photo, then one Blender session to separate turret + barrel.

## 5. Technical Requirements (Three.js / web build)

1. **Format:** GLB (GLTF) — all candidates convertible via Blender 5.0.1 (installed locally)
2. **Hierarchy requirement:** hull / turret / barrel as separate nodes — our demo code drives `turret.rotation.y` independently; a merged mesh breaks the mouse-aim mechanic
3. **Budget:** ≤30k tris ideal (Sketchfab models fit; TurboSquid premium does not); compress with Draco/meshopt (`gltf-transform`), target <2MB per model
4. **Muzzle point:** we attach a `muzzle` Object3D at the barrel tip for bullet spawn — needs the barrel node (or we place it by offset)
5. **Licensing for shipping:** CC BY (Sketchfab/Meshy-free) → credits screen; CC0 (Quaternius) → none; paid (itch/CGTrader/Fab) → marketplace RF terms

## Key Takeaways (Ranked Recommendation)

1. **Do first (free, today):** Download Dezryelle's M4A3(75)W (or M4 Early) from Sketchfab → open in Blender → check if turret is a separate object → add olive PBR material → export GLB → drop into the demo. Cost: 0 + one credit line.
2. **If structure/roster matters (small budget):** Test IsolatedSoulStudio's free Panzer IV sample → if quality is good, buy Lowpoly Tank Pack 01 for the ready-made body/turret/barrel split **plus Tiger II and T-34-76 for our other two roster tanks**.
3. **If stylized is acceptable (CC0, zero obligations):** Quaternius Animated Tanks Pack — matches the GDD's toy-like art direction, includes animations.
4. **Fallback/experiment:** Meshy image-to-3D via our existing API — fast, but plan one Blender session for turret separation.
5. **Avoid:** $74–$149 premium models at demo stage — wrong tri budget, wrong pipeline stage.

## Sources

1. [Low Poly M4A3(75)W Sherman — Sketchfab (Dezryelle, CC BY 4.0)](https://sketchfab.com/3d-models/low-poly-m4a375w-sherman-tank-0d5533e114bf4849bc8c9213e4ee9cf9) — primary free candidate
2. [Low Poly M4 Early — Sketchfab (Dezryelle)](https://sketchfab.com/3d-models/low-poly-m4-early-19f4f2295b6044c88a716ca371f3e502) — 30k tris, CC BY
3. [Low Poly M4A3(76) HVSS — Sketchfab (Dezryelle)](https://sketchfab.com/3d-models/low-poly-m4a376-hvss-710e93ef16c84160a5e8b980ce07163a) — 34.6k tris, CC BY
4. [M4A3E8 Sherman FREE — Sketchfab (Latin Tiro)](https://sketchfab.com/3d-models/m4a3e8-sherman-free-df99cad8d1f84e01888f2cde158bfb65) — 40.8k tris, CC BY
5. [Destroyed M4A1E9 Sherman — Sketchfab](https://sketchfab.com/3d-models/destroyed-m4a1e9-sherman-931f910486234ea683ce9fde5f9d008e) — textured wreck variant
6. [Lowpoly Tank Pack 01 — IsolatedSoulStudio (itch.io)](https://itch.io/jam/procjam/rate/514467) — body/turret/barrel split, 6 WWII tanks
7. [itch.io tanks tag browse](https://itch.io/game-assets/tag-low-poly/tag-tanks) — 28 low-poly tank packs
8. [Quaternius Animated Tanks Pack](https://quaternius.com/packs/animatedtanks.html) — CC0, 4 animated tanks
9. [Quaternius FAQ (CC0 confirmation)](https://quaternius.com/faq.html)
10. [Quaternius tank model specs — get3dmodels](https://www.get3dmodels.com/vehicles/tank/) — 6.5k tris, 4 animations
11. [Poly Pizza — Quaternius Animated Tank Pack mirror](https://poly.pizza/u/Quaternius/Lists)
12. [Sherman M4 Gameready Rigged — CGTrader](https://www.cgtrader.com/3d-models/military/military-vehicle/sherman-m4-gameready-rigged) — 5-object structure, suspension rig
13. [M4 Sherman Tank — TurboSquid ($149, 470k tris)](https://www.brand.turbosquid.com/3d-models/m4-sherman-tank-2264775)
14. [M4 Sherman Tank Challenger — Fab (10k tris GLB)](https://www.fab.com/listings/f222237e-931e-4e2a-88b7-094113f0d830?lang=en)
15. [M4A1 Sherman rigged — CGTrader/cghub ($74)](https://cghub.one/item/m4a1-sherman-3d-model-149585)
16. [Meshy review — 3D Next](https://3dnext.com/reviews/meshy-ai-3d-generation/) — hard-surface 80–90%, pricing tiers
17. [Best AI 3D generators 2026 — IJERT](https://www.ijert.org/best-ai-3d-model-generators-for-game-developers-creators-2026) — Stradion tank-pipeline case
18. [Meshy review — AIToolApp (Meshy 6 hands-on)](https://aitoolapp.com/meshy-ai) — single-mesh limitation, workflow

## Methodology

Searched 9 queries across web search. Analyzed 15+ unique sources; deep-read the Sketchfab model page (Dezryelle M4A3(75)W) and pack listing pages. Sub-questions investigated: (1) free CC-licensed M4 models, (2) pre-split game-ready tank packs, (3) premium price points, (4) AI-generation viability, (5) web/Three.js technical constraints. Gap acknowledged: exact price of Lowpoly Tank Pack 01 unverified (page fetch failed); turret-separation status of Sketchfab models requires post-download inspection.
