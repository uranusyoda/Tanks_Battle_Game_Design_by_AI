class_name ContentDB
extends RefCounted


static func load_json(path: String) -> Variant:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("Cannot read JSON: %s" % path)
		return null
	var parsed: Variant = JSON.parse_string(text)
	if parsed == null:
		push_error("Invalid JSON: %s" % path)
	return parsed


static func load_content(path: String = "res://content/content.json") -> Dictionary:
	var parsed: Variant = load_json(path)
	if parsed is Dictionary:
		return parsed
	push_error("content.json must be a JSON object")
	return {}
