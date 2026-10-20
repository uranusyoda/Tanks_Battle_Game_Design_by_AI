# 契约提取：把源游戏变成可执行的 oracle

> 目标不是“读懂代码”，而是产出 5 份能驱动 Godot 实现、能自动验收的契约。
> 输入：可运行的源版本。输出：`port/CONTRACT.md`、`port/contract/*.json`、`port/traces/*.json`。

---

## 1. 五类契约一览

| ID | 契约 | 必须回答 | 典型产物 |
|---|---|---|---|
| C1 | 内容 | 有哪些实体、数值、关卡、掉落、资产引用 | `content.json` + schema |
| C2 | 状态 | 什么是权威事实、单位、生命周期 | `state.md` / `state.schema.json` |
| C3 | 命令 | 玩家意图如何进入规则、范围、时机 | `commands.md` |
| C4 | 事件 | 规则如何通知表现、payload、顺序 | `events.md` / `events.json` |
| C5 | 资产 | 文件、缩放、朝向、节点、clip、材质、LOD | `assets.json` + 资产检查输出 |

原则：

- **机器导出优先**：能从模块 import 的，不手抄；能读 GLB 的，不凭记忆。
- **稳定 ID**：内容 ID、事件 type、节点 tag、clip 名都是跨引擎契约，改名等于破坏兼容。
- **单位写清**：米/秒、弧度、格、像素；角度统一弧度，避免度和弧度混用。
- **表现提示与规则分离**：颜色、涂装、相机参数可以进内容，但规则不得依赖它们。

---

## 2. C1 内容契约

### 2.1 盘点清单

- 玩家实体：ID、名称、血量、速度、转向、射速、伤害、弹速、炮塔转速、炮口偏移、技能、模型 LOD、涂装。
- 敌方实体：ID、血量（注意源可能用“单位数 × 25”）、速度、射速、伤害、射程、分数、缩放、涂装、特殊标记。
- 关卡：网格尺寸、tile 码、出生点、出生列、波次时间与组成、场上上限、鹰徽坐标、掩体坐标。
- 道具：ID、权重、颜色、标签、效果参数。
- 资产清单：稳定 ID → 文件、缩放、LOD、clip、节点 tag、fallback。
- 表现调参：履带速率、阴影尺寸、相机距离等；与规则分开存放。

### 2.2 导出脚本骨架

放到源项目外的 `port/tools/export_content.mjs`，用 `process.argv` 接收源目录，避免写死路径。

```js
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const SRC = path.resolve(process.argv[2] ?? 'v2');
const OUT = path.resolve(process.argv[3] ?? 'port/contract');

const load = (rel) => import(pathToFileURL(path.join(SRC, rel)).href);

const [
  { TANKS },
  { ENEMY_TYPES },
  { LEVEL, SHOWROOM },
  { POWERUPS },
  { MODEL_ASSETS, VIEW_TUNING },
] = await Promise.all([
  load('src/content/tanks.js'),
  load('src/content/enemies.js'),
  load('src/content/levels.js'),
  load('src/content/powerups.js'),
  load('src/content/assets.js'),
]);

// 稳定排序，保证 diff 可读；不要把函数/类实例写进 JSON。
function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortKeys(value[k])]));
  }
  return value;
}

const content = sortKeys({
  meta: { source: SRC }, // 不要放时间戳；否则每次 diff 都变
  tanks: TANKS,
  enemies: ENEMY_TYPES,
  levels: { LEVEL, SHOWROOM },
  powerups: POWERUPS,
  assets: MODEL_ASSETS,
  viewTuning: VIEW_TUNING,
});

await fs.mkdir(OUT, { recursive: true });
await fs.writeFile(path.join(OUT, 'content.json'), JSON.stringify(content, null, 2) + '\n');
console.log(`wrote ${path.join(OUT, 'content.json')}`);
```

注意：

- 不要在契约里放 `generatedAt`；时间戳会让每次 diff 都变化。需要留痕就写到 `port/BASELINE.md`。
- `undefined` 字段会被 JSON 丢掉；缺失字段要显式写 `null`，否则 Godot 侧无法区分“没有”和“默认”。
- 十六进制颜色在 JSON 里是数字；Godot 侧用 `Color.hex()` 或 `Color8` 转，不要手抄 RGB。

### 2.3 内容校验

至少校验：

- 所有 `waves[].list[]` 的敌人 ID 存在。
- 所有 `spawnCols` 在网格范围内。
- 鹰徽 tile 恰好 1 个。
- 所有 `model.lod` 在资产清单里有对应条目。
- 道具权重 > 0，ID 唯一。
- 关卡网格是 `rows × cols` 的矩形。

