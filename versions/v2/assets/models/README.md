# M4A1(76)W Sherman — 游戏资产（v2）

由 `tools/blender/export_game_sherman.py` 从
`../../../../assets/models/m4a1_sherman_anim.blend` 生成。**不要手改 GLB**；
改脚本后重跑导出。

在**仓库根目录**运行：

```bash
SHERMAN_EXPORT_OUT="$PWD/versions/v2/assets/models" \
/Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
  --factory-startup --python tools/blender/export_game_sherman.py
```

> 导出脚本默认写 `versions/v3/assets/models`，v3 是当前迭代目标；要更新 v2 快照时
> 才需要显式指定 `SHERMAN_EXPORT_OUT`。

## 文件

| 文件 | LOD | 大小 | 说明 |
|---|---|---|---|
| `m4a1_sherman_hero.glb` | hero | ~1.4 MB | 146 节独立履带板 + 18 个轮子 + 静态车体/炮塔/炮管；`Drive` 循环 + `Fire` 后坐 |
| `m4a1_sherman_troop.glb` | troop | ~0.4 MB | 履带合并为左右两条、轮组合并；只有 `Fire` |
| `manifest.json` | — | — | 构建时间、Blender 版本、hash、三角面、clip/tag 契约 |

两档共用同一套节点名、材质与朝向，`src/assets/tankRig.js` 不需要分支。

## 节点契约

```
M4A1_Sherman            根节点，原点在履带接地面
├── Hull                合并后的车体（多材质 primitive）
├── AnimLink_L_00…72     hero 专用：每节履带板
├── Tire_L_0… / …_R_5    hero 专用：负重轮（含螺栓）
└── Turret_Pivot        炮塔旋转轴（rotation.y = 炮塔角）
    ├── Turret          合并后的炮塔
    └── Gun_Pivot       炮管俯仰轴（rotation.x = 俯仰）
        ├── GunBarrel / GunSleeve / GunMuzzleRing   Fire 后坐
        └── GunMuzzle   炮口空节点（FX / 子弹起点）
```

游戏里：

```js
turret.rotation.y = yaw;
gun.rotation.x = pitch;
muzzle.getWorldPosition(spawnPos);
```

## 动画

| Clip | 长度 | 内容 |
|---|---|---|
| `Drive` | 12.1667 s | 履带 73 节按 4 帧/节循环；轮子转整圈；无缝循环 |
| `Fire` | 0.7083 s | 炮管三件套 + 炮口节点沿炮轴后坐 0.26 m 再回位 |

演示 blend 里的车体位移、炮塔转角、炮口闪光**没有**导出：位置由规则决定，炮塔角
由鼠标决定，炮口焰由 `view/fx.js` 在 `GunMuzzle` 位置生成。导出脚本会把源文件里
位于炮尾的 `GunMuzzle` 空节点移到炮口（local y = -3.025），并让它跟随 `Fire` 后坐。

## 规格

- 源单位：米；游戏统一 `scale = 0.22`（车长约 1.53 m，宽约 0.55，高约 0.76）。
- 朝向：glTF **+Z 车头，+Y 向上**。
- 材质：`Sherman_Olive / OliveDark / Metal / Rubber / Track / TrackLight / Glass / Star`。
- 无贴图、无外部 bin；GLB 自包含。
- 三角面约 10,866，hero 节点约 203 个。

## 来源与许可

模型由项目内的 `tools/blender/build_sherman.py` 按参考照片程序化重建，动画由
`tools/blender/animate_sherman.py` 生成；源文件与导出脚本都在本项目内。
