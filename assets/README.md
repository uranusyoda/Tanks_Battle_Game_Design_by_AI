# 共享资产（Source of Truth）

这里放**跨版本共用的源资产**。各版本目录下的 `assets/models/*.glb` 是导出副本，
游戏运行时只读副本；要改模型，改这里的 `.blend` 或 `tools/` 里的构建脚本，再重新导出。

```
assets/
├── models/
│   ├── m4a1_sherman_anim.blend   动画源文件（240 帧演示：行驶/炮塔/开火）
│   ├── m4a1_sherman.blend        静态 M4A1(76)W 源文件
│   ├── m4_sherman.blend          早期方块版 Sherman 源文件
│   ├── *.glb                     源文件直出的参考 GLB（非游戏用 LOD）
│   ├── manifest.json             构建记录：hash、三角面、节点 tag、尺寸
│   └── README.md                 模型规格、节点层级、重建命令
└── textures/
    └── track_tread.png           履带贴图（源）
```

## 谁在用

| 资产 | 消费者 |
|---|---|
| `m4a1_sherman_anim.blend` | `tools/blender/export_game_sherman.py` → v2 / v3 的 hero & troop GLB |
| `m4_sherman.blend` | `tools/blender/pipeline.py`（旧版模型流水线）、`media/models/build/` 预览 |
| `track_tread.png` | 旧版履带材质；v2/v3 的履带为纯色 PBR，不依赖此贴图 |
| `manifest.json` | 资产构建记录；v2/v3 各自的 `assets/models/manifest.json` 才是运行时契约 |

## 规则

- **不要**把版本专用的 GLB 放回这里；它们属于 `versions/<v>/assets/models/`。
- `.blend1` 是 Blender 自动备份，已加入 `.gitignore`，可随时删。
- 大文件（`.blend` / `.glb` / `.mp4`）不要重复提交多份；版本间通过复制导出产物隔离。
