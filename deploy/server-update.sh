#!/usr/bin/env bash
# ============================================================
# house-ai 服务器一键更新脚本
# ------------------------------------------------------------
# 用途：在部署服务器（/opt/house-ai 所在机器）上拉取最新代码，
#       并按「本次实际变更的文件」条件化地执行：
#         - 后端依赖安装（requirements.txt 有改动时）
#         - 前端构建（frontend-vue 源码有改动时，必须做！）
#         - 重启后端 systemd 服务（始终重启一次，保证拉取的代码生效）
#         - 按需 reload nginx（nginx 配置有改动时）
#         - 按需重启 xiaohongshu-mcp（其 service 文件有改动时）
#       最后做一次后端健康检查与前端可访问性检查，并打印更新摘要。
#
# 运行方式：
#         bash deploy/server-update.sh
#   需在 /opt/house-ai 所在的服务器上、以「拥有 sudo 权限的普通用户」执行。
#   （systemctl / systemctl reload 等命令内部已用 sudo。）
#
# 设计要点：
#   - 使用 set -uo pipefail（不含 -e）：systemctl / curl 健康检查失败
#     不会整体中断脚本，由各自的分支单独判断。
#   - git pull 采用 --ff-only，遇到本地冲突或非快进更新会给出清晰中文
#     提示并退出，避免把仓库弄乱。
#   - 仅在本脚本开头对 git pull 失败使用 exit 1，其余步骤失败只告警。
# ============================================================
set -uo pipefail

# —— 可配置变量（按需修改）——
PROJECT_DIR="/opt/house-ai"          # 部署根目录（git 仓库）
SERVICE="house-ai"                   # 后端 systemd 服务名
MCP_SERVICE="xiaohongshu-mcp"        # 小红书 MCP systemd 服务名
NGINX_SERVICE="nginx"                # nginx systemd 服务名
APP_USER="houseai"                   # 运行/拥有 venv 的专用低权限用户（见 tencent-setup.sh）
VENV_DIR="$PROJECT_DIR/backend/venv" # 后端 Python 虚拟环境目录
REQ_FILE="$PROJECT_DIR/backend/requirements.txt"
FRONTEND_DIR="$PROJECT_DIR/frontend-vue"
HEALTH_URL="http://127.0.0.1:8899/api/v1/health"   # 后端健康检查端点（实际服务端口 8899）
FRONTEND_URL="https://localhost/house-ai/"         # 前端入口（localhost 证书可能自签，用 -k）
SLEEP_AFTER_RESTART=3                # 重启后端后的等待秒数

# —— 本次更新摘要所需的状态标记 ——
BACKEND_DEPS_INSTALLED=0
FRONTEND_BUILT=0
NGINX_RELOADED=0
MCP_RESTARTED=0
HEALTH_OK=0
FRONTEND_HTTP="000"
RESTARTED_LIST=""                    # 记录被重启/重载的服务

# ============================================================
# 辅助函数：判断本次变更是否影响某个模块
# 入参统一基于 CHANGED_FILES（git diff --name-only 的逐行输出）
# ============================================================

# 后端依赖 requirements.txt 是否变更
backend_req_changed() {
    echo "$CHANGED_FILES" | grep -q '^backend/requirements\.txt$'
}

# 前端源码（frontend-vue/ 下，排除 dist 构建产物）是否变更
frontend_src_changed() {
    if echo "$CHANGED_FILES" | grep -q '^frontend-vue/'; then
        # 排除 dist 子目录后，若仍有 frontend-vue/ 下的变更，则视为源码变更
        if echo "$CHANGED_FILES" | grep -v '^frontend-vue/dist/' | grep -q '^frontend-vue/'; then
            return 0
        fi
    fi
    return 1
}

# nginx 相关配置（deploy/ 下的 *.conf，或任意含 nginx 的文件）是否变更
nginx_conf_changed() {
    echo "$CHANGED_FILES" | grep -Eq '^deploy/.*\.conf$|nginx'
}

# 小红书 MCP service 文件是否变更
mcp_service_changed() {
    echo "$CHANGED_FILES" | grep -q '^deploy/xiaohongshu-mcp\.service$'
}

