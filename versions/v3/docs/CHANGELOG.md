# v3 变更记录

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循语义化版本。每次改动追加到 `[Unreleased]`，发版时再落成版本号。

## [Unreleased]

### 计划中（尚未实现）

- [ ] troop LOD 履带 UV 滚动 / 着色器位移
- [ ] hero 履带板 `InstancedMesh` 化，压 draw call
- [ ] 炮塔转速 / 相机距离 / 履带滚速手感调参
- [ ] 移动端触控、暂停菜单、进度存档

### 新增

- （在这里写：新增了什么、为什么、验收方式）

### 变更

- （在这里写：改了哪个行为/数值，旧值 → 新值）

### 修复

- （在这里写：现象、根因、涉及文件）

---

## [3.0.0] - 2026-10-20

### 基线

- 从 `versions/v2@2.0.0` 完整复制，玩法、数值、资产、测试与 v2 一致。
- 独立端口：4174（`START-GAME.command`）/ 4176（`.test-start.command`）。
- 版本号改为 `3.0.0`，页面标题与 HUD 标注 `V3`。
- 导出脚本默认输出改为 `versions/v3/assets/models`。

### 已知限制（继承自 v2）

- 敌人使用 troop LOD，履带是静态合并网格。
- 没有按距离自动切 LOD；玩家固定 hero，敌人固定 troop。
- 无触控、暂停、进度存档；模型无碰撞体和烘焙贴图。
