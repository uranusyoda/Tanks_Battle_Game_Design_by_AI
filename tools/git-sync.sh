#!/usr/bin/env bash
# 钢铁防线 3D · GitHub 同步脚本
#
#   tools/git-sync.sh                 # 提交当前改动并推送（自动生成提交信息）
#   tools/git-sync.sh "feat: 加护盾"   # 用自定义提交信息提交并推送
#   tools/git-sync.sh --watch         # 守护模式：每 20 秒检查一次，有改动就自动同步
#   tools/git-sync.sh --watch 60      # 同上，间隔 60 秒
#   tools/git-sync.sh --dry-run       # 只显示会做什么，不真正提交/推送
#
# 完整说明见 docs/GIT-WORKFLOW.md

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || { echo "找不到项目根目录"; exit 1; }

BRANCH=""
INTERVAL="${SYNC_INTERVAL:-20}"
WATCH=0
DRY=0
MESSAGE=""

if [ -t 1 ]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_OFF=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_OFF=""
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✔%s %s\n' "$C_OK" "$C_OFF" "$*"; }
warn() { printf '%s!%s %s\n' "$C_WARN" "$C_OFF" "$*"; }
err()  { printf '%s✘%s %s\n' "$C_ERR" "$C_OFF" "$*"; }
dim()  { printf '%s%s%s\n' "$C_DIM" "$*" "$C_OFF"; }

usage() {
  sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --watch)
      WATCH=1; shift
      if [ $# -gt 0 ] && [[ "$1" =~ ^[0-9]+$ ]]; then INTERVAL="$1"; shift; fi
      ;;
    --interval) INTERVAL="${2:-20}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) MESSAGE="${MESSAGE:+$MESSAGE }$1"; shift ;;
  esac
done

current_branch() { git symbolic-ref --short -q HEAD 2>/dev/null; }

in_progress_ops() {
  [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]
}

remote_branch_exists() {
  git rev-parse --verify --quiet "refs/remotes/origin/$1" >/dev/null 2>&1
}

ahead_count() { git rev-list --count "origin/$1..HEAD" 2>/dev/null || echo 0; }
behind_count() { git rev-list --count "HEAD..origin/$1" 2>/dev/null || echo 0; }

auto_message() {
  local stamp dirs files
  stamp="$(date '+%Y-%m-%d %H:%M:%S')"
  files="$(git diff --cached --name-only)"
  if [ -z "$files" ]; then
    files="$(git status --porcelain | cut -c4- | sed 's/^.* -> //')"
  fi
  dirs="$(printf '%s\n' "$files" | awk -F/ 'NF>1{print $1; next}{print "."}' | sort -u | paste -sd ',' - | sed 's/,/, /g')"
  if [ -n "$dirs" ]; then
    printf 'chore(sync): 自动同步 %s（%s）' "$stamp" "$dirs"
  else
    printf 'chore(sync): 自动同步 %s' "$stamp"
  fi
}

check_large_files() {
  local f size limit=$((50 * 1024 * 1024)) bad=0
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    size=$(wc -c <"$f" | tr -d ' ')
    if [ "$size" -gt "$limit" ]; then
      err "文件超过 50MB，GitHub 会拒绝推送：$f ($((size / 1024 / 1024))MB)"
      bad=1
    fi
  done < <(git diff --cached --name-only --diff-filter=ACM)
  return "$bad"
}

sync_once() {
  BRANCH="$(current_branch)"
  if [ -z "$BRANCH" ]; then
    err "当前处于 detached HEAD，先切回分支：git switch main"
    return 1
  fi
  if in_progress_ops; then
    warn "检测到进行中的 merge/rebase，先处理完再同步。"
    return 1
  fi

  # 1) 拉取远端，避免落后
  if ! git fetch --quiet origin "$BRANCH" 2>/dev/null; then
    warn "无法连接 origin（离线？），跳过本次同步。"
    return 1
  fi

  # 2) 本地有改动 → 提交
  local dirty=0
  [ -n "$(git status --porcelain)" ] && dirty=1

  if [ "$dirty" -eq 1 ] && [ "$DRY" -eq 1 ]; then
    local nmsg="${MESSAGE:-$(auto_message)}"
    dim "[dry-run] 将提交 $(git status --porcelain | wc -l | tr -d ' ') 项改动：$nmsg"
  elif [ "$dirty" -eq 1 ]; then
    git add -A
    if ! check_large_files; then
      err "已取消提交。请把大文件放到 Releases 或使用 Git LFS。"
      return 1
    fi
    if [ -z "$(git diff --cached --name-only)" ]; then
      dim "只有被忽略的改动，无需提交。"
    else
      local msg="${MESSAGE:-$(auto_message)}"
      if [ "$DRY" -eq 1 ]; then
        dim "[dry-run] 将提交 $(git diff --cached --name-only | wc -l | tr -d ' ') 个文件：$msg"
      else
        if git commit --quiet -m "$msg"; then
          ok "已提交：$msg"
        else
          err "提交失败（检查 git 用户配置）"
          return 1
        fi
      fi
    fi
  fi

  # 3) 远端有新提交 → 变基拉取
  if remote_branch_exists "$BRANCH" && [ "$(behind_count "$BRANCH")" -gt 0 ]; then
    if [ "$DRY" -eq 1 ]; then
      dim "[dry-run] 将从 origin/$BRANCH 变基拉取 $(behind_count "$BRANCH") 个提交"
    elif git pull --rebase --autostash --quiet origin "$BRANCH"; then
      ok "已拉取远端更新（rebase）"
    else
      git rebase --abort >/dev/null 2>&1
      err "拉取时发生冲突，已中止。请手动执行 git pull --rebase 解决后在运行本脚本。"
      return 1
    fi
  fi

  # 4) 本地领先 → 推送
  if ! remote_branch_exists "$BRANCH"; then
    if [ "$DRY" -eq 1 ]; then
      dim "[dry-run] 将首次推送分支 $BRANCH 到 origin"
      return 0
    fi
    if git push --quiet -u origin "$BRANCH"; then
      ok "已创建远端分支 origin/$BRANCH"
    else
      err "推送失败：检查 GitHub 认证（见 docs/GIT-WORKFLOW.md 第 1 节）"
      return 1
    fi
    return 0
  fi

  if [ "$(ahead_count "$BRANCH")" -gt 0 ]; then
    if [ "$DRY" -eq 1 ]; then
      dim "[dry-run] 将推送 $(ahead_count "$BRANCH") 个提交到 origin/$BRANCH"
    elif git push --quiet origin "$BRANCH"; then
      ok "已推送 origin/$BRANCH（$(git rev-parse --short HEAD)）"
    else
      err "推送失败：检查 GitHub 认证，或远端有他人新提交（脚本会先拉取）。"
      return 1
    fi
  else
    dim "已是最新，无需推送。"
  fi
  return 0
}

trap 'echo; dim "已停止自动同步。"; exit 0' INT TERM

if [ "$WATCH" -eq 1 ]; then
  say "== 自动同步已开启：每 ${INTERVAL} 秒检查一次，Ctrl-C 停止 =="
  dim "分支会随当前 checkout 变化；建议留在 dev 分支工作。"
  say ""
  while :; do
    sync_once
    sleep "$INTERVAL"
  done
else
  sync_once
  exit $?
fi
