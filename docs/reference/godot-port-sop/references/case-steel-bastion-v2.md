# 案例：钢铁防线 3D · Sherman Edition v2 → Godot 4

> **仓库已重组（2026-10-20）**：活动版本是 `versions/v3`，v2 归档在 `versions/v2`。
> 下文路径里的 `v2/` 在 v3 上对应 `versions/v3/`；玩法/数值/资产/测试与 v2 一致。
> 试点结果与修订见 `references/pilot-findings.md`。

> 这是把 SOP 套到当前项目的具体清单。执行时仍以 `v2/` 源码为准；本文件帮你快速定位
> “有什么、改哪里、先做什么、哪里会翻车”。

---

## 1. 源项目事实

| 项 | 值 |
|---|---|
| 源目录 | `v2/`（根目录 `index.html` 是旧版，不作为移植基线） |
| 版本 | `2.0.0` |
| 入口 | `v2/index.html` + `src/main.js` |
| 启动 | `cd v2 && python3 -m http.server 4173` → `http://127.0.0.1:4173/` |
| 测试 | `cd v2 && npm test`（`node:test`，当前 14 项全过） |
| 源码规模 | `src/` 约 3,590 行；`assets/` 约 1.8 MB；`vendor/` Three.js |
| 目标引擎 | Godot 4.7.1（本机 `godot --version` 已验证） |
| 验收级别 | P1：行为等价 + 表现尽量等价；不承诺像素级 |

**只读清单**：`v2/` 全部；`assets/models/m4a1_sherman_anim.blend` 是模型源文件，移植期间不改。

---

## 2. 五类契约清单

### 2.1 内容（C1）

**玩家坦克**（`src/content/tanks.js`）：

| ID | HP | 速度 | 转向 | 射速(s) | 伤害 | 弹速 | 炮塔转速 | 炮口 | 技能（CD） |
|---|---|---|---|---|---|---|---|---|---|
| `sherman` | 100 | 3.0 | 2.8 | 0.5 | 25 | 9 | 6.0 | 0.82 | 烟幕 5s（20s） |
| `tiger` | 160 | 1.8 | 1.6 | 1.2 | 60 | 10 | 3.6 | 0.86 | 穿甲弹（15s，贯穿 2） |
| `t90` | 120 | 2.6 | 2.4 | 0.4 | 30 | 12 | 7.0 | 0.82 | 反应装甲 3 次/30s（25s） |

涂装：`paint.olive / oliveDark / star`，是表现提示，不影响规则。

**敌人**（`src/content/enemies.js`，实际 HP = `hp × 25`）：

| ID | HP | 速度 | 射速 | 伤害 | 射程 | 分数 | 缩放 | 备注 |
|---|---|---|---|---|---|---|---|---|
| `scout` | 25 | 3.6 | 1.5 | 10 | 5 | 100 | 0.8 | 看不见时蛇形 |
| `line` | 75 | 1.6 | 2.0 | 20 | 7 | 200 | 1.0 | 直线推进 |
| `sniper` | 50 | 2.2 | 2.5 | 30 | 9 | 300 | 0.9 | 远距离瞄准 0.55s，近身拉开 |

**关卡**（`src/content/levels.js`）：

- 13×13，tile 码：`0` 空、`1` 砖、`2` 钢、`3` 水、`4` 森林、`5` 冰、`9` 鹰徽。
- 波次：`t=0` 3 辆、`t=15` 3 辆、`t=30` 4 辆，共 10 辆；`maxOnField=4`。
- 出生列：`[1, 4, 8, 11]`；出生点 `z=-6`，世界 `x = col - 6`。
- 鹰徽：`row=12, col=6` → 世界 `(0, 6)`。
- 掩体：`[12,4], [12,5], [12,7], [12,8]`（加固时砖→钢，15 秒后恢复）。
- 玩家出生：`(0, 5)`，朝向 `PI`（面向 -Z / 屏幕上方，敌军出生方向；鹰徽在身后 +Z）。
- 车库空场：`SHOWROOM` 全 0、无波次。

**道具**（`src/content/powerups.js`，权重合计 82）：

