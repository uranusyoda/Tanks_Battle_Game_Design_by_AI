# Three.js → Godot 4 映射与实现约定

> 本文件假设目标为 Godot 4.x（本项目验证版本 4.7.1）。API 名称以 4.x 为准；
> 不同小版本若有差异，以编辑器/文档为准，但**契约不变**。

---

## 1. 坐标与单位契约（先定死，再写代码）

源的棋盘坐标：

```js
x = col - 6;  // 13×13，中心 (0,0)
z = row - 6;
```

Godot 映射：

```gdscript
position = Vector3(x, 0.0, z)
rotation.y = heading          # 绕 Y 轴，弧度
```

模型契约（源 GLB）：

- **+Z 车头，+Y 向上**；
- 原点在履带接地面；
- 统一 `scale = 0.22`；
- 炮塔 `Turret_Pivot` 的局部 `rotation.y = turretYaw`；
- 炮管 `Gun_Pivot` 的局部 `rotation.x = pitch`；
- 炮口 `GunMuzzle` 是空节点，取 `global_position`。

关键差异：

- Godot 的“前”通常是 **-Z**，`Node3D.look_at()` 会让 -Z 朝向目标。
- 本项目模型是 **+Z 车头**，所以：
  - **不要用 `look_at()`** 让坦克看目标；
  - 直接 `rotation.y = heading`，前进方向用 `Vector3(sin(heading), 0, cos(heading))`。
- 如果某个第三方模型是 -Z 车头，在 `TankRig` 里加一个 `model.rotation.y = PI` 的包装节点，
  把差异收在资产层，不要让玩法层出现 `+PI` 补丁。

单位：

| 量 | 单位 | 备注 |
|---|---|---|
| 位置 | 格 = 米 | 1 格 = 1 米 |
| 角度 | 弧度 | 不要混用度 |
| 时间 | 秒 | `dt` clamp 到 0.05 |
| 速度 | 米/秒 | 源数值直接沿用 |
| 缩放 | 无量纲 | 只应用一次 |

---

## 2. 工程设置

建议起点（按目标平台调整）：

| 设置 | 值 | 理由 |
|---|---|---|
| `application/config/name` | `Steel Bastion 3D` | 与源一致 |
| `application/run/main_scene` | `res://main.tscn` | 装配根 |
| `display/window/size/viewport_width` | `1280` | 源画布比例 |
| `display/window/size/viewport_height` | `720` | 16:9 |
| `display/window/stretch/mode` | `canvas_items` | HUD 随窗口缩放 |
| `rendering/renderer/rendering_method` | `gl_compatibility` 或 `forward_plus` | 需要 Web 导出选前者；桌面可后者 |
| `rendering/anti_aliasing/quality/msaa_3d` | `2`（可选） | 低模边缘 |
| `rendering/lights_and_shadows/directional_shadow/size` | `2048` | 一张主光 |
| `physics/common/physics_ticks_per_second` | `60` | 规则不走物理；保留默认即可 |

渲染器选择是**一次性决定**：`forward_plus` 的画面/光照更好，但 Web 导出通常要用
`gl_compatibility`。不要做到一半再换；如果必须支持 Web，从第一天就用 Compatibility 验证。

输入建议运行时注册，避免 `project.godot` 里大段序列化事件：

```gdscript
# platform/input_router.gd
const ACTIONS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"turn_left": [KEY_A, KEY_LEFT],
	"turn_right": [KEY_D, KEY_RIGHT],
	"fire": [KEY_SPACE],
	"skill": [KEY_E],
	"camera": [KEY_C],
	"garage": [KEY_R],
}

func _ready() -> void:
	for action in ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in ACTIONS[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)
```

鼠标左键开火用 `Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)`；不要假设有 pointer lock。

---

## 3. 场景树骨架

```
Main (Node3D, main.gd)
├── Stage (Node3D, stage.gd)
│   ├── WorldEnvironment
│   ├── DirectionalLight3D
│   └── CameraRig (Node3D, camera_rig.gd)
│       └── Camera3D
├── World (Node3D, world.gd)
├── Tanks (Node3D, tank_layer.gd)
├── Projectiles (Node3D, projectile_layer.gd)
├── FX (Node3D, fx.gd)
└── HUD (CanvasLayer, hud.gd)
    └── Root (Control)
```

