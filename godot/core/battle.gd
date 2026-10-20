class_name PortBattle
extends RefCounted

# Faithful port of versions/v3/src/core/battle.js.
# No Node, no scene tree, no Input, no asset loading. Content is injected.

const PLAYER_SPAWN := {"x": 0.0, "z": 5.0, "heading": PI}
const ENEMY_BULLET_SPEED := 7.5
const BULLET_LIFE := 2.6
const ICE_ACCEL := 3.0
const ENEMY_TURRET_SPEED := 4.0

var state: Dictionary = {}
var grid: BattleGrid
var _events: Array[Dictionary] = []

var _content: Dictionary
var _tanks: Dictionary
var _enemy_types: Dictionary
var _level: Dictionary
var _powerups: Array
var _spec: Dictionary
var _rand: BattleRng
var _waves: Array = []
var _input := {"throttle": 0.0, "turn": 0.0, "trigger": false}
var _aim := {"x": 0.0, "z": 0.0, "active": false}
var _enemy_seq := 0
var _bullet_seq := 0
var _pickup_seq := 0


func _init(content: Dictionary, tank_id: String, seed_value: int = 1, level_override: Variant = null, start_lives: int = 3) -> void:
	_content = content
	_tanks = content["tanks"]
	_enemy_types = content["enemies"]
	_powerups = content["powerups"]
	_level = level_override if level_override != null else content["levels"]["LEVEL"]

	if not _tanks.has(tank_id):
		push_error("Unknown tank id: %s" % tank_id)
		return
	_spec = _tanks[tank_id]
	_rand = BattleRng.new(seed_value)
	grid = BattleGrid.new(_level)

	var eagle := _find_eagle()
	var total := 0
	for wave in _level["waves"]:
		total += wave["list"].size()

	state = {
		"phase": "battle",
		"tankId": tank_id,
		"time": 0.0,
		"score": 0,
		"killed": 0,
		"totalEnemies": total,
		"wave": 0,
		"spawnQueue": [],
		"spawnTimer": 0.0,
		"spawnIndex": 0,
		"respawnTimer": 0.0,
		"skillCd": 0.0,
		"fortTimer": 0.0,
		"eagle": {"r": eagle["r"], "c": eagle["c"], "x": eagle["x"], "z": eagle["z"], "alive": true},
		"player": {
			"id": "player",
			"spec": _spec,
			"x": PLAYER_SPAWN["x"],
			"z": PLAYER_SPAWN["z"],
			"heading": PLAYER_SPAWN["heading"],
			"turretYaw": 0.0,
			"hp": float(_spec["hp"]),
			"maxHp": float(_spec["hp"]),
			"fireInterval": float(_spec["fire"]),
			"fireCd": 0.0,
			"damage": float(_spec["dmg"]),
			"bulletSpeed": float(_spec["bspd"]),
			"lives": start_lives,
			"invuln": 2.0,
			"shield": 0.0,
			"smoke": 0.0,
			"ap": false,
			"reactiveLeft": 0,
			"reactiveTimer": 0.0,
			"repair": 0.0,
			"alive": true,
			"vel": {"x": 0.0, "z": 0.0},
			"throttle": 0.0,
			"turn": 0.0,
			"speed": 0.0,
			"moving": false,
		},
		"enemies": [],
		"bullets": [],
		"pickups": [],
	}

	for wave in _level["waves"]:
		_waves.append({"t": float(wave["t"]), "list": wave["list"].duplicate()})


func _find_eagle() -> Dictionary:
	for r in range(PortConstants.ROWS):
		for c in range(PortConstants.COLS):
			if grid.tile(r, c) == PortConstants.TILE_EAGLE:
				return {"r": r, "c": c, "x": PortConstants.cx(c), "z": PortConstants.cz(r)}
	push_error("Level has no eagle tile (9)")
	return {"r": 0, "c": 0, "x": 0.0, "z": 0.0}


