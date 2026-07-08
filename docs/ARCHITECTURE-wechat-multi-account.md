# 微信公众号多账号配置 — 系统架构设计

> 项目：house-ai ｜ 角色：架构师 高见远（Gao）
> 关联 PRD：`docs/PRD-wechat-multi-account.md`
> 日期：2026-07-05
> 模式：**增量改造** — 不推翻现有 `WechatService`，扩展为多账号能力；单账号路径向后兼容。

---

## 0. 决策结论（主理人重点）

### Q1 — 多账号存储方案：✅ 数据库表

**结论：新增数据库表 `wechat_accounts`（`SQLAlchemy` ORM + `aiosqlite`）。**

理由：
1. 项目已用 `SQLAlchemy + aiosqlite`，新增表零额外依赖，且 `Base.metadata.create_all` 自动建表（见 `database.py`）。
2. 配置页需要增删改查 + 状态管理（启用/禁用、默认账号），数据库天然支持事务、唯一索引、外键关联 `PublishLog`，无需自研文件读写与并发锁。
3. 配置文件方案需自行实现读写安全、热加载、并发保护，且无法支撑 UI 动态管理，违背产品诉求（US-1/US-4）。

**迁移策略（种子 + 兜底双轨）：**
- **种子（Seed）**：应用启动时（`main.py` 的 `lifespan`）若 `wechat_accounts` 为空、且 `.env` 中 `WECHAT_APPID` / `WECHAT_APPSECRET` 均非空，则自动将该单账号加密后写入为首个默认账号（`is_default=true, is_active=true`）。**幂等**：表非空则跳过。
- **兜底（Fallback）**：保留 `config.py` 的 `WECHAT_APPID/WECHAT_APPSECRET`。当**数据库无默认账号**且发布未指定 `wechat_account_id` 时，回落到全局 `wechat_service` 单例（读 `.env`）。这样既兼容纯 `.env` 部署，又让 DB 账号成为优先来源。
- 旧 `.env` 单账号**不删除**，作为兜底与种子来源，避免破坏现有部署。

### Q2 — AppSecret 加密方式：✅ Fernet 对称加密

**结论：使用 `cryptography` 的 `Fernet`（AES-128-CBC + HMAC），密钥从环境变量 `ENCRYPTION_KEY` 读取。**

- **密钥读取位置**：`config.py` 新增 `ENCRYPTION_KEY: str = ""`。`crypto_utils.py` 在 `ENCRYPTION_KEY` 为空时回退到文件 `backend/.encryption_key`（首次运行自动生成并 `chmod 600`，已加入 `.gitignore`），保证零配置也能稳定解密。
- **加密/解密调用约定**：入库前 `encrypt_secret(plaintext)` → 存 `app_secret_encrypted`（密文）；调用微信 API 前 `decrypt_secret(ciphertext)` → 明文仅在内存短暂存在，绝不落库、绝不回传前端。
- **MVP 密钥轮换策略**：MVP 阶段不做自动轮换。轮换方式为运维手动：更新 `ENCRYPTION_KEY` 后运行一次性重加密脚本（遍历 `wechat_accounts` 用旧密钥解密、新密钥加密）。文档需明确：轮换期间服务不可用或短暂只读。**底线**：明文绝不落库、绝不回传前端（列表/详情接口只返回 `app_id_masked`）。

---

## 1. 实现方案与框架选型

### 1.1 核心难点
- **access_token 多账号隔离**：现有 `WechatService._access_token` 为实例级缓存，多账号会互相覆盖。→ 改为**按 `appid` 隔离**的模块级缓存（`TOKEN_CACHE: dict[appid -> (token, expires_at)]`），天然支持每账号独立刷新、且跨实例共享。
- **AppSecret 安全**：明文生命周期严格收束在后端（入库加密、调用前解密），前端零接触。
- **默认账号唯一性**：`is_default` 至多一个，需在新增/编辑事务内维护。
- **向后兼容**：现有单账号（`.env`）路径、全局单例 `wechat_service` 保留可用。

### 1.2 框架 / 库选型
| 关注点 | 选型 | 理由 |
| --- | --- | --- |
| 加密 | `cryptography`（Fernet） | 对称、易用、自带安全随机数与时间戳；无需 KMS，MVP 成本最低 |
| Web 框架 | FastAPI（沿用） | 无需变更 |
| ORM | SQLAlchemy async + aiosqlite（沿用） | 新增表 + 列迁移 |
| 前端 | Vue3 + Element Plus（沿用） | 新增配置页与下拉 |

