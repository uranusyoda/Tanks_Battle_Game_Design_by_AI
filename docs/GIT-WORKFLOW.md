# Git 与 GitHub 同步指南

> 仓库：<https://github.com/uranusyoda/Tanks_Battle_Game_Design_by_AI>
> 在线可玩：<https://uranusyoda.github.io/Tanks_Battle_Game_Design_by_AI/>
> 本文档覆盖：首次认证 → 分支模型 → 日常同步 → 自动化 → 出错怎么办。

---

## 0. 一分钟速查

| 我想…… | 做什么 |
|---|---|
| 把改动推到 GitHub | `./tools/git-sync.sh "feat: 改了什么"` |
| 双击就能同步 | 打开 Finder 双击 `同步到GitHub.command` |
| 边做边自动同步 | `./tools/git-sync.sh --watch`（Ctrl-C 停） |
| 开一个新功能分支 | `git switch dev && git switch -c feat/功能名` |
| 看 CI 结果 | `gh run list --limit 5` |
| 发布一个版本 | `git tag -a v3.1 -m "v3.1" && git push origin v3.1` |
| 出错怎么办 | 本文第 7、8、9 节 |

---

## 1. 首次认证（只做一次）

现在这台机器上还没有任何 GitHub 凭据：没有 `gh`、没有 SSH key、钥匙串里也没有 GitHub 密码。
三种方式选一种即可。

### 方式 A：GitHub CLI（推荐）

一条命令搞定登录和凭据存储，后面还能用来开 Pages、看 CI：

```bash
brew install gh          # 约 1 分钟
gh auth login            # GitHub.com → HTTPS → Login with a web browser
```

浏览器里输入终端显示的 8 位一次性代码即可。登录后执行一次：

```bash
gh auth setup-git        # 让 git 自动用 gh 的凭据
```

验证：`gh auth status` 显示 `Logged in to github.com as uranusyoda`。

### 方式 B：HTTPS + 个人访问令牌（PAT）

1. GitHub → Settings → Developer settings → **Personal access tokens → Fine-grained tokens**
2. Repository access 选 `Tanks_Battle_Game_Design_by_AI`，权限给 **Contents: Read and write**（想改 Pages 再加 Pages: Read and write）
3. 复制生成的 `github_pat_...`，然后：

```bash
git config --global credential.helper osxkeychain
git push -u origin main      # 用户名填 uranusyoda，密码粘贴 token
```

macOS 钥匙串会记住，之后 `git push` 不再询问。

### 方式 C：SSH 密钥

```bash
ssh-keygen -t ed25519 -C "uranusyoda@github" -f ~/.ssh/id_ed25519 -N ""
pbcopy < ~/.ssh/id_ed25519.pub
# 粘贴到 GitHub → Settings → SSH and GPG keys → New SSH key
git remote set-url origin git@github.com:uranusyoda/Tanks_Battle_Game_Design_by_AI.git
ssh -T git@github.com        # 出现 "Hi uranusyoda!" 即成功
```

### 验证连通

```bash
git ls-remote origin | head -3     # 能列出分支就通了
```

### 提交身份

仓库已配好本地的提交身份，不需要改全局配置：

```bash
git config user.name    # uranusyoda
git config user.email   # 205267522+uranusyoda@users.noreply.github.com
```

用 GitHub 的 noreply 邮箱可以让提交正确归属到你主页，同时不暴露真实邮箱。

---

## 2. 分支模型

```
main   ──●────●──────────────●────●──▶  稳定，随时可发布（Pages 从这里部署）
          \                /    ↑
dev        ●──●──●──●──●──●     │       日常开发，功能都先到这里
              \     /           │
feat/xxx       ●───●            │       单个功能，做完合回 dev
                                │
hotfix/xxx  ────────────────────●       线上紧急修复，修完合回 main 再同步 dev
```

| 分支 | 用途 | 谁能直接 push | 合并方向 |
|---|---|---|---|
| `main` | 可发布版本，触发在线部署 | 允许（仅禁止强推和删除） | `dev` → `main` |
| `dev` | 日常集成分支 | 允许 | `feat/*` → `dev` |
| `feat/*` | 单个功能或试验 | 允许 | 完成后合回 `dev` |
| `hotfix/*` | 线上紧急修复 | 允许 | 修完 → `main`，再 `main` → `dev` |

命名约定：

```
feat/shield-skill        新功能
fix/cursor-aim           修 bug
docs/update-index        只改文档
refactor/split-view      重构
test/add-rules-case      补测试
```

单人开发时 `main` / `dev` 可以直接 push；有协作者时建议在 GitHub 上开启 PR 评审后再合并。

---

## 3. 日常同步：三种方式

### 方式 1：一条命令（最常用）

```bash
./tools/git-sync.sh                       # 自动生成提交信息
./tools/git-sync.sh "feat: 新增护盾技能"   # 自己写提交信息
./tools/git-sync.sh --dry-run             # 先看会做什么，不动仓库
```

它做四件事：`git fetch` 拉远端 → 有改动就提交 → 落后就 `pull --rebase` → 领先就 `push`。
推送目标是**当前所在分支**，所以在 `dev` 上运行就推 `dev`。

### 方式 2：双击 `.command`

Finder 里双击 `同步到GitHub.command`，终端会跑一次同步并在结束时停住显示结果。

### 方式 3：自动同步（边写边推）

```bash
./tools/git-sync.sh --watch        # 每 20 秒检查一次
./tools/git-sync.sh --watch 60     # 每 60 秒检查一次
```

- 检测到改动就自动提交并推送；远端有新提交也会自动变基拉取。
- 一直跑到 `Ctrl-C`。想让它长期在后台跑：

