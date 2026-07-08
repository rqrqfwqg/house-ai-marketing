#!/usr/bin/env bash
# house-ai 后端手动启动脚本（非 systemd 场景）
# 仅绑定 127.0.0.1:8000，由 nginx 反代对外
set -e
cd "$(dirname "$0")/../backend"

if [ -x venv/bin/uvicorn ]; then
  exec venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --no-reload
else
  exec python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-reload
fi