# ------------------------------------------------------------------ commands
func set_move(throttle: float, turn: float) -> void:
	_input["throttle"] = clampf(throttle, -1.0, 1.0)
	_input["turn"] = clampf(turn, -1.0, 1.0)


func set_trigger(on: bool) -> void:
	_input["trigger"] = on


func aim_at(x: float, z: float) -> void:
	_aim["x"] = x
	_aim["z"] = z
	_aim["active"] = true


func use_skill() -> bool:
	if state["phase"] != "battle" or float(state["skillCd"]) > 0.0 or not bool(state["player"]["alive"]):
		return false
	return _activate_skill()


func stop() -> void:
	_input["throttle"] = 0.0
	_input["turn"] = 0.0
	_input["trigger"] = false


# -------------------------------------------------------------------- skill
func _activate_skill() -> bool:
	var p: Dictionary = state["player"]
	var id: String = p["spec"]["id"]
	if id == "sherman":
		p["smoke"] = 5.0
		state["skillCd"] = 20.0
		_emit("skill", {"kind": "smoke", "x": p["x"], "z": p["z"]})
		_emit("message", {"text": "烟幕释放!"})
	elif id == "tiger":
		p["ap"] = true
		state["skillCd"] = 15.0
		_emit("skill", {"kind": "ap"})
		_emit("message", {"text": "穿甲弹已装填"})
	else:
		p["reactiveLeft"] = 3
		p["reactiveTimer"] = 30.0
		state["skillCd"] = 25.0
		_emit("skill", {"kind": "reactive"})
		_emit("message", {"text": "反应装甲启动 x3"})
	return true


# ------------------------------------------------------------------- player
func _player_fire() -> void:
	var p: Dictionary = state["player"]
	var yaw := float(p["heading"]) + float(p["turretYaw"])
	var muzzle := float(p["spec"].get("muzzle", 0.82))
	var x := float(p["x"]) + sin(yaw) * muzzle
	var z := float(p["z"]) + cos(yaw) * muzzle
	var ap := bool(p["ap"])
	if ap:
		p["ap"] = false
	_spawn_bullet({
		"x": x, "z": z, "yaw": yaw, "speed": float(p["bulletSpeed"]),
		"damage": float(p["damage"]), "from": "player", "ownerId": p["id"],
		"ap": ap, "apLeft": 2 if ap else 0,
	})
	p["fireCd"] = p["fireInterval"]
	_emit("fire", {
		"from": "player", "shooterId": p["id"], "x": x, "z": z, "yaw": yaw, "ap": ap,
	})


