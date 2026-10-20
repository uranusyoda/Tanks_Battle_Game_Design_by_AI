# 钢铁防线 3D · v3（迭代工作区）

v3 从 **v2.0.0** 复制而来，是下一轮迭代的唯一活动版本。
`versions/v2/` 保持冻结，作为对照、回归和回滚基线。

- 基线：`versions/v2`（14 项测试全过）
- 当前状态：`v3.0.0` 基线，玩法与 v2 完全一致，尚未加入新特性
- 本地入口：<http://127.0.0.1:4174/>

![车库（v2 基线截图）](../v2/preview/garage.png)

> **注意：** v3 没有 `preview/` 目录，上图为 v2 基线画面；v3 有视觉改动后应重新截图。
> 不能直接双击 `index.html` 打开：ES Module + `.glb` 会被 `file://` 的 CORS 拦掉。

---

## 快速开始

```bash
cd versions/v3
npm start            # 等价于 python3 -m http.server 4174
# 打开 http://127.0.0.1:4174/
```

或双击本目录的 `START-GAME.command`（端口 4174）。

| 按键 | 动作 |
|---|---|
| W / S | 前进 / 后退 |
| A / D | 车体转向 |
| 鼠标 | 炮塔瞄准 |
| 空格 / 鼠标左键 | 开火（可按住连发） |
| E | 技能 |
| C | 追尾视角 ↔ 俯视视角 |
| R | 返回车库 |

---

## 测试

```bash
cd versions/v3
npm test
```

当前 14 项：资产契约（GLB hash / 节点 tag / clip / LOD）、规则（碰撞、拆砖、伤害、
护盾、胜负、道具、确定性）、分层约束（`core/` 不碰 Three.js / DOM / 资产）。

---

## 继承的架构

v3 的目录和依赖方向与 v2 相同，完整契约见
[`../v2/docs/game-architecture.md`](../v2/docs/game-architecture.md)。

```
versions/v3/
├── index.html              页面外壳：canvas + HUD DOM + importmap
├── css/hud.css             HUD / 车库 / 结算
├── src/
│   ├── main.js             启动、加载模型、装配 Game、主循环
│   ├── app/game.js         一局编排：模式、输入、事件分发
│   ├── core/               玩法内核（纯 JS，无 THREE / DOM）
│   ├── content/            坦克 / 敌人 / 关卡 / 道具 / 资产清单
│   ├── assets/             GLB 加载、坦克 rig、程序化贴图
│   ├── view/               场景 / 世界 / 坦克 / 炮弹 / FX / 相机 / HUD
│   ├── platform/           输入 / 音频 / 存档
│   └── shared/             纯 PRNG
├── assets/models/          hero / troop GLB + manifest
├── tests/                  node:test
├── docs/CHANGELOG.md       v3 改动记录（从这里开始写）
├── START-GAME.command      双击启动（4174）
└── .test-start.command     调试用启动（4176）
```

---

## 迭代规则

1. **规则**只改 `src/core/`；**数值/关卡/波次**只改 `src/content/`。
2. **表现**只读 `core.state` 和语义事件，不反向决定胜负。
3. **换模型**只改 `src/content/assets.js` + 重跑
   `tools/blender/export_game_sherman.py`（默认写回 `versions/v3/assets/models`）。
4. 行为改动必须带测试；`core/` 新增依赖会被分层测试拦下。
5. 每批改动追加到 [`docs/CHANGELOG.md`](docs/CHANGELOG.md)，并在
   `docs/` 里补一段可复现的验收步骤。

---

## v3 待办

见 [`docs/CHANGELOG.md`](docs/CHANGELOG.md)。从 v2 继承的候选增量：

- troop LOD 履带 UV 滚动 / 着色器位移（远处敌人履带目前是静态的）；
- hero 的 146 节履带板改 `InstancedMesh`，降低 draw call；
- 炮塔转速、相机距离、履带滚速的人工试玩调参；
- 移动端触控、暂停菜单、进度存档。