| ID | 权重 | 效果 |
|---|---|---|
| `star` | 20 | 射速间隔 ×0.7（下限 0.22），+500 分 |
| `grenade` | 12 | 全屏消灭当前敌人 |
| `shovel` | 12 | 鹰徽掩体加固 15s，+500 |
| `clock` | 14 | 全体敌人冻结 8s，+500 |
| `helmet` | 16 | 护盾 10s，+500 |
| `tank` | 8 | 备用坦克 +1 |

额外：任何道具被 Sherman 拾取时，`repair=5`（每秒回 2 HP）。

**资产**（`src/content/assets.js`）：

| ID | 文件 | LOD | clips | tags | 备注 |
|---|---|---|---|---|---|
| `sherman_hero` | `m4a1_sherman_hero.glb` | hero | `Drive`, `Fire` | `Turret_Pivot`, `Gun_Pivot`, `GunMuzzle` | 146 节独立履带；玩家 |
| `sherman_troop` | `m4a1_sherman_troop.glb` | troop | `Fire` | 同上 | 履带合并；敌人；无 Drive |

- 统一 `scale = 0.22`；**+Z 车头、+Y 向上**；原点在履带接地面。
- 材质名：`Sherman_Olive`、`Sherman_OliveDark`、`Sherman_Star`。
- `VIEW_TUNING.treadRate = 0.9`；阴影尺寸 `0.95 × 1.55`，透明度 `0.42`。

### 2.2 状态（C2）

`createBattle()` 的 `state`：

```
phase(battle|won|lost), tankId, time, score, killed, totalEnemies,
wave, spawnQueue[], spawnTimer, spawnIndex, respawnTimer, skillCd, fortTimer,
eagle{r,c,x,z,alive},
player{id,spec,x,z,heading,turretYaw,hp,maxHp,fireInterval,fireCd,damage,bulletSpeed,
       lives,invuln,shield,smoke,ap,reactiveLeft,reactiveTimer,repair,alive,
       vel{x,z},throttle,turn,speed,moving},
enemies[{id,type,prof,x,z,heading,turretYaw,hp,maxHp,scale,fireCd,aimTimer,stuck,
         jitterTimer,jitterYaw,freezeTimer,hitFlash,spawnTimer,seed,alive,moving,inForest}],
bullets[{id,x,z,yaw,speed,damage,from,ownerId,ap,apLeft,life}],
pickups[{id,def,x,z,life}]
```

规则：

- `hp` 用点数；敌人 `hp = prof.hp * 25`。
- 位置是格/米；角度弧度；时间秒。
- `spec`/`prof`/`def` 是内容引用，不参与 trace 比较（只记 ID）。
- `hitFlash`、`jitterTimer` 等是表现/计时提示；如果 Godot 放进 view，要保证规则不依赖。

### 2.3 命令（C3）

| 命令 | 参数 | 语义 | 时机 |
|---|---|---|---|
| `setMove(throttle, turn)` | -1..1 | 每帧移动意图；core clamp | 每帧 |
| `setTrigger(on)` | bool | 按住开火；冷却由 core 判断 | 每帧 |
| `aimAt(x, z)` | 世界坐标 | 炮塔目标；按 `turretSpeed` 逐步转 | 鼠标移动 |
| `useSkill()` | — | 返回是否成功；冷却/存活由 core 判断 | 按键边沿 |
| `stop()` | — | 清空输入；不改 phase | 结算 |

### 2.4 事件（C4，共 19 种）

| type | 主要 payload | 用途 |
|---|---|---|
| `fire` | `from, shooterId, x, z, yaw, ap?` | 炮口焰、后坐、音效 |
| `explosion` | `x, z, scale` | 爆炸、震屏、音效 |
| `impact` | `x, z, kind` | 砖/钢/鹰徽命中火花 |
| `spark` | `x, z` | 钢墙跳弹 |
| `tileChanged` | `r, c, tile, previous` | 拆砖、加固/失效 |
| `spawn` | `id, type, x, z, scale` | 出生特效 |
| `respawn` | `id, x, z` | 复活特效 |
| `pickupDropped` | `id, x, z, powerupId, color` | 掉落闪光 |
| `pickup` | `powerupId, x, z, label` | 拾取反馈 |
| `pickupExpired` | `id` | 消失 |
| `playerHit` | `x, z, damage` | 受击闪白/震屏 |
| `shieldBlock` | `x, z` | 护盾抵挡 |
| `reactiveBlock` | `x, z, left` | 反应装甲抵挡 |
| `skill` | `kind, x?, z?` | 烟幕/穿甲/反应装甲 |
| `message` | `text` | HUD 大字 |
| `enemyHit` | `id, x, z, damage` | 受击色/数字 |
| `enemyKilled` | `id, x, z, score` | 爆炸/计分 |
| `lifeLost` | `lives` | 生命 UI |
| `gameover` | `win, reason, score` | 结算 |

