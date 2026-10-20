# 移植一致性矩阵（PARITY）

> 一行一条玩家可见行为或关键规则。状态只允许：`pass` / `fail` / `deviation` / `todo`。
> `deviation` 必须能在 `DEVIATIONS.md` 找到同 ID 的记录。

| ID | 行为 | 源引用 | Godot 实现 | 验证方式 | 状态 | 偏差 |
|---|---|---|---|---|---|---|
| C-01 | 3 辆坦克可选，数值正确 | `content/tanks.js` | `content/tanks.json` | G5 内容测试 | todo | — |
| C-02 | 3 类敌人，HP = hp×25 | `content/enemies.js` | `content/enemies.json` | G5 内容测试 | todo | — |
| C-03 | 13×13、3 波 10 辆、maxOnField=4 | `content/levels.js` | `content/levels.json` | G5 胜利路径 | todo | — |
| C-04 | 6 种道具权重与效果 | `content/powerups.js` | `content/powerups.json` | G5 道具测试 | todo | — |
| R-01 | 玩家移动/转向/冰面滑行 | `core/battle.js` | `core/battle.gd` | G3 trace `drive_into_brick` | todo | — |
| R-02 | 炮塔有限转速 | `core/battle.js` | `core/battle.gd` | G3/G4 | todo | — |
| R-03 | 子弹速度/寿命/越界 | `core/battle.js` | `core/battle.gd` | G3 trace `fire_brick` | todo | — |
| R-04 | 砖/钢/水/森林/鹰徽判定 | `core/grid.js` | `core/grid.gd` | G3 trace | todo | — |
| R-05 | 敌人 AI（视线/卡住/狙击） | `core/battle.js` | `core/battle.gd` | G5 敌人测试 | todo | — |
| R-06 | 3 个技能与冷却 | `core/battle.js` | `core/battle.gd` | G5 技能测试 | todo | — |
| R-07 | 6 种道具效果 | `core/battle.js` | `core/battle.gd` | G5 道具测试 | todo | — |
| R-08 | 生命/复活/无敌 | `core/battle.js` | `core/battle.gd` | G5 生命路径 | todo | — |
| R-09 | 胜利/鹰徽失败/生命耗尽 | `core/battle.js` | `core/battle.gd` | G5 结局测试 | todo | — |
| R-10 | 同 seed 确定性 | `core/rng.js` | `core/rng.gd` | G3 双跑 digest | todo | — |
| A-01 | 两档 GLB、节点 tag、clip | `content/assets.js` | `content/assets.json` | G1 资产契约 | todo | — |
| A-02 | hero 履带滚动、负重轮同步 | `assets/tankRig.js` | `view/tank_rig.gd` | G4/G6 目视 + 动画检查 | todo | — |
| A-03 | 涂装三色/受击闪白/半透明 | `assets/tankRig.js` | `view/tank_rig.gd` | G6 截图 | todo | — |
| V-01 | 追尾/俯视相机、肩部偏移、震屏 | `view/camera.js` | `view/camera_rig.gd` | G6 截图 | todo | — |
| V-02 | 车库/战斗/结算 HUD | `view/hud.js` | `view/hud.tscn` | G6 截图 | todo | — |
| V-03 | 爆炸/烟/炮口焰/履带印/焦痕 | `view/fx.js` | `view/fx.gd` | G6 截图 | todo | — |
| V-04 | 音效与事件对齐 | `platform/audio.js` | `platform/audio.gd` | G6 听测 | todo | — |
| P-01 | W/S/A/D、鼠标、空格/左键、E/C/R | `platform/input.js` | `platform/input_router.gd` | G4 手动 | todo | — |
| P-02 | 最高分持久化 | `platform/storage.js` | `platform/save.gd` | G6 重启 | todo | — |

## 统计

- 总数：0
- pass：0
- fail：0
- deviation：0
- todo：0

## 结论

- [ ] 没有 `fail`。
- [ ] 所有 `deviation` 已在 `DEVIATIONS.md` 批准。
- [ ] 所有 `todo` 已关闭。
