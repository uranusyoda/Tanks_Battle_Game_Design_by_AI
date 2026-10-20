class_name BattleRng
extends RefCounted

var _state: int = 0


func _init(seed_value: int = 1) -> void:
	_state = seed_value & 0xFFFFFFFF


# Bit-exact port of mulberry32. Verified against Node for seeds 7 and 123456789.
func next() -> float:
	_state = (_state + 0x6D2B79F5) & 0xFFFFFFFF
	var t: int = ((_state ^ (_state >> 15)) * (1 | _state)) & 0xFFFFFFFF
	var sum: int = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF
	t = (sum ^ t) & 0xFFFFFFFF
	t = (t ^ (t >> 14)) & 0xFFFFFFFF
	return float(t) / 4294967296.0


func range_float(a: float, b: float) -> float:
	return a + (b - a) * next()


func int_range(a: int, b: int) -> int:
	return int(floor(float(a) + float(b - a + 1) * next()))


func chance(p: float) -> bool:
	return next() < p


func pick(items: Array) -> Variant:
	if items.is_empty():
		return null
	return items[int(floor(next() * float(items.size())))]


func weighted(items: Array) -> Dictionary:
	var total := 0.0
	for item in items:
		total += float(item["w"])
	var r := next() * total
	for item in items:
		r -= float(item["w"])
		if r <= 0.0:
			return item
	return items[items.size() - 1]
