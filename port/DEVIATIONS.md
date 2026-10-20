# 偏差记录（DEVIATIONS）

| ID | 行为/表现 | 源版本 | Godot 版本 | 原因 | 影响 | 状态 | 批准 | 对应测试 |
|---|---|---|---|---|---|---|---|---|
| D001 | `spawn` 事件被 payload 的 `type` 覆盖，事件 type 实际是敌人类型 | `core/battle.js` 的 `emit('spawn', { type: typeId, ... })` | 核心 `_emit` 按 JS 展开顺序复现；G4 视图同时兼容两种事件形状 | 源 `emit` 是 `{ type, ...data }`；payload 含同名 `type` | `view` 的 `case 'spawn'` 永远不命中，出生特效缺失；Godot 若不复现则 trace 不一致；G4 已用兼容分支创建敌人，但出生特效仍未补 | proposed | — | G3 5 条 trace |

## 建议

**推荐修源**，而不是在 Godot 里绕过：

```js
// 源：payload 改名，避免覆盖事件 type
emit('spawn', { id, enemyType: typeId, x, z, scale });
```

同步：

1. 更新 `app/game.js` / `view` 中读取 `event.type` 作为敌人类型的地方（当前没有消费，
   因为事件根本没命中 `case 'spawn'`）。
2. 重新录制 `hit_enemy`、`skill_smoke` 等包含 spawn 的 trace。
3. 在 Godot 侧保持 `_emit` 的 JS 展开语义，但 `spawn` payload 改为 `enemyType`；
   `case "spawn"` 才能真正生效。
4. 更新 `PARITY.md` E-01 为 pass，并在 CHANGELOG 记为“修复出生特效不触发”。

如果决定不修源，则 Godot 视图必须接受“出生特效不播放”，并把 E-01 标为已批准偏差；
不要一边复现 bug 一边又期望视图能收到 spawn。

## 说明

- 本轮没有修改 `versions/v3`；这是源侧缺陷，不是移植引入的差异。
- 其余实现差异（`tr` → `row_at`、`dt` 有理数传输、`Color.hex` → `Color8`）不影响可观察行为，不记为偏差。
