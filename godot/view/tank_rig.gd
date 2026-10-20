class_name TankRig
extends Node3D

# One game-ready tank: named turret/gun/muzzle, Drive loop, Fire one-shot,
# per-instance paint and hit flash. Presentation only; rules stay in PortBattle.

const MODEL_SCALE := 0.22
const TREAD_RATE := 0.9
const NO_SHADOW := "^(AnimLink_|Tire_|Hub_|HubCap_|Sprocket_|Idler_|Roller_|RunningGear_|Track_)"

const PAINT_KEYS := {
	"Sherman_Olive": "olive",
	"Sherman_OliveDark": "oliveDark",
	"Sherman_Star": "star",
}

var model: Node3D
var turret: Node3D
var gun: Node3D
var muzzle: Node3D
var drive_player: AnimationPlayer
var fire_player: AnimationPlayer

var _materials: Array[Dictionary] = []
var _flash_time := 0.0
var _flash_kind := ""


func setup(path: String, paint: Dictionary, scale_mult: float = 1.0) -> bool:
	var packed := load(path) as PackedScene
	if packed == null:
		push_error("Cannot load tank model: %s" % path)
		return false
	model = packed.instantiate()
	add_child(model)
	scale = Vector3.ONE * MODEL_SCALE * scale_mult

	turret = model.find_child("Turret_Pivot", true, false) as Node3D
	gun = model.find_child("Gun_Pivot", true, false) as Node3D
	muzzle = model.find_child("GunMuzzle", true, false) as Node3D
	if turret == null or gun == null or muzzle == null:
		push_error("Tank model is missing Turret_Pivot / Gun_Pivot / GunMuzzle: %s" % path)
		return false

	_setup_materials(paint)
	_setup_animations()
	return true


func _setup_materials(paint: Dictionary) -> void:
	var re := RegEx.new()
	re.compile(NO_SHADOW)
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		if re.search(str(mesh.name)) != null:
			mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		for i in range(mesh.mesh.get_surface_count()):
			var mat := mesh.get_active_material(i)
			if not mat is StandardMaterial3D:
				continue
			var copy: StandardMaterial3D = mat.duplicate()
			copy.resource_name = mat.resource_name
			var key: String = PAINT_KEYS.get(copy.resource_name, "")
			if key != "" and paint.has(key):
				var v := int(paint[key])
				copy.albedo_color = Color8((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)
			copy.emission_enabled = true
			copy.emission = Color(0.0, 0.0, 0.0)
			copy.emission_energy_multiplier = 0.0
			mesh.set_surface_override_material(i, copy)
			_materials.append({
				"mat": copy,
				"base": copy.albedo_color,
				"base_emission": copy.emission,
				"base_energy": copy.emission_energy_multiplier,
			})


func _setup_animations() -> void:
	var anim := model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim == null:
		return
	if anim.has_animation("Drive"):
		drive_player = anim
		var drive := anim.get_animation("Drive")
		drive.loop_mode = Animation.LOOP_LINEAR
		anim.play("Drive")
		anim.speed_scale = 0.0
	if anim.has_animation("Fire"):
		var host := anim.get_parent()
		fire_player = AnimationPlayer.new()
		fire_player.name = "FirePlayer"
		fire_player.root_node = anim.root_node
		host.add_child(fire_player)
		fire_player.add_animation_library("", anim.get_animation_library("").duplicate(true))
		var fire := fire_player.get_animation("Fire")
		fire.loop_mode = Animation.LOOP_NONE


func set_pose(x: float, z: float, heading: float, turret_yaw: float) -> void:
	position = Vector3(x, 0.0, z)
	rotation.y = heading
	if turret != null:
		turret.rotation.y = turret_yaw


func set_drive(speed: float) -> void:
	if drive_player == null:
		return
	if absf(speed) < 0.05:
		drive_player.speed_scale = 0.0
	else:
		drive_player.speed_scale = signf(speed) * minf(absf(speed) * TREAD_RATE, 2.4)


func fire() -> void:
	if fire_player == null:
		return
	fire_player.stop()
	fire_player.play("Fire")


func muzzle_position() -> Vector3:
	if muzzle != null:
		return muzzle.global_position
	return global_position + Vector3(0.0, 0.8, 0.0)


func flash(kind: String, duration: float = 0.12) -> void:
	_flash_time = duration
	_flash_kind = kind
	for entry in _materials:
		var mat: StandardMaterial3D = entry["mat"]
		if kind == "hit":
			mat.emission = Color(0.75, 0.08, 0.04)
			mat.emission_energy_multiplier = 1.8
		elif kind == "frozen":
			mat.emission = Color(0.05, 0.35, 0.65)
			mat.emission_energy_multiplier = 1.6
		else:
			mat.emission = entry["base_emission"]
			mat.emission_energy_multiplier = entry["base_energy"]


func _process(dt: float) -> void:
	if _flash_time <= 0.0:
		return
	_flash_time -= dt
	if _flash_time <= 0.0 and _flash_kind != "":
		_flash_kind = ""
		for entry in _materials:
			var mat: StandardMaterial3D = entry["mat"]
			mat.emission = entry["base_emission"]
			mat.emission_energy_multiplier = entry["base_energy"]