校验器可以先用 Node 写，再在 Godot 侧写一份等价校验；两边都跑，防止 JSON 被手改坏。

---

## 3. C2 状态契约

不要只写“有 player/enemies/bullets”。写清楚：

| 字段 | 类型 | 单位 | 谁写 | 生命周期 | 是否进 trace |
|---|---|---|---|---|---|
| `phase` | enum `battle/won/lost` | — | core | 一局 | 是 |
| `time` | float | 秒 | core | 一局 | 是 |
| `player.x/z` | float | 米（格） | core | 一局 | 是 |
| `player.heading` | float | 弧度 | core | 一局 | 是 |
| `player.turretYaw` | float | 弧度（相对车体） | core | 一局 | 是 |
| `player.hp` | int/float | 点 | core | 一局 | 是 |
| `bullets[].life` | float | 秒 | core | 子弹 | 可选 |
| `enemies[].hitFlash` | float | 秒 | core | 敌人 | 否（纯表现） |

规则：

- **权威状态只由 core 写**。表现层的 `hp`、`alive`、`score` 都是只读副本。
- 纯表现字段（闪白、粒子计时）不要塞进 core；如果源塞了，标注为“表现提示”，Godot 可放 view。
- 数组顺序也是契约：敌人/子弹的增删顺序会影响 RNG 与事件顺序，trace 要保留 ID 顺序。
- 浮点单位统一：位置用格（1 格 = 1 米），角度用弧度，时间用秒。

---

## 4. C3 命令契约

每个命令写 5 件事：

1. 参数与范围（例如 `throttle ∈ [-1,1]`，越界是否 clamp）。
2. 调用时机（每帧写 / 按下边沿 / 松开）。
3. 是否幂等（重复调用是否安全）。
4. 失败/冷却时返回值（`useSkill()` 返回 bool）。
5. 对状态的影响是否立即发生，还是下一次 `update` 才生效。

示例表：

| 命令 | 参数 | 语义 | 时机 | 备注 |
|---|---|---|---|---|
| `setMove(throttle, turn)` | -1..1 | 每帧写入移动意图 | 每帧 | 松开写 0；core clamp |
| `setTrigger(on)` | bool | 按住开火 | 每帧 | 冷却由 core 判断 |
| `aimAt(x, z)` | 世界坐标 | 炮塔目标点 | 鼠标移动 | 只改目标，不瞬间改角度 |
| `useSkill()` | — | 释放技能 | 按键边沿 | 返回是否成功 |
| `stop()` | — | 清空输入 | 结算 | 不改变 phase |

Godot 侧对应一个 `BattleCommands`（或 `Battle` 的方法），保持“意图进、结果出”，不要在
Input 层直接改 `player.hp`。

---

## 5. C4 事件契约

事件是**一次性语义通知**，不是逐帧状态。每条事件写：

- `type`（稳定字符串）
- payload 字段与单位
- 触发条件
- 触发顺序（同一帧内谁先谁后）
- 表现层允许做什么、不允许做什么

机械盘点：

```bash
grep -o "emit('[a-zA-Z]*'" src/core/battle.js | sort | uniq -c
```

然后人工补 payload。常见坑：

- 同一帧内 `explosion` 与 `enemyKilled` 的先后会影响音效/计分动画。
- `tileChanged` 可能在同一帧连续多次；表现层要按顺序处理，不能只取最后一次。
- `gameover` 之后仍可能有子弹/爆炸事件；是否继续消费要在契约里写清。
- 事件里不要塞对象引用（敌人实例、材质）；只放 ID、坐标、数值、枚举。

建议的 `events.json`：

```json
{
  "fire": { "payload": ["from", "shooterId", "x", "z", "yaw", "ap?"], "consumers": ["fx", "audio", "camera"] },
  "tileChanged": { "payload": ["r", "c", "tile", "previous"], "consumers": ["world"] }
}
```

---

## 6. C5 资产契约

对每个 GLB 记录：

| 字段 | 说明 |
|---|---|
| `id` | 稳定 ID，玩法只认 ID，不认路径 |
| `file` / `hash` | 文件名 + SHA-256 |
| `scale` | 游戏内缩放（例如 0.22） |
| `up` / `forward` | 例如 `+Y` / `+Z` |
| `origin` | 履带接地面 / 车体中心 |
| `tags.turret/gun/muzzle` | 节点名，必须真实存在 |
| `clips.drive/fire` | 动画名，必须真实存在；没有就写 `null` |
| `lod` | `hero` / `troop` / … |
| `fallback` | 加载失败时的替代 ID |
| `materials` | 可涂装材质名 → 语义槽位 |
| `bounds` | 世界包围盒（长宽高），用于相机/碰撞代理 |