func _update_player(dt: float) -> void:
	var p: Dictionary = state["player"]
	p["invuln"] = maxf(0.0, float(p["invuln"]) - dt)
	p["shield"] = maxf(0.0, float(p["shield"]) - dt)
	p["smoke"] = maxf(0.0, float(p["smoke"]) - dt)

	if float(p["reactiveTimer"]) > 0.0:
		p["reactiveTimer"] = float(p["reactiveTimer"]) - dt
		if float(p["reactiveTimer"]) <= 0.0:
			p["reactiveLeft"] = 0
	if float(p["repair"]) > 0.0:
		p["repair"] = float(p["repair"]) - dt
		p["hp"] = minf(float(p["maxHp"]), float(p["hp"]) + 2.0 * dt)

	if not bool(p["alive"]):
		if float(state["respawnTimer"]) > 0.0:
			state["respawnTimer"] = float(state["respawnTimer"]) - dt
			if float(state["respawnTimer"]) <= 0.0:
				_respawn_player()
		return

	p["heading"] = float(p["heading"]) + float(_input["turn"]) * float(p["spec"]["turn"]) * dt
	p["turn"] = _input["turn"]

	var dx := sin(float(p["heading"]))
	var dz := cos(float(p["heading"]))
	var on_ice := grid.tile(PortConstants.row_at(float(p["z"])), PortConstants.col_at(float(p["x"]))) == PortConstants.TILE_ICE
	var throttle := float(_input["throttle"])

	if on_ice:
		var target_x := dx * throttle * float(p["spec"]["speed"])
		var target_z := dz * throttle * float(p["spec"]["speed"])
		var vel: Dictionary = p["vel"]
		vel["x"] = float(vel["x"]) + (target_x - float(vel["x"])) * ICE_ACCEL * dt
		vel["z"] = float(vel["z"]) + (target_z - float(vel["z"])) * ICE_ACCEL * dt
		var moved := grid.try_move(p, float(vel["x"]) * dt, float(vel["z"]) * dt, PortConstants.TANK_R)
		if not moved:
			vel["x"] = float(vel["x"]) * 0.6
			vel["z"] = float(vel["z"]) * 0.6
		p["speed"] = sqrt(float(vel["x"]) * float(vel["x"]) + float(vel["z"]) * float(vel["z"])) * signf(throttle if throttle != 0.0 else 1.0)
		p["moving"] = absf(float(p["speed"])) > 0.05
	else:
		var vel: Dictionary = p["vel"]
		vel["x"] = 0.0
		vel["z"] = 0.0
		p["speed"] = throttle * float(p["spec"]["speed"])
		p["moving"] = false
		if throttle != 0.0:
			p["moving"] = grid.try_move(
				p,
				dx * throttle * float(p["spec"]["speed"]) * dt,
				dz * throttle * float(p["spec"]["speed"]) * dt,
				PortConstants.TANK_R
			)
	p["throttle"] = throttle

	if bool(_aim["active"]):
		var desired := PortConstants.wrap_angle(
			atan2(float(_aim["x"]) - float(p["x"]), float(_aim["z"]) - float(p["z"])) - float(p["heading"])
		)
		var max_step := float(p["spec"].get("turretSpeed", 6.0)) * dt
		var delta := PortConstants.wrap_angle(desired - float(p["turretYaw"]))
		p["turretYaw"] = PortConstants.wrap_angle(float(p["turretYaw"]) + clampf(delta, -max_step, max_step))

	p["fireCd"] = float(p["fireCd"]) - dt
	if bool(_input["trigger"]) and float(p["fireCd"]) <= 0.0:
		_player_fire()


func _respawn_player() -> void:
	var p: Dictionary = state["player"]
	p["alive"] = true
	p["x"] = PLAYER_SPAWN["x"]
	p["z"] = PLAYER_SPAWN["z"]
	p["heading"] = PLAYER_SPAWN["heading"]
	p["turretYaw"] = 0.0
	p["hp"] = p["maxHp"]
	p["invuln"] = 2.5
	p["vel"] = {"x": 0.0, "z": 0.0}
	p["speed"] = 0.0
	_emit("respawn", {"id": p["id"], "x": p["x"], "z": p["z"]})


func _damage_player(damage: float) -> void:
	var p: Dictionary = state["player"]
	if not bool(p["alive"]) or float(p["invuln"]) > 0.0:
		return
	if float(p["shield"]) > 0.0:
		_emit("shieldBlock", {"x": p["x"], "z": p["z"]})
		return
	if int(p["reactiveLeft"]) > 0:
		p["reactiveLeft"] = int(p["reactiveLeft"]) - 1
		_emit("reactiveBlock", {"x": p["x"], "z": p["z"], "left": p["reactiveLeft"]})
		return
	if p["spec"]["id"] == "tiger":
		damage *= 0.8
	p["hp"] = float(p["hp"]) - damage
	_emit("playerHit", {"x": p["x"], "z": p["z"], "damage": damage})
	if float(p["hp"]) <= 0.0:
		p["hp"] = 0.0
		_kill_player()


