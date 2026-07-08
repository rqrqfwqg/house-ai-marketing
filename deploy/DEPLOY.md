# house-ai 服务器部署指南（子路径 /house-ai/）

本文说明如何把「房屋租赁AI营销系统」部署到与 `tools-management` 同一台服务器上，
通过**子路径 `/house-ai/`** 与原有系统区分，避免端口/路径冲突。

> 腾讯云场景（安全组/防火墙、DNSPod 解析、免费 SSL 证书、TencentOS 系统初始化）请见 **第九章**。

---

## 一、端口规划与适配说明

| 端口 | 服务 | 本系统适配 |
|------|------|-----------|
| 22 | SSH | 不动 |
| 80 / 443 | HTTP / HTTPS 前端 | **复用**：house-ai 前端挂在 `/house-ai/` 子路径，与 tools-management 同域共存 |
| 3000 | tools-management 的 Node API | 不动（house-ai 后端是 Python，另占 8000） |
| **8000** | **house-ai 后端 (FastAPI)** | **新建**：仅绑定 `127.0.0.1`，由 nginx 反代 |
| 9222 | Chrome DevTools（代理调试） | 仅绑 `127.0.0.1`，外部走 SSH 隧道 |
| 31059 | 无关 Node 服务 | **不碰** |
| 53 | 系统 DNS | **不绑**：任何服务都不要占用 53，内部解析走系统 resolver |

> 关键：house-ai 后端**不监听公网**，只接受来自本机 nginx 的转发；对外只暴露 80/443。
> 腾讯云安全组/防火墙的端口放行清单见 **第九章第二节**。

---

## 二、部署路径约定

下文以 `/opt/house-ai` 为部署根目录（请按实际替换）：

```
/opt/house-ai/
├── backend/          # FastAPI 后端（含 venv、.env）
└── frontend-vue/
    └── dist/         # 前端构建产物（vite build 生成）
```

---

## 三、后端

### 1. 依赖与虚拟环境
```bash
cd /opt/house-ai/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 `.env`
复制 `backend/.env.example` 为 `.env`，至少填写：
```ini
# 微信多账号（草稿箱需已认证订阅号/服务号）
WECHAT_APPID=wxxxxxxxxx
WECHAT_APPSECRET=xxxxxxxx
# Fernet 密钥（可选；留空则首次启动自动生成 backend/.encryption_key）
ENCRYPTION_KEY=
# CORS：填前端对外地址（同域可留默认）
FRONTEND_URL=https://your-domain
# 数据库（默认 SQLite + aiosqlite，开箱即用）
# DATABASE_URL=sqlite+aiosqlite:///./house_ai.db
```
> 首次启动会在 `backend/` 生成 `.encryption_key`（已 gitignore），AppSecret 用它加密入库。

### 3. 启动
- systemd（推荐）：
  ```bash
  cp deploy/house-ai.service /etc/systemd/system/
  # 按需修改 service 里的 User/路径
  systemctl daemon-reload
  systemctl enable --now house-ai
  ```
- 或手动：`bash deploy/start-backend.sh`

后端监听 `127.0.0.1:8000`。验证：`curl 127.0.0.1:8000/api/v1/health`。

> 腾讯云 TencentOS 场景：建议用专用低权限用户 `houseai` 运行（与 `deploy/tencent-setup.sh`
> 初始化脚本创建的用户一致），并参考 **第九章第五节** 做系统初始化。

---

## 四、前端

```bash
cd /opt/house-ai/frontend-vue
npm install
# 用 .env.production 里的 VITE_BASE=/house-ai/ 与 VITE_API_BASE=/house-ai/api/v1 构建
npm run build
# 产物在 dist/，由 nginx 静态托管
```

> 构建时 `base` 自动变为 `/house-ai/`，所有资源走 `/house-ai/assets/...`；
> API 基址为 `/house-ai/api/v1`，nginx 会剥离 `/house-ai` 前缀转发到后端 `/api/v1`。

---

## 五、nginx

1. 把 `deploy/nginx-house-ai.conf` 的 location 块**粘贴进 tools-management 所在的 80/443 `server { }` 内**，
   或将整文件 `include` 进去（注意 `alias` 路径改为实际 `dist` 目录）。
2. 检查并重载：
   ```bash
   nginx -t
   systemctl reload nginx
   ```

外部访问：`https://your-domain/house-ai/`。

