# 发布包

| 文件 | 版本 | 内容 | 入口 |
|---|---|---|---|
| `steel-bastion-sherman-v2.zip` | v2.0.0 | `versions/v2/` 的纯静态站（index/css/src/assets/vendor/preview） | `index.html` |

直接拖到 Netlify Drop，或解压到任意静态托管的站点根目录即可；无后端、无构建步骤。

## 重新打包 v2

从项目根目录执行，排除测试与文档，保持站点相对路径：

```bash
cd versions/v2
zip -r ../../releases/steel-bastion-sherman-v2.zip \
  index.html css src assets vendor preview \
  -x '*.DS_Store'
```

## 打包 v3（首个可玩版本时）

```bash
cd versions/v3
zip -r ../../releases/steel-bastion-v3.zip \
  index.html css src assets vendor \
  -x '*.DS_Store'
```

> 上传前确认 `assets/models/*.glb` 与 `manifest.json` 同步，且 `npm test` 全过。
