# 钢铁防线 3D · 项目索引

> 浏览器 3D 坦克大战（Three.js + 原生 ES Module，无构建步骤）。
> 当前开发版本 **v3**，基线 **v2.0.0**。
> 最后整理：2026-10-20

---

## 1. 从这里开始

| 我想…… | 去这里 |
|---|---|
| **继续开发 v3** | [`versions/v3/`](versions/v3/) — 唯一活动版本 |
| 先玩一下 | `cd versions/v3 && npm start` → <http://127.0.0.1:4174/> |
| 看 v3 改了什么 / 待办 | [`versions/v3/docs/CHANGELOG.md`](versions/v3/docs/CHANGELOG.md) |
| 理解分层架构与契约 | [`versions/v2/docs/game-architecture.md`](versions/v2/docs/game-architecture.md)（v3 继承） |
| 找坦克数值/设计说明 | [`docs/design/钢铁防线3D_坦克档案.md`](docs/design/钢铁防线3D_坦克档案.md) |
| 改模型 / 重导 GLB | [`assets/README.md`](assets/README.md) + [`tools/README.md`](tools/README.md) |
| 找截图/渲染视频 | [`media/`](media/)（v2 截图在 `versions/v2/preview/`） |
| 拿部署包 | [`releases/steel-bastion-sherman-v2.zip`](releases/steel-bastion-sherman-v2.zip) |
| **看 Godot 移植可行性** | [`godot/README.md`](godot/README.md) + [`port/PILOT.md`](port/PILOT.md) |

---

## 2. 目录地图

```
坦克大战3D/
├── INDEX.md                      ← 本文件（唯一索引）
├── README.md                     ← 30 秒简介
├── index.html                    ← 可视化版本入口（版本卡片）
├── .gitignore
├── .secrets/
│   └── tripo.key                 ← Tripo API key（600，已 gitignore）
│
├── versions/                     ← 代码：一个版本一个自包含静态站
│   ├── v1/                       ← 初代单文件 Demo（归档）
│   │   ├── index.html            ← 全部玩法/渲染/UI 在这一个文件里
│   │   ├── vendor/               ← Three.js
│   │   ├── README.md
│   │   └── START-GAME.command    ← 4172
│   ├── v2/                       ← Sherman Edition（冻结基线）
│   │   ├── index.html            ← 页面外壳 + importmap
│   │   ├── src/{core,content,assets,view,platform,app,shared}/
│   │   ├── assets/models/        ← hero / troop GLB + manifest
│   │   ├── vendor/               ← Three.js + GLTFLoader
│   │   ├── tests/                ← 14 项 node:test
│   │   ├── docs/game-architecture.md
│   │   ├── preview/              ← v2 截图
│   │   ├── START-GAME.command    ← 4173
│   │   └── .test-start.command   ← 4175
│   └── v3/                       ← 下一版迭代工作区（开发中）
│       ├── index.html            ← 标题/HUD 标注 V3
│       ├── src/ …                ← 从 v2 复制，结构一致
│       ├── assets/models/        ← 从 v2 复制的 GLB（可重导）
│       ├── tests/                ← 14 项
│       ├── docs/CHANGELOG.md     ← ★ 每次改动写这里
│       ├── START-GAME.command    ← 4174
│       └── .test-start.command   ← 4176
│
├── godot/                        ← Godot 移植可行性工程（G0–G4 + 可玩切片 + 自动截图）
├── port/                         ← 移植契约/trace/证据/报告
├── docs/                         ← 跨版本文档
│   ├── design/                   ← 坦克档案（MD/DOCX/源图）
│   ├── research/                 ← Sherman 模型预研
│   └── reference/godot-port-sop/ ← Godot 移植 SOP（备查）
│
├── assets/                       ← 跨版本源资产（单一事实来源）
│   ├── models/                   ← .blend 源、参考 GLB、manifest、规格说明
│   └── textures/                 ← 履带贴图等
│
├── tools/                        ← 构建与生产工具
│   ├── blender/                  ← 参数化建模、导出、渲染、pipeline、specs
│   ├── build_sherman.py          ← 早期方块版构建
│   ├── render_preview.py         ← 动画片段渲染
│   ├── build_tank_dossier.py     ← 生成坦克档案 DOCX
│   └── tripo.mjs / tripo3d.py    ← 可选：文生模型
│
├── media/                        ← 截图与渲染产物（不参与运行）
│   ├── v1/                       ← 初代游戏截图、前后对比
│   └── models/                   ← 模型三视图、动画帧、MP4
│
└── releases/                     ← 可分发压缩包
    └── steel-bastion-sherman-v2.zip
```

**为什么这样分：**

- **代码按版本隔离**：每个 `versions/vX/` 都能单独起服务、单独打包、单独回滚，
  不会出现“改 v3 把 v2 弄坏”。
- **源资产 / 文档 / 工具 / 媒体跨版本共享**：模型 `.blend`、设计文档、Blender 脚本
  只存一份，避免 v1/v2/v3 各改一份对不上。
- **根目录只留索引与入口**：不再堆版本文件，新同学从 `INDEX.md` 就能找到所有东西。
- **导出产物就近存放**：v2/v3 各自持有 GLB 与 `manifest.json`，部署时互不依赖。

---

## 3. 版本矩阵

| 版本 | 状态 | 技术形态 | 入口 | 端口 | 测试 |
|---|---|---|---|---|---|
| v1 | 归档，只修阻塞 bug | 单 HTML + 内联 module；程序化方块坦克 | [`versions/v1/index.html`](versions/v1/index.html) | 4172 | 无 |
| v2 | **冻结基线**，不再加功能 | 分层 ES Module + M4A1 Sherman GLB 两档 LOD | [`versions/v2/index.html`](versions/v2/index.html) | 4173 | 14/14 |
| v3 | **开发中** | 同 v2，从 v2.0.0 复制 | [`versions/v3/index.html`](versions/v3/index.html) | 4174 | 14/14 |

