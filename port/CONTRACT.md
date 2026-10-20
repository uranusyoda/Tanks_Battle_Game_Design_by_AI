# G1 契约 — v3 → Godot

- 内容契约：`port/contract/content.json`
- 内容 SHA-256：`cbec06a4d634396bd9258d60f59ffe6b29bb67a3b9ba835a776f14801f27d59e`
- 录制脚本：`port/tools/export_content.mjs`、`port/tools/record_trace.mjs`
- 黄金 trace：`port/traces/*.json`（5 条，固定 seed / 固定 dt）
- 确定性：同脚本连跑两次，`diff -r` 无输出，证据 `port/evidence/G1/trace-digests.txt`

## C1 内容

| 类别 | 数量 | 关键字段 |
|---|---|---|
| 玩家坦克 | 3（sherman / tiger / t90） | hp、speed、turn、fire、dmg、bspd、turretSpeed、muzzle、skill、paint、model.lod |
| 敌人 | 3（scout / line / sniper） | hp（实际 ×25）、speed、fire、dmg、range、score、scale |
| 关卡 | 1 + 车库空场 | 13×13、3 波 10 辆、spawnCols `[1,4,8,11]`、maxOnField 4、鹰徽 `(0,6)` |
| 道具 | 6 | star / grenade / shovel / clock / helmet / tank，权重 20/12/12/14/16/8 |
| 资产 | 2 | hero / troop，tag + clip + scale + fallback |

内容导出是机械导入源模块 + 稳定排序，不手抄。`meta` 不含时间戳，保证 diff 干净。

## C2 状态

权威状态在 `PortBattle.state`：

- 全局：`phase`、`time`、`score`、`killed`、`totalEnemies`、`wave`、`spawnQueue`、`spawnTimer`、`spawnIndex`、`respawnTimer`、`skillCd`、`fortTimer`、`eagle`。
- 玩家：位置/朝向/炮塔角/HP/命/无敌/护盾/烟幕/AP/反应装甲/修理/速度/移动。
- 敌人数组：id、type、prof、x/z、heading、turretYaw、hp、scale、fireCd、aimTimer、stuck、jitter、freeze、hitFlash、seed。
- 子弹/道具数组：id、x/z、yaw/speed/damage/from、life；道具 id/def/x/z/life。

规则层只认标量 `float`；`Vector2/Vector3` 只在表现层使用。

## C3 命令

| 命令 | 语义 |
|---|---|
| `set_move(throttle, turn)` | 每帧移动意图，core clamp 到 -1..1 |
| `set_trigger(on)` | 按住开火；冷却由 core 判断 |
| `aim_at(x, z)` | 炮塔目标点；按 turretSpeed 逐步旋转 |
| `use_skill()` | 冷却/存活由 core 判断，返回 bool |
| `stop()` | 结算时清空输入 |

## C4 事件

共 19 种：`fire / explosion / impact / spark / tileChanged / spawn / respawn /
pickupDropped / pickup / pickupExpired / playerHit / shieldBlock / reactiveBlock /
skill / message / enemyHit / enemyKilled / lifeLost / gameover`。

**已发现的源侧缺陷**：`spawn` 事件的 payload 里有 `type: enemyType`，而源 `emit` 是
`{ type, ...data }`，payload 的 `type` 会覆盖事件 type。结果：源码里 `spawn` 事件的
`type` 实际是 `"scout" / "line" / "sniper"`，`view` 里 `case 'spawn'` 永远不命中。

Godot 核心为保持 parity，按 JS 展开顺序复现了这一行为（见 `godot/core/battle.gd::_emit`）。
这是**源 bug**，不是移植 bug；修复需要同时改源、view 和 trace，见 `DEVIATIONS.md` D001。

## C5 资产

Godot 实际导入结果（`godot/tests/TestAsset.gd`）：

| 资产 | MeshInstance3D | `AnimLink_` 履带板 | clips | tag |
|---|---|---|---|---|
| hero | 199 | 146 | `Drive`, `Fire` | 全部存在 |
| troop | 9 | 0 | `Fire` | 全部存在 |

这验证了：GLB 能导入、节点名未被改写、clip 名保留、hero/troop 的 LOD 差异真实存在。
`troop` 没有 `Drive`，`TankRig` 必须允许 `clips.drive = null`。

## 黄金 trace

| 场景 | 步数 | 事件 | 采样 | digest（前 12） |
|---|---|---|---|---|
| `drive_into_brick` | 120 | 3 | 24 | `59d0220c8011` |
| `fire_brick` | 120 | 6 | 24 | `fa45f440442a` |
| `hit_enemy` | 300 | 12 | 60 | `a86f7669a378` |
| `eagle_fail` | 120 | 6 | 24 | `f5c6c188d187` |
| `skill_smoke` | 180 | 6 | 36 | `34fbca5b71d3` |

## 跨引擎传输约定（本轮新增）

1. **`dt` 用有理数传输**：trace 里同时存 `dt_num: 1, dt_den: 60`，回放用
   `float(dt_num) / float(dt_den)` 在目标引擎重新计算。只传十进制 `dt` 会因 JSON
   解析差 1 ULP，导致 `spawnTimer` 在边界上差一帧（本轮真实踩到）。
2. **事件按 JS 展开顺序**：`{ type, ...data }`；payload 的 `type` 可以覆盖事件 type。
3. **RNG 用已验证的 mulberry32**，seed 7 / 123456789 的测试向量与 Node 一致。
4. **浮点比较**：事件序列/ID 顺序完全一致；位置/角度容差 `1e-5`；HP/分数整数一致。