职责：

- `Main`：只做装配和主循环；持有 `Battle`、`Game`、输入路由。
- `Game`（`RefCounted` 或 `Node`）：模式状态机（garage/battle/over）、事件分发、内容加载。
- `Stage`：环境、光照、相机、窗口；不碰规则。
- `World`：格子、鹰徽、砖/钢/水/森林/冰；只响应 `tileChanged`。
- `Tanks`：`TankRig` 的创建/销毁/同步；只读 `state`。
- `Projectiles`：只读 `state.bullets`。
- `FX`：只响应事件；不决定命中。
- `HUD`：只读 `state` + 事件消息。

**装配方向**：`Main → Game → (core, content) → view`；view 不允许反向持有 core 并改它。

---

## 4. 内核移植约定

### 4.1 只用 RefCounted，不用 Node

```gdscript
class_name Battle
extends RefCounted
```

禁止出现：`Node`、`get_tree()`、`get_node()`、`Input`、`AudioStreamPlayer`、`preload("*.tscn")`、
`Vector2`、`Vector3`、`randf()`、`Time.get_ticks_msec()`。

内容由构造函数注入：

```gdscript
func _init(content: Dictionary, tank_id: String, seed_value: int = 1) -> void:
	_tanks = content.tanks
	_enemy_types = content.enemies
	_level = content.levels.LEVEL
	_powerups = content.powerups
	_rng = Mulberry32.new(seed_value)
	# ... 初始化 state
```

### 4.2 状态用标量 float，不用 Vector2/Vector3

Godot 的 `Vector2/Vector3` 分量默认是 32 位浮点（`real_t`），而 JS 的 number 是 64 位 double。
内核里的位置、角度、速度用独立 `float`：

```gdscript
class PlayerState:
	var x: float = 0.0
	var z: float = 5.0
	var heading: float = PI
	var turret_yaw: float = 0.0
	var hp: float = 100.0
	var vx: float = 0.0
	var vz: float = 0.0
```

到表现层再组装 `Vector3(x, 0, z)`。这样 trace 的长程漂移会小一个量级。

### 4.3 更新顺序必须一致

源的顺序：

```
player → waves → enemies → bullets → pickups → fortify → checkWin
```

Godot 侧保持同一顺序，且 `dt` 只在入口 clamp 一次：

```gdscript
func update(dt: float) -> void:
	if state.phase != "battle":
		return
	dt = clampf(dt, 0.0, 0.05)
	state.time += dt
	state.skill_cd = maxf(0.0, state.skill_cd - dt)
	_update_player(dt)
	_update_waves(dt)
	_update_enemies(dt)
	_update_bullets(dt)
	_update_pickups(dt)
	_update_fortify(dt)
	_check_win()
```

### 4.4 事件缓冲

```gdscript
var _events: Array[Dictionary] = []

func _emit(type: String, data: Dictionary = {}) -> void:
	var event := data.duplicate()
	event["type"] = type
	_events.append(event)

func drain_events() -> Array[Dictionary]:
	var out := _events
	_events = []
	return out
```

不要用 `signal` 逐个发：Godot 的 `emit_signal`/`call_deferred` 可能改变同帧顺序，
而事件顺序是契约。

### 4.5 RNG：mulberry32 逐位复刻（已对拍）

源：

```js
a = (a + 0x6d2b79f5) | 0;
let t = Math.imul(a ^ (a >>> 15), 1 | a);
t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
```

Godot：

```gdscript
class_name Mulberry32
extends RefCounted

var _state: int = 0

func _init(seed_value: int) -> void:
	_state = seed_value & 0xFFFFFFFF

func next() -> float:
	_state = (_state + 0x6D2B79F5) & 0xFFFFFFFF
	var t: int = ((_state ^ (_state >> 15)) * (1 | _state)) & 0xFFFFFFFF
	var sum: int = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
	t = (sum ^ t) & 0xFFFFFFFF
	t = (t ^ (t >> 14)) & 0xFFFFFFFF
	return float(t) / 4294967296.0
```

