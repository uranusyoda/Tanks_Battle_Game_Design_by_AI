# 钢铁防线 3D（Steel Bastion 3D）

浏览器里的 3D 坦克大战：Three.js + 原生 ES Module，无构建步骤。当前迭代版本是
**v3**（从 v2.0.0 基线复制），入口在 [`versions/v3/`](versions/v3/)。

- 完整目录、命令与文档索引：[**INDEX.md**](INDEX.md)
- 可视化版本入口：[`index.html`](index.html)

```bash
cd versions/v3
npm start            # http://127.0.0.1:4174/
npm test             # 14 项
```

| 版本 | 状态 | 入口 |
|---|---|---|
| v1 | 归档（单文件 Demo） | [`versions/v1/`](versions/v1/) · 4172 |
| v2 | 冻结基线（Sherman Edition） | [`versions/v2/`](versions/v2/) · 4173 |
| v3 | **开发中** | [`versions/v3/`](versions/v3/) · 4174 |

> 每个版本目录都是自包含的纯静态站，必须用 HTTP 服务打开，不能双击 `index.html`。
