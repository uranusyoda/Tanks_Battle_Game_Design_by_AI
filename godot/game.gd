extends Node3D

# G4 vertical slice: one Sherman, one level, real rules, real GLB, three.js-free view.
# This file is deliberately a slice, not the final architecture. Core stays pure.

const HERO_PATH := "res://assets/models/m4a1_sherman_hero.glb"
const TROOP_PATH := "res://assets/models/m4a1_sherman_troop.glb"
const BOARD := 13.0

const ACTIONS := {
	"move_forward": [KEY_W, KEY_UP],
	"move_back": [KEY_S, KEY_DOWN],
	"turn_left": [KEY_A, KEY_LEFT],
	"turn_right": [KEY_D, KEY_RIGHT],
	"fire": [KEY_SPACE],
	"skill": [KEY_E],
	"camera": [KEY_C],
	"restart": [KEY_R],
}

var content: Dictionary
var battle: PortBattle
var player_rig: TankRig
var enemy_rigs: Dictionary = {}
var bullet_views: Dictionary = {}
var tile_nodes: Dictionary = {}

var tiles_root: Node3D
var tanks_root: Node3D
var effects_root: Node3D
var camera: Camera3D
var hud: CanvasLayer
var stats_label: Label
var message_label: Label
var hint_label: Label
var gameover_root: Control
var gameover_title: Label
var gameover_detail: Label

var camera_mode := 0
var camera_snap := true
var shake := 0.0
var message_timer := 0.0
var game_over := false

var autotest := false
var auto_mode := "battle"

var _font: Font
var _brick_mat: StandardMaterial3D
var _steel_mat: StandardMaterial3D
var _water_mat: StandardMaterial3D
var _ice_mat: StandardMaterial3D
var _forest_mat: StandardMaterial3D
var _trunk_mat: StandardMaterial3D
var _eagle_mat: StandardMaterial3D
var _flag_mat: StandardMaterial3D
var _bullet_mat: StandardMaterial3D


func _ready() -> void:
	content = ContentDB.load_content()
	var user_args := OS.get_cmdline_user_args()
	autotest = user_args.has("--autotest") or user_args.has("--eagle") or user_args.has("--combat") or user_args.has("--inputtest")
	auto_mode = "eagle" if user_args.has("--eagle") else ("combat" if user_args.has("--combat") else ("input" if user_args.has("--inputtest") else "battle"))
	_register_actions()
	_make_materials()
	_setup_environment()
	_setup_ground()
	tiles_root = Node3D.new()
	tiles_root.name = "Tiles"
	add_child(tiles_root)
	tanks_root = Node3D.new()
	tanks_root.name = "Tanks"
	add_child(tanks_root)
	effects_root = Node3D.new()
	effects_root.name = "Effects"
	add_child(effects_root)
	_setup_camera()
	_setup_hud()
	_start_battle(7 if autotest else -1)
	if autotest:
		_run_autotest()


func _register_actions() -> void:
	for action in ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			for key in ACTIONS[action]:
				var event := InputEventKey.new()
				event.physical_keycode = key
				InputMap.action_add_event(action, event)


func _make_materials() -> void:
	_brick_mat = _material(Color(0.55, 0.26, 0.14), 0.0, 0.95)
	_steel_mat = _material(Color(0.42, 0.44, 0.47), 0.65, 0.35)
	_water_mat = _material(Color(0.12, 0.35, 0.55, 0.72), 0.2, 0.12)
	_water_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_ice_mat = _material(Color(0.55, 0.78, 0.88, 0.9), 0.1, 0.18)
	_ice_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_forest_mat = _material(Color(0.10, 0.30, 0.14), 0.0, 0.9)
	_trunk_mat = _material(Color(0.22, 0.14, 0.08), 0.0, 0.95)
	_eagle_mat = _material(Color(0.85, 0.66, 0.18), 0.7, 0.3)
	_flag_mat = _material(Color(0.70, 0.12, 0.10), 0.0, 0.8)
	_bullet_mat = _material(Color(1.0, 0.78, 0.30), 0.0, 0.4)
	_bullet_mat.emission_enabled = true
	_bullet_mat.emission = Color(1.0, 0.55, 0.12)
	_bullet_mat.emission_energy_multiplier = 2.0