> 腾讯云场景见 **第九章**：
> - 若 house-ai 使用**独立子域名**（如 `house-ai.your-domain`），可直接 `include deploy/nginx-house-ai-tencent.conf`
>   这个完整的 80/443 server 块（自带 TLS 与腾讯云免费证书路径占位）。
> - 若沿用 tools-management **同域子路径**，则把 `nginx-house-ai.conf` 的 location 粘进 tools-management 现有
>   server，并在该 server 上挂证书（复用或单独申请，见第八章第 5 点）。

---

## 六、Chrome 调试实例（9222）

仅本机、用于发布/代理调试：
```bash
bash deploy/launch-chrome-debug.sh
```
外部要连调试端口，走 SSH 隧道（**不要**直接开放 9222）：
```bash
ssh -L 9222:127.0.0.1:9222 user@your-server
```

---

## 七、验证清单

- [ ] `curl https://your-domain/house-ai/api/v1/health` 返回 `{"status":"ok",...}`
- [ ] 浏览器打开 `https://your-domain/house-ai/`，页面正常、资源 200
- [ ] 发布页选「微信公众号」能拉到账号下拉（需先配凭证）
- [ ] 上传图片能正常显示（路径为 `/house-ai/uploads/...`）
- [ ] `https://your-domain/house-ai/api/docs` 返回 403（已 deny）

---

## 八、注意事项

1. **后端绝不绑 0.0.0.0**：生产用 `--host 127.0.0.1`，仅 nginx 可达。
2. **不要占用 53 / 31059**：前者是系统 DNS，后者是无关服务。
3. **防火墙**：公网只放 22/80/443；8000、9222 仅本机。腾讯云安全组/防火墙配置见第九章第二节。
4. **上传命名空间**：本系统上传挂在 `/house-ai/uploads`，与 tools-management 的 `/uploads`（如有）互不干扰。
   若你本机 tools-management 也用根 `/uploads` 且需共存，本方案已通过前缀规避冲突。
5. **证书（两种选项）**：
   - **选项 A（推荐，独立证书）**：在腾讯云 SSL 证书控制台为 house-ai 单独申请免费 DV 证书（见第九章第四节），
     部署到 `/etc/nginx/ssl/house-ai/`，由 `deploy/nginx-house-ai-tencent.conf` 或 tools-management 的 server 块引用。
   - **选项 B（复用证书）**：若 house-ai 与 tools-management 同域且共用同一张证书，可直接复用 tools-management 现有的
     80/443 证书，无需额外申请。
   > 腾讯云可单独为 house-ai 申请免费证书，并非必须复用 tools-management 的证书。

---

## 九、腾讯云部署专章

适用于把 house-ai 部署到**腾讯云**（CVM 或轻量应用服务器）的场景。本章在通用部署之上补齐：
服务器选型、安全组/防火墙、DNSPod 解析、免费 SSL 证书、TencentOS 系统初始化。

> 所有示例中的 `your-domain` 均为占位，请替换为你的真实域名；本章不写入任何真实密钥/证书内容。

### 9.1 服务器选型

| 类型 | 适用 | 防火墙形态 | 备注 |
|------|------|-----------|------|
| 腾讯云 CVM | 通用/生产 | **安全组**（控制台配置） | 系统可选 TencentOS Server 或 Ubuntu 22.04 |
| 轻量应用服务器 | 轻量/起步 | **防火墙**（控制台配置） | 入口同样只放 22/80/443 |

两者均自带 `systemd` 与 `python3`，部署步骤一致；区别仅在**云控制台侧**的入站规则叫"安全组"还是"防火墙"。

### 9.2 安全组 / 防火墙放行清单

**原则**：对外只放 `22 / 80 / 443`；内部 `8000`（后端）、`9222`（Chrome 调试）仅绑 `127.0.0.1`，**不需要**对外放行；
**绝不**对外开放 `53 / 31059 / 3000`。

腾讯云控制台路径：
- **CVM**：云服务器控制台 → 实例 → 「安全组」→ 入站规则 → 添加规则（协议端口：`TCP:22/80/443`，来源：`0.0.0.0/0`）。
- **轻量应用服务器**：轻量控制台 → 实例 → 「防火墙」→ 添加规则（应用类型选 `HTTPS`/`HTTP`/`SSH`，或自定义 TCP 端口 `443/80/22`）。

