# 版本升级：把 v3、v4 持续移植到 Godot

> 第一次移植靠 G0–G7；后续版本靠“分类 diff + oracle 更新 + 同一套门禁”。
> 目标：每次升级都能回答“变了什么、影响哪一层、哪条 trace 该变、哪些行为必须不变”。

---

## 0. 升级循环 U0–U6

| 步骤 | 动作 | 产物 |
|---|---|---|
| U0 | 冻新源版本，生成新 manifest、跑测试、截关键图 | `port/upgrades/v3/BASELINE.md` |
| U1 | 做源 diff，按文件/行为分类 | `port/upgrades/v3/DIFF.md` |
| U2 | 把 diff 映射到五类契约 | 受影响契约清单 |
| U3 | 重生成受影响的内容/trace，逐条 review | 新 `contract/`、`traces/`、变更说明 |
| U4 | 只改映射到的 Godot 文件 | 代码/内容/资产变更 |
| U5 | 重跑 G1–G7 | 证据目录 |
| U6 | 更新 manifest/parity、打 tag | `port-manifest.json`、release |

不要“整仓重新移植”。第一次移植的资产、场景、HUD 大部分可以复用；升级只动变化轴。

---

## 1. U0/U1：冻结与 diff

```bash
# 假设源版本用 git tag 或目录区分
git diff --stat v2..v3
git diff --name-status v2..v3

# 没有 git 时
diff -rq v2 v3 --exclude node_modules --exclude preview --exclude '*.zip'
```

把 diff 按层归类：

| 变化类型 | 典型文件 | 影响 | 需要动 |
|---|---|---|---|
| 内容/数值 | `content/tanks.js`、`levels.js`、`powerups.js` | 数值、波次、掉落 | `content/*.json`，必要时 trace 重录 |
| 规则 | `core/battle.js`、`grid.js`、`constants.js` | 行为、事件、胜负 | `core/*.gd` + 测试 + trace |
| 资产 | `content/assets.js`、GLB、manifest | 模型/动画/缩放/tag | `assets.json`、Godot 导入设置、`TankRig` |
| 表现 | `view/*`、`css/*` | 相机/HUD/FX/布局 | `view/*`、截图对比 |
| 平台 | `platform/*` | 输入/音频/存档 | `platform/*` |
| 纯文档/预览 | `README`、`preview/*` | 无运行时影响 | 只更新文档 |

先判断“行为是否变化”，再判断“实现是否要变”。**行为没变、实现变了**的 diff（重构）
原则上不需要改 Godot；**行为变了、实现没大改**的 diff 才需要更新 oracle。

---

## 2. U2/U3：更新契约与 oracle

### 2.1 内容变化

```bash
node port/tools/export_content.mjs v3 port/upgrades/v3/contract
diff -u port/contract/content.json port/upgrades/v3/contract/content.json
```

- 只改数值/波次：更新 Godot 的 `content/*.json`，重跑内容校验和相关测试。
- 新增坦克/敌人/道具：补 ID、模型 LOD、技能实现、图标、测试。
- 删除内容：先确认没有存档/关卡引用，再删；保留旧 ID 的迁移说明。

### 2.2 规则变化

- 先重录受影响 trace，**逐条 review 事件序列差异**。
- 每条差异标注来源：v3 的哪个 commit/行为变更。
- 再改 `core/*.gd`，直到新 trace 通过。
- 旧 trace 如果仍应通过（未受影响的场景），必须继续通过；否则说明改动外溢。

### 2.3 资产变化

- 重新计算 GLB hash、包围盒、节点 tag、clip 名。
- 如果 tag/clip 改名：这是一次契约破坏。要么在 `TankRig` 加兼容映射并记录，要么同步改
  所有引用；不要静默回退。
- 重新验证 hero/troop 的朝向、缩放、原点；截图对比。

### 2.4 表现变化

- 只改 `view/`；不要因为 HUD 改版去动 core。
- 更新 `port/evidence/G6/` 截图；差异写进 `PARITY.md`。
- 相机/手感参数进 `view_tuning.json`，不要散落在脚本里。

---

