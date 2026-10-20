---
name: godot-port-sop
description: 把 Three.js / Web 游戏按契约移植到 Godot 4.x 的可执行 SOP。适用于 Web 游戏转 Godot、Three.js 转 Godot、跨引擎版本迁移、Godot 重写、移植排期与验收。先锁源基线，抽内容/状态/命令/事件/资产五类契约与黄金回放，再按“规则内核 → 资产 → 表现 → 平台 → 验收”的顺序移植，用 G0–G7 门禁保证行为等价；不按文件逐行翻译。触发词：移植到 Godot、Web 游戏转 Godot、Three.js 转 Godot、Godot 重写、port to Godot。
version: 1.0.0
---

# Web 游戏 → Godot 4 移植 SOP

## 0. 立场：移植的是契约，不是文件

Three.js 代码天然和渲染器、DOM、资源加载、浏览器主循环绑在一起。逐行翻译会把源项目的
**引擎耦合**原样搬进 Godot，最后得到一个“能跑但不敢改”的工程。

正确的移植单位是五类契约：

| 契约 | 回答什么 | 在源项目里通常长什么样 |
|---|---|---|
| **内容** | 有哪些坦克/敌人/关卡/道具，数值是多少 | 纯数据表、常量、JSON、配置 |
| **状态** | 一局游戏里什么是权威事实 | `state` 对象、存档结构 |
| **命令** | 玩家意图如何进入规则 | `setMove / setTrigger / aimAt / useSkill` |
| **事件** | 规则如何通知表现 | `fire / explosion / tileChanged / gameover` |
| **资产** | 模型、动画、节点、朝向、缩放、材质 | GLB + 节点名 + clip 名 + manifest |

把五类契约抽成**可执行的金样本**，再在 Godot 里重建实现。这样“像不像”不是靠眼睛，
而是靠 trace、事件序列和截图逐条验收。

三条铁律：

1. **源版本只读**。所有新代码进 `godot/`，所有移植证据进 `port/`；不改 `v2/`。
2. **先内核等价，再画面**。规则没通过 G3，不做 HUD、不做特效、不调手感。
3. **每个门禁必须有证据**。命令输出、trace diff、截图、性能数字；口头“应该没问题”不算通过。

```
G0 基线 → G1 契约/金样本 → G2 骨架 → G3 内核等价 → G4 首个纵切片
   → G5 全内容/全系统 → G6 表现与平台 → G7 验收发布 →（下一版回到 G0）
```

---

## 1. 何时使用 / 不适用

**适用**

- 已有一个能跑的 Web / Three.js 游戏，要在 Godot 4.x 重建同一玩法。
- 已经有 v2，想把 v3、v4 持续移植到 Godot。
- 需要给移植排期、验收标准、回滚方案，而不是一次性“帮我重写”。

**不适用**

- 从零设计新玩法（先有 GDD 或可玩原型）。
- 只想换渲染后端、保留 Web 技术栈。
- 源版本跑不起来、也没有测试或截图（先补 G0，不要直接开写）。

---

## 2. 开工前必须确认的 6 个事实

只问会改变技术路线或验收口径的问题，其余用 `TBD` 承接，不要停住整个流程。

1. 源版本的**启动命令**和**测试命令**，当前是否全绿。
2. 目标平台：桌面 / Web / 移动；是否必须 Web 导出。
3. Godot 版本（默认用本机已安装的稳定版，本项目为 4.7.1）。
4. 验收口径：**P0 行为等价 / P1 表现等价 / P2 像素级**。默认 P1，不承诺像素级。
5. 哪些行为、数值、资产、存档 key 绝对不能变。
6. 哪些旧版已知问题允许顺手修，哪些必须原样保留（默认原样保留，另列 `DEVIATIONS.md`）。

产出一页 `port/BRIEF.md`：源、目标、范围、非目标、平台、验收级别、风险、里程碑。

---

## 3. 目录与产物约定

