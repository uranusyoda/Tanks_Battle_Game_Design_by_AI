#!/usr/bin/env bash
# 一次性配置 GitHub 远端（需要先 gh auth login）
#   - 打开 GitHub Pages（构建来源 = Actions）
#   - 写入仓库简介与 topics
#   - main 分支保护：禁止强推 / 禁止删除（不影响直接 push）
#
# 用法： tools/setup-github.sh

set -uo pipefail

OWNER="uranusyoda"
REPO="Tanks_Battle_Game_Design_by_AI"
SLUG="$OWNER/$REPO"

say()  { printf '%s\n' "$*"; }
ok()   { printf '✔ %s\n' "$*"; }
warn() { printf '! %s\n' "$*"; }
err()  { printf '✘ %s\n' "$*"; }

if ! command -v gh >/dev/null 2>&1; then
  err "未找到 gh（GitHub CLI）。先安装： brew install gh && gh auth login"
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  err "gh 尚未登录。先执行： gh auth login"
  exit 1
fi

say "== 配置 $SLUG =="

# 1) Pages：先看是否已启用
if gh api "repos/$SLUG/pages" >/dev/null 2>&1; then
  ok "GitHub Pages 已启用"
else
  if gh api -X POST "repos/$SLUG/pages" -f build_type=workflow >/dev/null 2>&1; then
    ok "已启用 GitHub Pages（来源：GitHub Actions）"
  else
    warn "自动启用 Pages 失败。手动步骤：仓库 Settings → Pages → Source 选 'GitHub Actions'"
  fi
fi

# 2) 仓库简介与 topics
if gh repo edit "$SLUG" \
  --description "钢铁防线 3D · 浏览器 3D 坦克大战（Three.js，无构建步骤）+ Godot 4 移植" \
  --add-topic threejs --add-topic webgl --add-topic game --add-topic godot --add-topic tanks >/dev/null 2>&1; then
  ok "已更新仓库简介与 topics"
else
  warn "更新仓库简介失败（可忽略）"
fi

# 3) main 分支保护：只禁止强推和删除，保持直接 push 的自由
cat > /tmp/protect-main.json <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
if gh api -X PUT "repos/$SLUG/branches/main/protection" --input /tmp/protect-main.json >/dev/null 2>&1; then
  ok "main 已受保护（禁止强推 / 删除，正常 push 不受影响）"
else
  warn "分支保护设置失败（免费私有仓库或权限不足时可能不支持）"
fi
rm -f /tmp/protect-main.json

say ""
say "完成。在线可玩地址（首次部署约 1-2 分钟生效）："
say "  https://$OWNER.github.io/$REPO/"
