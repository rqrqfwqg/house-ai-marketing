"""
API路由模块
包含所有API路由的注册
"""
from fastapi import APIRouter

# 创建主路由（如果需要统一前缀）
# main_router = APIRouter(prefix="/api/v1")

# 导入各路由模块
from . import house, script, publish, history, wechat_account

__all__ = ["house", "script", "publish", "history", "wechat_account"]