```bash
nohup ./tools/git-sync.sh --watch > logs-sync.txt 2>&1 &
```

- 建议在 `dev` 分支开着它，`main` 只在发布时手动合。
- 它不会在 merge/rebase 未完成时动手，也不会提交超过 50MB 的文件。

### 方式 4：纯手动 Git

```bash
git add -A
git commit -m "feat: xxx"
git pull --rebase
git push
```

---

## 4. 一次完整的功能开发流程

```bash
# 1) 从 dev 开分支
git switch dev
git pull --rebase
git switch -c feat/shield-skill

# 2) 写代码，随手本地验证
cd versions/v3 && npm start     # http://127.0.0.1:4174/
npm test                        # 14 项
cd ../..

# 3) 提交并推送这个分支
./tools/git-sync.sh "feat: 护盾技能吸收一次伤害"

# 4) 合回 dev
git switch dev
git merge --no-ff feat/shield-skill -m "merge: 护盾技能"
git push
git branch -d feat/shield-skill

# 5) 确认 dev 稳定后发布到 main
git switch main
git merge --ff-only dev
git push                      # 自动触发 GitHub Pages 在线更新
```

---

## 5. 提交信息规范

格式：`类型(范围): 中文描述`，类型用 Conventional Commits。

| 类型 | 含义 | 例子 |
|---|---|---|
| `feat` | 新功能 | `feat(skill): 新增护盾技能` |
| `fix` | 修 bug | `fix(aim): 修复鼠标瞄准偏移` |
| `docs` | 只改文档 | `docs: 补充 Git 工作流说明` |
| `refactor` | 不改行为的重构 | `refactor(view): 拆分 world.js` |
| `test` | 测试相关 | `test: 补充道具掉落用例` |
| `perf` | 性能 | `perf(render): 合并重复 Mesh` |
| `chore` | 杂务/构建/依赖 | `chore: 更新 .gitignore` |

一次提交只做一件事；描述写"为什么"而不只是"改了什么"。

---

## 6. 自动化：CI 与在线部署

三个工作流在 `.github/workflows/` 下，推送到 GitHub 后自动生效：

| 文件 | 触发 | 做什么 |
|---|---|---|
| `ci.yml` | push 到 `main`/`dev`、PR | 跑 v3 的 14 项测试；校验静态站必需文件与相对路径；扫描密钥 |
| `deploy-pages.yml` | push 到 `main` 且改动 `versions/v3/` | 把 `versions/v3` 发布到 GitHub Pages |

在线地址：<https://uranusyoda.github.io/Tanks_Battle_Game_Design_by_AI/>

首次需要在仓库 Settings → Pages → Source 选 **GitHub Actions**；
执行一次 `tools/setup-github.sh` 可以自动完成（含仓库简介、topics、main 分支保护）。

查看运行结果：

```bash
gh run list --limit 5
gh run watch               # 实时跟随最近一次
gh run view --log-failed   # 只看失败日志
```

> 免费账号的 Actions 分钟数对公开仓库不限量；私有仓库每月 2000 分钟，本项目每次 CI 约 20 秒，够用。

---

## 7. 冲突怎么处理

`git-sync.sh` 遇到冲突会**自动中止**，不会留下半截状态。手动解：

```bash
git pull --rebase origin dev
# 打开冲突文件，按 <<<<<<< 标记改成想要的结果
git add <冲突文件>
git rebase --continue
# 想放弃重来：
git rebase --abort
```

常见原因：同一文件在两台机器上改过。养成"开工先 `git pull --rebase`"的习惯能避免九成冲突。

---

## 8. 撤销与回滚

| 场景 | 命令 |
|---|---|
| 还没提交的改动，想全部丢弃 | `git restore .` |
| 交了但没推，想改提交信息 | `git commit --amend -m "新的信息"` |
| 交了但没推，想撤掉这次提交、保留改动 | `git reset --soft HEAD~1` |
| 已经推上去，想撤销 | `git revert <sha>` 然后 `git push`（安全，留痕） |
| 想回到某个发布版本 | `git switch -c 回到v3 v3.0 && git switch main` |
| 误提交了密钥 | ① 立刻去 GitHub 吊销该 token ② 用 `git filter-repo` 清历史 ③ 强推（仅此情形） |

`main` 已设为禁止强推 / 禁止删除，所以历史不会被误覆盖；要强推必须先在 GitHub 上临时解除保护。

---

## 9. 常见问题

**push 时报 `Authentication failed` / `403`**
凭据没配好。回到第 1 节；用 gh 的话执行 `gh auth setup-git`。

**push 被拒：`updates were rejected`**
远端有你的新提交。`git pull --rebase origin <分支>` 后再推，或直接再跑一次 `./tools/git-sync.sh`。

**文件超过 100MB 推不上去**
GitHub 单文件上限 100MB（>50MB 会警告）。脚本会拦下 50MB 以上的文件。
大素材放 Releases，或装 Git LFS：`brew install git-lfs && git lfs install && git lfs track "*.blend"`。

**`.DS_Store`、`.secrets/` 会被提交吗**
不会，`.gitignore` 已覆盖。`.secrets/tripo.key` 永远不会进仓库——这是刻意设计。

**换一台电脑继续做**

```bash
git clone https://github.com/uranusyoda/Tanks_Battle_Game_Design_by_AI.git
cd Tanks_Battle_Game_Design_by_AI/versions/v3 && npm start
```

**中文字子和换行**
`.gitattributes` 已统一按 LF 存储、二进制文件走原样传输，跨 macOS/Windows 协作不会出现整文件 diff。