**新增依赖**：仅 `cryptography`（其余均为现有栈）。

### 1.3 架构模式
- 后端：`路由层(routes)` → `服务层(services/WechatService)` → `加密工具(crypto_utils)` → `模型层(models)`。
- 账号 CRUD 与发布路由解耦；发布路由通过 `wechat_account_id` 解析账号后构造**按账号的 `WechatService` 实例**。
- 前端：`api/` 封装 + `types/` 类型 + 独立配置页 `WechatAccountPage.vue`。

---

## 2. 文件列表（区分新增 / 修改）

### 后端（backend/）
| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `backend/crypto_utils.py` | **新增** | Fernet 加解密工具 |
| `backend/models.py` | **修改** | 新增 `WechatAccount` 模型；`PublishLog` 增加 `wechat_account_id` 列 |
| `backend/config.py` | **修改** | 新增 `ENCRYPTION_KEY`；保留 `WECHAT_APPID/WECHAT_APPSECRET` |
| `backend/wechat_service.py` | **修改** | 构造支持 `app_id/app_secret` 入参；token 缓存改为按 appid 隔离；保留全局单例 |
| `backend/routes/wechat_account.py` | **新增** | 账号 CRUD + 测试连通 + 启动种子函数 |
| `backend/routes/__init__.py` | **修改** | 注册 `wechat_account` 路由模块 |
| `backend/routes/publish.py` | **修改** | `/publish/wechat` 支持 `wechat_account_id`，解析账号→构造服务→写日志 |
| `backend/schemas.py` | **修改** | 新增账号相关 Schema；`PublishRequest` 增加 `wechat_account_id` |
| `backend/main.py` | **修改** | 注册账号路由；`lifespan` 增加 `wechat_accounts` 种子迁移 + `publish_logs.wechat_account_id` ALTER 迁移 |

### 前端（frontend-vue/src/）
| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `src/types/index.ts` | **修改** | 新增 `WechatAccount` 系列类型；`PublishRequest` 增加 `wechat_account_id?` |
| `src/api/wechatAccount.ts` | **新增** | 账号 CRUD/列表/测试 API |
| `src/api/publish.ts` | **修改** | 发布请求类型补充 `wechat_account_id`（已随 types 调整） |
| `src/pages/WechatAccountPage.vue` | **新增** | 公众号配置页（列表 + 新增/编辑对话框） |
| `src/pages/PublishPage.vue` | **修改** | 选「微信公众号」时展示账号下拉，随请求带上 `wechat_account_id` |
| `src/router/index.ts` | **修改** | 新增 `/settings/wechat-accounts` 路由 |
| `src/App.vue` | **修改** | 增加「公众号配置」入口（导航/链接） |

### 配置 / 其他
| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `.gitignore` | **修改** | 追加 `backend/.encryption_key` |
| `.env.example` | **修改** | 追加 `ENCRYPTION_KEY` 说明 |

---

## 3. 数据结构与接口（类图见 `docs/class-diagram.mermaid`）

### 3.1 WechatAccount 模型（新增）
```python
class WechatAccount(Base):
    __tablename__ = "wechat_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="账号名称")
    app_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="AppID(wx开头)")
    app_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False, comment="AppSecret密文(Fernet)")
    remark: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="备注")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认账号(至多1个)")
    created_at / updated_at: Mapped[datetime]
```
- `masked_app_id()` → 如 `wx12****3f9a`（前4后4，中间 `*`）。
- 业务约束：`app_id` 唯一；`is_default` 至多一个（应用层维护 + 可选部分唯一索引 `WHERE is_default=1`）。

### 3.2 PublishLog 变更
- 新增 `wechat_account_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("wechat_accounts.id", ondelete="SET NULL"), nullable=True)`。
- 历史记录（小红书/旧记录）该列为 `NULL`，可区分账号维度追溯。