验证方式（Godot 侧最可靠）：

```gdscript
# tests/AssetContractTest.gd（节选）
func check_model(path: String, tags: Dictionary, clips: Dictionary) -> Array[String]:
	var errors: Array[String] = []
	var packed: PackedScene = load(path)
	if packed == null:
		return ["cannot load %s" % path]
	var root := packed.instantiate()
	var anim := root.find_child("AnimationPlayer", true, false) as AnimationPlayer
	for key in tags:
		if root.find_child(tags[key], true, false) == null:
			errors.append("%s missing tag %s (%s)" % [path, key, tags[key]])
	for key in clips:
		if clips[key] != null and (anim == null or not anim.has_animation(clips[key])):
			errors.append("%s missing clip %s" % [path, clips[key]])
	root.free()
	return errors
```

还要检查：

- 包围盒是否符合预期（车长、宽、高），缩放是否只应用一次。
- 朝向：在 +Z 放一个测试用空节点/箭头，进游戏确认车头方向。
- 材质名是否被导入器改写（大小写、后缀）；涂装槽位用“语义名”映射，不要依赖自动生成名字。
- hero/troop 两档的节点名、材质名、朝向必须一致，`TankRig` 才能不分叉。

---

## 7. 黄金回放（golden trace）

### 7.1 为什么需要

单元测试只能证明“某个函数在这个输入下对”。黄金回放证明“整局在固定输入下，每一步的
状态和事件都对”。它是跨引擎移植最强的 oracle，也是后续版本升级的回归基线。

### 7.2 场景设计

至少 5 条，覆盖不同系统，控制在 200–600 步（约 3–10 秒模拟）：

| 场景 | 目的 | 关键命令 |
|---|---|---|
| `drive_into_brick` | 移动、碰撞、滑动、朝向 | `setMove(1,0)` 持续 |
| `fire_brick` | 开火、冷却、子弹、拆砖、事件顺序 | `aimAt` + `setTrigger` |
| `hit_enemy` | 敌人受伤/死亡、计分、掉落 | 对准出生列，持续开火 |
| `eagle_fail` | 鹰徽被毁、gameover | 对准鹰徽开火（含玩家自己的炮弹） |
| `skill_powerup` | 技能、冷却、道具、护盾/冻结 | `useSkill` + 靠近掉落物 |

如果要覆盖胜利，另做 `win_smoke`，只校验最终 `phase/score/killed`，不逐步 trace。

### 7.3 录制器骨架

```js
// port/tools/record_trace.mjs
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const SRC = path.resolve(process.argv[2] ?? 'v2');
const OUT = path.resolve(process.argv[3] ?? 'port/traces');
const load = (rel) => import(pathToFileURL(path.join(SRC, rel)).href);

const [{ createBattle }, { TANKS }, { ENEMY_TYPES }, { LEVEL }, { POWERUPS }] =
  await Promise.all([
    load('src/core/battle.js'),
    load('src/content/tanks.js'),
    load('src/content/enemies.js'),
    load('src/content/levels.js'),
    load('src/content/powerups.js'),
  ]);

const DT = 1 / 60;
const SCENARIOS = [
  {
    id: 'fire_brick', tankId: 'sherman', seed: 7, steps: 180,
    commands: [
      { step: 0, op: 'aimAt', args: [0, 3] },
      { step: 10, op: 'setTrigger', args: [true] },
      { step: 25, op: 'setTrigger', args: [false] },
    ],
  },
  // ... 其余场景
];

const snap = (battle) => {
  const s = battle.state;
  return {
    t: s.time, phase: s.phase, score: s.score, wave: s.wave,
    player: {
      x: s.player.x, z: s.player.z, heading: s.player.heading,
      turretYaw: s.player.turretYaw, hp: s.player.hp, lives: s.player.lives,
      alive: s.player.alive,
    },
    enemies: s.enemies.map((e) => ({ id: e.id, x: e.x, z: e.z, heading: e.heading, hp: e.hp })),
    bullets: s.bullets.map((b) => ({ id: b.id, x: b.x, z: b.z })),
    pickups: s.pickups.map((p) => ({ id: p.id, x: p.x, z: p.z })),
    eagle: s.eagle.alive,
  };
};

const canonical = (v) => Array.isArray(v)
  ? v.map(canonical)
  : v && typeof v === 'object'
    ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canonical(v[k])]))
    : v;

for (const sc of SCENARIOS) {
  const battle = createBattle({
    tankId: sc.tankId, tanks: TANKS, enemyTypes: ENEMY_TYPES,
    level: LEVEL, powerups: POWERUPS, seed: sc.seed,
  });
  const events = [];
  const samples = [];
  for (let step = 0; step < sc.steps; step++) {
    for (const c of sc.commands.filter((c) => c.step === step)) {
      battle.commands[c.op](...c.args);
    }
    battle.update(DT);
    for (const e of battle.drainEvents()) events.push({ step, ...e });
    if (step % 5 === 0) samples.push({ step, state: snap(battle) });
  }
  const final = snap(battle);
  const digest = crypto.createHash('sha256')
    .update(JSON.stringify(canonical({ samples, final, events }))).digest('hex');
  const trace = { schema: 1, scenario: sc.id, seed: sc.seed, dt: DT, steps: sc.steps,
    commands: sc.commands, events, samples, final, digest };
  await fs.mkdir(OUT, { recursive: true });
  await fs.writeFile(path.join(OUT, `${sc.id}.json`), JSON.stringify(trace, null, 2) + '\n');
  console.log(`${sc.id}: ${events.length} events, digest=${digest.slice(0, 12)}`);
}
```

