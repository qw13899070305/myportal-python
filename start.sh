#!/usr/bin/env bash
# MyPortal 启动脚本（脱离终端常驻运行）
#
# 用法：
#   ./start.sh            以稳定模式启动（不做热重载，适合长期挂着）
#   ./start.sh --reload   带热重载启动（改 backend/ 下的代码会自动重启）
#   ./stop.sh             停止
#
# 启动后：
#   - 日志写到 logs/service.log
#   - 屏幕上会打印可以从哪些内网地址访问
set -uo pipefail

cd "$(dirname "$0")"

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

# 端口占用检查
PORT="${PORT:-$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2)}"
PORT="${PORT:-8000}"
if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo "端口 ${PORT} 已被占用，先执行 ./stop.sh"
  exit 1
fi

if [ "${1:-}" = "--reload" ]; then
  echo "以热重载模式启动（只监视 backend/）"
  DEBUG=true setsid nohup "$PY" app.py >> logs/service.log 2>&1 < /dev/null &
else
  echo "以稳定模式启动（不做热重载）"
  DEBUG=false setsid nohup "$PY" app.py >> logs/service.log 2>&1 < /dev/null &
fi

disown 2>/dev/null || true
sleep 8

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo "已启动 ✓  日志：logs/service.log"
  echo
  "$PY" - <<'PYEOF'
from backend.core.network import local_urls
print("可以从以下地址访问：")
for url in local_urls(8000):
    print("   ", url)
PYEOF
else
  echo "启动失败，看看日志： tail -30 logs/service.log"
  exit 1
fi
