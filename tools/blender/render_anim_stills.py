import os
import bpy

BASE = "/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D"
OUT = os.path.join(BASE, "media", "models", "anim")
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
scene.render.image_settings.media_type = "IMAGE"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 960
scene.render.resolution_y = 540
for f in (24, 60, 94, 96, 120, 200):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, f"f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
    print("wrote", scene.render.filepath)