```
<project>/
├── v2/                      # 源版本，只读；不要为了让 Godot 好写而改它
├── godot/                   # Godot 工程（唯一新代码目录）
│   ├── project.godot
│   ├── main.tscn / main.gd  # 装配根：模式、输入、事件分发
│   ├── core/                # 纯规则，RefCounted，无 Node / 无场景树
│   ├── content/             # 数值、关卡、资产清单（JSON + 校验器）
│   ├── app/                 # 一局编排、模式状态机
│   ├── view/                # 场景、坦克、炮弹、FX、相机、HUD
│   ├── platform/            # 输入、音频、存档
│   ├── assets/              # GLB、材质、TankRig
│   └── tests/               # 规则测试 + 资产契约 + 黄金回放
└── port/                    # 移植证据，不进游戏包
    ├── BRIEF.md
    ├── BASELINE.md
    ├── source-manifest.sha256
    ├── CONTRACT.md
    ├── contract/*.json
    ├── traces/*.json
    ├── PARITY.md
    ├── DEVIATIONS.md
    ├── port-manifest.json
    └── evidence/G0..G7/
```

如果仓库已有约定（`docs/`、`tools/`、`tests/`），跟随现有约定，不要另起一套。

---

## 4. 阶段 0｜锁基线（0.5–1 天）

**目标**：让“移植前是什么样”可复现、可对比、不可争议。

**动作**

1. 记录源版本身份：路径、`git rev-parse HEAD`、`git status --short`、`package.json` 版本、日期。
2. 生成文件哈希清单（排除 `node_modules`、构建产物、预览大图可选）：
   ```bash
   cd v2
   find . -type f -not -path './node_modules/*' -print0 \
     | sort -z | xargs -0 shasum -a 256 > ../port/source-manifest.sha256
   ```
3. 跑源测试，原样保存输出到 `port/evidence/G0/tests.txt`。
4. 按源项目的方式真实启动一次，走完关键路径：车库 → 选车 → 战斗 → 开火命中 →
   鹰徽失败 → 结算 → 返回车库。保存截图或录屏。
5. 如果源项目有部署包（zip），记录校验和；把它当作只读参考。
6. 写 `port/BASELINE.md`：命令、版本、测试数、截图路径、已知失败、不能复现的环境差异。

**门禁 G0**

- [ ] 源测试全绿；若有红色，逐条列入 `BASELINE.md` 并确认是否纳入本轮。
- [ ] 关键路径至少 3 张截图：车库、战斗、失败/结算。
- [ ] `source-manifest.sha256` 已生成，后续每次移植前复核。
- [ ] 源目录已标记只读（至少团队约定 + `git status` 干净）。

**失败时**：源测试红、游戏起不来，先修源或缩小范围；不要用“Godot 里重写一遍就好了”跳过基线。

---

## 5. 阶段 1｜抽契约与黄金回放（1–2 天）

**目标**：把源游戏变成 5 份 JSON 契约 + 至少 5 条可重放的确定性 trace。

**动作**

1. **C1 内容**：用脚本导入源数据模块，导出 `content.json`，不要手抄。
   - 保留稳定 ID、单位、默认值、颜色、技能文本。
   - 排序键固定，方便 diff。
2. **C2 状态**：列出权威字段、类型、单位、生命周期；区分“规则状态”和“纯表现状态”。
3. **C3 命令**：列出每个命令的参数、范围、幂等性、调用时机；写清“每帧写”还是“边沿触发”。
4. **C4 事件**：列出每个事件的 type、payload、触发条件、顺序约束；事件是一次性语义通知，
   不是逐帧状态。用 `grep -o "emit('[a-zA-Z]*'"` 先做机械盘点，再人工补 payload。
5. **C5 资产**：对每个 GLB 记录文件 hash、缩放、朝向、原点、节点 tag、clip 名、LOD、
   材质名、碰撞代理；用引擎或 glTF 工具实际读取，不靠记忆。
6. **黄金回放**：固定 `seed`、固定 `dt = 1/60`、脚本化命令序列，跑源内核，逐步记录
   状态摘要 + 事件序列，输出 `traces/*.json`。
   - 最少 5 条：直线撞墙、开火拆砖、命中敌人、鹰徽失败、技能/道具。
   - 胜利路径可以只做冒烟，不必逐步 trace（太长且容易因输入脚本漂移）。
7. **可复现性**：同一脚本连跑两次，输出必须逐字节一致；不一致先找 `Date.now()`、
   `Math.random()`、对象遍历顺序、浮点累加。

**门禁 G1**

- [ ] 5 类契约都有文档，字段能对上源代码。
- [ ] `content.json` 通过 schema 校验；所有 ID 在关卡/波次/资产引用中存在。
- [ ] 资产节点 tag 与 clip 名已在真实 GLB 上验证。
- [ ] 5 条 trace 可重复生成，digest 一致。
- [ ] 每个事件都有 payload 说明和至少一个触发场景。

