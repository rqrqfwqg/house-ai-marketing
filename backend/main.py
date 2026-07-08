"""
FastAPI应用入口
负责：应用初始化、CORS配置、路由注册、全局异常处理、lifespan管理
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from config import settings
from database import create_tables, engine
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时：创建数据库表
    关闭时：清理资源
    """
    logger.info("应用启动中...")
    await create_tables()
    logger.info("数据库表创建/检查完成")

    # 迁移：为 scripts 表添加 highlights 列（如果不存在）
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE scripts ADD COLUMN highlights TEXT"))
            logger.info("迁移成功：scripts 表添加 highlights 列")
        except Exception:
            pass  # 列已存在，忽略

    # 迁移：为 houses 表添加 highlights 列（如果不存在）
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE houses ADD COLUMN highlights TEXT"))
            logger.info("迁移成功：houses 表添加 highlights 列")
        except Exception:
            pass  # 列已存在，忽略

    # 迁移：为 publish_logs 表添加 wechat_account_id 列（如果不存在）
    async with engine.begin() as conn:
        try:
            await conn.execute(
                text(
                    "ALTER TABLE publish_logs "
                    "ADD COLUMN wechat_account_id INTEGER REFERENCES wechat_accounts(id) ON DELETE SET NULL"
                )
            )
            logger.info("迁移成功：publish_logs 表添加 wechat_account_id 列")
        except Exception:
            pass  # 列已存在，忽略

    # 种子：从 .env 导入首个默认公众号账号（幂等，仅当表为空且配置了 .env 凭证时）
    try:
        from routes.wechat_account import seed_wechat_accounts_from_env
        await seed_wechat_accounts_from_env()
    except Exception as e:
        logger.error(f"种子账号初始化失败：{e}")

    yield
    logger.info("应用关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title="房屋租赁AI营销系统",
    description="AI驱动的房源文案生成与多平台发布系统",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    default_response_class=JSONResponse,
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # 从环境变量读取，默认 http://localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    捕获所有未处理的异常，返回统一格式的错误响应
    """
    logger.error(f"全局异常: {request.method} {request.url} - {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )


@app.get("/api/v1/health", tags=["系统"])
async def health_check():
    """
    健康检查接口
    用于前端检测后端服务是否正常运行
    """
    return {"status": "ok", "message": "房屋租赁AI营销系统运行正常"}


# 注册路由
from routes import house, script, publish, history, wechat_account
app.include_router(house.router, prefix="/api/v1")
app.include_router(script.router, prefix="/api/v1")
app.include_router(publish.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(wechat_account.router, prefix="/api/v1")

# 静态文件服务（用于访问上传的图片）—— 命名空间到 /house-ai/uploads，避免与同机其它系统冲突
from fastapi.staticfiles import StaticFiles
import os
upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
if os.path.exists(upload_dir):
    app.mount("/house-ai/uploads", StaticFiles(directory=upload_dir), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.BACKEND_PORT,  # 默认 8899
        reload=True,
        log_level="info",
    )
