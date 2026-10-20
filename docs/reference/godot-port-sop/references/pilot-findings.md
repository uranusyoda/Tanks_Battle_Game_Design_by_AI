# 试点发现：钢铁防线 v3 → Godot 4.7.1

- 日期：2026-10-20
- 范围：G0 基线 → G1 契约/黄金 trace → G2 工程骨架 → G3 内核回放 → G4 视觉纵切片 → GLB 资产契约
- 结果：**通过**。10 项规则测试、5 条 trace、2 个 GLB 资产契约、G4 四个自动场景全绿（移动/输入/击杀/失败）。
- 证据：项目内 `port/PILOT.md`、`port/evidence/`。

## 已验证的事实

- 718 行 `battle.js` → 721 行 `battle.gd`，逐函数对照移植；未用 Godot 物理、
  未用 `Vector2/Vector3` 存权威数值、未用 signal 发事件。
- `mulberry32` 在 Godot 4.7.1 与 Node 逐位一致（seed 7 / 123456789）。
- hero：199 个 `MeshInstance3D`、146 个 `AnimLink_` 履带板、`Drive` + `Fire`。
- troop：9 个 `MeshInstance3D`、0 个履带板、只有 `Fire`。
- 5 条 trace：`drive_into_brick`、`fire_brick`、`hit_enemy`、`eagle_fail`、`skill_smoke`。
- G4：移动、开火拆砖（`tile9_6=0`）、击杀敌人（`score=100`）、鹰徽失败（`phase=lost`）、
  战斗 HUD、追尾/俯视相机、自动截图。

## 发现 1：`dt` 不能用十进制跨引擎传输

trace 里写 `dt: 0.016666666666666666`，Godot JSON 解析后比 `1.0/60.0` 小 1 ULP。
60 次累加后 `spawnTimer` 从 `-1.39e-15` 变成 `+1.89e-15`，第二次刷怪从第 60 步
推到第 61 步，3 条 trace 失败。改成 `dt_num: 1, dt_den: 60`，回放时在目标引擎
重新计算，5/5 通过。

**修订**：trace 格式必须带 `dt_num/dt_den`；禁止只传十进制 `dt` 当权威值。

## 发现 2：事件展开顺序会制造“假 type”

源 `emit = (type, data) => events.push({ type, ...data })`；`spawn` 的 payload 里
有 `type: enemyType`，展开后覆盖事件 type。结果源码里 `spawn` 事件 type 实际是
`"scout" / "line" / "sniper"`，`case 'spawn'` 永远不命中，出生特效缺失。

**修订**：移植事件时按 `{type, ...data}` 的展开顺序复现；如果 payload 有 `type`、
`id` 等可能冲突的键，先记录为源缺陷，再决定修源还是接受偏差。视图可以同时兼容
“type 是敌人类型”和“type=spawn + enemyType”两种形状。

## 发现 3：`Color.hex(int)` 把 RGB 当 RGBA

源涂装是 `0x7a8b56`（RGB）。Godot 4.7 的 `Color.hex(0x7a8b56)` 按 `0xRRGGBBAA`
解释，得到 `(0, 0.478, 0.545, 0.337)` —— 青色半透明，坦克直接变青。

正确写法：

```gdscript
var v := int(paint[key])
copy.albedo_color = Color8((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)
```

**修订**：所有“十六进制颜色数字”必须显式拆通道；不要用 `Color.hex(int)` 猜。

## 发现 4：`tr` 是 Godot `Object` 的保留方法名

`PortConstants.tr()` 与 `Object.tr()` 冲突，Godot 报
“overrides a method from native class”。改名 `row_at()` / `col_at()`。
类似风险：`tc`、`signal`、`connect`、`get`、`set`、`name` 等命名，先在 Godot 里
小规模编译验证。

## 发现 5：资产契约必须在目标引擎里实例化验证

只看 manifest 不够；Godot 实际导入后：

- hero 的 `Drive`、`Fire` 都在，tag 全在；
- troop 没有 `Drive`，`TankRig` 必须允许 `clips.drive = null`；
- hero 的 146 节履带就是 146 个节点，G6 的 draw call 风险被提前确认。

**修订**：G1 的资产检查必须在 Godot 里 `load().instantiate()`，检查
`find_child(tag)` 与 `AnimationPlayer.has_animation(clip)`，不能只信 JSON。

## 发现 6：中文 HUD 要显式给字体

Godot 默认字体不含中文。`SystemFont` 在 macOS 上可能回退到缺字的字体（“敌”变方框）。
本机用 `FontFile.load_dynamic_font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")`
解决；跨平台项目应打包一份可商用 CJK 字体。

**修订**：HUD 本地化在 G4 就要验证，不要等到发布才发现缺字。

## 对 SOP 的最小修订

1. 黄金 trace 增加 `dt_num` / `dt_den`；回放重新计算 `dt`。
2. 事件复现采用 `{type, ...data}` 展开顺序；payload 键冲突要显式处理。
3. 颜色数字用 `Color8` 拆通道，禁止 `Color.hex(int)` 猜 RGBA。
4. 资产契约增加“目标引擎实例化”检查。
5. 命名先做目标引擎编译检查，避免与 `Object` 方法冲突。
6. 中文 HUD 在 G4 验证字体，不要留到发布。
7. 把这些检查写进 G1/G3/G4 门禁，不靠记忆。

## 复跑

```bash
cd versions/v3 && npm test && cd ../..
node port/tools/export_content.mjs versions/v3 port/contract
node port/tools/record_trace.mjs versions/v3 port/traces port/contract/content.json
HOME=/tmp/godot-home godot --headless --path godot --import
HOME=/tmp/godot-home godot --headless --path godot res://tests/TestRunner.tscn
HOME=/tmp/godot-home godot --path godot --rendering-driver opengl3 -- --autotest
HOME=/tmp/godot-home godot --path godot --rendering-driver opengl3 -- --combat
HOME=/tmp/godot-home godot --path godot --rendering-driver opengl3 -- --eagle
```