func _material(color: Color, metallic: float = 0.0, roughness: float = 0.9) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.metallic = metallic
	mat.roughness = roughness
	return mat


func _setup_environment() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.52, 0.64, 0.78)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.68, 0.73, 0.78)
	e.ambient_light_energy = 0.8
	env.environment = e
	add_child(env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52.0, -32.0, 0.0)
	sun.light_energy = 1.25
	sun.shadow_enabled = true
	add_child(sun)


func _setup_ground() -> void:
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(BOARD, BOARD)
	ground.mesh = plane
	ground.material_override = _material(Color(0.21, 0.25, 0.19), 0.0, 0.98)
	ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(ground)

	var lines := ImmediateMesh.new()
	lines.surface_begin(Mesh.PRIMITIVE_LINES)
	for i in range(14):
		var p := -6.5 + float(i)
		lines.surface_add_vertex(Vector3(p, 0.012, -6.5))
		lines.surface_add_vertex(Vector3(p, 0.012, 6.5))
		lines.surface_add_vertex(Vector3(-6.5, 0.012, p))
		lines.surface_add_vertex(Vector3(6.5, 0.012, p))
	lines.surface_end()
	var line_mesh := MeshInstance3D.new()
	line_mesh.mesh = lines
	var line_mat := _material(Color(0.08, 0.10, 0.08, 0.55), 0.0, 1.0)
	line_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	line_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	line_mesh.material_override = line_mat
	line_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(line_mesh)



func _setup_camera() -> void:
	camera = Camera3D.new()
	camera.name = "Camera"
	camera.fov = 55.0
	camera.current = true
	add_child(camera)
	camera.position = Vector3(0.0, 4.0, 10.0)
	camera.look_at(Vector3(0.0, 0.5, 0.0), Vector3.UP)


func _start_battle(seed_value: int = -1) -> void:
	for child in tiles_root.get_children():
		child.queue_free()
	for child in tanks_root.get_children():
		child.queue_free()
	for child in effects_root.get_children():
		child.queue_free()
	tile_nodes.clear()
	enemy_rigs.clear()
	bullet_views.clear()
	player_rig = null
	game_over = false
	shake = 0.0
	message_timer = 0.0
	if gameover_root != null:
		gameover_root.visible = false

	var seed_use := seed_value if seed_value >= 0 else randi()
	battle = PortBattle.new(content, "sherman", seed_use, content["levels"]["LEVEL"])
	_build_tiles()
	_spawn_player_view()
	camera_snap = true
	_update_camera(0.016, true)
	show_message("守住鹰徽 · 消灭全部敌军")


func _build_tiles() -> void:
	for r in range(13):
		for c in range(13):
			var code := int(battle.grid.tile(r, c))
			if code != PortConstants.TILE_EMPTY:
				_create_tile(r, c, code)