func _kill_player() -> void:
	var p: Dictionary = state["player"]
	_emit("explosion", {"x": p["x"], "z": p["z"], "scale": 1.4})
	p["alive"] = false
	p["lives"] = int(p["lives"]) - 1
	_emit("lifeLost", {"lives": p["lives"]})
	if int(p["lives"]) <= 0:
		_end_battle(false, "全部坦克损毁")
	else:
		state["respawnTimer"] = 1.5


# -------------------------------------------------------------------- waves
func _spawn_enemy(type_id: String) -> void:
	var prof: Dictionary = _enemy_types[type_id]
	var cols: Array = _level["spawnCols"]
	var col := int(cols[int(state["spawnIndex"]) % cols.size()])
	state["spawnIndex"] = int(state["spawnIndex"]) + 1
	var hp := float(prof["hp"]) * 25.0
	var enemy := {
		"id": "e%d" % _enemy_seq,
		"type": type_id,
		"prof": prof,
		"x": PortConstants.cx(col),
		"z": -6.0,
		"heading": 0.0,
		"turretYaw": 0.0,
		"hp": hp,
		"maxHp": hp,
		"scale": float(prof["scale"]),
		"fireCd": 1.2 + _rand.next(),
		"aimTimer": 0.0,
		"stuck": 0.0,
		"jitterTimer": 0.0,
		"jitterYaw": 0.0,
		"freezeTimer": 0.0,
		"hitFlash": 0.0,
		"spawnTimer": 0.0,
		"seed": _rand.range_float(0.0, 10.0),
		"alive": true,
	}
	_enemy_seq += 1
	state["enemies"].append(enemy)
	_emit("spawn", {
		"id": enemy["id"], "type": type_id, "x": enemy["x"], "z": enemy["z"], "scale": enemy["scale"],
	})


func _update_waves(dt: float) -> void:
	while int(state["wave"]) < _waves.size() and float(_waves[int(state["wave"])]["t"]) <= float(state["time"]):
		var list: Array = _waves[int(state["wave"])]["list"]
		for type_id in list:
			state["spawnQueue"].append(type_id)
		state["wave"] = int(state["wave"]) + 1
		_emit("message", {"text": "第 %d 波来袭" % int(state["wave"])})

	state["spawnTimer"] = float(state["spawnTimer"]) - dt
	if state["spawnQueue"].size() > 0 and state["enemies"].size() < int(_level["maxOnField"]) and float(state["spawnTimer"]) <= 0.0:
		_spawn_enemy(str(state["spawnQueue"].pop_front()))
		state["spawnTimer"] = 1.0


# ------------------------------------------------------------------ enemies
func _enemy_fire(enemy: Dictionary, error: float) -> void:
	var p: Dictionary = state["player"]
	var yaw := atan2(float(p["x"]) - float(enemy["x"]), float(p["z"]) - float(enemy["z"])) + (_rand.next() - 0.5) * 2.0 * error
	var muzzle := 0.85 * float(enemy["scale"])
	var x := float(enemy["x"]) + sin(yaw) * muzzle
	var z := float(enemy["z"]) + cos(yaw) * muzzle
	_spawn_bullet({
		"x": x, "z": z, "yaw": yaw, "speed": ENEMY_BULLET_SPEED,
		"damage": float(enemy["prof"]["dmg"]), "from": "enemy", "ownerId": enemy["id"],
	})
	_emit("fire", {"from": "enemy", "shooterId": enemy["id"], "x": x, "z": z, "yaw": yaw})