顺序约束：同一帧内按 core 产生顺序消费；`gameover` 后仍可能有爆炸/子弹事件，HUD 不应
因此复活。

### 2.5 资产（C5）

见 2.1 的表。额外要求：

- 在 Godot 里递归找节点；不要假设根节点就是 `M4A1_Sherman`。
- `troop` 没有 `Drive` clip：`TankRig` 必须允许 `clips.drive = null`，不要报错。
- `hero` 的 146 节履带是 draw call 大头；先测，再决定 MultiMesh/合并。
- 导入后检查包围盒：车长约 1.53、宽约 0.55、高约 0.76（`scale=0.22`）。

---

## 3. 规则移植要点

### 3.1 更新顺序

```
updatePlayer → updateWaves → updateEnemies → updateBullets → updatePickups → updateFortify → checkWin
```

顺序不能换。尤其：

- `updateWaves` 先推波次再生成敌人；`maxOnField=4`。
- `updateEnemies` 在子弹前，敌人本帧开火会先生成子弹，再被 `updateBullets` 推进。
- `checkWin` 在最后，避免清场当帧提前结束导致掉落/爆炸丢失。

### 3.2 移动与碰撞

- `TANK_R = 0.4`、`BULLET_R = 0.14`。
- 实心格：砖、钢、水、鹰徽；森林可过、阻挡远距离视线；冰面改变加速度。
- 玩家非冰面：直接 `tryMove(dx * speed * dt, dz * speed * dt, TANK_R)`；撞墙不滑。
- 冰面：速度插值 `ICE_ACCEL=3`，撞墙速度 ×0.6。
- 敌人移动：转向速率 3.2 rad/s；`|delta| < 0.9` 才前进；卡住 0.35s 后抖动 0.7s。
- 敌人与玩家重叠时互相推开（`TANK_R * 1.7`）。

### 3.3 战斗

- 玩家子弹：从炮口 `muzzle` 偏移（0.82–0.86）发出，速度 9/10/12，寿命 2.6s，越界 ±7.5。
- 敌人子弹速度 7.5；伤害来自 `prof.dmg`。
- 砖：普通弹摧毁并消失；AP 弹继续穿透。
- 钢：普通弹跳弹消失；AP 弹摧毁并继续。
- 鹰徽：任何子弹（含玩家）命中 → `destroyEagle()` → 失败。
- 敌人受击 `hitFlash=0.12`；死亡移除、加分、22% 掉落。
- 玩家受击：无敌/护盾/反应装甲依次判定；Tiger 伤害 ×0.8；死亡扣命，1.5s 后复活。
- 胜利：波次放完、生成队列空、场上无敌人。

### 3.4 技能/道具/加固

- Sherman：`smoke=5`，`skillCd=20`；烟幕内敌人无法锁定。
- Tiger：`ap=true`，`skillCd=15`；下一发 AP，`apLeft=2`。
- T-90：`reactiveLeft=3`，`reactiveTimer=30`，`skillCd=25`。
- 道具按权重抽取；`grenade` 逐个 `killEnemy(false)`（不掉落）。
- `fortify` 把掩体砖变钢，`fortTimer=15`；到期钢变砖并发 `message`。

### 3.5 确定性

- 源 `createBattle` 接受 `seed`；`app/game.js` 用 `Date.now() ^ Math.random()` 生成。
  **移植/录像时必须注入固定 seed**，否则 trace 不可复现。
- 所有随机走 `mulberry32`；`rand.chance/range/weighted` 的调用次数必须一致。
- 不要用 Godot 的 `randf()`、`Array.shuffle()`、`Dictionary` 无序遍历。

---

## 4. Godot 文件映射（建议）

