# 工具与模型管线

所有命令都在**项目根目录**执行。Blender 路径按本机安装：

```bash
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
```

## 脚本一览

| 脚本 | 作用 | 产出 |
|---|---|---|
| `blender/pipeline.py` | 规格驱动的全流程：建模 → 导出 → 预览 → 校验 | `assets/models/*.glb`、`media/models/build/*.png`、manifest |
| `blender/export_game_sherman.py` | 把动画 demo 拆成游戏用 `Drive` / `Fire`，导出 hero / troop 两档 LOD | 默认 `versions/v3/assets/models/`（`SHERMAN_EXPORT_OUT` 可改） |
| `blender/build_sherman.py` | 参数化重建 M4A1(76)W（尺寸常量在文件顶部） | 内存中的 Blender 场景 |
| `blender/animate_sherman.py` | 给静态模型加 240 帧演示动画 | `assets/models/m4a1_sherman_anim.blend` |
| `blender/headless.py` | 无头重建 + 导出 + 渲染一条龙 | `assets/models/`、`media/models/` |
| `blender/render_preview.py` | 三视图棚拍渲染 | `media/models/build/` |
| `blender/render_anim_stills.py` | 动画关键帧静帧 | `media/models/anim/` |
| `render_preview.py` | 行驶 / 开火 / 炮塔转向片段渲染 | `media/models/anim_*.png` |
| `build_sherman.py` | 早期方块版 Sherman 构建 | `assets/models/m4_sherman.*` |
| `build_tank_dossier.py` | 由游戏数值 + 截图生成坦克档案 DOCX | `docs/design/钢铁防线3D_坦克档案.docx` |
| `tripo.mjs` / `tripo3d.py` | Tripo3D 文生模型（可选，需 API key） | 指定输出目录 |

## 常用命令

```bash
# 1) 规格驱动重建 + 校验（m4a1_sherman 规格在 tools/blender/specs/）
$BLENDER -b --factory-startup -noaudio -P tools/blender/pipeline.py -- build m4a1_sherman

# 2) 只导出游戏用 hero/troop GLB（默认写 v3）
$BLENDER -b -noaudio --factory-startup -P tools/blender/export_game_sherman.py

# 3) 写回 v2 快照
SHERMAN_EXPORT_OUT="$PWD/versions/v2/assets/models" \
  $BLENDER -b -noaudio --factory-startup -P tools/blender/export_game_sherman.py

# 4) 三视图 / 动画帧
$BLENDER -b -noaudio -P tools/blender/render_preview.py
$BLENDER -b -noaudio -P tools/blender/render_anim_stills.py

# 5) 坦克档案 DOCX（需要 python-docx）
python3 tools/build_tank_dossier.py
```

## Tripo3D（可选）

```bash
node tools/tripo.mjs check
node tools/tripo.mjs gen "low poly ww2 medium tank, olive green"
```

API key 读取顺序：`TRIPO_API_KEY` 环境变量 → `.secrets/tripo.key`
（已 gitignore，权限 600）。**不要把 key 写进脚本或提交。**

## 预览输出位置

| 内容 | 目录 |
|---|---|
| 模型棚拍三视图、构建对比 | `media/models/build/` |
| 动画关键帧、contact sheet | `media/models/anim/` |
| 行驶 / 开火 / 炮塔转向条图、MP4 | `media/models/` |
| v1 游戏截图 | `media/v1/` |
