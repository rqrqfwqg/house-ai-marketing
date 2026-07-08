# house-ai 服务器部署指南（子路径 /house-ai/）

本文说明如何把「房屋租赁AI营销系统」部署到与 `tools-management` 同一台服务器上，
通过**子路径 `/house-ai/`** 与原有系统区分，避免端口/路径冲突。

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
3. **防火墙**：公网只放 22/80/443；8000、9222 仅本机。
4. **上传命名空间**：本系统上传挂在 `/house-ai/uploads`，与 tools-management 的 `/uploads`（如有）互不干扰。
   若你本机 tools-management 也用根 `/uploads` 且需共存，本方案已通过前缀规避冲突。
5. **证书**：复用 tools-management 现有的 80/443 证书即可，无需额外申请。