func _enemy_think(enemy: Dictionary, dt: float) -> void:
	var prof: Dictionary = enemy["prof"]
	var p: Dictionary = state["player"]
	var pd := sqrt(
		(float(p["x"]) - float(enemy["x"])) * (float(p["x"]) - float(enemy["x"]))
		+ (float(p["z"]) - float(enemy["z"])) * (float(p["z"]) - float(enemy["z"]))
	)

	var can_see := false
	if bool(p["alive"]) and float(p["smoke"]) <= 0.0:
		var hidden := grid.tile(PortConstants.row_at(float(p["z"])), PortConstants.col_at(float(p["x"]))) == PortConstants.TILE_FOREST and pd > 3.0
		can_see = not hidden and pd < float(prof["range"]) + 4.0 and grid.line_of_sight(
			float(enemy["x"]), float(enemy["z"]), float(p["x"]), float(p["z"])
		)

	var tx := float(state["eagle"]["x"])
	var tz := float(state["eagle"]["z"])
	var hold := false
	if can_see:
		if prof["id"] == "sniper":
			if pd < 4.2:
				tx = float(enemy["x"]) * 2.0 - float(p["x"])
				tz = float(enemy["z"]) * 2.0 - float(p["z"])
			elif pd < float(prof["range"]):
				hold = true
			else:
				tx = float(p["x"])
				tz = float(p["z"])
		else:
			tx = float(p["x"])
			tz = float(p["z"])

	var desired := atan2(tx - float(enemy["x"]), tz - float(enemy["z"]))
	if float(enemy["jitterTimer"]) > 0.0:
		enemy["jitterTimer"] = float(enemy["jitterTimer"]) - dt
		desired = float(enemy["jitterYaw"])
	elif prof["id"] == "scout" and not can_see:
		desired += sin(float(state["time"]) * 2.3 + float(enemy["seed"])) * 0.5

	var delta := PortConstants.wrap_angle(desired - float(enemy["heading"]))
	enemy["heading"] = PortConstants.wrap_angle(
		float(enemy["heading"]) + signf(delta) * minf(absf(delta), 3.2 * dt)
	)

	var moving := not (hold and float(enemy["jitterTimer"]) <= 0.0)
	var moved := false
	if moving and absf(delta) < 0.9:
		moved = grid.try_move(
			enemy,
			sin(float(enemy["heading"])) * float(prof["speed"]) * dt,
			cos(float(enemy["heading"])) * float(prof["speed"]) * dt,
			PortConstants.TANK_R * float(enemy["scale"])
		)
	if not moving or not moved:
		enemy["stuck"] = float(enemy["stuck"]) + dt
		if float(enemy["stuck"]) > 0.35 and float(enemy["jitterTimer"]) <= 0.0:
			enemy["stuck"] = 0.0
			enemy["jitterTimer"] = 0.7
			var dir := 1.0 if _rand.chance(0.5) else -1.0
			enemy["jitterYaw"] = PortConstants.wrap_angle(float(enemy["heading"]) + dir * PI / 2.0)
	else:
		enemy["stuck"] = 0.0
	enemy["moving"] = moving and moved
	enemy["inForest"] = grid.tile(PortConstants.row_at(float(enemy["z"])), PortConstants.col_at(float(enemy["x"]))) == PortConstants.TILE_FOREST

	if bool(p["alive"]):
		var ddx := float(enemy["x"]) - float(p["x"])
		var ddz := float(enemy["z"]) - float(p["z"])
		var dd := sqrt(ddx * ddx + ddz * ddz)
		if dd < PortConstants.TANK_R * 1.7 and dd > 0.001:
			var push := PortConstants.TANK_R * 1.7 - dd
			grid.try_move(
				enemy, (ddx / dd) * push, (ddz / dd) * push,
				PortConstants.TANK_R * float(enemy["scale"])
			)

	if can_see:
		var desired_turret := PortConstants.wrap_angle(
			atan2(float(p["x"]) - float(enemy["x"]), float(p["z"]) - float(enemy["z"])) - float(enemy["heading"])
		)
		var step := ENEMY_TURRET_SPEED * dt
		enemy["turretYaw"] = PortConstants.wrap_angle(
			float(enemy["turretYaw"]) + clampf(
				PortConstants.wrap_angle(desired_turret - float(enemy["turretYaw"])), -step, step
			)
		)
		enemy["fireCd"] = float(enemy["fireCd"]) - dt
		if float(enemy["fireCd"]) <= 0.0 and pd <= float(prof["range"]) + 1.0:
			if prof["id"] == "sniper":
				enemy["aimTimer"] = float(enemy["aimTimer"]) + dt
				if float(enemy["aimTimer"]) >= 0.55:
					_enemy_fire(enemy, 0.03)
					enemy["aimTimer"] = 0.0
					enemy["fireCd"] = float(prof["fire"])
			else:
				_enemy_fire(enemy, 0.14)
				enemy["fireCd"] = float(prof["fire"]) * (0.8 + _rand.next() * 0.4)
	else:
		enemy["turretYaw"] = PortConstants.wrap_angle(float(enemy["turretYaw"]) * maxf(0.0, 1.0 - 3.0 * dt))
		enemy["aimTimer"] = 0.0
		enemy["fireCd"] = maxf(float(enemy["fireCd"]), 0.6)


