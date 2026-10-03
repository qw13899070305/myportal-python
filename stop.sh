#!/usr/bin/env bash
# MyPortal 停止脚本：按端口找到后端进程并优雅结束
set -uo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2)}"
PORT="${PORT:-8000}"

PIDS=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | grep -oP '(?<=pid=)\d+' | sort -u)

if [ -z "$PIDS" ]; then
  echo "端口 ${PORT} 上没有正在运行的服务"
  exit 0
fi

for pid in $PIDS; do
  echo "结束进程 $pid"
  kill "$pid" 2>/dev/null || true
done

sleep 3
if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo "还有残留，强制结束"
  for pid in $PIDS; do kill -9 "$pid" 2>/dev/null || true; done
  sleep 1
fi

ss -tln 2>/dev/null | grep -q ":${PORT} " && echo "停止失败" || echo "已停止 ✓"
