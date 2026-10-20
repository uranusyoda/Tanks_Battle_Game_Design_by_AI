# 钢铁防线 3D · Sherman Edition — 分层架构

版本：v2.0 · 2026-10-20  
原版入口：`../v1/index.html`（**未修改**，仍可单独运行）  
新版入口：`index.html`（本目录）

---

## 1. 这一版解决什么问题

原版是一个 1685 行的单文件 Demo：坦克数值、敌人 AI、波次、碰撞、Three.js 场景、
程序化贴图、HUD 和模型工厂全部写在同一个 `<script>` 里。换一辆坦克的模型，会同时
牵动：

- 模型工厂、炮塔/炮管节点名、后坐力代码；
- 场景初始化、材质和阴影；
- 玩法数值与技能。

本版把同一个可玩原型重做成**四条边**：

1. **玩法内核**只算结果，不知道 Three.js 和模型文件；
2. **内容数据**只放数值、波次、关卡和资产 ID；
3. **资产层**只负责把 `.glb` 变成可用的坦克 rig；
4. **表现层**只读状态、放事件，不决定胜负。

换模型只改资产清单和 Blender 导出；改数值只改 `content/`；改规则只改 `core/`。

---

## 2. 分层与依赖方向

```
                 ┌────────────────────────────┐
                 │        app/game.js         │  只做装配：输入→命令→事件→表现
                 └───────┬─────────┬──────────┘
                         │         │
        ┌────────────────▼──┐   ┌──▼──────────────────┐
        │   core（纯规则）   │   │  view（Three.js）    │
        │  无 DOM / 无 THREE │   │  场景 / 坦克 / FX    │
        └────────┬───────────┘   └──▲───────────▲──────┘
                 │                   │           │
        ┌────────▼──────────┐   ┌────┴─────┐  ┌──┴──────────┐
        │ content（数据）     │   │ assets   │  │ platform    │
        │ 坦克/敌人/关卡/资产 │   │ 清单/加载 │  │ 输入/音频/存档│
        └────────────────────┘   │ rig/贴图  │  └─────────────┘
                                 └───────────┘
```

依赖规则（由 `tests/core.test.mjs` 自动检查）：

| 层 | 可以依赖 | 禁止 |
|---|---|---|
| `core/` | 自己、`shared/` | Three.js、DOM、`view/`、`assets/`、`content/` |
| `content/` | 无 import（纯数据） | 任何运行时依赖 |
| `assets/` | Three.js、`content/assets.js`、`shared/` | `core/battle.js`、DOM |
| `view/` | Three.js、`assets/`、`core/constants.js`、`content/assets.js` | 修改 `core` 状态 |
| `app/` | `core/`、`content/`、`platform/` | 直接创建 Three.js 对象（通过 view 完成） |
| `main.js` | 全部 | — |

`core` 不 import `content`：坦克表、敌人表、关卡都由 `createBattle({...})` 注入。
这样同一套规则可以跑别的关卡或别的数值，测试也不需要浏览器。

---

## 3. 目录职责

