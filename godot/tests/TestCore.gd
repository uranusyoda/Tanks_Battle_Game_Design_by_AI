class_name TestCore
extends RefCounted

static var _content_cache: Dictionary = {}


static func _content() -> Dictionary:
	if _content_cache.is_empty():
		_content_cache = ContentDB.load_content()
	return _content_cache


static func _clone(value: Variant) -> Variant:
	return JSON.parse_string(JSON.stringify(value))


static func _make_level(waves: Variant = null, bunker: Variant = null) -> Dictionary:
	var level: Dictionary = _clone(_content()["levels"]["LEVEL"])
	if waves != null:
		level["waves"] = waves
	if bunker != null:
		level["bunker"] = bunker
	return level


static func _make_battle(tank_id: String = "sherman", level: Variant = null, seed_value: int = 7) -> PortBattle:
	var content := _content()
	var use_level: Variant = level if level != null else content["levels"]["LEVEL"]
	return PortBattle.new(content, tank_id, seed_value, use_level)


static func _tick(battle: PortBattle, seconds: float, step: float = 1.0 / 60.0) -> void:
	var n := PortConstants.js_round(seconds / step)
	for i in range(n):
		battle.update(step)


static func _events_of(battle: PortBattle, type: String) -> Array:
	var out: Array = []
	for event in battle.drain_events():
		if event["type"] == type:
			out.append(event)
	return out


static func _check(name: String, ok: bool, detail: String = "") -> int:
	if ok:
		print("PASS ", name)
		return 0
	print("FAIL ", name, "  ", detail)
	return 1


static func run_all() -> int:
	var failed := 0
	failed += _test_content()
	failed += _test_grid_brick()
	failed += _test_fire_brick()
	failed += _test_enemy_damage()
	failed += _test_shield()
	failed += _test_eagle_fail()
	failed += _test_win()
	failed += _test_star()
	failed += _test_determinism()
	failed += _test_core_purity()
	return failed


static func _test_content() -> int:
	var content := _content()
	var ok := true
	var detail := ""
	for tank in content["tanks"].values():
		if not tank.has("skill") or not tank["skill"].has("name"):
			ok = false
			detail += "tank %s missing skill; " % tank.get("id", "?")
		if not tank.has("model") or not tank["model"].has("lod"):
			ok = false
			detail += "tank %s missing lod; " % tank.get("id", "?")
	for wave in content["levels"]["LEVEL"]["waves"]:
		for enemy_id in wave["list"]:
			if not content["enemies"].has(enemy_id):
				ok = false
				detail += "missing enemy %s; " % enemy_id
	var eagles := 0
	for row in content["levels"]["LEVEL"]["grid"]:
		for tile in row:
			if int(tile) == PortConstants.TILE_EAGLE:
				eagles += 1
	if eagles != 1:
		ok = false
		detail += "eagles=%d; " % eagles
	return _check("content: every tank and enemy in the waves is defined", ok, detail)


static func _test_grid_brick() -> int:
	var battle := _make_battle()
	var p: Dictionary = battle.state["player"]
	p["x"] = 0.0
	p["z"] = 5.0
	p["heading"] = PI
	battle.set_move(1.0, 0.0)
	_tick(battle, 1.5)
	return _check("grid: a tank cannot drive through a brick", float(p["z"]) > 3.5, "z=%.6f" % float(p["z"]))


static func _test_fire_brick() -> int:
	var battle := _make_battle()
	var p: Dictionary = battle.state["player"]
	p["x"] = 0.0
	p["z"] = 5.0
	p["heading"] = PI
	p["invuln"] = 0.0
	battle.aim_at(0.0, 3.0)
	battle.set_trigger(true)
	battle.update(1.0 / 60.0)
	battle.set_trigger(false)
	_tick(battle, 0.5)
	var tile_ok := battle.grid.tile(9, 6) == PortConstants.TILE_EMPTY
	var changed := _events_of(battle, "tileChanged")
	var event_ok := changed.size() == 1 and int(changed[0]["r"]) == 9 and int(changed[0]["c"]) == 6
	return _check(
		"rules: firing destroys a brick and emits a semantic event",
		tile_ok and event_ok,
		"tile=%d events=%d" % [battle.grid.tile(9, 6), changed.size()]
	)


static func _test_enemy_damage() -> int:
	var level := _make_level([{"t": 0, "list": ["line"]}], [])
	var battle := _make_battle("sherman", level)
	battle.update(1.0 / 60.0)
	if battle.state["enemies"].is_empty():
		return _check("rules: an enemy shot damages the player", false, "enemy did not spawn")
	var enemy: Dictionary = battle.state["enemies"][0]
	var p: Dictionary = battle.state["player"]
	enemy["x"] = p["x"]
	enemy["z"] = float(p["z"]) - 1.5
	enemy["heading"] = 0.0
	enemy["fireCd"] = 0.0
	p["invuln"] = 0.0
	battle.update(1.0 / 60.0)
	_tick(battle, 0.6)
	return _check(
		"rules: an enemy shot damages the player",
		float(p["hp"]) < float(p["maxHp"]),
		"hp=%.3f" % float(p["hp"])
	)