func _create_tile(r: int, c: int, code: int) -> Node3D:
	var key := "%d,%d" % [r, c]
	var root := Node3D.new()
	root.name = "Tile_%s" % key
	root.position = Vector3(PortConstants.cx(c), 0.0, PortConstants.cz(r))
	tiles_root.add_child(root)
	tile_nodes[key] = root

	match code:
		PortConstants.TILE_BRICK:
			root.add_child(_box(Vector3(1.0, 0.8, 1.0), Vector3(0, 0.4, 0), _brick_mat))
		PortConstants.TILE_STEEL:
			root.add_child(_box(Vector3(1.0, 1.0, 1.0), Vector3(0, 0.5, 0), _steel_mat))
		PortConstants.TILE_WATER:
			var water := _box(Vector3(1.0, 0.06, 1.0), Vector3(0, 0.03, 0), _water_mat, false)
			root.add_child(water)
		PortConstants.TILE_ICE:
			var ice := _box(Vector3(1.0, 0.04, 1.0), Vector3(0, 0.02, 0), _ice_mat, false)
			root.add_child(ice)
		PortConstants.TILE_FOREST:
			root.add_child(_cylinder(0.08, 0.08, 0.5, Vector3(0, 0.25, 0), _trunk_mat))
			root.add_child(_cone(0.42, 1.15, Vector3(0, 0.85, 0), _forest_mat))
		PortConstants.TILE_EAGLE:
			root.add_child(_cylinder(0.48, 0.48, 0.08, Vector3(0, 0.04, 0), _eagle_mat))
			root.add_child(_cylinder(0.28, 0.28, 0.12, Vector3(0, 0.12, 0), _flag_mat))
			root.add_child(_cone(0.18, 0.24, Vector3(0, 0.30, 0), _eagle_mat))
	return root


func _box(size: Vector3, pos: Vector3, mat: Material, shadow: bool = true) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.material_override = mat
	mesh.position = pos
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if shadow else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mesh


func _cylinder(top: float, bottom: float, height: float, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = top
	cyl.bottom_radius = bottom
	cyl.height = height
	cyl.radial_segments = 12
	mesh.mesh = cyl
	mesh.material_override = mat
	mesh.position = pos
	return mesh


func _cone(radius: float, height: float, pos: Vector3, mat: Material) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = radius
	cone.height = height
	cone.radial_segments = 7
	mesh.mesh = cone
	mesh.material_override = mat
	mesh.position = pos
	return mesh


func _spawn_player_view() -> void:
	var spec: Dictionary = battle.state["player"]["spec"]
	player_rig = TankRig.new()
	player_rig.name = "Player"
	tanks_root.add_child(player_rig)
	player_rig.setup(HERO_PATH, spec["paint"], 1.0)
	var p: Dictionary = battle.state["player"]
	player_rig.set_pose(float(p["x"]), float(p["z"]), float(p["heading"]), float(p["turretYaw"]))
	player_rig.set_drive(0.0)


func _spawn_enemy_view(event: Dictionary) -> void:
	var id := str(event.get("id", ""))
	if id == "" or enemy_rigs.has(id):
		return
	var type_id := str(event.get("enemyType", event.get("type", "")))
	if not content["enemies"].has(type_id):
		return
	var prof: Dictionary = content["enemies"][type_id]
	var rig := TankRig.new()
	rig.name = "Enemy_%s" % id
	tanks_root.add_child(rig)
	rig.setup(TROOP_PATH, prof["paint"], float(event.get("scale", prof["scale"])))
	rig.set_pose(float(event.get("x", 0.0)), float(event.get("z", 0.0)), 0.0, 0.0)
	enemy_rigs[id] = rig


func _remove_enemy(id: String) -> void:
	if enemy_rigs.has(id):
		var rig: TankRig = enemy_rigs[id]
		enemy_rigs.erase(id)
		rig.queue_free()


func _read_input(skip_aim: bool = false) -> void:
	if Input.is_action_just_pressed("restart"):
		get_tree().reload_current_scene()
		return
	if game_over:
		return
	var throttle := Input.get_action_strength("move_forward") - Input.get_action_strength("move_back")
	var turn := Input.get_action_strength("turn_left") - Input.get_action_strength("turn_right")
	battle.set_move(throttle, turn)
	battle.set_trigger(Input.is_action_pressed("fire") or Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT))

	if Input.is_action_just_pressed("skill"):
		battle.use_skill()
	if Input.is_action_just_pressed("camera"):
		camera_mode = 1 - camera_mode
		camera_snap = true
	if skip_aim:
		return
	var mouse := get_viewport().get_mouse_position()
	var from := camera.project_ray_origin(mouse)
	var dir := camera.project_ray_normal(mouse)
	var hit: Variant = Plane(Vector3.UP, 0.0).intersects_ray(from, dir)
	if hit != null:
		battle.aim_at(float(hit.x), float(hit.z))


