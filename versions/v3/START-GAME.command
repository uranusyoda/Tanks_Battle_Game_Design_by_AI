#!/bin/bash
# 双击本文件：启动本地静态服务并打开游戏。
# 关掉终端窗口或按 Ctrl+C 即可停止服务。
cd "$(dirname "$0")" || exit 1

PORT=4174
URL="http://127.0.0.1:${PORT}/"

if lsof -nP -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "钢铁防线 3D · v3 已在运行：${URL}"
  open "${URL}"
  exit 0
fi

echo "正在启动本地服务：${URL}"
python3 -m http.server "${PORT}" >/tmp/steel-bastion-v3-server.log 2>&1 &
PID=$!
trap 'kill ${PID} 2>/dev/null' EXIT

sleep 1
open "${URL}"
echo "服务运行中。关闭此窗口或按 Ctrl+C 停止。"
wait ${PID}
