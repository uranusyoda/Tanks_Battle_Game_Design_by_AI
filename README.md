# 钢铁防线 3D（Steel Bastion 3D）

[![CI](https://github.com/uranusyoda/Tanks_Battle_Game_Design_by_AI/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/uranusyoda/Tanks_Battle_Game_Design_by_AI/actions/workflows/ci.yml)
[![Deploy](https://github.com/uranusyoda/Tanks_Battle_Game_Design_by_AI/actions/workflows/deploy-pages.yml/badge.svg?branch=main)](https://uranusyoda.github.io/Tanks_Battle_Game_Design_by_AI/)

浏览器里的 3D 坦克大战：Three.js + 原生 ES Module，无构建步骤。当前迭代版本是
**v3**（从 v2.0.0 基线复制），入口在 [`versions/v3/`](versions/v3/)。

**🎮 在线试玩：<https://uranusyoda.github.io/Tanks_Battle_Game_Design_by_AI/>**

- 完整目录、命令与文档索引：[**INDEX.md**](INDEX.md)
- Git 分支模型与同步流程：[**docs/GIT-WORKFLOW.md**](docs/GIT-WORKFLOW.md)
- 可视化版本入口：[`index.html`](index.html)

```bash
cd versions/v3
npm start            # http://127.0.0.1:4174/
npm test             # 14 项
```

## 同步到 GitHub

| 场景 | 命令 |
|---|---|
| 提交并推送当前分支 | `./tools/git-sync.sh "feat: 改了什么"` |
| 双击同步 | 双击 `同步到GitHub.command` |
| 边写边自动同步 | `./tools/git-sync.sh --watch` |
| 首次配置远端（Pages / 分支保护） | `tools/setup-github.sh`（需先 `gh auth login`） |

推送 `main` 会自动跑 CI 并把 v3 部署到在线地址。分支模型：`main`（稳定、可发布）/
`dev`（日常开发）/ `feat/*`（单个功能），详见 [docs/GIT-WORKFLOW.md](docs/GIT-WORKFLOW.md)。

| 版本 | 状态 | 入口 |
|---|---|---|
| v1 | 归档（单文件 Demo） | [`versions/v1/`](versions/v1/) · 4172 |
| v2 | 冻结基线（Sherman Edition） | [`versions/v2/`](versions/v2/) · 4173 |
| v3 | **开发中** | [`versions/v3/`](versions/v3/) · 4174 |

> 每个版本目录都是自包含的纯静态站，必须用 HTTP 服务打开，不能双击 `index.html`。