func _run_autotest() -> void:
	await get_tree().process_frame
	match auto_mode:
		"input":
			Input.action_press("move_forward")
			for i in range(36):
				_read_input(true)
				_step(1.0 / 60.0)
			Input.action_release("move_forward")
			var z := float(battle.state["player"]["z"])
			print("INPUTTEST z=%.3f moved=%s" % [z, z < 4.9])
			_capture_autotest("input.png")
		"eagle":
			for i in range(120):
				battle.set_move(0.0, 0.0)
				battle.aim_at(0.0, 6.0)
				battle.set_trigger(i >= 12 and i < 72)
				_step(1.0 / 60.0)
			_capture_autotest("eagle-fail.png")
		"combat":
			for i in range(600):
				battle.set_move(0.0, 0.0)
				battle.aim_at(0.0, -6.0)
				battle.set_trigger(true)
				_step(1.0 / 60.0)
				if int(battle.state["killed"]) > 0:
					break
			_capture_autotest("combat.png")
		_:
			for i in range(168):
				if i < 54:
					battle.set_move(1.0, 0.0)
					battle.aim_at(0.0, 3.0)
					battle.set_trigger(false)
				elif i < 102:
					battle.set_move(0.0, 0.0)
					battle.aim_at(0.0, 3.0)
					battle.set_trigger(true)
				else:
					battle.set_move(0.0, 0.0)
					battle.aim_at(0.0, -6.0)
					battle.set_trigger(true)
				_step(1.0 / 60.0)
			_capture_autotest("battle.png")


func _step(dt: float) -> void:
	battle.update(dt)
	for event in battle.drain_events():
		_handle_event(event)
	_sync_views()
	_update_camera(dt)
	_update_hud(dt)


func _capture_autotest(filename: String) -> void:
	if auto_mode == "combat":
		await get_tree().create_timer(0.45).timeout
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var path := ProjectSettings.globalize_path("res://") + "../port/evidence/G4/" + filename
	var err := img.save_png(path)
	print("AUTOTEST mode=%s phase=%s score=%d hp=%d enemies=%d tile9_6=%d err=%d" % [
		auto_mode, battle.state["phase"], int(battle.state["score"]),
		int(battle.state["player"]["hp"]), battle.state["enemies"].size(),
		battle.grid.tile(9, 6), err,
	])
	print("AUTOTEST screenshot ", path, " size=", img.get_size())
	get_tree().quit()


func _process(dt: float) -> void:
	if battle == null or autotest:
		return
	dt = clampf(dt, 0.0, 0.05)
	_read_input()
	if not game_over:
		battle.update(dt)
		for event in battle.drain_events():
			_handle_event(event)
	_sync_views()
	_update_camera(dt)
	_update_hud(dt)


func _sync_views() -> void:
	var p: Dictionary = battle.state["player"]
	if player_rig != null:
		player_rig.set_pose(float(p["x"]), float(p["z"]), float(p["heading"]), float(p["turretYaw"]))
		player_rig.set_drive(float(p["speed"]))

	for enemy in battle.state["enemies"]:
		var id := str(enemy["id"])
		var rig: TankRig = enemy_rigs.get(id)
		if rig == null:
			continue
		rig.set_pose(float(enemy["x"]), float(enemy["z"]), float(enemy["heading"]), float(enemy["turretYaw"]))
		rig.set_drive(float(enemy["prof"]["speed"]) if bool(enemy["moving"]) else 0.0)

	var alive := {}
	for bullet in battle.state["bullets"]:
		var id := str(bullet["id"])
		alive[id] = true
		var view: Node3D = bullet_views.get(id)
		if view == null:
			view = MeshInstance3D.new()
			var sphere := SphereMesh.new()
			sphere.radius = 0.09
			sphere.height = 0.18
			view.mesh = sphere
			view.material_override = _bullet_mat
			view.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			effects_root.add_child(view)
			bullet_views[id] = view
		view.position = Vector3(float(bullet["x"]), 0.46, float(bullet["z"]))
	for id in bullet_views.keys():
		if not alive.has(id):
			var old: Node3D = bullet_views[id]
			bullet_views.erase(id)
			old.queue_free()