### 3.3 WechatService 改造签名
```python
# 模块级，按 appid 隔离 token 缓存
TOKEN_CACHE: dict[str, tuple[str, float]] = {}

class WechatService:
    def __init__(self, app_id: str = None, app_secret: str = None):
        self.appid = (app_id or settings.WECHAT_APPID or "").strip()
        self.appsecret = (app_secret or settings.WECHAT_APPSECRET or "").strip()
        # 不再持有实例级 _access_token，改读 TOKEN_CACHE[self.appid]

    async def _get_access_token(self) -> str:
        # 优先 TOKEN_CACHE[self.appid]；缺失/临期则请求并写回 TOKEN_CACHE
        ...

    async def create_draft(self, title, body, images, tags=None, highlights=None) -> dict:
        # 签名/流程不变；仅 token 来源改为按 appid 缓存
        ...

# 全局单例保留（.env 兜底路径）
wechat_service = WechatService()
```
- **向后兼容**：`WechatService()` 无参时退化为读 `.env`（原行为）。
- **多账号**：`WechatService(app_id=acc.app_id, app_secret=decrypt_secret(acc.app_secret_encrypted))` 构造按账号实例；token 天然按 appid 隔离。

### 3.4 加解密工具 `crypto_utils.py`
```python
def encrypt_secret(plaintext: str) -> str: ...   # plaintext→Fernet密文(字符串)
def decrypt_secret(ciphertext: str) -> str: ...   # 密文→明文；InvalidToken 抛 RuntimeError
```
- 密钥解析顺序：`settings.ENCRYPTION_KEY` → 回退 `backend/.encryption_key`（自动生成 + 600）。

### 3.5 CRUD 接口契约（前缀 `/api/v1`）
| 方法 | 路径 | 说明 | 请求体 | 响应 |
| --- | --- | --- | --- | --- |
| GET | `/wechat-accounts` | 列表；`?active_only=true` 仅启用 | — | `WechatAccountListResponse{items,total}` |
| POST | `/wechat-accounts` | 新增 | `WechatAccountCreate` | `WechatAccountResponse`（无明文） |
| PUT | `/wechat-accounts/{id}` | 编辑；`app_secret` 空=不修改 | `WechatAccountUpdate` | `WechatAccountResponse` |
| DELETE | `/wechat-accounts/{id}` | 删除；原默认则清空默认 | — | `SuccessResponse` |
| POST | `/wechat-accounts/{id}/test` | 测试连通(R-12 P2) | — | `{success, message}` |

**Schema（Pydantic）**
```python
class WechatAccountCreate(BaseModel):
    name: str                              # ≤50 必填
    app_id: str                            # 必填，wx 开头
    app_secret: str                        # 必填（新增）
    remark: Optional[str] = None           # ≤200
    is_active: bool = True
    is_default: bool = False

class WechatAccountUpdate(BaseModel):
    name: Optional[str]
    app_id: Optional[str]
    app_secret: Optional[str] = None       # 空=保留原值
    remark: Optional[str]
    is_active: Optional[bool]
    is_default: Optional[bool]

class WechatAccountResponse(BaseModel):
    id: int
    name: str
    app_id_masked: str                     # 脱敏，绝不返回明文 app_id / app_secret
    remark: Optional[str]
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
```
- **安全红线**：所有响应（含列表、详情）均不含 `app_secret` 与 `app_id` 明文，仅 `app_id_masked`。
- **校验**：`app_id` 必须以 `wx` 开头且长度合理；新增/编辑校验唯一性（重复返回 409/400 友好提示）。
- **默认账号维护**：设某账号 `is_default=true` 时，事务内将其余账号 `is_default` 置 `false`。
- **鉴权（R-15 P2）**：路由统一加 `verify_bearer` 依赖——`settings.API_BEARER_TOKEN` 非空时校验 `Authorization: Bearer <token>`，为空则放行。

### 3.6 发布接口变更
- `PublishRequest` 增加 `wechat_account_id: Optional[int] = None`。
- `POST /api/v1/publish/wechat` 解析逻辑：
  1. 传 `wechat_account_id` → 查账号；不存在 404，存在但 `is_active=false` → 400「该账号已禁用」。
  2. 未传 → 取 `is_default=true` 账号；为空 → 回落 `wechat_service` 单例（`.env`）。
  3. 均不可用 → 400「未配置可用的公众号账号」。
  4. 构造 `WechatService(app_id, decrypt_secret(...))` → `create_draft(...)`；写 `PublishLog(wechat_account_id=...)`。
- 返回结构不变（`PublishResponse`）。

---

## 4. 程序调用流程（时序图见 `docs/sequence-diagram.mermaid`）