调试用启动器：v2 `4175`、v3 `4176`（`.test-start.command`，日志分别写到 `/tmp`）。

---

## 4. 运行与验证

### 运行

```bash
# v3（当前开发版）
cd versions/v3
npm start                 # = python3 -m http.server 4174
# 打开 http://127.0.0.1:4174/

# v2（冻结基线，对照用）
cd versions/v2
npm start                 # 4173

# v1（归档）
cd versions/v1
python3 -m http.server 4172
```

也可以双击各版本的 `START-GAME.command`：自动起服务并打开浏览器。

> 三个版本都是纯静态站，必须走 HTTP。直接双击 `index.html` 会因 `file://` 的
> CORS 限制白屏。根目录 `index.html` 只是导航页，不启动游戏。

### 测试

```bash
cd versions/v3 && npm test     # 14 passed
cd versions/v2 && npm test     # 14 passed（冻结基线回归）
```

覆盖：GLB hash / 节点 tag / clip / LOD 差异；碰撞、拆砖、伤害、护盾、胜负、
道具、同 seed 确定性；`core/` 不 import Three.js / DOM / 资产层。

### 重新导出模型

```bash
# 默认写 versions/v3/assets/models
/Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
  --factory-startup -P tools/blender/export_game_sherman.py

# 要更新 v2 快照时显式指定输出
SHERMAN_EXPORT_OUT="$PWD/versions/v2/assets/models" \
  /Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
  --factory-startup -P tools/blender/export_game_sherman.py
```

细则：[`tools/README.md`](tools/README.md) · [`assets/models/README.md`](assets/models/README.md)

### 打包发布

```bash
cd versions/v3
zip -r ../../releases/steel-bastion-v3.zip index.html css src assets vendor -x '*.DS_Store'
```

v2 部署包已存在：[`releases/steel-bastion-sherman-v2.zip`](releases/steel-bastion-sherman-v2.zip)。
上传清单与注意事项见 [`releases/README.md`](releases/README.md)。

---

## 5. 文档索引

| 文档 | 内容 |
|---|---|
| [`versions/v2/docs/game-architecture.md`](versions/v2/docs/game-architecture.md) | v2 分层架构、依赖规则、命令/事件/资产契约、一帧数据流 |
| [`versions/v3/docs/CHANGELOG.md`](versions/v3/docs/CHANGELOG.md) | v3 基线说明、改动记录、待办 |
| [`docs/design/钢铁防线3D_坦克档案.md`](docs/design/钢铁防线3D_坦克档案.md) | 三车数值、敌军、道具、设计意图 |
| [`docs/design/钢铁防线3D_坦克档案.docx`](docs/design/钢铁防线3D_坦克档案.docx) | 排版版（对外分发） |
| [`docs/research/m4-sherman-3d-model-pre-research.md`](docs/research/m4-sherman-3d-model-pre-research.md) | Sherman 模型选型预研 |
| [`versions/v2/README.md`](versions/v2/README.md) | v2 玩法、操作、已知限制 |
| [`versions/v1/README.md`](versions/v1/README.md) | v1 归档说明 |

---

## 6. 改东西去哪里

| 想改 | 改这里 | 不要动 |
|---|---|---|
| 血量 / 速度 / 射速 / 伤害 / 技能冷却 | `versions/v3/src/content/tanks.js` | core / view / 模型 |
| 敌人配置、波次、出生列 | `.../content/enemies.js`、`levels.js` | core |
| 道具权重 | `.../content/powerups.js` | core |
| 碰撞 / AI / 开火 / 胜负 | `.../src/core/` | 资产 / DOM |
| HUD / 相机 / 爆炸 / 场景 | `.../src/view/`、`css/hud.css` | core 状态 |
| 模型、缩放、节点 tag、clip | `.../src/content/assets.js` + Blender 导出 | core |
| 关卡棋盘尺寸、tile 码 | `.../src/core/constants.js` + `content/levels.js` | — |

依赖方向硬规则（测试会自动检查）：

```
app → core / content / platform
view → assets / core(只读状态) / content
assets → three / content/assets.js
core → shared（禁止 THREE / DOM / view / assets）
content → 无 import（纯数据）
```

---

## 7. 约定与卫生

- **端口的约定**：v1 `4172`、v2 `4173`、v3 `4174`，调试 `4175/4176`。
- **密钥**：只放 `.secrets/`，已 gitignore；不要写进脚本、截图或文档。
- **二进制**：`.blend` / `.glb` / `.mp4` 不进 `src/`；源资产进 `assets/`，
  导出产物进 `versions/<v>/assets/models/`，截图进 `media/` 或版本 `preview/`。
- **版本号**：`package.json` 与 `docs/CHANGELOG.md` 同步升；v3 现在 `3.0.0`。
- **提交前**：`npm test` 全过 + 至少跑一遍浏览器冒烟（车库、开火、技能、结算、返回）。
- **不要**在 v2 上继续加功能；v2 只接受阻塞性修复，保证回滚基线干净。

---

## 8. 当前状态与下一步

- v3 基线已建好，代码/资产/测试与 v2 等价，14 项测试通过。
- 下一步从 [`versions/v3/docs/CHANGELOG.md`](versions/v3/docs/CHANGELOG.md) 的
  `[Unreleased]` 里挑一项开始，按“规则 → 内容 → 表现 → 验收”的顺序做。
- 候选增量：troop 履带 UV 滚动 / hero 履带 `InstancedMesh` / 手感调参 /
  触控与暂停 / 按距离切 LOD。