**失败时**：trace 不可复现，先修源侧的随机源/时间源；不要带着不确定的 oracle 进 G3。

详细提取方法、脚本骨架、trace 格式见
[references/contract-extraction.md](references/contract-extraction.md)。

---

## 6. 阶段 2｜Godot 走路骨架（0.5–1 天）

**目标**：在没有任何玩法的情况下，先让 Godot 工程能导入、能启动、能一帧一帧跑。

**动作**

1. 新建 `godot/` 工程，固定 Godot 版本；写进 `project.godot` 和 README。
2. 先定渲染器：需要 Web 导出选 `gl_compatibility`；只做桌面可选 `forward_plus`。
   这个决定写在 `BRIEF.md`，不要中途反复换。
3. 定坐标契约（必须写进 `view/README` 或代码注释）：
   - 棋盘 `x = col - 6`、`z = row - 6`，1 格 = 1 米。
   - 模型 **+Z 车头、+Y 向上**，原点在履带接地面，统一 `scale = 0.22`。
   - Godot 里 `position = Vector3(x, 0, z)`、`rotation.y = heading`。
   - **不要用 `look_at()` 处理 +Z 模型**：Godot 的 `look_at` 默认让 -Z 朝向目标。
4. 搭最小场景树：`Main → Stage / World / Tanks / Projectiles / FX / CameraRig / HUD`。
5. 输入用运行时 `InputMap.add_action` 或 `project.godot` 的 `[input]`，二选一，写清楚。
6. 主循环用 `_process(delta)`，`delta` 必须 clamp 到 `0.05`，和源 `Math.min(dt, 0.05)` 对齐。
7. 做一个“假内核”：一个命令改一个数，发一个事件，HUD 打一行字。证明命令 → 状态 →
   事件 → 表现这条线通了。

**门禁 G2**

- [ ] `godot --headless --path godot --import` 退出码 0，无资源导入错误。
- [ ] `godot --headless --path godot --quit-after 120 res://main.tscn` 能跑 120 帧。
- [ ] 没有 `SCRIPT ERROR`、`Invalid call`、空引用；允许的已知警告记录在案。
- [ ] 一张骨架截图，坐标/朝向用可视化辅助确认（例如 +Z 箭头）。

**失败时**：先解决导入、主场景、输入映射；不要在骨架阶段引入玩法代码。

---

## 7. 阶段 3｜规则内核等价（2–4 天，最关键）

**目标**：把 `core` 原样重建成 Godot 里可无头运行的纯规则，并通过源测试与黄金回放。

**动作**

1. 按源顺序移植：常量 → RNG → 网格/碰撞 → 战斗循环。保持函数名、字段名、更新顺序，
   只做命名风格转换（`camelCase` → `snake_case`）。
2. **内核只用 `RefCounted`**：不继承 `Node`，不 `get_tree()`，不读 `Input`，不 `preload`
   场景/材质。内容由构造函数注入。
3. **内核状态用标量 `float`，不要用 `Vector2/Vector3`**。Godot 的 `Vector2/Vector3`
   分量默认是 32 位浮点，源是 64 位 double；用向量会在长 trace 里累积误差。
4. **RNG 逐位复刻**。以 `mulberry32` 为例，必须显式 `& 0xFFFFFFFF` 模拟 32 位；
   用已验证的测试向量校验（见 [references/godot-mapping.md](references/godot-mapping.md)）。
5. **事件用数组缓冲**，`drain_events()` 一次取走并清空；不要用 Godot signal 逐个发，
   避免 deferred call 改变顺序。
6. 移植源测试（本项目 14 项），再写 trace 回放测试。两条都过才算 G3。
7. **不要用 Godot 物理引擎替代网格碰撞**。源用圆-格数学、滑动、视线；换成 `CharacterBody3D`
   会改变贴墙、拆砖、AI 卡住的行为。

**门禁 G3**

- [ ] 源测试逐项有对应测试，全部通过（允许命名不同，不允许静默跳过）。
- [ ] 5 条 trace 的事件序列 **完全一致**；数值最大误差 < `1e-5`（HP/分数是整数，必须完全一致）。
- [ ] 同 seed 连跑两次，Godot 侧 digest 一致。
- [ ] 内核目录没有 `Node`、场景、输入、音频、资产引用（用脚本静态检查）。
- [ ] 第一个不一致点能定位到 step 和字段，而不是“大概差不多”。