### 4.1 配置页增删改查
- 新增：`FE → POST /wechat-accounts → 校验 → encrypt_secret → 入库（维护默认唯一）→ 返回脱敏响应`。
- 列表：`FE → GET /wechat-accounts → 返回 app_id_masked 列表`。
- 编辑/删除：更新密文（空则保留）、维护默认标记、级联清空。

### 4.2 启动种子迁移（lifespan）
`main.py` 启动：`create_tables()` → `seed_wechat_accounts_from_env()`（表空且 `.env` 有凭证则加密写入默认账号）→ 其余 ALTER 迁移。

### 4.3 发布选号调 draft/add
`FE 拉取 active 账号 → 选号随 POST /publish/wechat 提交 → 后端解析账号 → decrypt_secret → WechatService(按账号) → token/add_material/uploadimg/draft/add → 写 PublishLog(wechat_account_id) → 返回`。

---

## 5. 任务列表（有序 + 依赖，工程师直接依据）

> 按实现顺序排列；依赖指"本任务开始前应已完成"的前置任务。

| 任务 | 名称 | 源文件（新增/修改） | 依赖 | 优先级 | 做什么 |
| --- | --- | --- | --- | --- | --- |
| **T1** | 基础设施与加密模块 | `backend/config.py`(改)、`backend/crypto_utils.py`(新)、`.gitignore`(改)、`.env.example`(改) | 无 | P0 | `config.py` 增 `ENCRYPTION_KEY`；新建 `crypto_utils.py`（`encrypt_secret`/`decrypt_secret`，密钥优先 env、回退 `.encryption_key`）；`.gitignore` 加 `backend/.encryption_key`；`.env.example` 补 `ENCRYPTION_KEY` 说明与生成命令 |
| **T2** | 数据模型与库迁移 | `backend/models.py`(改)、`backend/main.py`(改) | 无（T1 可选前置） | P0 | `models.py` 新增 `WechatAccount`；`PublishLog` 增 `wechat_account_id`(FK, nullable)；`main.py` lifespan 增加 `ALTER TABLE publish_logs ADD COLUMN wechat_account_id INTEGER`（兼容旧库） |
| **T3** | WechatService 多账号化 | `backend/wechat_service.py`(改) | 无 | P0 | 构造支持 `app_id/app_secret` 入参（无参退化为 `.env`）；`_access_token` 实例缓存改为模块级 `TOKEN_CACHE` 按 `appid` 隔离；保留全局单例 `wechat_service` |
| **T4** | 账号 CRUD 路由 + 注册 + 种子 | `backend/routes/wechat_account.py`(新)、`backend/routes/__init__.py`(改)、`backend/main.py`(改)、`backend/schemas.py`(改) | T1, T2, T3 | P0 | 新增账号路由（GET/POST/PUT/DELETE + /test）；`WechatAccountCreate/Update/Response` 等 Schema；`app_id` 校验与唯一性、`is_default` 唯一维护、响应脱敏；`verify_bearer` 鉴权（R-15）；`seed_wechat_accounts_from_env()`；`routes/__init__.py` 与 `main.py` 注册路由 |
| **T5** | 发布路由改造 | `backend/routes/publish.py`(改)、`backend/schemas.py`(改) | T2, T3 | P0 | `PublishRequest` 增 `wechat_account_id`；`create_wechat_draft` 解析账号（指定/默认/`.env` 兜底）、禁用报错、构造按账号 `WechatService`、`decrypt_secret`、写 `PublishLog.wechat_account_id` |
| **T6** | 前端 API 与类型 | `src/types/index.ts`(改)、`src/api/wechatAccount.ts`(新)、`src/api/publish.ts`(改) | 无（可与后端并行） | P0 | `types` 增 `WechatAccount/Create/Update/Response/ListResponse`，`PublishRequest` 增 `wechat_account_id?`；新增 `wechatAccount.ts`（列表/新增/编辑/删除/测试）；`publish.ts` 随类型补充 |
| **T7** | 前端配置页 | `src/pages/WechatAccountPage.vue`(新)、`src/router/index.ts`(改)、`src/App.vue`(改) | T6 | P1 | 新建配置页（el-table 列表 + el-dialog 表单：名称/AppID/AppSecret 密码框/备注/默认/启用，保存即加密入库）；路由 `/settings/wechat-accounts`；`App.vue` 增加入口链接 |
| **T8** | 前端发布页下拉 | `src/pages/PublishPage.vue`(改) | T6 | P1 | 选「微信公众号」时 `GET /wechat-accounts?active_only=true` 拉取下拉；选中值随 `POST /publish/wechat` 带 `wechat_account_id`；未选且有默认则提示默认 |