已在 Godot 4.7.1 与 Node 对拍，测试向量：

| seed | 前 3 个值 |
|---|---|
| `7` | `0.01170475315302610`、`0.06195825757458806`、`0.97690763277933002` |
| `123456789` | `0.25779074383899570`、`0.97077211155556142`、`0.78532801428809762` |

要求：内核里所有随机都走这个 RNG；禁止 `randf()`、`randi()`、`shuffle()`。

### 4.6 角度 wrap 必须同边界

源是 `(-PI, PI]`：

```js
while (a > Math.PI) a -= Math.PI * 2;
while (a <= -Math.PI) a += Math.PI * 2;
```

Godot 的 `wrapf(a, -PI, PI)` 在 `PI` 边界行为不同。自己写：

```gdscript
static func wrap_angle(a: float) -> float:
	while a > PI:
		a -= TAU
	while a <= -PI:
		a += TAU
	return a
```

### 4.7 JS `Math.round` 不等于 `roundi`

源用 `Math.round(x + 6)` 做格子索引。JS 的半值规则是**向 +∞**：

```js
Math.round(-0.5) // -0
Math.round(-1.5) // -1
```

Godot 的 `roundi` 是**半值远离 0**，在负半值上会差 1 格，直接影响碰撞/拆砖/命中。
内核统一用：

```gdscript
static func js_round(v: float) -> int:
	return int(floor(v + 0.5))
```

`tc(x)` / `tr(z)` 必须走这个函数；不要图省事用 `roundi`。

### 4.8 不要用 Godot 物理替代网格碰撞

源用圆-格数学：`tryMove`、滑动、`lineOfSight`、拆格。换成 `CharacterBody3D` + `move_and_slide`
会改变：

- 贴墙时的滑动方向；
- 拆砖后能否通过；
- 敌人卡住/抖动/绕行的节奏；
- 子弹与坦克的命中顺序。

规则层的碰撞保持纯数学；物理节点只用于相机遮挡/鼠标拾取（可选）。

### 4.9 数组遍历中删除元素要复现源语义

源在 `for (const enemy of state.enemies)` 里可能 `splice` 删除当前敌人。JS 的迭代器
按下标前进，删除后可能跳过下一个元素——这是可观察行为（会影响同帧命中/掉落/RNG）。

Godot 侧不要擅自改成“先复制数组再删”“倒序遍历”或“标记后统一删”；先按源语义实现，
用 trace 验证。如果为了安全要改，必须证明事件序列与 RNG 调用次数不变。

### 4.10 内容注入而不是全局单例

`Battle` 通过构造函数拿 `tanks/enemies/level/powerups`，不要用 `Autoload` 全局内容。
这样同一套规则可以跑测试关卡、车库空场、未来新关卡，不需要改内核。

---

## 5. JS → Godot API 映射

