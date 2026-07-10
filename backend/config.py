"""
配置管理模块
使用pydantic-settings从环境变量加载配置，所有配置项都有默认值
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv


# 强制从 .env 文件加载配置，并覆盖系统环境变量
# 解决 pydantic-settings 默认优先级：系统环境变量 > .env 文件 的问题
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class Settings(BaseSettings):
    """
    应用配置类
    所有配置项都从环境变量读取，支持 .env 文件
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # 环境变量不区分大小写
    )
    
    # ========== 应用基础配置 ==========
    APP_NAME: str = "房屋租赁AI营销系统"
    BACKEND_PORT: int = 8899  # 后端端口（统一使用8899，不再用8000）
    FRONTEND_URL: str = "http://localhost:3000"  # 前端URL（用于CORS）
    
    # ========== DeepSeek API配置 ==========
    DEEPSEEK_API_KEY: str = ""  # DeepSeek API密钥（必填）
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"  # DeepSeek API地址
    DEEPSEEK_MODEL: str = "deepseek-chat"  # 使用的模型
    
    # ========== 小红书MCP配置 ==========
    XHS_MCP_URL: str = "http://localhost:18060"  # xiaohongshu-mcp服务地址
    
    # ========== 微信公众号配置 ==========
    WECHAT_APPID: str = ""  # 微信公众号AppID（可选，V1只创建草稿）
    WECHAT_APPSECRET: str = ""  # 微信公众号AppSecret（可选，作为多账号兜底/种子来源）

    # ========== 安全加密配置 ==========
    # AppSecret 对称加密密钥（Fernet，44 字符 urlsafe base64）。
    # 为空则回退 backend/.encryption_key（首次运行自动生成并 chmod 600，已加入 .gitignore）。
    # 生成命令：python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""
    
    # ========== 文件存储配置 ==========
    UPLOAD_DIR: str = "./uploads"  # 图片上传目录
    IMAGE_RETENTION_DAYS: int = 7  # 图片保留天数（超过自动清理）
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 单张图片最大10MB
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/webp"]  # 允许的图片格式

    # 上传房源照片在落盘前统一压缩的目标上限（500KB）。
    # 先按 MAX_IMAGE_SIZE(10MB) 拦截超大文件，再在此处无损判断 + 有损压缩到 500KB 以内，
    # 避免磁盘堆积大图、并兼顾前端加载与微信等下游平台的尺寸约束。
    UPLOAD_IMAGE_MAX_BYTES: int = 500 * 1024  # 上传图片落盘前压缩目标（500KB）
    
    # ========== 数据库配置 ==========
    DATABASE_URL: str = "sqlite+aiosqlite:///./house_ai.db"  # SQLite数据库路径
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = "INFO"  # 日志级别
    LOG_DIR: str = "./logs"  # 日志目录
    
    # ========== AI文案生成配置 ==========
    AI_MAX_TOKENS: int = 2000  # AI生成最大token数
    AI_TEMPERATURE: float = 0.7  # AI生成温度参数
    
    # ========== 系统配置 ==========
    DEBUG: bool = False  # 调试模式
    API_BEARER_TOKEN: str = ""  # API Bearer Token认证（可选）


# 创建全局配置实例
settings = Settings()

"""
使用说明：
1. 在 backend/.env 文件中配置环境变量
2. 必填项：DEEPSEEK_API_KEY
3. 可选项：WECHAT_APPID, WECHAT_APPSECRET（如需微信公众号草稿功能）
4. 其他配置都有合理的默认值，可直接使用

示例 .env 文件内容：
---
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
XHS_MCP_URL=http://localhost:18060
WECHAT_APPID=xxxxxxxxxxxxx
WECHAT_APPSECRET=xxxxxxxxxxxxx
BACKEND_PORT=8899
FRONTEND_URL=http://localhost:3000
UPLOAD_DIR=./uploads
IMAGE_RETENTION_DAYS=7
DEBUG=True
---
"""