# ============================================================
# 辅助函数：后端依赖安装（多策略自适应）
# ============================================================
install_backend_deps() {
    if [ ! -f "$REQ_FILE" ]; then
        echo "    （未找到 $REQ_FILE，跳过安装）"
        return 0
    fi
    echo "==> 安装/更新后端依赖：pip install -r $REQ_FILE"
    if [ -w "$VENV_DIR" ]; then
        # 当前用户对 venv 有写权限：直接激活后安装
        echo "    方式：激活 venv 后 pip install"
        # shellcheck disable=SC1091
        ( source "$VENV_DIR/bin/activate" && pip install -r "$REQ_FILE" )
    elif id "$APP_USER" >/dev/null 2>&1; then
        # venv 由专用用户 houseai 拥有：用其身份执行安装（避免权限拒绝）
        echo "    方式：sudo -u $APP_USER 使用 venv 内 python 安装"
        sudo -u "$APP_USER" "$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"
    else
        # 兜底：用 sudo 直接以 venv 内 python 安装
        echo "    方式：sudo 使用 venv 内 python 安装"
        sudo "$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"
    fi
    return $?
}

# ============================================================
# 主流程
# ============================================================
echo "==> house-ai 一键更新开始"

# ---------- 0. 前置检查：部署目录存在且为 git 仓库 ----------
if [ ! -d "$PROJECT_DIR" ]; then
    echo "!! 部署目录 $PROJECT_DIR 不存在，请在目标服务器上以正确路径执行。" >&2
    exit 1
fi
cd "$PROJECT_DIR" || { echo "!! 无法进入部署目录 $PROJECT_DIR" >&2; exit 1; }

# 让 git（以 sudo 运行时）信任该仓库目录，避免 "dubious ownership" 报错
# （仓库可能由专用用户/root 拥有，普通用户直接 git 会被拒绝）
sudo git config --global --add safe.directory "$PROJECT_DIR"

if ! sudo git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "!! $PROJECT_DIR 不是 git 仓库，无法执行 git pull。" >&2
    exit 1
fi

# ---------- 1. 记录更新前状态（旧 HEAD）----------
OLD_HEAD="$(sudo git rev-parse HEAD)"
OLD_HEAD_SHORT="$(sudo git rev-parse --short HEAD)"
echo "==> 更新前 commit: $OLD_HEAD_SHORT"

# ---------- 2. git pull（仅快进）----------
echo "==> 执行 git pull --ff-only"
if ! sudo git pull --ff-only; then
    echo "!! git pull 失败：本地可能存在未提交改动或存在非快进更新（远程历史分叉）。" >&2
    echo "   请先处理本地改动（stash / commit / rebase）后，再重新执行本脚本。" >&2
    exit 1
fi

# ---------- 3. 计算本次变更文件列表 ----------
NEW_HEAD="$(sudo git rev-parse HEAD)"
NEW_HEAD_SHORT="$(sudo git rev-parse --short HEAD)"
CHANGED_FILES="$(sudo git diff --name-only "$OLD_HEAD" HEAD)"

if [ -z "$CHANGED_FILES" ]; then
    echo "==> 已是最新（$OLD_HEAD_SHORT == $NEW_HEAD_SHORT），无文件变更。"
else
    echo "==> 本次变更文件："
    echo "$CHANGED_FILES" | sed 's/^/      - /'
fi

# ---------- 4. 条件化：后端依赖安装 ----------
if backend_req_changed; then
    if install_backend_deps; then
        BACKEND_DEPS_INSTALLED=1
        echo "    ✔ 后端依赖安装/更新完成"
    else
        echo "!! 后端依赖安装失败，请检查 venv 与 $REQ_FILE。" >&2
    fi
else
    echo "==> requirements 未变，跳过安装"
fi

# ---------- 5. 条件化：前端构建（关键步骤，务必执行）----------
if frontend_src_changed; then
    echo "==> 前端源码有变更，开始构建（cd $FRONTEND_DIR && npm install && npm run build）"
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo "!! 前端目录 $FRONTEND_DIR 不存在，跳过构建。" >&2
    else
        (
            cd "$FRONTEND_DIR" || exit 1
            npm install && npm run build
        )
        if [ $? -eq 0 ]; then
            FRONTEND_BUILT=1
            echo "    ✔ 前端构建完成（产物位于 $FRONTEND_DIR/dist/，由 nginx 经 alias 静态托管）"
        else
            echo "!! 前端构建失败，请查看上方 npm 报错。" >&2
        fi
    fi
else
    echo "==> 前端未变，跳过构建"
fi

