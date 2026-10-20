# 验证主干：G0–G7 的命令、证据与判定

> 每个门禁都要留下可复查的证据。没有证据的“通过”视为未通过。
> 证据统一放 `port/evidence/Gx/`，文件名稳定，方便 CI 与人工复核。

---

## 0. 门禁总表

| 门禁 | 目的 | 主要命令 | 通过标准 |
|---|---|---|---|
| G0 | 源基线可复现 | 源测试 + 真实启动 | 测试全绿；关键路径截图；哈希清单 |
| G1 | 契约与 oracle | 导出内容 + 录像 trace ×2 | schema 通过；两次 digest 相同 |
| G2 | Godot 骨架 | `--import` + 跑 120 帧 | 退出码 0；无脚本错误；骨架截图 |
| G3 | 内核等价 | 规则测试 + trace 回放 | 测试全过；事件序列完全一致；数值误差 < 1e-5 |
| G4 | 首个纵切片 | 自动/手动 smoke | 车库→战斗→命中→失败全通；4 张截图 |
| G5 | 全内容/全系统 | 全量测试 + 胜利/失败路径 | 3 波 10 辆、3 技能、6 道具、5 条结局路径 |
| G6 | 表现与平台 | 截图对比 + 性能 + soak | 60 fps；音频正确；10 分钟无泄漏 |
| G7 | 验收发布 | 导出 + 运行产物 | 产物能完成一局；PARITY 100% 或批准偏差 |

---

## G0｜源基线

```bash
cd v2
git rev-parse HEAD && git status --short
npm test 2>&1 | tee ../port/evidence/G0/tests.txt

# 启动（按源项目实际命令）
python3 -m http.server 4173
```

手动/自动走：

1. 车库：3 张坦克卡可见，可点选。
2. 战斗：W 前进、鼠标转炮塔、开火、E 技能。
3. 命中：敌人 HP 下降、砖块消失。
4. 失败：炮击鹰徽 → 结算 → R 返回车库。

截图存 `port/evidence/G0/{garage,battle,eagle-fail}.png`。

**判定**：测试数、通过数、截图、commit 全部写进 `port/BASELINE.md`。若源测试有红，
逐条列出并确认是否纳入本轮；不要静默忽略。

---

## G1｜契约与黄金回放

```bash
node port/tools/export_content.mjs v2 port/contract
node port/tools/record_trace.mjs v2 port/traces

# 再跑一次到临时目录，逐字节比较
node port/tools/record_trace.mjs v2 /tmp/traces-rerun
diff -r port/traces /tmp/traces-rerun
```

如果项目还没有这些脚本，先按 [contract-extraction.md](contract-extraction.md) 创建；
不要把“手抄一份 JSON”当成 G1。

**判定**：

- [ ] `content.json` 通过校验，所有引用存在。
- [ ] 资产 tag/clip 在 Godot 里实例化验证通过（见下）。
- [ ] 5 条 trace 均生成；`diff -r` 无输出。
- [ ] 每条 trace 的事件数与摘要写入 `port/CONTRACT.md`。

资产检查脚本（Godot headless 也能跑）：

```bash
godot --headless --path godot res://tests/AssetContractTest.tscn
```

---

## G2｜Godot 骨架

```bash
godot --headless --path godot --import 2>&1 | tee port/evidence/G2/import.txt
godot --headless --path godot --quit-after 120 res://main.tscn \
  2>&1 | tee port/evidence/G2/boot.txt
```

**判定**：

- [ ] 两条命令退出码 0。
- [ ] `boot.txt` 无 `SCRIPT ERROR`、`Invalid call`、`Cannot open`。
- [ ] 主场景能跑 120 帧不崩。
- [ ] 骨架截图：坐标轴/箭头确认 +Z 车头。

> 沙箱环境提示：若 headless 报 `Could not create directory: 'user://logs'`，是
> `~/Library/Application Support/Godot` 不可写导致的环境问题。临时把 `HOME` 指到可写目录再跑，
> 例如 `HOME=/tmp/godot-home godot ...`；不要把它误判成工程错误。

---

## G3｜内核等价（硬闸门）

### 3.1 规则测试

```bash
godot --headless --path godot res://tests/TestRunner.tscn -- --suite=core \
  2>&1 | tee port/evidence/G3/core-tests.txt
```

测试运行器骨架：

