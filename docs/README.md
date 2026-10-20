# 文档

```
docs/
├── design/      玩法与内容设计：坦克档案（MD + DOCX）、源图、生成脚本入口
├── research/    立项前的模型/素材调研
└── reference/   外部方法论文档（Godot 移植 SOP，暂存备查）
```

## design/

| 文件 | 说明 |
|---|---|
| `钢铁防线3D_坦克档案.md` | 三辆可选坦克 + 敌军 + 道具的数值与设计说明（可编辑源） |
| `钢铁防线3D_坦克档案.docx` | 对外分发的排版版，由 `tools/build_tank_dossier.py` 生成 |
| `assets/*.jpg` | 档案用图：三车合影、属性图、实车参考、战场截图 |

改数值后重新生成 DOCX：

```bash
python3 tools/build_tank_dossier.py
```

## research/

`m4-sherman-3d-model-pre-research.md`：免费/付费 Sherman 模型调研与选型结论。
属于历史记录，不再更新。

## reference/

`godot-port-sop/`：把 Web 游戏移植到 Godot 的 SOP（来自技能库的临时副本）。
当前项目不依赖它，保留是为了将来做 Godot 版时有统一口径。

## 版本专属文档

分层架构、契约、测试矩阵随版本走，不放在这里：

- v2：[`../versions/v2/docs/game-architecture.md`](../versions/v2/docs/game-architecture.md)
- v3：[`../versions/v3/docs/CHANGELOG.md`](../versions/v3/docs/CHANGELOG.md)（架构继承 v2）
