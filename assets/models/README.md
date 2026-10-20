# M4A1(76)W Sherman — 游戏用低模

按 `docs/assets/sherman.jpg`（铸造车体 M4A1 + 76mm 炮）程序化重建的版本，
用于《钢铁防线 3D》。旧的方块版模型仍在 Blender 场景里，未删除。

## 文件

| 文件 | 说明 |
|---|---|
| `m4a1_sherman.glb` | 游戏用导出，0.43 MB，10,386 三角面，7 个材质 |
| `m4a1_sherman.blend` | Blender 源文件（含完整层级，可直接改参数重建） |
| `../../tools/blender/build_sherman.py` | 参数化建造脚本，所有尺寸在文件顶部常量里 |
| `../../tools/blender/headless.py` | 无头重建 + 导出 + 渲染一条龙 |

重建（不需要打开 GUI）：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b -noaudio \
  --factory-startup --python tools/blender/headless.py
```

## 规格

- 尺寸：车体宽 2.51 m，全长 6.98 m（含炮管），高 3.59 m（含天线）
- 原点：车体中心投影，**履带底面 = y 0**，可直接落地
- 朝向：Blender 中车头为 -Y；glTF 导出后车头为 **+Z**（Y 轴向上）
- 材质：`Sherman_Olive / OliveDark / Metal / Rubber / Track / Glass / Star`，
  纯色 PBR（无贴图），需要细节可后续烘焙
- 未包含：LOD、碰撞体、可动履带、轮子动画 —— 需要时再加

## 节点层级（游戏里驱动炮塔/俯仰用）

```
M4A1_Sherman            根部空物体，位于地面
├── Hull_Lower / Hull_Upper     车体
├── Track_L / Track_R           履带（链节为静态网格）
├── Tire_* / Hub_* / Sprocket_* 负重轮、主动轮、诱导轮
└── Turret_Pivot              炮塔旋转轴（glTF 位置 y=1.70）
    └── Gun_Pivot             炮管俯仰轴（glTF 位置 y=0.28, z=1.05）
        └── GunMuzzle         炮口空物体（局部 z=3.03）
```

Three.js 里直接：

```js
turret.rotation.y = aimYaw;        // Turret_Pivot
gun.rotation.x = -elevation;       // Gun_Pivot
muzzle.getWorldPosition(spawnPos); // GunMuzzle
```

## 与照片的差异

车体按铸造型 M4A1 做了圆角与斜首上装甲，但**不是逐颗铆钉的历史复刻**：
悬挂按 6 对负重轮 + 3 个托带轮的 HVSS 观感简化，细节（工具箱、备用履带等）
做了取舍以控制在 1 万面以内。需要的具体特征可以按脚本里的站点表逐项调。

---

# 动画版（炮塔 / 开炮 / 行驶）

`m4a1_sherman_anim.blend` 在静态模型基础上加了 240 帧（24 fps，10 秒）的演示动画：

| 帧 | 内容 |
|---|---|
| 1 – 81 | 前进 3.3 m，炮塔从 0° 转到 53°，履带与负重轮同步滚动 |
| 81 – 100 | 停车，**第 95 帧开火**：炮管后坐 0.26 m、炮口闪光 + 闪光点光源 |
| 100 – 140 | 炮塔回正 |
| 165 – 237 | 倒车 3 m，履带反向滚动、轮子反转 |

## 结构

- `AnimLink_L_00 … _72` / `AnimLink_R_00 … _72`：每节履带板是一个独立物体，
  按 4 帧/节的节奏沿跑道循环，正反两个阶段分开打关键帧。
  原来的 `Track_L / Track_R` 静态履带被隐藏（`hide_render`），导出游戏模型时用它。
- 负重轮 / 主动轮 / 诱导轮 / 托带轮绕自身 X 轴旋转，角速度 = 行程 / 半径。
- `Turret_Pivot` 绕 Z 转，`Gun_Pivot` 不动（俯仰留给你），炮管三件套做后坐位移。
- `MuzzleFlash` + `MuzzleLight` 挂在 `Gun_Pivot` 下，只在第 95–100 帧可见。

重建动画：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b assets/models/m4a1_sherman.blend \
  --python tools/blender/animate_sherman.py
```

渲染预览（MP4 / 关键帧 PNG）：

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b assets/models/m4a1_sherman_anim.blend -a
```