```
versions/v2/
├── index.html                 页面外壳：canvas + HUD DOM + importmap
├── css/hud.css                HUD / 车库 / 结算样式
├── src/
│   ├── main.js                启动：建场景、加载模型、装配 Game、主循环
│   ├── app/game.js            一局的编排：模式、输入读取、事件分发、镜头/粒子
│   ├── core/                  ★ 玩法内核
│   │   ├── constants.js       棋盘常量、tile 码、角度/坐标换算
│   │   ├── grid.js            格子、圆-格碰撞、滑动、视线、拆格
│   │   ├── rng.js             可注入的确定性随机
│   │   └── battle.js          移动/炮塔/开火/子弹/敌人 AI/波次/道具/技能/胜负
│   ├── content/               ★ 内容与数值
│   │   ├── tanks.js           3 辆可选坦克的数值、技能、涂装、模型 LOD
│   │   ├── enemies.js         3 类敌人
│   │   ├── levels.js          13×13 关卡、3 波、出生列、鹰徽掩体、车库空场
│   │   ├── powerups.js        6 种道具权重
│   │   └── assets.js          资产清单：稳定 ID、GLB、缩放、clip、节点 tag
│   ├── assets/                ★ 资产层
│   │   ├── modelStore.js      GLTFLoader、缓存、LOD fallback
│   │   ├── tankRig.js         glTF → turret/gun/muzzle + Drive/Fire + 涂装/透明
│   │   └── procedural.js      地面/砖/钢/水/树叶/天空/FX 贴图
│   ├── view/                  ★ 表现层
│   │   ├── stage.js           renderer、天空、光照、远景、尘埃、指针拾取
│   │   ├── world.js           格子场景、鹰徽、水面、砖块破坏/加固
│   │   ├── tanks.js           玩家/敌人/车库展示的 rig 管理
│   │   ├── projectiles.js     炮弹可视化
│   │   ├── fx.js              爆炸/烟/炮口焰/履带印/焦痕/护盾/道具
│   │   ├── camera.js          追尾/俯视/车库环绕/震屏
│   │   └── hud.js             分数/血量/技能冷却/波次/车库/结算
│   ├── platform/              平台端口
│   │   ├── input.js           键鼠 → 意图
│   │   ├── audio.js           WebAudio 音效
│   │   └── storage.js         最高分
│   └── shared/random.js       纯 PRNG（规则与程序化贴图共用）
├── assets/models/             hero / troop GLB + manifest
├── tests/                     node:test：规则 + 资产契约 + 分层约束
└── docs/game-architecture.md  本文件
```

---

## 4. 一帧的数据流

```
键盘/鼠标
  → platform/input.js           只记录按键、鼠标 NDC、鼠标按下
  → app/game.js readInput()     转成 throttle / turn / trigger / aimAt
  → core.commands.*             意图进入内核
  → core.update(dt)             移动、炮塔、AI、子弹、道具、胜负
  → core.drainEvents()          语义事件
  → app.handleEvent()           分发给表现层
      ├─ view/fx.js             爆炸、炮口焰、烟、履带印、焦痕
      ├─ view/world.js          tileChanged → 拆块/加固
      ├─ view/tanks.js          rig.fire() / 模型增删
      ├─ view/camera.js         震屏
      ├─ view/hud.js            消息
      └─ platform/audio.js      音效
  → view/tanks.sync(state)      读 state 摆位置、炮塔角、履带速度、透明/受击色
  → view/projectiles.sync()     读 state.bullets
  → view/fx.syncPickups()       读 state.pickups
  → stage.render()
```

关键点：**表现层只读 `state` 和事件，不往回写**。子弹命中、拆砖、得分、胜负都由
`core` 决定；`view` 里没有任何“看起来打中了所以扣血”的判断。

---

## 5. 契约

### 5.1 命令（app → core）

| 方法 | 参数 | 说明 |
|---|---|---|
| `setMove(throttle, turn)` | -1…1 | 每帧写入，松开为 0 |
| `setTrigger(on)` | bool | 按住空格/左键为 true，可连发 |
| `aimAt(x, z)` | 世界坐标 | 鼠标射线与地面交点 |
| `useSkill()` | — | 冷却/存活由内核判断，返回是否成功 |
| `stop()` | — | 结算时清空输入 |

### 5.2 事件（core → app）

| type | 字段 | 用途 |
|---|---|---|
| `fire` | `from, shooterId, x,z,yaw,ap` | 炮口焰、音效、后坐动画 |
| `explosion` | `x,z,scale` | 爆炸、震屏、音效 |
| `impact` / `spark` | `x,z,kind` | 砖/钢/鹰徽命中火花 |
| `tileChanged` | `r,c,tile,previous` | 砖块销毁、掩体加固/失效 |
| `spawn` / `respawn` | `id,x,z,...` | 出生特效 |
| `pickupDropped` / `pickup` / `pickupExpired` | `id,x,z,powerupId` | 道具表现 |
| `playerHit` | `x,z,damage` | 受击闪光 |
| `shieldBlock` / `reactiveBlock` | `x,z` | 护盾/反应装甲反馈 |
| `skill` | `kind,x,z` | 烟幕、穿甲、反应装甲反馈 |
| `enemyHit` / `enemyKilled` | `id,x,z,score` | 受击色、爆炸、计分 |
| `lifeLost` | `lives` | 剩余命 |
| `message` | `text` | HUD 大字 |
| `gameover` | `win,reason,score` | 结算，切模式 |