```gdscript
# tests/TestRunner.gd
extends Node

func _ready() -> void:
	var failures := 0
	failures += TestCore.run_all()
	failures += TestContract.run_all()
	failures += TestTrace.run_all()

	if failures == 0:
		print("ALL TESTS PASSED")
	else:
		push_error("%d test(s) failed" % failures)
	get_tree().quit(1 if failures > 0 else 0)
```

```gdscript
# tests/TestCore.gd
class_name TestCore

static func run_all() -> int:
	var failed := 0
	failed += _test("brick blocks tank", _brick_blocks_tank)
	failed += _test("fire destroys brick", _fire_destroys_brick)
	# ... 对应源测试
	return failed

static func _test(name: String, fn: Callable) -> int:
	var ok := bool(fn.call())
	print(("PASS " if ok else "FAIL ") + name)
	return 0 if ok else 1
```

要求：源测试逐项有对应项；允许命名不同，不允许静默跳过。测试里不要 `await` 真实时间；
用固定 `dt` 手动推进。

### 3.2 trace 回放

```bash
godot --headless --path godot res://tests/TestRunner.tscn -- --suite=trace \
  2>&1 | tee port/evidence/G3/trace.txt
```

对比逻辑：

1. 读源 trace 与 Godot 回放结果。
2. **事件序列**：长度、顺序、`type`、payload 的 ID/枚举完全一致。
3. **采样状态**：HP/分数/生命/波次/数组 ID 顺序完全一致；位置/角度误差 < `1e-5`。
4. 第一个不一致点打印：

```
DIVERGE step=137 field=player.x source=1.234567 godot=1.234891 delta=3.24e-4
  previous events: fire, impact, tileChanged
```

5. 失败时保存完整 diff 到 `port/evidence/G3/trace-diff.json`。

GDScript 对比骨架：

```gdscript
static func compare_trace(src: Dictionary, got: Dictionary) -> Array[String]:
	var errors: Array[String] = []
	if src.events.size() != got.events.size():
		errors.append("event count %d != %d" % [src.events.size(), got.events.size()])
	var n: int = mini(src.events.size(), got.events.size())
	for i in n:
		var a: Dictionary = src.events[i]
		var b: Dictionary = got.events[i]
		if a.type != b.type:
			errors.append("event[%d] type %s != %s" % [i, a.type, b.type])
			break
		# 逐 payload 字段比较；浮点用 is_equal_approx 或自定义 eps
	for i in mini(src.samples.size(), got.samples.size()):
		var a: Dictionary = src.samples[i].state
		var b: Dictionary = got.samples[i].state
		if absf(a.player.x - b.player.x) > 1e-5:
			errors.append("step %d player.x %f != %f" % [src.samples[i].step, a.player.x, b.player.x])
			break
	return errors
```

### 3.3 静态纯净检查

```bash
# core/ 不应出现这些；按项目实际命名调整
grep -rnE '\b(Node|get_tree|get_node|Input|AudioStreamPlayer|preload|Vector2|Vector3)\b' \
  godot/core/ && echo "CORE PURITY VIOLATION" && exit 1 || true
```

**判定**：

- [ ] 源测试对应项全过。
- [ ] 5 条 trace 事件序列一致，数值误差 < `1e-5`。
- [ ] 同 seed 两次回放 digest 一致。
- [ ] 静态纯净检查通过。
- [ ] 能指出第一处分歧的 step/字段，而不是“整体差不多”。

G3 不过，禁止开始 HUD、特效、手感调整。

---

## G4｜首个纵切片

推荐做一个可脚本化的自动 smoke，避免每次都靠手点：

```bash
godot --path godot res://main.tscn -- --autotest=slice_a
```

`main.gd` 读取 `OS.get_cmdline_user_args()`，按脚本执行：

1. 等 1 秒 → 选 Sherman。
2. 前进 0.5 秒 → 开火 3 次。
3. 检查砖块状态、敌人 HP、事件计数。
4. 瞄准鹰徽 → 开火 → 等 `phase == "lost"`。
5. 写 `port/evidence/G4/slice_a.json`，退出码 0/1。

同时保留人工截图：

- 车库；
- 进场；
- 开火命中；
- 鹰徽失败/结算。

**判定**：

- [ ] 全流程无脚本错误。
- [ ] 4 张截图。
- [ ] 炮口焰/子弹起点与 `GunMuzzle` 对齐（≤ 0.05 米）。
- [ ] 砖块状态与画面一致；重开恢复。
- [ ] 60 秒操作后 `OBJECT_ORPHAN_NODE_COUNT` 不持续增长。

