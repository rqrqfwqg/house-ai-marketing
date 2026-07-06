"""
数据库管理模块
使用SQLAlchemy async + aiosqlite，定义异步引擎、SessionLocal、Base
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from loguru import logger

from config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # 调试模式下打印SQL语句
    future=True,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建声明式基类（所有ORM模型继承此类）
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖函数
    用于FastAPI路由中通过Depends(get_db)注入数据库会话
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库会话异常: {str(e)}")
            raise
        finally:
            await session.close()


async def create_tables():
    """
    创建所有数据库表
    在应用启动时通过lifespan调用
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表创建/检查完成")
    except Exception as e:
        logger.error(f"创建数据库表失败: {str(e)}")
        raise


async def drop_tables():
    """
    删除所有数据库表（仅用于测试/开发环境）
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("所有数据库表已删除（开发环境）")
    except Exception as e:
        logger.error(f"删除数据库表失败: {str(e)}")
        raise


async def close_db_connection():
    """
    关闭数据库连接
    在应用关闭时通过lifespan调用
    """
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {str(e)}")
        raise


# 为了在异步环境中使用SQLite，需要启用WAL模式以提高并发性能
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    设置SQLite的WAL模式（提高并发性能）
    同时启用外键约束
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