事件是**一次性语义通知**，不是逐帧状态。位置、血量、冷却等每帧状态直接读
`core.state`。

### 5.3 资产清单（content/assets.js）

```js
sherman_hero: {
  url, scale: 0.22, lod: 'hero',
  clips: { drive: 'Drive', fire: 'Fire' },
  tags: { turret: 'Turret_Pivot', gun: 'Gun_Pivot', muzzle: 'GunMuzzle' },
  fallback: 'sherman_troop',
}
```

- 玩法只认 `tanks[id].model.lod`（`hero` / `troop`），不认文件路径。
- 换模型：改 `assets.js` 的 `url` + `scale` + 节点 tag；其余代码不动。
- 资产加载失败会退回另一档 LOD，并在控制台记录；游戏仍能启动。

---

## 6. 模型与动画管线

源文件：`../../assets/models/m4a1_sherman_anim.blend`（240 帧演示动画）。

演示时间线不能直接当游戏动画用：它把车体位移、炮塔转角、后坐、炮口闪光和
履带滚动烘在同一条时间线上。导出脚本 `../../tools/blender/export_game_sherman.py`
会：

1. 删掉预览相机/灯光/地面/箱子；
2. 清掉车体位移（位置由规则决定）；
3. 清掉炮塔转角（角度由鼠标/玩家决定）；
4. 把履带链节和负重轮重烘成 **Drive** 无缝循环
   （73 节履带、4 帧/节、周长 12.17 m，轮子转整圈避免循环跳变）；
5. 把炮管三件套重烘成 **Fire** 单次后坐；把源文件里位于炮尾的 `GunMuzzle`
   空节点移到炮口，保证炮口焰/子弹起点对齐；
6. 合并车体/炮塔静态网格；
7. 导出两档 LOD：

| 文件 | LOD | 说明 |
|---|---|---|
| `m4a1_sherman_hero.glb` | hero | 保留 146 节独立履带板 + 18 个轮子，`Drive` + `Fire` |
| `m4a1_sherman_troop.glb` | troop | 履带合并成左右两条、轮组各合并为一，只有 `Fire` |

玩家用 hero（履带会滚），最多 4 辆敌人用 troop（约 20 个 draw call/辆）。
两档共用同一套节点名、材质和朝向，`tankRig.js` 不需要分支。

规格：

- 源单位米；游戏统一 `scale = 0.22`（车长约 1.53，宽约 0.55，高约 0.76）。
- glTF 朝向：**+Z 车头，+Y 向上**，原点在履带接地面。
- 节点：`M4A1_Sherman` → `Turret_Pivot` → `Gun_Pivot` → `GunMuzzle`。
- 游戏里直接 `turret.rotation.y = yaw`、`gun.rotation.x = pitch`，
  `GunMuzzle.getWorldPosition()` 取炮口。

重新生成（在仓库根目录运行）：

```bash
SHERMAN_EXPORT_OUT="$PWD/versions/v2/assets/models" \
/Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
  --factory-startup --python tools/blender/export_game_sherman.py
```

默认输出目录是 `versions/v3/assets/models`（当前迭代版本）。

---

## 7. 改什么去哪里

| 想改 | 改这里 | 不需要动 |
|---|---|---|
| 坦克血量/速度/射速/伤害/技能冷却 | `src/content/tanks.js` | core / view / 模型 |
| 敌人血量/速度/射程/分数 | `src/content/enemies.js` | core / view |
| 波次时间、敌人组合、出生列 | `src/content/levels.js` | core / view |
| 关卡格子、鹰徽位置、掩体 | `src/content/levels.js` | core |
| 道具权重/颜色 | `src/content/powerups.js` | core |
| 换一辆坦克模型 | `src/content/assets.js` + 重新导出 GLB | core / view |
| 涂装颜色 | `src/content/tanks.js` 的 `paint` | 模型 |
| 履带滚速观感 | `src/content/assets.js` 的 `VIEW_TUNING.treadRate` | core |
| 碰撞/命中/拆砖/AI/胜负 | `src/core/` | view / 模型 |
| 相机、HUD、爆炸、车库 | `src/view/` | core |
| 按键、音效、最高分存储 | `src/platform/` | core |