| 协议:端口 | 策略 | 说明 |
|-----------|------|------|
| TCP 22 | 允许 | SSH 管理 |
| TCP 80 | 允许 | HTTP（强制跳 HTTPS） |
| TCP 443 | 允许 | HTTPS 前端 |
| TCP 8000 | 拒绝/不开放 | 仅本机，由 nginx 反代，勿放公网 |
| TCP 9222 | 拒绝/不开放 | 仅本机 + SSH 隧道 |
| TCP 53 / 3000 / 31059 | 拒绝 | 系统 DNS / 无关服务，绝不开放 |

> 同时确认系统内部防火墙（firewalld / ufw）也只放 22/80/443；`deploy/tencent-setup.sh` 会自动处理。

### 9.3 DNSPod 解析

在**腾讯云 DNSPod**（dnspod.cloud.tencent.com）为域名添加解析，按 house-ai 的访问方式二选一：

- **方式一（同域子路径 `/house-ai`，与 tools-management 同域）**：
  若 `your-domain` 已有 A 记录指向本机公网 IP，则**无需新增**解析，house-ai 复用该 A 记录，
  仅通过 `/house-ai/` 子路径区分。
- **方式二（独立子域名，如 `house-ai.your-domain`）**：
  新增一条 **A 记录**：主机记录 `house-ai`，记录值 = 服务器**公网 IP**，TTL 默认。
  此时 nginx 用独立 server 块（见 9.6 与 `deploy/nginx-house-ai-tencent.conf`），`server_name house-ai.your-domain;`。

> 证书与 server_name 必须和 DNSPod 解析的域名一致，否则浏览器会报证书不匹配。

### 9.4 腾讯云免费 SSL 证书

1. 进入**腾讯云 SSL 证书控制台**（console.cloud.tencent.com/ssl）→「我的证书」→「申请免费证书」。
2. 证书品牌选 **TrustAsia 免费 DV**，填写域名（同域场景填 `your-domain`；独立子域名填 `house-ai.your-domain`）。
3. 按提示完成 DNS 验证（在 DNSPod 加一条 `_dnsauth` TXT 记录）。
4. 签发后「下载」→ 选择 **Nginx** 格式（得到 `xxx.pem` + `xxx.key`，通常打包为 `fullchain.pem` 与 `privkey.pem`）。
5. 上传到服务器目录（建议 `/etc/nginx/ssl/house-ai/`，该目录由 `tencent-setup.sh` 预创建）：
   ```
   /etc/nginx/ssl/house-ai/
   ├── fullchain.pem     # 证书（含中间证书）
   └── privkey.pem       # 私钥
   ```
6. 设好权限，确保 nginx 运行用户（及 house-ai 后端用户 `houseai`，若需读取）可读取：
   ```bash
   chmod 644 /etc/nginx/ssl/house-ai/*.pem
   chmod 755 /etc/nginx/ssl/house-ai
   ```
   > 证书由**你在腾讯云控制台申请+下载**，脚本不代办；请勿把私钥提交到 git。

### 9.5 TencentOS 系统初始化

在 TencentOS Server（或 Ubuntu 22.04）上一键初始化：`sudo bash deploy/tencent-setup.sh`
脚本会（幂等、不写密钥）：
1. 检测系统（TencentOS 用 `dnf`/`yum`，Ubuntu 用 `apt`）并安装 `nginx`；
2. 创建专用低权限用户 `houseai`；
3. 创建 `/opt/house-ai/{backend,frontend-vue/dist}` 目录结构；
4. 初始化 `python3` 虚拟环境（`/opt/house-ai/backend/venv`），**不装业务依赖**——
   传代码后请 `source venv/bin/activate && pip install -r requirements.txt`；
5. 设置目录属主为 `houseai`；
6. 放行系统防火墙 `22/80/443`（检测到 firewalld/ufw 时）；
7. 预创建 `/etc/nginx/ssl/house-ai/` 目录并提示证书权限（不下载证书）。

> 手动等效命令（节选）：
> ```bash
> # TencentOS
> sudo dnf install -y nginx
> sudo useradd -r -s /sbin/nologin -d /opt/house-ai houseai
> sudo mkdir -p /opt/house-ai/backend /opt/house-ai/frontend-vue/dist
> sudo python3 -m venv /opt/house-ai/backend/venv
> sudo chown -R houseai:houseai /opt/house-ai
> sudo mkdir -p /etc/nginx/ssl/house-ai && sudo chmod 755 /etc/nginx/ssl/house-ai
> ```

### 9.6 证书在 nginx 中的位置