func _update_enemies(dt: float) -> void:
	for enemy in state["enemies"]:
		enemy["spawnTimer"] = float(enemy["spawnTimer"]) + dt
		if float(enemy["hitFlash"]) > 0.0:
			enemy["hitFlash"] = float(enemy["hitFlash"]) - dt
		if float(enemy["freezeTimer"]) > 0.0:
			enemy["freezeTimer"] = float(enemy["freezeTimer"]) - dt
			continue
		_enemy_think(enemy, dt)


func _hit_enemy(enemy: Dictionary, damage: float) -> void:
	enemy["hp"] = float(enemy["hp"]) - damage
	enemy["hitFlash"] = 0.12
	_emit("enemyHit", {"id": enemy["id"], "x": enemy["x"], "z": enemy["z"], "damage": damage})
	if float(enemy["hp"]) <= 0.0:
		_kill_enemy(enemy, true)


func _kill_enemy(enemy: Dictionary, allow_drop: bool) -> void:
	var idx := -1
	for i in range(state["enemies"].size()):
		if state["enemies"][i]["id"] == enemy["id"]:
			idx = i
			break
	if idx < 0:
		return
	state["enemies"].remove_at(idx)
	_emit("explosion", {"x": enemy["x"], "z": enemy["z"], "scale": float(enemy["scale"]) * 1.2})
	_emit("enemyKilled", {
		"id": enemy["id"], "x": enemy["x"], "z": enemy["z"], "score": int(enemy["prof"]["score"]),
	})
	state["score"] = int(state["score"]) + int(enemy["prof"]["score"])
	state["killed"] = int(state["killed"]) + 1
	if allow_drop and _rand.chance(0.22):
		_drop_pickup(float(enemy["x"]), float(enemy["z"]))


# ------------------------------------------------------------------ bullets
func _spawn_bullet(data: Dictionary) -> void:
	var bullet := data.duplicate()
	bullet["id"] = "b%d" % _bullet_seq
	bullet["life"] = BULLET_LIFE
	_bullet_seq += 1
	state["bullets"].append(bullet)