---

## 8. 验证

| 级别 | 内容 | 命令/证据 |
|---|---|---|
| V0 内容/资产 | GLB hash、节点 tag、clip 名、channel 目标、LOD 差异、内容表完整性 | `node --test tests/assets.test.mjs` |
| V1 规则 | 碰撞、拆砖、敌人伤害、护盾、鹰徽失败、胜利、道具、确定性、分层约束 | `node --test tests/core.test.mjs` |
| V2 运行 | 浏览器加载、车库选车、开火、鼠标炮塔、结算、返回车库 | `preview/*.png` + CDP 冒烟 |
| V3 人工 | 手感、节奏、可理解性 | 待试玩 |

全部测试：

```bash
cd versions/v2 && npm test
# 14 passed
```

浏览器冒烟（本次实际跑过）：

- 车库里点 Tiger I → `mode=battle`、`spec.id=tiger`；
- 按 E → `skillCd≈15`、`player.ap=true`；
- 按 R → 回车库；
- 玩家炮击鹰徽 → `phase=lost`、`mode=over`、结算文案正确；
- 鼠标瞄准 → `Turret_Pivot.rotation.y` 跟随；
- W 前进 → 位置变化、`AnimLink_L_00` 四元数变化（履带在滚）；
- 开火 → 子弹生成、敌人 HP 75→50、`GunBarrel` 后坐位移。

---

## 9. 与旧版的行为差异

保留：3 辆可选坦克、相同数值/技能、相同 13×13 关卡和 3 波 10 辆敌人、相同道具、
相同胜负条件（包括“自己的炮弹打鹰徽也算输”）、相同操作键位。

有意改变：

1. **所有坦克都使用 Sherman 模型**，用不同涂装区分 Sherman / Tiger / T-90 和三类敌人。
2. **炮塔改为有限转速**（`turretSpeed` 3.6–7.0 rad/s），鼠标不再瞬间吸附；这是为了让
   炮塔转动动画看得出来，数值在 `tanks.js` 里可调。
3. **追尾镜头加了一点肩部偏移**，避免出生点的鹰徽正好挡住玩家坦克。
4. **车库改成空场 + 展示台**，避免模型被砖墙遮挡。
5. 新版最高分使用独立 key（`sb3d_sherman_hi`），不污染旧版记录。

已知限制：

- troop LOD 的履带是静态合并网格（远处敌人不滚履带）；hero 的 146 节履带板是主要
  draw call 来源。
- 没有按距离自动切 LOD，玩家固定 hero、敌人固定 troop。
- 没有移动端触控、暂停菜单、关卡选择、存档进度。
- 模型是 1 万面级别的低模，没有 LOD 链、碰撞体或烘焙贴图。

---

## 10. 本次架构档位（内部记录）

| 刻度盘 | 档位 | 理由 |
|---|---|---|
| L 架构级别 | L1（模块分层，局部 L2 契约） | 有真实的变化轴（换模型/调数值/改规则），但不需要 ECS/插件/编辑器框架 |
| E 编辑器级别 | E0 | 关卡只有 1 张，内容表是 JS 数据；做编辑器会先于内容量 |
| V 验证级别 | V0 + V1 + V2 | 资产契约、无头规则测试、浏览器冒烟都已跑 |
| R 可重算 | R0 | 随机可注入且同 seed 可复现，但没有录制回放 |
| P 便携 | P0 | 内核不依赖引擎，但未拆成独立包；未来做无头平衡测试可升 P1 |

主动放弃的过度设计：ECS、事件总线库、依赖注入容器、JSON Schema 校验器、
地图编辑器、按距离自动 LOD、运行时 LLM。当前内容量和变化频率都不支持它们的成本。

---

## 11. 下一步最小增量

1. 给 troop LOD 加履带 UV 滚动或着色器位移，让远处敌人也有履带感。
2. 按距离在 hero/troop 间切换，或给 hero 履带做 InstancedMesh（把 146 个 draw call
   压到 1 个）。
3. 补 V3 人工试玩，调整炮塔转速、相机距离和履带滚速。
4. 内容量上来后再考虑 E1（JSON 关卡 + 校验脚本），而不是先做编辑器。
