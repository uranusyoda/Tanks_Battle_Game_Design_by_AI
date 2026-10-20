class_name TestTrace
extends RefCounted

const TRACE_DIR := "res://tests/golden"
const TOL := 1e-5


static func run_all() -> int:
	var content := ContentDB.load_content()
	var content_hash := _sha256_file("res://content/content.json")
	var files: Array[String] = []
	var dir := DirAccess.open(TRACE_DIR)
	if dir == null:
		print("FAIL cannot open ", TRACE_DIR)
		return 1
	dir.list_dir_begin()
	var file := dir.get_next()
	while file != "":
		if file.ends_with(".json"):
			files.append(file)
		file = dir.get_next()
	dir.list_dir_end()
	files.sort()

	var failed := 0
	for trace_file in files:
		var trace: Variant = ContentDB.load_json(TRACE_DIR + "/" + trace_file)
		if not trace is Dictionary:
			print("FAIL ", trace_file, ": not a JSON object")
			failed += 1
			continue
		var errors: Array = []
		if str(trace.get("contentHash", "")) != content_hash:
			errors.append("contentHash mismatch: trace=%s godot=%s" % [trace.get("contentHash", ""), content_hash])
		errors.append_array(_replay(trace, content))
		if errors.is_empty():
			print("PASS trace ", trace["scenario"], " (", trace["steps"], " steps)")
		else:
			failed += 1
			print("FAIL trace ", trace["scenario"])
			for i in range(mini(errors.size(), 8)):
				print("  - ", errors[i])
	return failed


static func _sha256_file(path: String) -> String:
	var bytes := FileAccess.get_file_as_bytes(path)
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(bytes)
	return ctx.finish().hex_encode()


static func _apply_command(battle: PortBattle, op: String, args: Array) -> void:
	match op:
		"setMove":
			battle.set_move(float(args[0]), float(args[1]))
		"setTrigger":
			battle.set_trigger(bool(args[0]))
		"aimAt":
			battle.aim_at(float(args[0]), float(args[1]))
		"useSkill":
			battle.use_skill()
		"stop":
			battle.stop()
		_:
			push_error("unknown trace command: %s" % op)


static func _replay(trace: Dictionary, content: Dictionary) -> Array:
	var errors: Array = []
	var battle := PortBattle.new(content, str(trace["tankId"]), int(trace["seed"]), trace["level"])
	var initial: Variant = trace.get("initial")
	if initial is Dictionary:
		for key in initial:
			battle.state["player"][key] = initial[key]

	var commands: Array = trace["commands"]
	var expected_events: Array = trace["events"]
	var expected_samples: Array = trace["samples"]
	var got_events: Array = []
	var got_samples: Array = []
	var steps := int(trace["steps"])
	var dt := float(trace.get("dt_num", 1)) / float(trace.get("dt_den", 60))

	for step in range(steps):
		for command in commands:
			if int(command["step"]) == step:
				_apply_command(battle, str(command["op"]), command["args"])
		battle.update(dt)
		for event in battle.drain_events():
			var got_event: Dictionary = event.duplicate()
			got_event["step"] = step
			got_events.append(got_event)
		if step % 5 == 0:
			got_samples.append({"step": step, "state": _snap(battle)})

	var got_final := _snap(battle)
	_compare("events", expected_events, got_events, errors)
	_compare("samples", expected_samples, got_samples, errors)
	_compare("final", trace["final"], got_final, errors)
	return errors


static func _snap(battle: PortBattle) -> Dictionary:
	var s: Dictionary = battle.state
	var enemies: Array = []
	for enemy in s["enemies"]:
		enemies.append({
			"id": enemy["id"], "x": enemy["x"], "z": enemy["z"], "heading": enemy["heading"],
			"turretYaw": enemy["turretYaw"], "hp": enemy["hp"],
		})
	var bullets: Array = []
	for bullet in s["bullets"]:
		bullets.append({"id": bullet["id"], "x": bullet["x"], "z": bullet["z"], "from": bullet["from"]})
	var pickups: Array = []
	for pickup in s["pickups"]:
		pickups.append({
			"id": pickup["id"], "x": pickup["x"], "z": pickup["z"],
			"powerupId": pickup["def"]["id"],
		})
	return {
		"t": s["time"], "phase": s["phase"], "score": s["score"], "wave": s["wave"],
		"killed": s["killed"], "skillCd": s["skillCd"],
		"player": {
			"x": s["player"]["x"], "z": s["player"]["z"], "heading": s["player"]["heading"],
			"turretYaw": s["player"]["turretYaw"], "hp": s["player"]["hp"],
			"lives": s["player"]["lives"], "alive": s["player"]["alive"],
			"invuln": s["player"]["invuln"], "smoke": s["player"]["smoke"],
		},
		"enemies": enemies, "bullets": bullets, "pickups": pickups,
		"eagle": s["eagle"]["alive"],
	}


static func _compare(path: String, expected: Variant, got: Variant, errors: Array) -> void:
	if errors.size() >= 8:
		return
	var te := typeof(expected)
	var tg := typeof(got)
	if te == TYPE_DICTIONARY and tg == TYPE_DICTIONARY:
		var expected_dict: Dictionary = expected
		var got_dict: Dictionary = got
		for key in expected_dict:
			if not got_dict.has(key):
				errors.append("%s.%s missing in Godot" % [path, key])
				continue
			_compare("%s.%s" % [path, key], expected_dict[key], got_dict[key], errors)
		for key in got_dict:
			if not expected_dict.has(key):
				errors.append("%s.%s extra in Godot" % [path, key])
		return
	if te == TYPE_ARRAY and tg == TYPE_ARRAY:
		var expected_arr: Array = expected
		var got_arr: Array = got
		if expected_arr.size() != got_arr.size():
			errors.append("%s size %d != %d" % [path, expected_arr.size(), got_arr.size()])
			return
		for i in range(expected_arr.size()):
			_compare("%s[%d]" % [path, i], expected_arr[i], got_arr[i], errors)
		return
	if (te == TYPE_INT or te == TYPE_FLOAT) and (tg == TYPE_INT or tg == TYPE_FLOAT):
		var diff := absf(float(expected) - float(got))
		if diff > TOL:
			errors.append("%s %.9f != %.9f (delta %s)" % [path, float(expected), float(got), str(diff)])
		return
	if expected != got:
		errors.append("%s %s != %s" % [path, str(expected), str(got)])
