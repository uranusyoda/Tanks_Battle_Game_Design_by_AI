# G0 基线 — 钢铁防线 3D v3

- 日期：2026-10-20
- 工作区：`/Users/yoda/Desktop/工作/2026上半年/超脑AI/坦克大战3D`
- 活动版本：`versions/v3`（`3.0.0`，v2 的完整复制，玩法/数值/资产/测试与 v2 一致）
- 冻结基线：`versions/v2`（`2.0.0`，只读参考）
- 版本控制：当前目录不是 git 仓库，使用文件哈希清单代替 commit
- 源清单：`port/source-manifest.sha256`（41 个文件）

## 测试

```bash
cd versions/v3 && npm test
```

结果：**14 passed / 0 failed**，证据 `port/evidence/G0/tests.txt`。

## 资产

| 资产 | SHA-256 | 大小 |
|---|---|---|
| `m4a1_sherman_hero.glb` | `54b7286190de96ea4a90c2f746f0cb7d34c7b973a16f9dd7fc0d3d23af5c6ab4` | 1,477,664 B |
| `m4a1_sherman_troop.glb` | `ff6a296b0bed2540d3e612efc215debbf577e8c0421bde7f36f0b6d0d5c7bc01` | 435,172 B |

模型契约（来自 `versions/v3/assets/models/manifest.json`）：

- 统一 `scale = 0.22`；glTF **+Z 车头、+Y 向上**，原点在履带接地面。
- 节点 tag：`Turret_Pivot` / `Gun_Pivot` / `GunMuzzle`。
- clip：`Drive` / `Fire`。
- hero 有 `Drive`，troop **没有** `Drive`（履带为静态合并网格）。

## 视觉基线

v3 与 v2 的差异只有标题/端口/文档（`diff -rq` 已确认），因此视觉基线使用：

- `versions/v2/preview/garage.png`
- `versions/v2/preview/battle.png`
- `versions/v2/preview/sherman-close.png`

G4 已补 Godot 实机截图（`port/evidence/G4/`）；源浏览器截图仍使用 v2 preview（v3 仅标题/端口差异）。

## 环境

- Godot `4.7.1.stable.official.a13da4feb`（`/opt/homebrew/bin/godot`）
- Node `v22+`（源测试与 trace 录制）
- macOS；headless 运行需要把 `HOME` 指到可写目录（本机用 `/tmp/godot-home`），
  否则 Godot 创建 `user://logs` 失败。