| 源 | Godot | 类型 | 门禁 |
|---|---|---|---|
| `src/core/constants.js` | `core/constants.gd` | rules | G3 |
| `src/core/rng.js` / `shared/random.js` | `core/rng.gd` | rules | G3 |
| `src/core/grid.js` | `core/grid.gd` | rules | G3 |
| `src/core/battle.js` | `core/battle.gd` | rules | G3 |
| `src/content/*.js` | `content/*.json` + `content/content_db.gd` | content | G1/G5 |
| `src/app/game.js` | `app/game.gd` | app | G4 |
| `src/main.js` | `main.gd` + `main.tscn` | app | G2 |
| `src/view/stage.js` | `view/stage.gd` + `stage.tscn` | view | G2/G6 |
| `src/view/world.js` | `view/world.gd` | view | G4 |
| `src/view/tanks.js` | `view/tank_layer.gd` | view | G4 |
| `src/assets/tankRig.js` | `view/tank_rig.gd` | assets/view | G4 |
| `src/assets/modelStore.js` | `assets/model_store.gd` | assets | G1 |
| `src/assets/procedural.js` | `assets/textures/*.png` + `view/water.gdshader` | assets | G6 |
| `src/view/projectiles.js` | `view/projectile_layer.gd` | view | G4 |
| `src/view/fx.js` | `view/fx.gd` + `view/fx/*.tscn` | view | G6 |
| `src/view/camera.js` | `view/camera_rig.gd` | view | G4/G6 |
| `src/view/hud.js` | `view/hud.tscn` + `view/hud.gd` | view | G6 |
| `src/platform/input.js` | `platform/input_router.gd` | platform | G4 |
| `src/platform/audio.js` | `platform/audio.gd` + `assets/audio/*.wav` | platform | G6 |
| `src/platform/storage.js` | `platform/save.gd` | platform | G6 |
| `tests/*.mjs` | `tests/test_core.gd`、`test_contract.gd`、`test_trace.gd` | tests | G3/G5 |
| `docs/game-architecture.md` | `godot/docs/architecture.md` | docs | — |

建议目录：

```
godot/
├── project.godot
├── main.tscn / main.gd
├── core/{constants,rng,grid,battle}.gd
├── content/{content_db.gd,tanks.json,enemies.json,levels.json,powerups.json,assets.json,view_tuning.json}
├── app/game.gd
├── view/{stage.tscn,stage.gd,world.gd,tank_layer.gd,tank_rig.gd,
│        projectile_layer.gd,fx.gd,camera_rig.gd,hud.tscn,hud.gd}
├── platform/{input_router.gd,audio.gd,save.gd}
├── assets/{models/*.glb,textures/*.png,audio/*.wav}
└── tests/{TestRunner.tscn,test_core.gd,test_contract.gd,test_trace.gd,golden/*.json}
```

---

## 5. 里程碑（按本项目估算）

| 里程碑 | 内容 | 门禁 | 相对工作量 |
|---|---|---|---|
| M0 | 基线 + 五类契约 + 5 条 trace | G0/G1 | S–M |
| M1 | Godot 工程骨架 + 坐标/输入/主循环 | G2 | S |
| M2 | `core` 全量移植 + 源测试 + trace 回放 | G3 | M–L |
| M3 | 一辆 Sherman + 一类敌人 + 13×13 + 拆砖 + 鹰徽失败 | G4 | M |
| M4 | 3 坦克/3 敌人/3 波/技能/道具/生命/胜负 | G5 | M–L |
| M5 | FX/相机/HUD/音频/存档/性能 | G6 | L |
| M6 | 导出、验收、文档、tag | G7 | S–M |

一个熟悉 Godot 的开发者，P1 目标大约 10–16 个工作日；如果只做规则 + 基础画面（不做
车库/完整 HUD/音效），可以压到 6–8 天。给用户的排期用区间，不给单点承诺。

---

## 6. 本项目高风险点