## 3. Oracle 变更协议（最重要）

黄金 trace 是“源行为的法律”。改它必须满足：

1. **有源侧依据**：对应 v3 的 commit、GDD 变更或用户确认的行为变更。
2. **有 diff 说明**：哪一步、哪个字段、从什么变成什么、为什么。
3. **有 review**：不能由实现者单方面“更新预期”。
4. **不放宽 tolerance**：除非证明是引擎精度差异，且记录原因与影响范围。
5. **不删场景**：如果某个场景不再适用，标记 `retired` 并说明替代场景，不直接删文件。

推荐在 `port/upgrades/v3/ORACLE-CHANGES.md` 记录：

```md
| trace | step | field | v2 | v3 | 原因 | 关联 commit |
|---|---|---|---|---|---|---|
| fire_brick | 42 | player.hp | 100 | 90 | v3 新增敌方首发命中 | abc123 |
```

---

## 4. port-manifest.json

它是“源文件 ↔ Godot 文件 ↔ 验证门禁”的映射，升级时按它找影响面。

```json
{
  "schema": 1,
  "source": { "root": "v2", "version": "2.0.0", "commit": "REPLACE" },
  "target": { "root": "godot", "engine": "4.7.1", "renderer": "gl_compatibility" },
  "parity": {
    "level": "P1",
    "tolerance": { "position": 1e-5, "angle": 1e-5, "hp": 0, "score": 0 }
  },
  "mappings": [
    { "source": "src/core/battle.js", "target": "core/battle.gd", "kind": "rules", "gate": "G3" },
    { "source": "src/content/levels.js", "target": "content/levels.json", "kind": "content", "gate": "G1" },
    { "source": "src/content/assets.js", "target": "content/assets.json", "kind": "assets", "gate": "G1" },
    { "source": "src/view/camera.js", "target": "view/camera_rig.gd", "kind": "view", "gate": "G6" }
  ],
  "assets": [
    {
      "id": "sherman_hero",
      "source": "assets/models/m4a1_sherman_hero.glb",
      "target": "assets/models/m4a1_sherman_hero.glb",
      "sha256": "REPLACE",
      "scale": 0.22,
      "forward": "+Z",
      "tags": { "turret": "Turret_Pivot", "gun": "Gun_Pivot", "muzzle": "GunMuzzle" },
      "clips": { "drive": "Drive", "fire": "Fire" }
    }
  ],
  "deviations": [
    { "id": "D001", "summary": "Godot 版 HUD 使用 Theme，不复刻 CSS 像素", "approved": true }
  ]
}
```

规则：

- 每个源文件最多映射到一个 Godot 主文件；共享代码可多对一。
- `kind` 只用 `content/rules/assets/view/platform/app`。
- `gate` 指向最相关的门禁；升级时按 `kind` 批量找影响面。
- 资产 hash 必须可复算；tag/clip 改名要升级 schema 版本。

---

## 5. 回滚策略

- 每次通过 G3 打一个 `core-green` tag；通过 G7 打 `godot-v<version>` tag。
- 升级失败时，按层回滚：
  - 规则回归失败 → 回滚 `core/` + `traces/`，保留内容/表现改动；
  - 资产回归失败 → 回滚 `assets/` + `assets.json`，保留规则；
  - 表现回归失败 → 回滚 `view/`，不影响已通过的 G3。
- 不要用“整仓 git reset”解决单层问题；会丢掉已验证的成果。
- 回滚后重跑对应门禁，确认回到绿色，再继续。

---

## 6. 升级检查清单

- [ ] 新源版本有独立 BASELINE，旧版本证据未被覆盖。
- [ ] diff 已按五类契约分类，没有“其他”大类。
- [ ] 受影响 trace 已重录并 review，变更逐条对应源 commit。
- [ ] 未受影响的旧 trace 仍通过。
- [ ] `port-manifest.json`、`PARITY.md`、`DEVIATIONS.md` 已更新。
- [ ] G1–G7 重跑，证据在 `port/upgrades/<version>/evidence/`。
- [ ] 新 tag 已打；旧 tag 可回滚。