---

## G5｜全内容/全系统

```bash
godot --headless --path godot res://tests/TestRunner.tscn -- --suite=full \
  2>&1 | tee port/evidence/G5/full-tests.txt
```

至少覆盖：

| 路径 | 检查 |
|---|---|
| 胜利 | 3 波 10 辆全灭，`phase=won`，分数正确 |
| 鹰徽失败 | 玩家/敌人炮弹均能触发，`phase=lost` |
| 生命耗尽 | 3 次死亡后 `gameover`，不再复活 |
| 技能 | 3 辆坦克各一次，冷却/持续时间正确 |
| 道具 | 6 种均能掉落/生效/过期 |
| 掩体 | 加固 15 秒后恢复砖块 |
| 冰面 | 加速度/滑行与源一致 |
| 森林 | 远距离隐身/视线遮挡与源一致 |

**判定**：

- [ ] 上表全部有测试或自动 smoke。
- [ ] 全量测试通过。
- [ ] 新增内容有校验，不靠人工点。

---

## G6｜表现与平台

### 6.1 截图对比

固定窗口 1280×720，保存：

- `garage.png`
- `battle.png`
- `topdown.png`
- `gameover.png`

与 `port/evidence/G0/` 的源截图并排，记录差异（布局、颜色、字体、相机距离、特效强度）。
差异不等于失败；未记录的差异才是失败。

### 6.2 性能

```gdscript
# 每 60 帧打印一次
print("fps=%d draw_calls=%d objects=%d orphans=%d" % [
	Engine.get_frames_per_second(),
	int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
	int(Performance.get_monitor(Performance.OBJECT_COUNT)),
	int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)),
])
```

目标：

- 1280×720 稳定 60 fps（最低 55）。
- draw call < 400（hero 履带优化后）。
- 三角形 < 150k。
- 10 分钟 soak：orphan 不持续增长，内存不持续上涨。

### 6.3 音频/存档

- 每个事件音效只触发一次；连续爆炸不爆音。
- 最高分写入后，退出重进仍在。
- 窗口缩放/全屏后 HUD 不破。

**判定**：

- [ ] 4 组截图 + 差异记录。
- [ ] 性能数字写入 `port/evidence/G6/perf.txt`。
- [ ] 10 分钟 soak 记录。
- [ ] 音频/存档检查通过。

---

## G7｜验收发布

```bash
# 以实际 preset 名称为准
godot --headless --path godot --export-release "macOS" build/SteelBastion.app
# 或
godot --headless --path godot --export-release "Web" build/web/index.html
```

运行导出产物：

1. 启动 → 车库。
2. 选车 → 打完 3 波或触发失败。
3. 结算 → 返回车库 → 退出。
4. 检查日志无错误、无缺失资源。

**判定**：

- [ ] `PARITY.md` 每行有状态；未通过项全部是 `DEVIATIONS.md` 里已批准的偏差。
- [ ] 导出产物完成一局。
- [ ] 全量测试 + trace 回归通过。
- [ ] README/版本 tag/证据目录齐全。
- [ ] 用户明确接受手感与视觉差异。

---

## 附：证据目录模板

```
port/evidence/
├── G0/
│   ├── tests.txt
│   ├── garage.png
│   ├── battle.png
│   └── eagle-fail.png
├── G1/
│   ├── content-schema.txt
│   ├── asset-contract.txt
│   └── trace-digests.txt
├── G2/
│   ├── import.txt
│   ├── boot.txt
│   └── skeleton.png
├── G3/
│   ├── core-tests.txt
│   ├── trace.txt
│   └── trace-diff.json
├── G4/
│   ├── slice_a.json
│   └── *.png
├── G5/
│   └── full-tests.txt
├── G6/
│   ├── perf.txt
│   ├── soak.txt
│   └── *.png
└── G7/
    ├── export.txt
    └── run-exported.txt
```

## 附：CI 最小集

```yaml
- name: source tests
  run: cd v2 && npm test

- name: godot import
  run: godot --headless --path godot --import

- name: godot tests
  run: godot --headless --path godot res://tests/TestRunner.tscn
```

CI 只跑无头部分；截图/性能/导出产物 smoke 放在发布前的人工或专用 runner。