---

## 6. 依赖包列表
```
- cryptography>=42.0.0   # Fernet 对称加密 AppSecret（新增唯一依赖）
- fastapi                 # 沿用
- sqlalchemy[asyncio]     # 沿用（async + aiosqlite）
- aiosqlite               # 沿用
- pydantic / pydantic-settings  # 沿用
- loguru                  # 沿用
- httpx                   # 沿用（WechatService 已用）
前端：vue@3, element-plus, axios（均沿用，无新增）
```

---

## 7. 共享知识（跨文件约定）

- **加密密钥**：`ENCRYPTION_KEY`（Fernet 合法 key，44 字符 urlsafe base64）。生成：`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`。缺失时回退 `backend/.encryption_key`（首次自动生成，`chmod 600`，已被 gitignore）。**密钥不匹配将致 `decrypt_secret` 抛 `InvalidToken`**。
- **AppSecret 红线**：明文只在 `decrypt_secret` 调用后、传入 `WechatService` 构造时短暂存在；**绝不**写库、**绝不**出现在任何 API 响应。
- **token 缓存隔离**：`wechat_service.py` 模块级 `TOKEN_CACHE: dict[appid -> (token, expires_at)]`；刷新提前量 `TOKEN_REFRESH_AHEAD=300s`（沿用）。
- **前后端字段命名**：统一 snake_case（`app_id`、`app_secret`、`is_default`、`is_active`、`wechat_account_id`），与现有前端类型风格一致；列表/详情返回 `app_id_masked`（脱敏），不返回 `app_secret`。
- **默认账号**：至多一个 `is_default=true`；任何设置默认的操作须在事务内清除其他默认。
- **发布回落顺序**：`指定 wechat_account_id` → `is_default 账号` → `全局 wechat_service(.env)` → 否则 400。
- **账号禁用**：不进发布下拉；被显式指定发布时返回明确 400 错误。
- **鉴权**：账号配置类接口在 `API_BEARER_TOKEN` 非空时强制 Bearer 校验（R-15，P2 轻量实现）。
- **迁移兼容**：旧库通过 `main.py` lifespan 的 `ALTER TABLE` 补 `publish_logs.wechat_account_id`；`wechat_accounts` 为新表由 `create_all` 自动建。

---

## 8. 待明确事项 / 风险

1. **Q3 默认账号回落 + 记忆上次选择**：当前设计为「未指定 → 默认账号 → `.env`」。是否需要「记忆用户上次在发布页的选择」（前端 localStorage）？建议 MVP 不做，仅默认账号提示。*待主理人确认。*
2. **Q7 账号数量软上限**：PRD R-13 建议 20。当前设计未强制上限。建议 MVP 不限制（或仅前端提示），避免误伤。*待确认是否纳入。*
3. **Q8 配置页权限粒度**：R-15 接入 `API_BEARER_TOKEN` 已纳入（轻量）。是否需要更细的角色/操作审计（R-14）？MVP 暂不做审计日志。*待确认。*
4. **密钥轮换与运维**：MVP 不实现自动轮换；`.encryption_key` 回退文件需确保文件系统权限（已 `chmod 600`）且**不进版本库**（已 gitignore）。若用 env 注入密钥，需运维保证密钥持久可用，否则旧密文无法解密。*风险：密钥丢失=所有账号不可用，需重新录入。*
5. **`is_default` 并发**：多请求同时设默认，应用层维护存在竞态。MVP 单操作者场景可接受；高并发建议加部分唯一索引 + 事务。*低风险。*
6. **种子迁移与已有 `.env` 冲突**：若 DB 已有账号但 `.env` 也配了，DB 优先，`.env` 仅兜底。运营应把 `.env` 账号迁移进 DB 后清理 `.env`（可选）。*待知会运营。*
7. **R-12 测试连通**：已纳入 `POST /wechat-accounts/{id}/test`（P2），用解密后的凭证拉一次 `access_token` 验证，不泄露明文。*确认是否需在 MVP 交付。*

---

> 附：类图 `docs/class-diagram.mermaid`、时序图 `docs/sequence-diagram.mermaid`，供工程师直接引用。