**失败时**：按“第一处分歧”排查，不要放宽 tolerance 掩盖问题。常见原因：更新顺序、RNG
掩码、`Vector2` 精度、角度 wrap 边界、命令在 `update` 前/后应用。

**G3 是硬闸门。G3 不过，禁止开始做 HUD、特效和手感。**

---

## 8. 阶段 4｜首个纵切片（2–4 天）

**目标**：一条完整可玩的路径：车库 → 选一辆车 → 进场 → 移动/瞄准/开火 → 拆砖 →
命中一个敌人 → 鹰徽失败 → 结算。

**动作**

1. **资产契约落地**：写 `TankRig`，按 tag 找 `Turret_Pivot / Gun_Pivot / GunMuzzle`，
   按 clip 名找 `Drive / Fire`；找不到就报错，不要静默回退到空节点。
2. 先做一辆 hero 坦克、一类敌人、一张 13×13 关卡、一种砖、一颗炮弹。
3. 世界格子由 `tileChanged` 事件驱动显隐/换材质；表现层不得自己判断“打中了”。
4. 相机先做追尾，不做震屏/俯视；HUD 只做分数/血量/提示三样。
5. 炮口位置用 `GunMuzzle.global_position`；没有 muzzle 节点时才回退到车体上方。
6. 每次只接一个事件，接完跑一次；不要一次性把 19 个事件全接上。

**门禁 G4**

- [ ] 从启动到失败结算，全程无脚本错误。
- [ ] 四张截图：车库、进场、开火命中、鹰徽失败/结算。
- [ ] 炮口焰/子弹起点与 `GunMuzzle` 对齐（允许 0.05 米误差）。
- [ ] 砖块被摧毁后，格子状态与画面一致；重开一局能恢复。
- [ ] 60 秒连续操作无 orphan node 增长。

---

## 9. 阶段 5｜全内容与全系统（3–5 天）

**目标**：3 辆坦克、3 类敌人、3 波 10 辆、6 种道具、3 个技能、生命/复活、胜负全通。

**动作**

1. 内容全部从 `content/*.json` 读，代码里不写死数值；加载时校验 ID 和引用。
2. 技能、道具、加固、冻结、护盾、反应装甲逐项接事件；每项至少一条测试/冒烟。
3. 敌人 AI 的“看不见/卡住/抖动/狙击瞄准”逐条对照源实现；不要用“更聪明”的寻路替代。
4. 玩家死亡、复活、生命耗尽、胜利、鹰徽失败五条路径都要能走通。
5. 每次新增内容，补一条内容校验测试；不要靠人工点。

**门禁 G5**

- [ ] 胜利路径：3 波 10 辆全灭，结算显示正确分数。
- [ ] 失败路径：鹰徽被毁（包括玩家自己的炮弹）与生命耗尽都能触发。
- [ ] 3 辆坦克的数值/技能/涂装差异可见、可玩。
- [ ] 6 种道具都能掉落并生效；权重与源一致。
- [ ] 新增规则有对应无头测试；全量测试通过。

---

## 10. 阶段 6｜表现与平台对齐（3–5 天）

**目标**：从“规则对”到“看起来、听起来、操作起来像同一个游戏”。

**动作**

1. **FX**：爆炸、烟、炮口焰、火花、履带印、焦痕、护盾、道具。按事件驱动，按源时长/尺度
   对齐；允许实现不同，不允许时序错位。
2. **相机**：追尾/俯视切换、肩部偏移、震屏、车库环绕；参数进 `view_tuning.json`。
3. **HUD**：车库卡片、分数、血量、技能冷却、波次、提示、结算、最高分；CSS 布局翻成
   `Control` + `Theme`，不要用 100 个绝对坐标硬摆。
4. **音频**：源是 WebAudio 合成音时，优先用 `OfflineAudioContext` 离线烘成 WAV，再导入
   Godot；不要凭听感重写一套。
5. **存档**：`ConfigFile` + `user://`；最高分 key 与源保持一致或明确迁移，写进 README。
6. **性能**：统计 draw call、三角形、帧时间；hero 的 146 节履带是重点，必要时
   `MultiMeshInstance3D` 或合并；敌人继续用 troop LOD。
7. **可访问性/窗口**：分辨率、拉伸、全屏、暂停；不要改变源的操作键位，除非用户确认。

**门禁 G6**

