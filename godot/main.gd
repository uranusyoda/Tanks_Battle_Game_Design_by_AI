extends Node3D

func _ready() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.55, 0.65, 0.78)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.75, 0.75, 0.75)
	e.ambient_light_energy = 0.7
	env.environment = e
	add_child(env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50.0, -30.0, 0.0)
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	add_child(sun)

	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(30.0, 30.0)
	ground.mesh = plane
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.28, 0.30, 0.28)
	ground.material_override = mat
	add_child(ground)

	var cam := Camera3D.new()
	cam.position = Vector3(1.9, 1.15, 2.4)
	add_child(cam)
	cam.look_at(Vector3(0.0, 0.32, 0.0))
	cam.current = true
	cam.fov = 40.0

	var packed: PackedScene = load("res://assets/models/m4a1_sherman_hero.glb")
	var tank := packed.instantiate()
	tank.scale = Vector3.ONE * 0.22
	tank.rotation.y = deg_to_rad(-20.0)
	add_child(tank)
	var turret := tank.find_child("Turret_Pivot", true, false)
	if turret:
		turret.rotation.y = deg_to_rad(30.0)
	var gun := tank.find_child("Gun_Pivot", true, false)
	if gun:
		gun.rotation.x = deg_to_rad(-5.0)

	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var out := ProjectSettings.globalize_path("res://") + "../port/evidence/G2/tank.png"
	var err := img.save_png(out)
	print("saved ", out, " err=", err, " size=", img.get_size())
	get_tree().quit()
