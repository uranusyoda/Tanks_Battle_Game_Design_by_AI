class_name BattleGrid
extends RefCounted

var rows: int = PortConstants.ROWS
var cols: int = PortConstants.COLS
var tiles: Array = []

var _solid := {
	PortConstants.TILE_BRICK: true,
	PortConstants.TILE_STEEL: true,
	PortConstants.TILE_WATER: true,
	PortConstants.TILE_EAGLE: true,
}


func _init(level: Dictionary) -> void:
	for row in level["grid"]:
		tiles.append(row.duplicate())


func tile(r: int, c: int) -> int:
	if r < 0 or r >= rows or c < 0 or c >= cols:
		return PortConstants.TILE_STEEL
	return int(tiles[r][c])


func is_solid(t: int) -> bool:
	return _solid.has(t)


func center(r: int, c: int) -> Dictionary:
	return {"x": PortConstants.cx(c), "z": PortConstants.cz(r)}


func circle_hits_solid(x: float, z: float, rad: float) -> bool:
	var rr := PortConstants.row_at(z)
	var cc := PortConstants.col_at(x)
	for r in range(rr - 1, rr + 2):
		for c in range(cc - 1, cc + 2):
			if not is_solid(tile(r, c)):
				continue
			var nx := clampf(x, PortConstants.cx(c) - 0.5, PortConstants.cx(c) + 0.5)
			var nz := clampf(z, PortConstants.cz(r) - 0.5, PortConstants.cz(r) + 0.5)
			if (x - nx) * (x - nx) + (z - nz) * (z - nz) < rad * rad:
				return true
	return false


# Axis-separated slide. Mutates entity["x"] / entity["z"]. Returns moved.
func try_move(entity: Dictionary, dx: float, dz: float, rad: float) -> bool:
	var moved := false
	if dx != 0.0 and not circle_hits_solid(float(entity["x"]) + dx, float(entity["z"]), rad):
		entity["x"] = float(entity["x"]) + dx
		moved = true
	if dz != 0.0 and not circle_hits_solid(float(entity["x"]), float(entity["z"]) + dz, rad):
		entity["z"] = float(entity["z"]) + dz
		moved = true
	return moved


func line_of_sight(x1: float, z1: float, x2: float, z2: float) -> bool:
	var d := sqrt((x2 - x1) * (x2 - x1) + (z2 - z1) * (z2 - z1))
	var steps := maxi(1, int(ceil(d * 3.0)))
	for i in range(1, steps):
		var t := float(i) / float(steps)
		var t2 := tile(
			PortConstants.row_at(z1 + (z2 - z1) * t),
			PortConstants.col_at(x1 + (x2 - x1) * t)
		)
		if is_solid(t2) and t2 != PortConstants.TILE_WATER:
			return false
	return true


func destroy(r: int, c: int) -> int:
	var t := tile(r, c)
	if t != PortConstants.TILE_BRICK and t != PortConstants.TILE_STEEL:
		return t
	tiles[r][c] = PortConstants.TILE_EMPTY
	return t


func set_tile(r: int, c: int, t: int) -> void:
	if r < 0 or r >= rows or c < 0 or c >= cols:
		return
	tiles[r][c] = t
