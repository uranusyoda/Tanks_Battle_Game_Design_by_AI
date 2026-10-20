# 媒体与截图

跨版本的渲染产物、动画预览和游戏截图。**游戏运行不读这里**，可随时清理或重渲。

```
media/
├── v1/         初代单文件版的游戏内截图 + 材质重制前后对比
└── models/     Blender 模型渲染
    ├── build/  三视图棚拍（m4_sherman）、构建对比
    └── anim/   动画关键帧、contact sheet
```

| 文件 | 内容 |
|---|---|
| `v1/scene-garage.png` | v1 车库 |
| `v1/scene-battle.png` | v1 战斗视角 |
| `v1/scene-topdown.png` | v1 俯视视角 |
| `v1/before-after.png` | v1 场景/材质重制前后对比 |
| `models/m4a1_hero.png` · `_side` · `_front` | M4A1(76)W 三视图 |
| `models/m4_sherman.png` | 早期方块版 Sherman |
| `models/anim_*.png` · `sherman_anim.mp4` | 行驶 / 开火 / 炮塔转向预览 |
| `models/build/*.png` | 模型流水线自动生成的棚拍 |
| `models/anim/f*.png` · `contact_sheet.png` | 逐帧静帧与拼图 |

v2 的截图在 [`../versions/v2/preview/`](../versions/v2/preview/)；v3 有视觉改动后
新建 `versions/v3/preview/`，不要覆盖 v2 的证据图。

重渲命令见 [`../tools/README.md`](../tools/README.md)。
