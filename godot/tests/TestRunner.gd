extends Node


func _ready() -> void:
	var failures := 0
	print("=== G3 core tests ===")
	failures += TestCore.run_all()
	print("=== G1/G3 asset contract ===")
	failures += TestAsset.run_all()
	print("=== G3 golden trace replay ===")
	failures += TestTrace.run_all()

	if failures == 0:
		print("ALL TESTS PASSED")
	else:
		push_error("%d test(s) failed" % failures)
	get_tree().quit(1 if failures > 0 else 0)
