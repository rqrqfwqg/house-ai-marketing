#!/usr/bin/env bash
# ============================================================
# house-ai 腾讯云系统初始化一键脚本（幂等，可重复执行）
# 功能：检测系统 → 安装 nginx → 创建 houseai 用户 → 建目录 → 初始化 python3 venv
#       → 设属主 → 放行系统防火墙 22/80/443 → 预建 SSL 证书目录
# 不做什么：
#   - 不下载 SSL 证书（需在腾讯云控制台申请，见 DEPLOY.md 9.4）；
#   - 不安装业务依赖（传代码后请手动 pip install -r requirements.txt）；
#   - 不写入任何真实密钥、域名或证书内容。
# 用法：sudo bash deploy/tencent-setup.sh
# ============================================================
set -euo pipefail

# —— 可配置变量（均为本地路径/用户名，不含任何密钥或真实域名）——
DEPLOY_ROOT="/opt/house-ai"
APP_USER="houseai"
SSL_DIR="/etc/nginx/ssl/house-ai"

echo "==> house-ai 腾讯云初始化开始（幂等，可重复执行）"

# ---------- 1. 检测系统 ----------
detect_os() {
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

OS_ID="$(detect_os)"
echo "==> 检测到系统 ID: $OS_ID"

case "$OS_ID" in
    tencentos|centos|fedora|rhel|anolis|opencloudos)
        PKG_MGR="dnf"
        command -v dnf >/dev/null 2>&1 || PKG_MGR="yum"
        ;;
    ubuntu|debian)
        PKG_MGR="apt"
        ;;
    *)
        echo "!! 未识别的系统（$OS_ID），仅尝试通用流程，可能失败。" >&2
        PKG_MGR="unknown"
        ;;
esac

# ---------- 2. 安装 nginx ----------
if command -v nginx >/dev/null 2>&1; then
    echo "==> nginx 已安装，跳过"
else
    echo "==> 安装 nginx (PKG_MGR=$PKG_MGR)"
    case "$PKG_MGR" in
        dnf|yum)
            "$PKG_MGR" install -y nginx
            ;;
        apt)
            apt-get update
            apt-get install -y nginx
            ;;
        *)
            echo "!! 无法自动安装 nginx，请手动安装后重跑。" >&2
            exit 1
            ;;
    esac
fi

# ---------- 3. 创建专用低权限用户 houseai ----------
if id "$APP_USER" >/dev/null 2>&1; then
    echo "==> 用户 $APP_USER 已存在，跳过"
else
    echo "==> 创建用户 $APP_USER"
    useradd -r -s /sbin/nologin -d "$DEPLOY_ROOT" "$APP_USER"
fi

# ---------- 4. 创建目录结构 ----------
echo "==> 创建目录 $DEPLOY_ROOT"
mkdir -p "$DEPLOY_ROOT/backend" "$DEPLOY_ROOT/frontend-vue/dist"

# ---------- 5. 初始化 python3 虚拟环境 ----------
VENV_DIR="$DEPLOY_ROOT/backend/venv"
if [ -f "$VENV_DIR/bin/activate" ]; then
    echo "==> venv 已存在，跳过 ($VENV_DIR)"
else
    echo "==> 初始化 python3 venv: $VENV_DIR"
    # Ubuntu 需要先有 python3-venv 模块
    if [ "$PKG_MGR" = "apt" ] && ! python3 -m venv --help >/dev/null 2>&1; then
        apt-get update
        apt-get install -y python3-venv python3-pip
    fi
    python3 -m venv "$VENV_DIR"
    # 注意：此处不安装业务依赖。传代码后请执行：
    #   source "$VENV_DIR/bin/activate"
    #   pip install -r "$DEPLOY_ROOT/backend/requirements.txt"
    echo "    （已创建 venv，业务依赖请在上传代码后手动 pip install -r requirements.txt）"
fi

# ---------- 6. 设置目录属主 ----------
echo "==> 设置 $DEPLOY_ROOT 属主为 $APP_USER"
chown -R "$APP_USER:$APP_USER" "$DEPLOY_ROOT"

# ---------- 7. 放行系统防火墙 22/80/443 ----------
echo "==> 配置系统防火墙（仅放 22/80/443）"
if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=ssh   || true
    firewall-cmd --permanent --add-service=http  || true
    firewall-cmd --permanent --add-service=https || true
    firewall-cmd --reload
    echo "    已通过 firewalld 放行 ssh/http/https"
elif command -v ufw >/dev/null 2>&1; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "    已通过 ufw 放行 22/80/443"
else
    echo "    （未检测到 firewalld/ufw，跳过系统防火墙；请确认云控制台安全组/防火墙已放 22/80/443，见 DEPLOY.md 9.2）"
fi

# ---------- 8. 预建 SSL 证书目录（不下载证书） ----------
echo "==> 预建 SSL 证书目录 $SSL_DIR（证书请在腾讯云控制台申请并上传）"
mkdir -p "$SSL_DIR"
chmod 755 "$SSL_DIR"
echo "    请将腾讯云下载的 Nginx 格式证书放至此目录："
echo "      $SSL_DIR/fullchain.pem"
echo "      $SSL_DIR/privkey.pem"
echo "    并设权限：chmod 644 $SSL_DIR/*.pem"

# ---------- 收尾 ----------
echo "==> 启用并启动 nginx"
systemctl enable nginx >/dev/null 2>&1 || true
systemctl start nginx >/dev/null 2>&1 || true

echo "==> 初始化完成。"
echo "下一步："
echo "  1) 在腾讯云 DNSPod 添加解析（DEPLOY.md 9.3）"
echo "  2) 在腾讯云 SSL 控制台申请免费 DV 证书并下载 Nginx 格式，上传到 $SSL_DIR（DEPLOY.md 9.4）"
echo "  3) 上传后端/前端代码，pip install 依赖，构建前端"
echo "  4) 部署 nginx 配置（deploy/nginx-house-ai.conf 或 deploy/nginx-house-ai-tencent.conf），nginx -t && systemctl reload nginx"
echo "  5) 安装 systemd 单元：cp deploy/house-ai.service /etc/systemd/system/ && systemctl enable --now house-ai"