func _update_camera(dt: float, force_snap: bool = false) -> void:
	var p: Dictionary = battle.state["player"]
	var forward := Vector3(sin(float(p["heading"])), 0.0, cos(float(p["heading"])))
	var right := Vector3(cos(float(p["heading"])), 0.0, -sin(float(p["heading"])))
	var target_pos := Vector3(float(p["x"]), 0.55, float(p["z"]))
	var desired: Vector3
	var look: Vector3
	if camera_mode == 0:
		desired = Vector3(float(p["x"]), 0.0, float(p["z"])) - forward * 5.4 + right * 1.7 + Vector3(0, 4.0, 0)
		look = target_pos + forward * 1.4 + Vector3(0, 0.15, 0)
	else:
		desired = Vector3(float(p["x"]), 11.0, float(p["z"]) + 0.01)
		look = target_pos

	if force_snap or camera_snap:
		camera.position = desired
		camera_snap = false
	else:
		camera.position = camera.position.lerp(desired, 1.0 - exp(-7.0 * dt))
	camera.look_at(look, Vector3.UP)

	if shake > 0.001:
		var s := shake * 0.18
		camera.position += Vector3(randf_range(-s, s), randf_range(-s, s), 0.0)
		shake = maxf(0.0, shake - dt * 2.2)


func _handle_event(event: Dictionary) -> void:
	var etype := str(event.get("type", ""))

	# D001: the source spawn event's payload "type" overwrites the event type.
	# Accept both the current (enemy type) and the fixed ("spawn" + enemyType) shape.
	if content["enemies"].has(etype) and event.has("scale") and event.has("id"):
		_spawn_enemy_view(event)
		return

	match etype:
		"spawn":
			_spawn_enemy_view(event)
		"fire":
			_on_fire(event)
		"explosion":
			_explosion(float(event["x"]), float(event["z"]), float(event.get("scale", 1.0)))
			shake = minf(0.9, shake + float(event.get("scale", 1.0)) * 0.18)
		"impact":
			_flash_at(float(event["x"]), float(event["z"]), Color(1.0, 0.55, 0.2), 0.28)
		"spark":
			_flash_at(float(event["x"]), float(event["z"]), Color(1.0, 0.9, 0.5), 0.18)
		"tileChanged":
			_on_tile_changed(int(event["r"]), int(event["c"]), int(event["tile"]), int(event.get("previous", 0)))
		"enemyHit":
			var hit_rig: TankRig = enemy_rigs.get(str(event.get("id", "")))
			if hit_rig != null:
				hit_rig.flash("hit", 0.12)
		"enemyKilled":
			_remove_enemy(str(event.get("id", "")))
		"playerHit":
			if player_rig != null:
				player_rig.flash("hit", 0.16)
			shake = minf(1.0, shake + 0.35)
		"shieldBlock":
			if player_rig != null:
				player_rig.flash("frozen", 0.2)
		"reactiveBlock":
			_flash_at(float(event["x"]), float(event["z"]), Color(1.0, 0.45, 0.15), 0.4)
		"skill":
			if str(event.get("kind", "")) == "smoke":
				_flash_at(float(event.get("x", 0.0)), float(event.get("z", 0.0)), Color(0.6, 0.65, 0.55), 0.8)
		"message":
			show_message(str(event.get("text", "")))
		"pickupDropped":
			_flash_at(float(event["x"]), float(event["z"]), Color(1.0, 0.9, 0.3), 0.35)
		"pickup":
			show_message("拾取: %s" % str(event.get("label", "")))
		"lifeLost":
			show_message("剩余坦克 %d" % int(event.get("lives", 0)))
		"respawn":
			if player_rig != null:
				player_rig.set_pose(float(event["x"]), float(event["z"]), PI, 0.0)
		"gameover":
			_show_gameover(bool(event.get("win", false)), str(event.get("reason", "")), int(event.get("score", 0)))


