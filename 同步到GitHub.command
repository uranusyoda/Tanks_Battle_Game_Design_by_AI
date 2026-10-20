#!/bin/bash
# 双击运行：把当前改动同步到 GitHub
# 也可以在终端里用： ./同步到GitHub.command "feat: 提交信息"

cd "$(dirname "$0")" || exit 1

if [ "${1:-}" = "--watch" ]; then
  exec ./tools/git-sync.sh --watch "${2:-20}"
fi

echo "== 同步「钢铁防线 3D」到 GitHub =="
echo

./tools/git-sync.sh "$@"
code=$?

echo
if [ "$code" -ne 0 ]; then
  echo "同步没有完成。常见原因："
  echo "  · 还没完成 GitHub 登录 → 见 docs/GIT-WORKFLOW.md 第 1 节"
  echo "  · 与远端冲突 → 先手动 git pull --rebase 解决"
fi

read -n 1 -s -r -p "按任意键关闭窗口…"
echo