要点：

- 命令在 `update` **之前**应用；和 Godot 侧约定一致。
- 每 5 步采样一次；事件逐步记录，不采样。
- `digest` 用于快速比较；定位差异仍要逐 sample / 逐 event 对比。
- 不要用 `Date.now()` 做 seed；把 seed 写进 trace。
- 不要记录对象引用、函数、`spec` 整表；只记录可比较的标量/ID。

### 7.4 容差

| 类型 | 容差 | 说明 |
|---|---|---|
| 事件序列 | 0 | type、顺序、payload 的 ID/枚举必须完全一致 |
| HP、分数、生命、波次 | 0 | 整数，必须完全一致 |
| 位置 x/z | `1e-5` | 先看第一处分歧；持续漂移通常是精度/顺序问题 |
| 角度 heading/turretYaw | `1e-5` | 注意 ±π 边界，先 wrap 再比较 |
| 时间 time | `1e-5` | 固定 dt 下应几乎一致 |
| 浮点数组长度/ID 顺序 | 0 | 少一个敌人/子弹通常是规则差异，不是精度 |

如果误差随步数线性增大，不要直接放大 tolerance；先查：

1. `dt` 是否同一帧被 clamp 两次/未 clamp。
2. 角度是否用 `wrapf`（范围 `[-π, π]`）而源是 `(-π, π]`。
3. `tc/tr` 的格子索引是否用了 `roundi` 而不是 JS 语义的 `floor(v + 0.5)`。
4. 内核是否误用 `Vector2/Vector3`（32 位）。
5. 同一帧内命令应用顺序、系统更新顺序。
6. 数组遍历中删除元素是否改变了“跳过/重复”的语义。
7. RNG 调用次数是否多一次/少一次（掉落、抖动、AI 都会抽随机）。

> **试点修正（v3）**：trace 必须同时存 `dt_num` / `dt_den`，回放时在目标引擎用
> `float(dt_num) / float(dt_den)` 重新计算。只传十进制 `dt` 会差 1 ULP，足以让计时器差一帧。

### 7.5 trace 文件结构

见 `templates/golden-trace.schema.json`。建议至少包含：

```json
{
  "schema": 1,
  "scenario": "fire_brick",
  "seed": 7,
  "dt": 0.016666666666666666,
  "steps": 180,
  "source": { "root": "v2", "commit": "...", "manifest": "port/source-manifest.sha256" },
  "commands": [{ "step": 0, "op": "aimAt", "args": [0, 3] }],
  "events": [{ "step": 11, "type": "fire", "from": "player" }],
  "samples": [{ "step": 0, "state": {} }],
  "final": {},
  "digest": "..."
}
```

---

## 8. G1 检查清单

- [ ] `content.json` 由脚本生成，ID 稳定，排序稳定。
- [ ] 5 类契约都有文档；每个字段能指回源文件/行。
- [ ] 资产 tag/clip 在真实 GLB 上验证过（不是看 manifest 猜）。
- [ ] 5 条 trace 连跑两次 digest 相同。
- [ ] 每条 trace 都有“预期事件序列”摘要，方便人工 review。
- [ ] 已知不确定项写入 `DEVIATIONS.md` 的“待确认”，不藏在代码里。