# ---------- 6. 重启后端（始终重启一次，保证拉取的代码生效）----------
echo "==> 重启后端服务：$SERVICE"
if sudo systemctl restart "$SERVICE"; then
    RESTARTED_LIST="$RESTARTED_LIST $SERVICE"
    echo "    已重启 $SERVICE，等待 ${SLEEP_AFTER_RESTART}s 让进程就绪..."
    sleep "$SLEEP_AFTER_RESTART"
else
    echo "!! 重启 $SERVICE 失败，请检查：sudo systemctl status $SERVICE" >&2
fi

# ---------- 7. 条件化：reload nginx ----------
if nginx_conf_changed; then
    echo "==> 检测到 nginx 配置变更，reload $NGINX_SERVICE"
    if sudo systemctl reload "$NGINX_SERVICE"; then
        NGINX_RELOADED=1
        RESTARTED_LIST="$RESTARTED_LIST $NGINX_SERVICE(reload)"
        echo "    ✔ $NGINX_SERVICE 已 reload"
    else
        echo "!! $NGINX_SERVICE reload 失败，建议先：sudo nginx -t 检查配置。" >&2
    fi
else
    echo "==> nginx 配置未变，跳过 reload"
fi

# ---------- 8. 条件化：重启 xiaohongshu-mcp ----------
if mcp_service_changed; then
    echo "==> 检测到 MCP service 文件变更，daemon-reload 并重启 $MCP_SERVICE"
    sudo systemctl daemon-reload
    if sudo systemctl restart "$MCP_SERVICE"; then
        MCP_RESTARTED=1
        RESTARTED_LIST="$RESTARTED_LIST $MCP_SERVICE"
        echo "    ✔ $MCP_SERVICE 已重启"
    else
        echo "!! $MCP_SERVICE 重启失败，请检查：sudo systemctl status $MCP_SERVICE" >&2
    fi
else
    echo "==> xiaohongshu-mcp service 未变，跳过其重启"
fi

# ---------- 9. 健康检查 ----------
echo "==> 后端健康检查：GET $HEALTH_URL"
HEALTH_BODY="$(curl -fsS "$HEALTH_URL" 2>/dev/null)"
HEALTH_RC=$?
if [ "$HEALTH_RC" -eq 0 ]; then
    HEALTH_OK=1
    echo "    ✔ 后端存活（HTTP 2xx）。响应: $HEALTH_BODY"
else
    echo "!! 后端健康检查失败（curl 返回 $HEALTH_RC）。请查看日志：" >&2
    echo "    sudo journalctl -u $SERVICE -n 50 --no-pager" >&2
fi

echo "==> 前端可访问性检查：GET $FRONTEND_URL（localhost 证书可能自签，已用 -k）"
FRONTEND_HTTP="$(curl -fsS -k -o /dev/null -w '%{http_code}' "$FRONTEND_URL" 2>/dev/null || echo '000')"
echo "    返回 HTTP 状态码：$FRONTEND_HTTP"

# ---------- 10. 更新摘要 ----------
echo ""
echo "============================================================"
echo " house-ai 更新摘要"
echo "============================================================"
echo " 更新前 commit : $OLD_HEAD_SHORT"
echo " 更新后 commit : $NEW_HEAD_SHORT"
echo " 后端依赖安装 : $([ "$BACKEND_DEPS_INSTALLED" -eq 1 ] && echo '是' || echo '否（未变/跳过）')"
echo " 前端构建     : $([ "$FRONTEND_BUILT" -eq 1 ] && echo '是' || echo '否（未变/跳过）')"
echo " 已重启服务   : ${RESTARTED_LIST:-（无）}"
echo " nginx reload : $([ "$NGINX_RELOADED" -eq 1 ] && echo '是' || echo '否')"
echo " MCP 重启     : $([ "$MCP_RESTARTED" -eq 1 ] && echo '是' || echo '否')"
echo " 后端健康检查 : $([ "$HEALTH_OK" -eq 1 ] && echo '通过 (OK)' || echo '失败 (告警)')"
echo " 前端可达性   : HTTP $FRONTEND_HTTP"
echo "============================================================"

# 后端健康检查失败则给出非零退出码，便于运维/CI 感知；不中断上述流程。
if [ "$HEALTH_OK" -ne 1 ]; then
    echo "!! 警告：后端健康检查未通过，请优先排查 $SERVICE 服务状态。" >&2
    exit 1
fi

echo "==> house-ai 一键更新完成。"
exit 0
