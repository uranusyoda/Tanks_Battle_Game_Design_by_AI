# Godot Port Pilot — 钢铁防线 3D v3

这是移植可行性验证工程，不是最终游戏。当前完成 G0–G4：

- G0 基线：源 `versions/v3` 测试 14/14、文件哈希、资产哈希。
- G1 契约：`content.json`、5 条黄金 trace。
- G2 骨架：Godot 4.7.1 工程可导入；GLB 实机渲染截图。
- G3 内核：`core/` 规则移植，10 项规则测试 + 5 条 trace 回放全部通过。
- G4 切片：TankRig、13×13 世界、追尾/俯视相机、鼠标瞄准、开火/拆砖、敌人击杀、
  鹰徽失败结算、战斗 HUD。
- 资产契约：hero/troop 的 tag、clip、LOD 在 Godot 里实例化验证。

**未完成**：车库/选车、其余技能/道具/生命的专门测试、音频、完整美术/特效、性能优化、
导出（G5–G7）。

完整报告：[../port/PILOT.md](../port/PILOT.md)。画面是原型级，不是最终美术。

## 运行

```bash
# 导入资源（首次或 GLB 变更后）
HOME=/tmp/godot-home godot --headless --path . --import

# 规则 + 资产 + trace 回放
HOME=/tmp/godot-home godot --headless --path . res://tests/TestRunner.tscn

# 可玩切片（打开窗口）
HOME=/tmp/godot-home godot --path . --rendering-driver opengl3

# 自动截图（会打开窗口，写 ../port/evidence/G4/）
HOME=/tmp/godot-home godot --path . --rendering-driver opengl3 -- --autotest
HOME=/tmp/godot-home godot --path . --rendering-driver opengl3 -- --inputtest
HOME=/tmp/godot-home godot --path . --rendering-driver opengl3 -- --combat
HOME=/tmp/godot-home godot --path . --rendering-driver opengl3 -- --eagle

# 最小 GLB 渲染（G2 截图）
HOME=/tmp/godot-home godot --path . res://main.tscn --rendering-driver opengl3
```

> `HOME=/tmp/godot-home` 是本机沙箱的 workaround：Godot 需要写 `user://logs`，
> 默认 `~/Library/Application Support/Godot` 不可写。正常桌面环境不需要。

## 操作

| 按键 | 动作 |
|---|---|
| W / S | 前进 / 后退 |
| A / D | 车体转向 |
| 鼠标 | 炮塔瞄准 |
| 空格 / 鼠标左键 | 开火 |
| E | 技能（当前 Sherman 烟幕） |
| C | 追尾 / 俯视 |
| R | 重开（结算后也可用） |

## 结构

```
game.tscn / game.gd   可玩切片：场景、世界、相机、输入、HUD、事件接线
view/tank_rig.gd      GLB → 炮塔/炮管/炮口/Drive/Fire/涂装
core/                 纯规则 RefCounted：constants / rng / grid / battle
content/              content.json + 加载器
tests/                TestRunner + 规则/资产/trace 测试 + golden/*.json
assets/               hero / troop GLB
main.tscn             最小 GLB 渲染场景（G2 截图用）
```

## 已知问题

- `D001`：源 `spawn` 事件的 payload `type` 覆盖事件 type，导致 `case 'spawn'` 不命中。
  核心为 trace parity 复现；G4 视图同时兼容两种事件形状。见
  [../port/DEVIATIONS.md](../port/DEVIATIONS.md)。
- `troop` 没有 `Drive` clip，`TankRig` 必须允许 `clips.drive = null`。
- 当前直接进战斗，没有车库/选车；HUD 是文本版，没有血条/技能图标。
- 砖/钢是纯色 BoxMesh，森林是圆锥，爆炸是简单球体；没有贴图、粒子、音频。
- hero 146 节履带会产生大量 draw call，G6 需要 MultiMesh/合并。
- HUD 字体在 macOS 读 `Arial Unicode.ttf`；其他平台回退 `SystemFont`，发布前需内置可商用 CJK 字体。