func _update_bullets(dt: float) -> void:
	for i in range(state["bullets"].size() - 1, -1, -1):
		var b: Dictionary = state["bullets"][i]
		var step := float(b["speed"]) * dt
		b["x"] = float(b["x"]) + sin(float(b["yaw"])) * step
		b["z"] = float(b["z"]) + cos(float(b["yaw"])) * step
		b["life"] = float(b["life"]) - dt

		var dead := float(b["life"]) <= 0.0 or absf(float(b["x"])) > 7.5 or absf(float(b["z"])) > 7.5
		var r := PortConstants.row_at(float(b["z"]))
		var c := PortConstants.col_at(float(b["x"]))
		var tile := grid.tile(r, c)

		if not dead:
			if tile == PortConstants.TILE_BRICK:
				var prev := grid.destroy(r, c)
				_emit("tileChanged", {"r": r, "c": c, "tile": PortConstants.TILE_EMPTY, "previous": prev})
				_emit("impact", {"x": b["x"], "z": b["z"], "kind": "brick"})
				if not bool(b["ap"]):
					dead = true
			elif tile == PortConstants.TILE_STEEL:
				if bool(b["ap"]):
					var prev := grid.destroy(r, c)
					_emit("tileChanged", {"r": r, "c": c, "tile": PortConstants.TILE_EMPTY, "previous": prev})
					_emit("impact", {"x": b["x"], "z": b["z"], "kind": "steel"})
				else:
					_emit("spark", {"x": b["x"], "z": b["z"]})
					dead = true
			elif tile == PortConstants.TILE_EAGLE:
				_destroy_eagle()
				_emit("impact", {"x": b["x"], "z": b["z"], "kind": "eagle"})
				dead = true

		if not dead:
			if b["from"] == "enemy":
				var p: Dictionary = state["player"]
				if bool(p["alive"]) and sqrt(
					(float(b["x"]) - float(p["x"])) * (float(b["x"]) - float(p["x"]))
					+ (float(b["z"]) - float(p["z"])) * (float(b["z"]) - float(p["z"]))
				) < PortConstants.TANK_R + PortConstants.BULLET_R:
					_damage_player(float(b["damage"]))
					dead = true
			else:
				for enemy in state["enemies"]:
					var hit_dist := sqrt(
						(float(b["x"]) - float(enemy["x"])) * (float(b["x"]) - float(enemy["x"]))
						+ (float(b["z"]) - float(enemy["z"])) * (float(b["z"]) - float(enemy["z"]))
					)
					if hit_dist < PortConstants.TANK_R * float(enemy["scale"]) + PortConstants.BULLET_R:
						_hit_enemy(enemy, float(b["damage"]))
						if bool(b["ap"]) and int(b["apLeft"]) > 0:
							b["apLeft"] = int(b["apLeft"]) - 1
							if int(b["apLeft"]) <= 0:
								dead = true
						else:
							dead = true
						break

		if dead:
			state["bullets"].remove_at(i)


func _destroy_eagle() -> void:
	if not bool(state["eagle"]["alive"]):
		return
	state["eagle"]["alive"] = false
	_emit("explosion", {"x": state["eagle"]["x"], "z": state["eagle"]["z"], "scale": 2.2})
	_end_battle(false, "鹰徽被毁，防线崩溃")


# ----------------------------------------------------------------- powerups
func _drop_pickup(x: float, z: float) -> void:
	var def: Dictionary = _rand.weighted(_powerups)
	var pickup_id := "p%d" % _pickup_seq
	_pickup_seq += 1
	state["pickups"].append({"id": pickup_id, "def": def, "x": x, "z": z, "life": 12.0})
	_emit("pickupDropped", {
		"id": pickup_id, "x": x, "z": z, "powerupId": def["id"], "color": def["color"],
	})


func _apply_powerup(def: Dictionary) -> void:
	var p: Dictionary = state["player"]
	var pid: String = def["id"]
	match pid:
		"star":
			p["fireInterval"] = maxf(0.22, float(p["fireInterval"]) * 0.7)
			state["score"] = int(state["score"]) + 500
			_emit("message", {"text": "火力升级!"})
		"grenade":
			var copy: Array = state["enemies"].duplicate()
			for enemy in copy:
				_kill_enemy(enemy, false)
			_emit("message", {"text": "全体歼灭!"})
		"shovel":
			_fortify()
			state["score"] = int(state["score"]) + 500
			_emit("message", {"text": "鹰徽加固 15 秒"})
		"clock":
			for enemy in state["enemies"]:
				enemy["freezeTimer"] = 8.0
			state["score"] = int(state["score"]) + 500
			_emit("message", {"text": "敌军冻结 8 秒!"})
		"helmet":
			p["shield"] = 10.0
			state["score"] = int(state["score"]) + 500
			_emit("message", {"text": "能量护盾 10 秒"})
		"tank":
			p["lives"] = int(p["lives"]) + 1
			_emit("message", {"text": "备用坦克 +1"})
	if p["spec"]["id"] == "sherman":
		p["repair"] = 5.0
	_emit("pickup", {"powerupId": def["id"], "x": p["x"], "z": p["z"], "label": def["label"]})