- [ ] 车库/战斗/俯视/结算四组截图与源并排对比，差异有记录。
- [ ] 1280×720 目标平台稳定 60 fps；draw call / 三角形有数字。
- [ ] 音效在正确事件触发；无爆音、无延迟漂移。
- [ ] 最高分退出重进仍在；窗口缩放不破布局。
- [ ] 10 分钟连续游玩，orphan node / 内存不持续增长。

---

## 11. 阶段 7｜验收与发布（1–2 天）

**目标**：把“移植完成”变成可交付、可回归、可升级的工程。

**动作**

1. 填 `port/PARITY.md`：每条行为一行，源引用、Godot 实现、验证方式、状态、偏差。
2. 所有偏差进 `DEVIATIONS.md`：ID、行为、原因、影响、用户是否批准、对应测试。
3. 配 `export_presets.cfg`，做目标平台导出；运行导出产物，不只跑编辑器。
4. 写 `godot/README.md`：启动、测试、导出、已知限制、与源版本差异。
5. 打 tag：`godot-v<source-version>`；保存 G0–G7 证据目录。
6. 用户验收：手感、炮塔转速、相机距离、履带速度、难度；只改 `view_tuning.json` 和内容表，
   不改内核。

**门禁 G7**

- [ ] `PARITY.md` 100% 有状态；未通过项全部是已批准偏差。
- [ ] 导出产物能启动、能完成一局、能退出。
- [ ] 全量测试通过；trace 回归通过。
- [ ] 用户明确接受手感与视觉差异。
- [ ] 版本 tag、README、证据目录齐全。

---

## 12. 阶段 8｜下一版怎么继续移植（升级循环）

v3 到来时，不要重开一遍，按 `U0–U6` 走：

1. **U0/U1 冻新基线 + 分类 diff**：新源版本只读，生成新 manifest、跑新测试、截新图；
   把源 diff 按五类契约归类。
2. **U2/U3 更新影响面与 oracle**：只有内容变化就只更 JSON + 测试；规则变化才动 `core/`；
   只重录受影响的 trace，每条变化必须能对应到源 commit。
3. **U4 只改映射到的文件**：按 `port-manifest.json` 找影响面，不整仓重写。
4. **U5/U6 全门禁回归 + 发布**：G1 → G7 重跑；更新 `PARITY.md`、`DEVIATIONS.md`、打 tag。

规则：**源行为变化不是移植 bug**。先更新 oracle，再改实现；禁止为了让 trace 变绿而
悄悄放宽 tolerance 或删测试。

详细流程见 [references/version-upgrade.md](references/version-upgrade.md)。

---

## 13. 并行与角色

- **G3 之前单线程**：内核、内容、资产契约互相牵连，多人并行会制造“各自以为对”的假等价。
- **G4 之后可并行**：`world / fx / hud / camera` 在 `TankRig` 与事件表冻结后可以分头做。
- **验证者独立**：写实现的人不要给自己发 G3/G6 通过；至少让另一个 agent/人按门禁清单复核。
- **一个写入者**：`port/contract/*.json`、`port/traces/*.json`、`port/PARITY.md` 同一时间
  只允许一个 agent 写，避免覆盖。

---

## 14. 硬规则（违反即停）

1. 不改源目录；不把 Godot 代码写进 `v2/`。
2. 没有 G1 的契约与 trace，不写 `core/`。
3. `core/` 不出现 `Node`、`get_tree`、`Input`、`AudioStreamPlayer`、`preload("*.tscn")`。
4. 不用 Godot 物理替代源网格碰撞；不用“更聪明”的寻路替代源 AI。
5. 坐标/朝向只定义一次；禁止一部分代码假设 +Z、另一部分假设 -Z。
6. 内核状态不用 `Vector2/Vector3` 存权威数值；用标量 `float`。
7. RNG 必须逐位复刻；浮点比较用 epsilon + 事件序列，不做 bit-exact。
8. 表现层只读 `state` 和事件，不反向写规则。
9. 先移植行为，再做改良；每个差异进 `DEVIATIONS.md`，不夹带。
10. 每个门禁留证据；没有证据的“通过”视为未通过。
11. 跨引擎传 `dt` 用 `dt_num/dt_den` 有理数，不传十进制浮点；事件按 `{type, ...data}` 展开顺序复现。
12. 十六进制颜色数字用 `Color8` 拆通道；Godot 4.7 的 `Color.hex(int)` 按 `0xRRGGBBAA` 解析，会把 RGB 读成 RGBA。