| # | 风险 | 影响 | 处理 |
|---|---|---|---|
| 1 | hero 146 节履带 = 146 个 draw call | 帧率 | 先测；MultiMesh/合并；敌人继续 troop；阴影只留车体 |
| 2 | troop 没有 `Drive` clip | 加载报错/敌人不动 | `clips.drive = null` 合法；`TankRig` 不强制 |
| 3 | +Z 车头 vs Godot -Z | 全场朝向反 | 禁用 `look_at`；统一 `rotation.y = heading`；资产层包装 |
| 4 | `scale=0.22` 重复应用 | 模型过大/过小 | 只在 `TankRig` 应用一次；资产检查包围盒 |
| 5 | `procedural.js` 486 行贴图 | 视觉差异/工期 | 先用源脚本烘 PNG 导入；只把水面等动态效果改成 shader |
| 6 | WebAudio 合成音 | 音色/工期 | `OfflineAudioContext` 烘 WAV，不重写合成器 |
| 7 | DOM/CSS HUD | 布局返工 | `Control` + `Theme`；先做信息层级，再抠像素 |
| 8 | `startBattle` 随机 seed | trace 不可复现 | 录像/自动测试注入 seed；生产局才用随机 |
| 9 | Godot `Vector2/3` 是 32 位 | trace 漂移 | 内核用标量 `float`；表现层再组 Vector3 |
| 10 | Drive 变速 + Fire 单次共用一个 player | 开火打断履带/后坐速度错 | 双 AnimationPlayer 或按里程 seek |
| 11 | `Math.imul` 的 32 位语义 | RNG 不同 | 用已验证的 GDScript 版本 + 测试向量 |
| 12 | Web 导出 | 渲染器/线程/音频 | 若必须 Web，从第一天用 `gl_compatibility` 验证 |
| 13 | `Math.round` 与 `roundi` 负半值不同 | 格子索引偏 1 格，碰撞/命中错 | `tc/tr` 用 `int(floor(v + 0.5))` |
| 14 | 数组遍历中 `splice` 删除敌人 | 跳过/重复处理，RNG 次数变 | 复现源迭代语义；用 trace 验证 |

---

## 7. 本项目的验收清单

### 车库

- [ ] 3 张坦克卡：Sherman / Tiger I / T-90，名称、级别、数值、技能文案正确。
- [ ] 选车进入战斗；展示台环绕；模型不被砖墙遮挡。
- [ ] 最高分显示；旧 key `sb3d_sherman_hi` 的行为明确（沿用或迁移）。

### 操作

- [ ] W/S 前进后退，A/D 转向；鼠标炮塔；空格/左键开火（可按住连发）。
- [ ] E 技能；C 追尾/俯视；R 返回车库。
- [ ] 炮塔有限转速（3.6–7.0 rad/s），不是瞬间吸附。

### 战斗

- [ ] 3 波 10 辆，场上最多 4 辆，出生列 1/4/8/11。
- [ ] 砖可拆、钢可挡/AP 可拆、水不可过、森林遮挡远距离视线、冰面滑行。
- [ ] 鹰徽被任何炮弹（含玩家）命中即失败。
- [ ] 3 个技能效果/冷却/持续时间正确。
- [ ] 6 种道具掉落、生效、过期；权重一致。
- [ ] 玩家 3 条命、1.5s 复活；初始无敌 2s、复活无敌 2.5s；Tiger 伤害 ×0.8。
- [ ] 胜利：全灭结算；失败：鹰徽/生命耗尽；结算分数/最高分正确。

### 表现

- [ ] 追尾/俯视相机、肩部偏移、震屏、车库环绕。
- [ ] 炮口焰、后坐、爆炸、烟、火花、履带印、焦痕、护盾、道具。
- [ ] HUD：分数/血量/技能冷却/波次/提示/结算。
- [ ] 音效与事件对齐；无爆音。
- [ ] 1280×720 稳定 60 fps；10 分钟无 orphan 增长。

---

## 8. 开始执行的前 5 条命令

```bash
# 1. 复核源基线
cd v2 && npm test && cd ..

# 2. 建证据目录
mkdir -p port/{contract,traces,evidence/G0,evidence/G1}

# 3. 确认 Godot
godot --version        # 期望 4.7.1.stable 或项目锁定版本

# 4. 生成源哈希
cd v2 && find . -type f -not -path './node_modules/*' -print0 \
  | sort -z | xargs -0 shasum -a 256 > ../port/source-manifest.sha256 && cd ..

# 5. 按 references/contract-extraction.md 创建导出/录像脚本
#    先跑通 content.json，再录 5 条 trace；不要先打开 Godot 建场景
```

前置判断：如果 `npm test` 不是 14 项全过，先把差异写进 `port/BASELINE.md`，再决定是否
缩小移植范围；不要带着不稳定基线进入 G3。