func _on_fire(event: Dictionary) -> void:
	var shooter := str(event.get("shooterId", ""))
	var rig: TankRig = null
	if str(event.get("from", "")) == "player":
		rig = player_rig
	else:
		rig = enemy_rigs.get(shooter)
	var pos := Vector3(float(event.get("x", 0.0)), 0.66, float(event.get("z", 0.0)))
	if rig != null:
		rig.fire()
		pos = rig.muzzle_position()
	_muzzle_flash(pos, bool(event.get("ap", false)))


func _on_tile_changed(r: int, c: int, tile: int, previous: int) -> void:
	var key := "%d,%d" % [r, c]
	if tile_nodes.has(key):
		var old: Node3D = tile_nodes[key]
		tile_nodes.erase(key)
		if previous == PortConstants.TILE_BRICK or previous == PortConstants.TILE_STEEL:
			_debris(old.position, previous)
		old.queue_free()
	if tile != PortConstants.TILE_EMPTY:
		_create_tile(r, c, tile)


func _debris(pos: Vector3, previous: int) -> void:
	var color := Color(0.55, 0.26, 0.14) if previous == PortConstants.TILE_BRICK else Color(0.42, 0.44, 0.47)
	for i in range(4):
		var piece := _box(Vector3(0.16, 0.16, 0.16), Vector3(randf_range(-0.3, 0.3), 0.35, randf_range(-0.3, 0.3)), _material(color, 0.0, 0.9), false)
		piece.position += pos
		effects_root.add_child(piece)
		var tween := create_tween()
		tween.set_parallel(true)
		tween.tween_property(piece, "position", piece.position + Vector3(randf_range(-0.8, 0.8), 0.6, randf_range(-0.8, 0.8)), 0.35)
		tween.tween_property(piece, "scale", Vector3.ZERO, 0.35)
		tween.chain().tween_callback(piece.queue_free)


func _muzzle_flash(pos: Vector3, ap: bool) -> void:
	var mat := _material(Color(1.0, 0.9, 0.55), 0.0, 0.3)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.75, 0.25)
	mat.emission_energy_multiplier = 3.0
	var flash := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.16 if not ap else 0.22
	sphere.height = 0.32
	flash.mesh = sphere
	flash.material_override = mat
	flash.position = pos
	flash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	effects_root.add_child(flash)
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.7, 0.3)
	light.light_energy = 2.0
	light.omni_range = 2.0
	flash.add_child(light)
	create_tween().tween_property(flash, "scale", Vector3.ZERO, 0.09).finished.connect(flash.queue_free)


func _flash_at(x: float, z: float, color: Color, size: float) -> void:
	var mat := _material(color, 0.0, 0.4)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.emission_enabled = true
	mat.emission = color
	mat.emission_energy_multiplier = 2.0
	var flash := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.15
	sphere.height = 0.3
	flash.mesh = sphere
	flash.material_override = mat
	flash.position = Vector3(x, 0.55, z)
	flash.scale = Vector3.ONE * size
	flash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	effects_root.add_child(flash)
	create_tween().tween_property(flash, "scale", Vector3.ZERO, 0.22).finished.connect(flash.queue_free)