---

## 15. 常见失败与处理

| 症状 | 最可能原因 | 处理 |
|---|---|---|
| 源测试就红 | 基线本身不稳 | 先修源/缩范围，记录已知失败；不要带病移植 |
| trace 第 1 步就不同 | 初始状态、单位、坐标、seed 不同 | 对比初始 state 的每个字段；检查 `dt` 与命令应用时机 |
| trace 中途缓慢漂移 | 浮点精度（Vector2/3）、累加顺序 | 内核改标量 double；对齐运算顺序；用第一处分歧定位 |
| 事件数量对、顺序不同 | 同一帧内系统顺序不同 | 对齐 `player → waves → enemies → bullets → pickups → fortify → win` |
| 模型节点找不到 | 导入改名、根节点不同、大小写 | 用递归 `find_child`；打印实际节点树；把 tag 写进资产契约 |
| Drive 不循环 / Fire 不播 | clip 名、loop 设置、一个 player 被复用 | 校验 `has_animation`；Drive 设 loop；Drive/Fire 用双 player 或 AnimationTree |
| 画面像但规则不对 | 表现层偷偷改状态 | 搜 `state.` 写入；所有结果只允许 `core` 改 |
| 60 fps 不达标 | 履带 draw call、阴影、粒子 | MultiMesh/合并、关小件投影、GPU 粒子限量、先测再优化 |
| Web 导出失败 | 渲染器/线程/音频 | 用 `gl_compatibility`；查导出日志；先在桌面版验规则 |
| 手感不对但规则对 | 相机/转速/履带速度/音效 | 只调 `view_tuning.json`，不回改内核 |

---

## 16. 反模式

- 把 `battle.js` 一行行翻成 GDScript，连 Three.js 的临时对象一起翻。
- 先做 HUD、爆炸、车库，最后发现规则不对，返工全部表现接线。
- 用 `Area3D` / `CharacterBody3D` 重做碰撞，觉得“物理更真实”。
- 用 `look_at()` 让 +Z 模型看目标，然后给所有模型加 180° 补丁。
- 内核里 `Vector3` 满天飞，trace 对不上就调 tolerance。
- 为了让测试过，删掉“太难复现”的用例。
- 边移植边“优化”数值、AI、关卡；最后无法判断差异来自移植还是改设计。
- 只在编辑器里点，不做无头测试；换一台机器就复现不了。

---

## 17. 完成定义（Definition of Done）

- G0–G7 全部有证据，且通过。
- `PARITY.md` 覆盖全部玩家可见行为；未通过项 100% 是已批准偏差。
- 导出产物在目标平台能完成一局并正常退出。
- 全量测试 + 黄金回放可一条命令重跑。
- 10 分钟 soak 无 orphan/内存持续增长。
- README 写清启动、测试、导出、与源版本差异。
- 用户明确接受手感与视觉差异。

---

## 18. 参考文件

- [references/contract-extraction.md](references/contract-extraction.md)：五类契约、导出脚本、
  黄金 trace 格式与容差。
- [references/godot-mapping.md](references/godot-mapping.md)：Three.js → Godot 映射、坐标契约、
  RNG 逐位移植、场景树、资产导入、动画/材质/性能。
- [references/verification.md](references/verification.md)：G0–G7 命令、测试运行器、trace 对比、
  性能与 soak 检查。
- [references/version-upgrade.md](references/version-upgrade.md)：v3+ 的分类 diff、oracle 更新、
  `port-manifest.json` 与回滚。
- [references/case-steel-bastion-v2.md](references/case-steel-bastion-v2.md)：本项目（钢铁防线 3D
  Sherman Edition v2）的契约清单、Godot 文件映射、里程碑、风险与验收清单。
- `templates/port-manifest.json`、`templates/parity-matrix.md`、
  `templates/DEVIATIONS.md`、`templates/golden-trace.schema.json`。

- [references/pilot-findings.md](references/pilot-findings.md)：v3 → Godot 4.7 试点结果与五条修订
  （dt 有理数传输、事件展开顺序、资产实例化检查、命名冲突）。

**本项目的下一步**：先读 case 文件，按阶段 0 生成基线；阶段 1 的导出脚本和 trace 场景
在 case 文件里有具体清单。不要直接从“新建 Godot 工程”开始。
