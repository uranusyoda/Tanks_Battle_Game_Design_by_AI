class_name PortConstants
extends RefCounted

const ROWS := 13
const COLS := 13
const TANK_R := 0.4
const BULLET_R := 0.14

const TILE_EMPTY := 0
const TILE_BRICK := 1
const TILE_STEEL := 2
const TILE_WATER := 3
const TILE_FOREST := 4
const TILE_ICE := 5
const TILE_EAGLE := 9

const SOLID_TILES := [TILE_BRICK, TILE_STEEL, TILE_WATER, TILE_EAGLE]


static func cx(col: int) -> float:
	return float(col - 6)


static func cz(row: int) -> float:
	return float(row - 6)


# JS Math.round is floor(v + 0.5); Godot roundi is half-away-from-zero.
static func js_round(v: float) -> int:
	return int(floor(v + 0.5))


static func col_at(x: float) -> int:
	return js_round(x + 6.0)


static func row_at(z: float) -> int:
	return js_round(z + 6.0)


static func wrap_angle(a: float) -> float:
	while a > PI:
		a -= TAU
	while a <= -PI:
		a += TAU
	return a