| Three.js / Web | Godot 4 | 备注 |
|---|---|---|
| `import` / ES Module | `class_name` / `preload` | 内核不要 `preload` 场景 |
| 对象字面量 | `Dictionary` / 内部类 | 内容表可先用 Dictionary |
| `Math.sin/cos/atan2` | `sin/cos/atan2` | 参数顺序相同 |
| `Math.hypot(a,b)` | `sqrt(a*a + b*b)` | 避免 `Vector2.length()` 的 32 位 |
| `Math.round` | `int(floor(v + 0.5))` | JS 半值向 +∞；`roundi` 半值远离 0，负半值会差 1 |
| `Math.sign` | `signf` | 返回 -1/0/1 |
| `Math.min/max` | `minf/maxf` | 泛型 `min/max` 也可 |
| `clamp` | `clampf` | — |
| `>>> 0` | `& 0xFFFFFFFF` | 32 位无符号 |
| `Math.imul` | 显式 32 位掩码乘法 | 见 RNG |
| `performance.now()` | `_process(delta)` | `delta` 秒 |
| `requestAnimationFrame` | `_process` | 不要自己开线程 |
| `THREE.Scene` | `Node3D` | 场景根 |
| `THREE.PerspectiveCamera` | `Camera3D` | `fov`、`near/far` |
| `THREE.WebGLRenderer` | 视口/`RenderingServer` | 不要手写渲染循环 |
| `THREE.Mesh` | `MeshInstance3D` | `BoxMesh`/`PlaneMesh`/`ArrayMesh` |
| `THREE.InstancedMesh` | `MultiMeshInstance3D` | 履带、砖块 |
| `THREE.Group` | `Node3D` | — |
| `THREE.GLTFLoader` | `load("res://*.glb")` → `PackedScene` | 导入为场景 |
| `THREE.AnimationMixer` | `AnimationPlayer` | clip 名对应 |
| `THREE.Raycaster` | `Camera3D.project_ray_*` + `Plane.intersects_ray` | 鼠标拾取地面 |
| `THREE.CanvasTexture` | `ImageTexture` / `GradientTexture2D` | 程序化贴图建议烘 PNG |
| `THREE.ShaderMaterial` | `ShaderMaterial` | GLSL 要改写成 Godot shading language |
| `THREE.Points` | `GPUParticles3D` | 粒子系统不同，按事件重做 |
| `THREE.Sprite` | `Sprite3D` | 炮口焰/道具图标 |
| DOM HUD | `CanvasLayer` + `Control` | 不要用绝对像素硬摆 |
| CSS `linear-gradient` | `GradientTexture2D` / `StyleBoxFlat` | — |
| WebAudio | `AudioStreamPlayer` / `AudioStreamPlayer3D` | 建议离线烘 WAV |
| `localStorage` | `ConfigFile` + `user://` | — |
| `window.__battle` | 调试桥/`OS.get_cmdline_user_args()` | 仅 debug build |

---

## 6. 资产导入与 TankRig

### 6.1 导入

1. 把 `m4a1_sherman_hero.glb`、`m4a1_sherman_troop.glb` 放到 `res://assets/models/`。
2. 选中 GLB，在 Import 面板确认：
   - 场景根类型为 `Node3D`；
   - 动画导入开启，clip 名保持 `Drive` / `Fire`；
   - 材质提取策略一致（内嵌/外部）。
3. 点 Reimport，打开生成的场景检查节点树：
   - `M4A1_Sherman → Turret_Pivot → Gun_Pivot → GunMuzzle`；
   - `AnimationPlayer` 是否存在，`get_animation_list()` 是否包含 clip。
4. 不要在 Godot 里手动改 GLB 场景的节点名；名字是契约。需要包装就新建 `tank_rig.tscn`。

### 6.2 TankRig

```gdscript
class_name TankRig
extends Node3D

var turret: Node3D
var gun: Node3D
var muzzle: Node3D
var drive_player: AnimationPlayer
var fire_player: AnimationPlayer
var _materials: Array[StandardMaterial3D] = []

func setup(def: Dictionary, paint: Dictionary) -> void:
	var packed: PackedScene = load(def.file_path)
	var model := packed.instantiate()
	add_child(model)
	scale = Vector3.ONE * float(def.scale)

	turret = model.find_child(def.tags.turret, true, false) as Node3D
	gun = model.find_child(def.tags.gun, true, false) as Node3D
	muzzle = model.find_child(def.tags.muzzle, true, false) as Node3D
	assert(turret != null, "missing turret tag")
	assert(gun != null, "missing gun tag")
	assert(muzzle != null, "missing muzzle tag")

	drive_player = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	_apply_paint(model, paint)
	_setup_animations(def)
```

要点：

- `find_child(name, true, false)` 递归找；不要写死 `$M4A1_Sherman/Turret_Pivot`，导入器可能加根节点。
- 找不到 tag 直接 `assert`/报错，不要静默用 `null`；否则炮口焰会飘到原点。
- `scale` 只在这里应用一次；资产 JSON 里不要再乘一次。

### 6.3 Drive 与 Fire 不能共用一个 speed_scale

`AnimationPlayer.speed_scale` 是全局的。如果同一个 player 同时播 `Drive`（需要随速度
变 timeScale）和 `Fire`（需要 1× 单次后坐），会互相干扰。