`deploy/nginx-house-ai-tencent.conf` 是一份**完整的 80/443 server 块范例**，可直接 `include`：
- `listen 80` → 301 跳 `https`；
- `listen 443 ssl`，`ssl_certificate` / `ssl_certificate_key` 指向占位
  `/etc/nginx/ssl/house-ai/fullchain.pem`、`/etc/nginx/ssl/house-ai/privkey.pem`；
- TLS 加固：`TLSv1.2`/`TLSv1.3` + 强 cipher + `HSTS`；
- 通过 `include /opt/house-ai/deploy/nginx-house-ai.conf;` 复用既有 location（API 反代 / uploads / 前端 SPA / deny docs）。

使用方式（二选一，与 9.3 对应）：
- **独立子域名**：把本文件放进 `/etc/nginx/conf.d/`（或 `sites-enabled/`），`server_name` 设子域名，`nginx -t && systemctl reload nginx`。
- **同域子路径**：不要单独 include 本 server 块；改为把 `nginx-house-ai.conf` 的 location 粘进 tools-management 现有
  80/443 server，并在该 server 上引用 9.4 的腾讯云证书。

---

## 十、小红书 MCP 服务（必需依赖）

house-ai 后端**不直接驱动浏览器**，而是通过 HTTP 调用一个**独立的外部服务 `xiaohongshu-mcp`**
（默认地址 `http://localhost:18060`，端点 `/mcp`）来完成小红书登录二维码获取与笔记发布。
**这是小红书二维码/发布功能的硬依赖**；服务缺失时相关接口会报错，必须在同一台服务器上安装并运行它。

### 10.1 为什么是必需依赖

- `backend/services/xhs_service.py` 的 `XhsService._mcp_call()` 用 `httpx` POST 到
  `XHS_MCP_URL`（默认 `http://localhost:18060`）。
- 若 `xiaohongshu-mcp` 未安装/未启动，`/api/v1/publish/xhs-qrcode` 等接口会连不上 18060 端口。
- 自 v2 起后端已对这类**连接错误做友好包装**：返回清晰中文报错，例如
  `小红书MCP服务(xiaohongshu-mcp)未启动或不可达，请先在服务器启动该服务（默认地址 http://localhost:18060，命令：xiaohongshu-mcp --headless=true --port :18060）`，
  而不是晦涩的泛 500（`All connection attempts failed`）。

### 10.2 安装方式（任选其一）

1. **npm 全局安装（推荐）**：
   ```bash
   npm install -g xiaohongshu-mcp
   ```
   开源地址：https://github.com/xpzouying/xiaohongshu-mcp
2. **源码编译安装**：
   ```bash
   git clone https://github.com/xpzouying/xiaohongshu-mcp
   cd xiaohongshu-mcp && npm install && npm run build && npm link
   ```
3. **Docker（可选）**：参考上游仓库自行容器化，再把 `XHS_MCP_URL` 指向容器地址即可。

### 10.3 启动命令

```bash
xiaohongshu-mcp --headless=true --port :18060
```

若 `xiaohongshu-mcp` 不在 `PATH`，先 `which xiaohongshu-mcp` 拿绝对路径，改用绝对路径启动。

### 10.4 systemd 自启

`deploy/xiaohongshu-mcp.service` 已提供 systemd 单元（运行用户 `houseai`、监听 18060、
`Restart=on-failure`）。注册并自启：

```bash
cp deploy/xiaohongshu-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now xiaohongshu-mcp
```

> 该 unit 通过 `After=network.target` 启动；`house-ai.service` 用 `Wants=`（非 `Requires`）
> 关联它——MCP 没起时 house-ai 仍能启动，只是小红书功能返回上面 10.1 的清晰报错。

### 10.5 腾讯云一键脚本

`deploy/tencent-setup.sh` 在 **5.5 节**已幂等补齐该依赖：检测/安装 node+npm →
`npm install -g xiaohongshu-mcp`（已装则跳过）→ 注册并自启 `xiaohongshu-mcp.service`。
若不想开机自启，可注释掉脚本中对应 `systemctl enable --now xiaohongshu-mcp` 两行。

### 10.6 验证

```bash
# 服务状态（active 即正常）
systemctl status xiaohongshu-mcp

# 端口/健康检查（服务自带 /health，返回 200 即正常）
curl -s http://localhost:18060/health

# 接口联调：拿到清晰二维码或明确报错（非泛 500）
curl -s https://your-domain/house-ai/api/v1/publish/xhs-qrcode
```

若 `curl` 健康检查返回非 200 或连接失败，说明 MCP 服务未正常启动，请回看 10.2/10.3 排查。