func _explosion(x: float, z: float, size: float) -> void:
	var mat := _material(Color(1.0, 0.42, 0.12, 0.9), 0.0, 0.5)
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.35, 0.05)
	mat.emission_energy_multiplier = 4.0
	var boom := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.35
	sphere.height = 0.7
	boom.mesh = sphere
	boom.material_override = mat
	boom.position = Vector3(x, 0.45, z)
	boom.scale = Vector3.ONE * 0.2
	boom.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	effects_root.add_child(boom)
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.5, 0.2)
	light.light_energy = 3.0 * size
	light.omni_range = 3.0 * size
	boom.add_child(light)
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(boom, "scale", Vector3.ONE * (0.45 + size * 0.8), 0.35)
	tween.tween_property(boom, "position:y", 1.2, 0.35)
	tween.tween_property(mat, "albedo_color", Color(1.0, 0.42, 0.12, 0.0), 0.35)
	tween.chain().tween_callback(boom.queue_free)


func _load_cjk_font() -> Font:
	var file := FontFile.new()
	if file.load_dynamic_font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf") == OK:
		return file
	var system := SystemFont.new()
	system.font_names = PackedStringArray(["PingFang SC", "Heiti SC", "Arial Unicode MS"])
	return system


func _setup_hud() -> void:
	_font = _load_cjk_font()
	hud = CanvasLayer.new()
	hud.layer = 10
	add_child(hud)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(root)

	stats_label = _label("", 22, Color(0.96, 0.95, 0.88))
	stats_label.position = Vector2(24, 18)
	stats_label.size = Vector2(900, 34)
	root.add_child(stats_label)

	message_label = _label("", 34, Color(1.0, 0.84, 0.35))
	message_label.position = Vector2(0, 74)
	message_label.size = Vector2(1280, 50)
	message_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	message_label.visible = false
	root.add_child(message_label)

	hint_label = _label("WASD 移动 · 鼠标瞄准 · 空格/左键开火 · E 技能 · C 视角 · R 重开", 18, Color(0.86, 0.88, 0.84))
	hint_label.position = Vector2(0, 682)
	hint_label.size = Vector2(1280, 28)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(hint_label)

	gameover_root = Control.new()
	gameover_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	gameover_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	gameover_root.visible = false
	root.add_child(gameover_root)
	var dim := ColorRect.new()
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.02, 0.03, 0.04, 0.62)
	gameover_root.add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	gameover_root.add_child(center)
	var box := VBoxContainer.new()
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	box.add_theme_constant_override("separation", 12)
	center.add_child(box)
	gameover_title = _label("", 64, Color(1.0, 0.82, 0.3))
	gameover_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(gameover_title)
	gameover_detail = _label("", 24, Color(0.92, 0.92, 0.88))
	gameover_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(gameover_detail)
	var again := _label("按 R 重新开始", 20, Color(0.75, 0.78, 0.74))
	again.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(again)


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_override("font", _font)
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 0.85))
	label.add_theme_constant_override("outline_size", 5)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label


func show_message(text: String) -> void:
	if message_label == null:
		return
	message_label.text = text
	message_label.visible = true
	message_label.modulate.a = 1.0
	message_timer = 2.6


func _update_hud(dt: float) -> void:
	if stats_label == null:
		return
	var p: Dictionary = battle.state["player"]
	var total_waves: int = content["levels"]["LEVEL"]["waves"].size()
	stats_label.text = "得分 %d    HP %d/%d    波次 %d/%d    敌军 %d" % [
		int(battle.state["score"]), int(p["hp"]), int(p["maxHp"]),
		mini(maxi(1, int(battle.state["wave"])), total_waves), total_waves,
		battle.state["enemies"].size(),
	]
	if message_timer > 0.0:
		message_timer -= dt
		message_label.modulate.a = clampf(message_timer, 0.0, 1.0)
		if message_timer <= 0.0:
			message_label.visible = false


func _show_gameover(win: bool, reason: String, score: int) -> void:
	game_over = true
	battle.stop()
	message_label.visible = false
	gameover_root.visible = true
	gameover_title.text = "胜利" if win else "失败"
	gameover_title.add_theme_color_override("font_color", Color(1.0, 0.85, 0.35) if win else Color(1.0, 0.4, 0.3))
	gameover_detail.text = "%s\n得分 %d" % [reason, score]
