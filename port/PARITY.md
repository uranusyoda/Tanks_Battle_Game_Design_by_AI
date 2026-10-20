# 移植一致性矩阵（Pilot 阶段）

> 状态：`pass` / `fail` / `deviation` / `todo`。
> 本轮覆盖 G0–G4 + 资产契约；G5–G7 行为标 `todo`。
> 画面为原型级：通过表示“行为/链路成立”，不表示最终美术。

| ID | 行为 | 源引用 | Godot 实现 | 验证方式 | 状态 | 偏差 |
|---|---|---|---|---|---|---|
| C-01 | 3 辆坦克，数值/技能正确 | `content/tanks.js` | `content/content.json` | G3 内容测试 | pass | — |
| C-02 | 3 类敌人，HP = hp×25 | `content/enemies.js` | `content/content.json` | G3 内容测试 | pass | — |
| C-03 | 13×13、3 波 10 辆、maxOnField=4 | `content/levels.js` | `content/content.json` | G3 内容测试 / trace | pass | — |
| C-04 | 6 种道具权重与效果 | `content/powerups.js` | `content/content.json` | G3 Star 测试 | pass | — |
| R-01 | 玩家移动/转向/碰撞 | `core/battle.js` | `core/battle.gd` | trace `drive_into_brick` + G4 驾驶 | pass | — |
| R-02 | 炮塔有限转速 | `core/battle.js` | `core/battle.gd` | trace `fire_brick` + G4 瞄准 | pass | — |
| R-03 | 子弹速度/寿命/越界 | `core/battle.js` | `core/battle.gd` | trace `fire_brick` | pass | — |
| R-04 | 砖/钢/水/森林/鹰徽判定 | `core/grid.js` | `core/grid.gd` | trace + 单测 + G4 拆砖 | pass | — |
| R-05 | 敌人 AI（视线/卡住/狙击） | `core/battle.js` | `core/battle.gd` | trace `hit_enemy` / `drive_into_brick` | pass | — |
| R-06 | Sherman 烟幕技能 | `core/battle.js` | `core/battle.gd` | trace `skill_smoke` | pass | — |
| R-07 | Tiger AP / T-90 反应装甲 | `core/battle.js` | `core/battle.gd` | 代码对照，未单独 trace | todo | — |
| R-08 | 6 种道具效果 | `core/battle.js` | `core/battle.gd` | 仅 Star 有测试 | todo | — |
| R-09 | 生命/复活/无敌 | `core/battle.js` | `core/battle.gd` | 代码对照，未单独 trace | todo | — |
| R-10 | 胜利/鹰徽失败/生命耗尽 | `core/battle.js` | `core/battle.gd` | 单测 + G4 鹰徽失败 | pass | — |
| R-11 | 同 seed 确定性 | `core/rng.js` | `core/rng.gd` | 单测 + 5 条 trace | pass | — |
| A-01 | hero/troop 的 tag 与 clip | `content/assets.js` | `content/content.json` | TestAsset | pass | — |
| A-02 | hero 146 节履带 / troop 合并 | `assets/tankRig.js` | `view/tank_rig.gd` | TestAsset + G4 画面 | pass | — |
| A-03 | 涂装 / 受击闪白 | `assets/tankRig.js` | `view/tank_rig.gd` | G4 画面（橄榄绿）+ 代码 | pass | 半透明未实现 |
| V-01 | 追尾/俯视相机、肩部偏移、震屏 | `view/camera.js` | `game.gd::_update_camera` | G4 画面 + 代码 | pass | — |
| V-02a | 战斗 HUD（得分/HP/波次/敌军/提示/结算） | `view/hud.js` | `game.gd::_setup_hud` | G4 三张截图 | pass | 美术简化 |
| V-02b | 车库/选车 HUD | `view/hud.js` | 尚未实现 | — | todo | — |
| V-03 | 爆炸/炮口焰/拆砖碎片 | `view/fx.js` | `game.gd` 占位 FX | G4 `combat.png` | pass | 原型级，无粒子/贴图 |
| V-04 | 音效 | `platform/audio.js` | 尚未实现 | — | todo | — |
| P-01 | W/S/A/D、鼠标、空格/左键、E/C/R | `platform/input.js` | `game.gd::_read_input` | G4 自动 + 手动 | pass | — |
| P-02 | 最高分持久化 | `platform/storage.js` | 尚未实现 | — | todo | — |
| G4-01 | 开火拆砖 | `core/battle.js` | 核心 + 世界更新 | `tile9_6=0` | pass | — |
| G4-02 | 击杀敌人/计分 | `core/battle.js` | 核心 + 敌人视图 | `score=100, killed=1` | pass | — |
| G4-03 | 鹰徽失败/结算 | `core/battle.js` | 核心 + 结算浮层 | `phase=lost` + 截图 | pass | — |
| E-01 | `spawn` 事件 type 正确 | `core/battle.js` | `core/battle.gd`（复现源 bug） | trace | deviation | D001 |

## 统计

- 总数：29
- pass：22
- fail：0
- deviation：1（D001）
- todo：6

## 结论

- 核心规则、资产管线、可玩纵切片都已成立。
- 剩余工作集中在：车库/选车、其余技能/道具/生命的专门测试、音频、完整美术/特效、
  性能优化、导出。
- D001 需要产品/代码 owner 决定：修源，还是接受出生特效缺失。