两种可行做法：

**A. 双 AnimationPlayer**

```gdscript
func _setup_animations(def: Dictionary) -> void:
	if drive_player != null and def.clips.get("drive") != null:
		var drive := drive_player.get_animation(def.clips.drive)
		drive.loop_mode = Animation.LOOP_LINEAR
		drive_player.play(def.clips.drive)
		drive_player.speed_scale = 0.0

	if drive_player != null and def.clips.get("fire") != null:
		fire_player = AnimationPlayer.new()
		fire_player.add_animation_library("", drive_player.get_animation_library("").duplicate(true))
		add_child(fire_player)
		var fire := fire_player.get_animation(def.clips.fire)
		fire.loop_mode = Animation.LOOP_NONE
```

**B. 单 player + 按里程 seek（更稳）**

不依赖 `speed_scale`：每帧按行驶距离 `seek` Drive 的相位，Fire 单独用一个 player 或
`AnimationTree`。这样履带速度与位移严格对应，也更容易和源 `treadRate` 对齐。

选一种写进 `TankRig` 契约，并在 G4 验证“停车不滚、倒车反向、开火不打断履带”。

### 6.4 涂装

源按材质名映射：

```js
const PAINT_MATERIALS = {
  Sherman_Olive: 'olive',
  Sherman_OliveDark: 'oliveDark',
  Sherman_Star: 'star',
};
```

Godot：

```gdscript
func _apply_paint(root: Node, paint: Dictionary) -> void:
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		for i in mesh.mesh.get_surface_count():
			var mat := mesh.get_active_material(i)
			if mat is StandardMaterial3D:
				var copy: StandardMaterial3D = mat.duplicate()
				var key := _paint_key(copy.resource_name)
				if key != "" and paint.has(key):
					var v := int(paint[key])
				copy.albedo_color = Color8((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)
				mesh.set_surface_override_material(i, copy)
				_materials.append(copy)
```

注意：

- `duplicate()` 每个实例一份，避免所有坦克共享同一材质。
- 颜色 JSON 是数字（`0x7a8b56`）。Godot 4.7 的 `Color.hex(int)` 按 `0xRRGGBBAA` 解析，会把 RGB 读成 RGBA；必须用 `Color8((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)` 拆通道。
- 受击闪白/冻结：`emission_enabled = true`、`emission`、`emission_energy_multiplier`；
  记录 base emission，恢复时还原。
- 半透明（复活无敌/烟幕）：`transparency = BaseMaterial3D.TRANSPARENCY_ALPHA`，
  `albedo_color.a`；`cast_shadow` 关闭。

### 6.5 阴影

源对履带/轮子关闭投影，只保留车体轮廓。Godot：

```gdscript
var re := RegEx.new()
re.compile("^(AnimLink_|Tire_|Hub_|HubCap_|Sprocket_|Idler_|Roller_|RunningGear_|Track_)")
for node in model.find_children("*", "MeshInstance3D", true, false):
	if re.search(node.name) != null:
		(node as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
```

先保证轮廓，再谈性能；不要一上来把所有阴影关掉。

---

## 7. 世界、相机、输入

### 7.1 格子

- 13×13，tile 码与源一致：`0 empty, 1 brick, 2 steel, 3 water, 4 forest, 5 ice, 9 eagle`。
- 每格一个 `MeshInstance3D` 在 169 格规模下可接受；砖块销毁用 `visible=false` + 碎片 FX。
- 共享 `BoxMesh`/`PlaneMesh` 和材质，避免每格 new。
- `tileChanged` 到达时只改对应格，不整关重建。
- 鹰徽是玩法格 + 表现模型；不要给鹰徽加独立碰撞体让物理决定失败。

### 7.2 鼠标瞄准

```gdscript
func ground_point(camera: Camera3D, screen_pos: Vector2) -> Variant:
	var from := camera.project_ray_origin(screen_pos)
	var dir := camera.project_ray_normal(screen_pos)
	var plane := Plane(Vector3.UP, 0.0)
	return plane.intersects_ray(from, dir)
```