func _fortify() -> void:
	for pair in _level["bunker"]:
		var r := int(pair[0])
		var c := int(pair[1])
		if grid.tile(r, c) == PortConstants.TILE_BRICK:
			grid.set_tile(r, c, PortConstants.TILE_STEEL)
			_emit("tileChanged", {
				"r": r, "c": c, "tile": PortConstants.TILE_STEEL, "previous": PortConstants.TILE_BRICK,
			})
	state["fortTimer"] = 15.0


func _update_fortify(dt: float) -> void:
	if float(state["fortTimer"]) <= 0.0:
		return
	state["fortTimer"] = float(state["fortTimer"]) - dt
	if float(state["fortTimer"]) > 0.0:
		return
	for pair in _level["bunker"]:
		var r := int(pair[0])
		var c := int(pair[1])
		if grid.tile(r, c) == PortConstants.TILE_STEEL:
			grid.set_tile(r, c, PortConstants.TILE_BRICK)
			_emit("tileChanged", {
				"r": r, "c": c, "tile": PortConstants.TILE_BRICK, "previous": PortConstants.TILE_STEEL,
			})
	_emit("message", {"text": "加固失效"})


func _update_pickups(dt: float) -> void:
	var p: Dictionary = state["player"]
	for i in range(state["pickups"].size() - 1, -1, -1):
		var pickup: Dictionary = state["pickups"][i]
		pickup["life"] = float(pickup["life"]) - dt
		if float(pickup["life"]) <= 0.0:
			state["pickups"].remove_at(i)
			_emit("pickupExpired", {"id": pickup["id"]})
			continue
		if bool(p["alive"]) and sqrt(
			(float(pickup["x"]) - float(p["x"])) * (float(pickup["x"]) - float(p["x"]))
			+ (float(pickup["z"]) - float(p["z"])) * (float(pickup["z"]) - float(p["z"]))
		) < 0.62:
			state["pickups"].remove_at(i)
			_apply_powerup(pickup["def"])


# --------------------------------------------------------------------- flow
func _end_battle(win: bool, reason: String) -> void:
	if state["phase"] != "battle":
		return
	state["phase"] = "won" if win else "lost"
	_emit("gameover", {"win": win, "reason": reason, "score": int(state["score"])})


func _check_win() -> void:
	if (
		state["phase"] == "battle"
		and int(state["wave"]) >= _waves.size()
		and state["spawnQueue"].is_empty()
		and state["enemies"].is_empty()
	):
		_end_battle(true, "全部敌军歼灭")


func update(dt: float) -> void:
	if state["phase"] != "battle":
		return
	dt = clampf(dt, 0.0, 0.05)
	state["time"] = float(state["time"]) + dt
	state["skillCd"] = maxf(0.0, float(state["skillCd"]) - dt)

	_update_player(dt)
	_update_waves(dt)
	_update_enemies(dt)
	_update_bullets(dt)
	_update_pickups(dt)
	_update_fortify(dt)
	_check_win()


func drain_events() -> Array[Dictionary]:
	var out := _events
	_events = []
	return out


func _emit(type: String, data: Dictionary = {}) -> void:
	# JS does { type, ...data }: a payload field named "type" overwrites the
	# event type. The v3 "spawn" event does exactly that (payload.type = enemy
	# type), so replicating the spread order is required for trace parity.
	var event := {"type": type}
	for key in data:
		event[key] = data[key]
	_events.append(event)
