#!/usr/bin/env bash
# 启动一个仅绑定 127.0.0.1 的 Chrome 远程调试实例（端口 9222）
# 用途：house-ai 发布/代理调试（小红书、微信等需要浏览器上下文的场景）
#
# ⚠️ 安全：9222 仅绑本机，绝不暴露到公网。
# 外部访问请走 SSH 端口转发，不要直接开放该端口：
#   ssh -L 9222:127.0.0.1:9222 user@your-server
set -e
CHROME_BIN="${CHROME_BIN:-google-chrome}"
USER_DATA_DIR="${HOME}/.house-ai-chrome-debug"
mkdir -p "$USER_DATA_DIR"
exec "$CHROME_BIN" \
  --headless=new \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run --no-default-browser-check \
  --disable-gpu --disable-dev-shm-usage