返回 `Variant`，失败为 `null`。不要用 `Raycaster` + 物理层；地面是数学平面。

### 7.3 相机

- 追尾：目标点 = 坦克位置 + 高度 + 后方偏移；`lerp` 平滑；不要每帧 `look_at` 造成抖动。
- 俯视：切换 `Camera3D.projection` 或移动相机；保持同一 `Camera3D`，避免重建。
- 震屏：在相机局部偏移上叠加噪声，衰减到 0；不要把震动写进 gameplay 坐标。
- 车库环绕：绕展示台旋转；展示用坦克不要参与战斗状态。

---

## 8. HUD、音频、存档

### 8.1 HUD

- `CanvasLayer` 下放 `Control`，用锚点/容器布局；不要 100 个绝对坐标。
- 字体：中文用可商用字体；`Theme` 统一字号/颜色。
- 车库卡片：3 辆坦克，显示名称/级别/血量/速度/伤害/技能；按钮 `pressed` 连接 `start_battle(id)`。
- 战斗 HUD：分数、血量条、技能冷却、波次/剩余敌人、提示大字。
- 结算：胜/负、原因、分数、最高分、返回车库。
- 闪烁用 `Tween`，不要每帧改 `modulate` 造成无谓重绘。

### 8.2 音频

源是 WebAudio 合成音时：

1. 在浏览器里用 `OfflineAudioContext` 按源参数离线渲染每个音效为 WAV；
2. 导入 Godot，设为 `AudioStreamWAV`；
3. `AudioStreamPlayer`（UI/2D）或 `AudioStreamPlayer3D`（世界）；
4. 总线 `Master → SFX`，限制同时播放数，避免爆炸叠音爆音。

不要凭听感重写一套合成器；音色差异会被用户立刻听出来。

### 8.3 存档

```gdscript
var cfg := ConfigFile.new()
var err := cfg.load("user://steel_bastion.cfg")
var hi: int = 0 if err != OK else int(cfg.get_value("progress", "high_score", 0))
cfg.set_value("progress", "high_score", max(hi, score))
cfg.save("user://steel_bastion.cfg")
```

- key 与源一致（例如 `sb3d_sherman_hi`）或明确新 key；写进 README。
- 浏览器 localStorage 不能自动迁移到 Godot；如果需要，提供手动导入。

---

## 9. 性能

先量后调：

```gdscript
var draw_calls := Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
var objects := Performance.get_monitor(Performance.OBJECT_COUNT)
var orphans := Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)
```

重点：

- **146 节履带**：hero 模型每节一个 `MeshInstance3D`，draw call 高。优先
  `MultiMeshInstance3D`（同材质合批）或导入前合并；troop 继续用合并网格。
- **阴影**：只让车体/炮塔投影；履带/轮子关闭。
- **粒子**：GPU 粒子，限制数量；爆炸/烟用池化，不要每次 `instantiate/free`。
- **节点复用**：子弹、履带印、焦痕用对象池；`queue_free()` 不是免费的。
- **材质**：共享基础材质，涂装才 duplicate；不要每个 tile 一份材质。
- **可见性**：远处敌人可 `visibility_range` 或切 troop；不要每帧遍历全场景。

目标（按本项目低模规模）：1280×720 稳定 60 fps，draw call < 400，三角形 < 150k。
以实际测量为准，写进 `port/evidence/G6/perf.txt`。

---

## 10. 不要移植的东西

- `WebGLRenderer` 初始化、resize、pixelRatio、toneMapping 设置 → Godot 工程设置/环境。
- DOM 查询、CSS、`requestAnimationFrame` 外壳、`window.__game` 调试钩子。
- `GLTFLoader` 缓存/失败回退逻辑 → Godot 导入器 + `ResourceLoader`。
- Three.js 的 `AnimationMixer` 内部状态、`ShaderMaterial` GLSL 源码。
- 浏览器音频解锁、自动播放策略 → Godot 音频总线。
- 为了兼容 Web 而写的 polyfill、事件监听器。

这些是**平台适配**，在 Godot 里有等价物；照抄只会增加维护面。