static func _test_shield() -> int:
	var level := _make_level([{"t": 0, "list": ["line"]}], [])
	var battle := _make_battle("sherman", level)
	battle.update(1.0 / 60.0)
	if battle.state["enemies"].is_empty():
		return _check("rules: a shield absorbs a hit without losing HP", false, "enemy did not spawn")
	var enemy: Dictionary = battle.state["enemies"][0]
	var p: Dictionary = battle.state["player"]
	enemy["x"] = p["x"]
	enemy["z"] = float(p["z"]) - 1.5
	enemy["fireCd"] = 0.0
	p["invuln"] = 0.0
	p["shield"] = 10.0
	battle.update(1.0 / 60.0)
	_tick(battle, 0.6)
	var blocks := _events_of(battle, "shieldBlock")
	return _check(
		"rules: a shield absorbs a hit without losing HP",
		float(p["hp"]) == float(p["maxHp"]) and blocks.size() >= 1,
		"hp=%.3f blocks=%d" % [float(p["hp"]), blocks.size()]
	)


static func _test_eagle_fail() -> int:
	var battle := _make_battle()
	var p: Dictionary = battle.state["player"]
	p["x"] = 0.0
	p["z"] = 5.0
	p["heading"] = 0.0
	p["turretYaw"] = 0.0
	p["invuln"] = 0.0
	battle.set_trigger(true)
	battle.update(1.0 / 60.0)
	battle.set_trigger(false)
	_tick(battle, 0.2)
	var gameover := _events_of(battle, "gameover")
	return _check(
		"rules: killing the eagle loses the battle, even with the player shot",
		battle.state["phase"] == "lost" and not bool(battle.state["eagle"]["alive"])
			and gameover.size() == 1 and not bool(gameover[0]["win"]),
		"phase=%s gameover=%d" % [battle.state["phase"], gameover.size()]
	)


static func _test_win() -> int:
	var battle := _make_battle("sherman", _make_level([], []))
	battle.update(1.0 / 60.0)
	var s: Dictionary = battle.state
	s["wave"] = _content()["levels"]["LEVEL"]["waves"].size()
	s["spawnQueue"].clear()
	s["enemies"].clear()
	battle.update(1.0 / 60.0)
	var gameover := _events_of(battle, "gameover")
	return _check(
		"rules: clearing the last wave wins",
		s["phase"] == "won" and gameover.size() == 1 and bool(gameover[0]["win"]),
		"phase=%s gameover=%d" % [s["phase"], gameover.size()]
	)


static func _test_star() -> int:
	var battle := _make_battle()
	var p: Dictionary = battle.state["player"]
	var before := float(p["fireInterval"])
	var star: Dictionary = {}
	for def in _content()["powerups"]:
		if def["id"] == "star":
			star = def
			break
	battle.state["pickups"].append({"id": "test", "def": star, "x": p["x"], "z": p["z"], "life": 5.0})
	battle.update(1.0 / 60.0)
	return _check(
		"rules: a star power-up improves rate of fire exactly once",
		float(p["fireInterval"]) < before and battle.state["pickups"].is_empty(),
		"before=%.3f after=%.3f pickups=%d" % [before, float(p["fireInterval"]), battle.state["pickups"].size()]
	)


static func _test_determinism() -> int:
	var first := _run_determinism()
	var second := _run_determinism()
	return _check("rules: same seed + same inputs produce the same battle", first == second, "digests differ")


static func _run_determinism() -> String:
	var battle := _make_battle("sherman", null, 42)
	var parts: Array[String] = []
	for i in range(180):
		battle.set_move(1.0 if i < 90 else -1.0, 1.0 if i % 30 == 0 else 0.0)
		battle.set_trigger(i % 12 == 0)
		battle.aim_at(1.0, 2.0)
		battle.update(1.0 / 60.0)
		battle.drain_events()
		var enemy_parts: Array[String] = []
		for enemy in battle.state["enemies"]:
			enemy_parts.append("%.3f,%.3f" % [float(enemy["x"]), float(enemy["z"])])
		parts.append("%.4f,%.4f,%s" % [
			float(battle.state["player"]["x"]),
			float(battle.state["player"]["z"]),
			"|".join(enemy_parts),
		])
	return ";".join(parts)


static func _test_core_purity() -> int:
	var dir := DirAccess.open("res://core")
	if dir == null:
		return _check("layering: core is pure RefCounted", false, "cannot open res://core")
	var ok := true
	var detail := ""
	dir.list_dir_begin()
	var file := dir.get_next()
	while file != "":
		if file.ends_with(".gd"):
			var text := FileAccess.get_file_as_string("res://core/" + file)
			if not text.contains("extends RefCounted"):
				ok = false
				detail += "%s does not extend RefCounted; " % file
			for banned in ["get_tree(", "Input.", "preload(\"res://"]:
				if text.contains(banned):
					ok = false
					detail += "%s contains %s; " % [file, banned]
		file = dir.get_next()
	dir.list_dir_end()
	return _check("layering: core is pure RefCounted with no engine/asset calls", ok, detail)
