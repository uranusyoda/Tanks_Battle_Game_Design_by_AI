class_name TestAsset
extends RefCounted


static func _check(name: String, ok: bool, detail: String = "") -> int:
	if ok:
		print("PASS ", name)
		return 0
	print("FAIL ", name, "  ", detail)
	return 1


static func _inspect(path: String, tags: Dictionary, expect_drive: bool, expect_fire: bool) -> Array:
	var errors: Array = []
	var packed: Resource = load(path)
	if not packed is PackedScene:
		return ["%s is not a PackedScene" % path]
	var root: Node = (packed as PackedScene).instantiate()
	if root == null:
		return ["%s failed to instantiate" % path]

	for key in tags:
		var node := root.find_child(str(tags[key]), true, false)
		if node == null:
			errors.append("missing tag %s (%s)" % [key, tags[key]])

	var anim := root.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if anim == null:
		errors.append("missing AnimationPlayer")
	else:
		if expect_drive and not anim.has_animation("Drive"):
			errors.append("missing Drive clip")
		if expect_fire and not anim.has_animation("Fire"):
			errors.append("missing Fire clip")
		if not expect_drive and anim.has_animation("Drive"):
			errors.append("troop unexpectedly has Drive clip")

	var meshes := root.find_children("*", "MeshInstance3D", true, false)
	if meshes.is_empty():
		errors.append("no MeshInstance3D")
	var tracks := 0
	for m in meshes:
		if str(m.name).begins_with("AnimLink_"):
			tracks += 1
	print("  %s: meshes=%d track_links=%d clips=%s" % [
		path.get_file(), meshes.size(), tracks,
		"?" if anim == null else str(anim.get_animation_list()),
	])
	root.free()
	return errors


static func run_all() -> int:
	var failed := 0
	var tags := {"turret": "Turret_Pivot", "gun": "Gun_Pivot", "muzzle": "GunMuzzle"}

	var hero_errors := _inspect("res://assets/models/m4a1_sherman_hero.glb", tags, true, true)
	failed += _check("asset contract: sherman_hero (tags + Drive/Fire)", hero_errors.is_empty(), str(hero_errors))

	var troop_errors := _inspect("res://assets/models/m4a1_sherman_troop.glb", tags, false, true)
	failed += _check("asset contract: sherman_troop (tags + Fire, no Drive)", troop_errors.is_empty(), str(troop_errors))
	return failed
