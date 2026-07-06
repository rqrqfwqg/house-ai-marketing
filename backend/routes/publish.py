"""
发布相关路由
定义：发布到小红书、创建公众号草稿、获取发布记录、小红书登录二维码
"""
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_db
from schemas import PublishRequest, PublishResponse, PublishLogResponse, SuccessResponse
from services.xhs_service import xhs_service
from services.wechat_service import wechat_service
from models import PublishLog, Script, House
from database import AsyncSessionLocal
from config import settings

# 创建路由
router = APIRouter(
    prefix="/publish",  # ✅ 添加prefix，确保API路径正确
    tags=["发布管理"],
)


def _parse_json_field(value, default=None):
    """
    解析 JSON 字段（兼容字符串和已解析的对象）

    Args:
        value: 数据库中的值（可能是 JSON 字符串或 None）
        default: 解析失败时的默认返回值

    Returns:
        解析后的列表或默认值
    """
    if not value:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


def _resolve_image_paths(house) -> list:
    """
    从房源记录解析图片路径，将相对路径转为绝对路径

    Args:
        house: House ORM 对象

    Returns:
        图片绝对路径列表
    """
    image_paths = []
    raw_images = _parse_json_field(house.images)
    if not raw_images:
        return image_paths

    # UPLOAD_DIR 默认 ./uploads，resolve 后为绝对路径
    # 图片存储格式如 /uploads/1/xxx.jpg，需要转为绝对路径
    upload_base = Path(settings.UPLOAD_DIR).resolve()
    backend_dir = upload_base.parent  # backend 目录

    for img_path in raw_images:
        # img_path 格式如 "/uploads/1/xxx.jpg"
        rel_path = img_path.lstrip("/")
        abs_path = str(backend_dir / rel_path)
        image_paths.append(abs_path)

    return image_paths


@router.get("/xhs-qrcode", response_model=SuccessResponse)
async def get_xhs_login_qrcode():
    """
    获取小红书登录二维码

    返回：二维码图片（base64 或 URL）、有效期
    """
    try:
        logger.info("收到小红书登录二维码请求")

        result = await xhs_service.get_login_qrcode()

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "获取二维码失败"))

        return SuccessResponse(
            message="获取二维码成功",
            data={
                "qr_code": result.get("qr_code"),
                "qr_code_url": result.get("qr_code_url"),
                "expire_in": result.get("expire_in", 120),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小红书二维码失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取二维码失败：{str(e)}")


@router.get("/xhs-login-status")
async def check_xhs_login_status():
    """
    检查小红书登录状态

    返回：logged_in（bool）
    """
    try:
        result = await xhs_service.check_login_status()
        return {
            "logged_in": result.get("logged_in", False),
            "error": result.get("error"),
        }
    except Exception as e:
        logger.error(f"检查小红书登录状态失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"检查登录状态失败：{str(e)}")


@router.post("/xiaohongshu", response_model=PublishResponse)
async def publish_to_xiaohongshu(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发布文案到小红书

    - **script_id**: 文案ID
    - **images**: 图片路径列表（后端实际从房源获取）

    返回：发布结果
    """
    try:
        logger.info(f"收到小红书发布请求：script_id={request.script_id}")

        # 1. 获取文案和房源信息
        async with AsyncSessionLocal() as session:
            script = await session.get(Script, request.script_id)
            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            house = await session.get(House, script.house_id)
            if not house:
                raise HTTPException(status_code=404, detail="房源不存在")

        # 2. 解析房源图片路径，转为绝对路径
        image_paths = _resolve_image_paths(house)
        if not image_paths:
            logger.warning(f"房源 {house.id} 无图片，小红书发布可能失败")

        # 解析文案标签
        script_tags = _parse_json_field(script.tags)

        # 3. 调用小红书发布服务（通过 MCP 协议）
        result = await xhs_service.publish_note(
            title=script.title,
            body=script.body,
            images=image_paths,
            tags=script_tags,
        )

        # 4. 记录发布日志
        async with AsyncSessionLocal() as session:
            log = PublishLog(
                house_id=script.house_id,
                script_id=request.script_id,
                platform="xiaohongshu",
                status="success" if result["success"] else "failed",
                error_msg=result.get("error"),
                xhs_note_id=result.get("note_id"),
            )

            session.add(log)
            await session.commit()

        # 5. 返回结果
        return PublishResponse(
            success=result["success"],
            platform="xiaohongshu",
            note_id=result.get("note_id"),
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"小红书发布失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"发布失败：{str(e)}")


@router.post("/wechat", response_model=PublishResponse)
async def create_wechat_draft(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    创建公众号草稿（调用微信草稿箱 API）

    - **script_id**: 文案ID
    - **images**: 图片路径列表（后端实际从房源获取）

    返回：包含草稿 media_id
    """
    try:
        logger.info(f"收到公众号草稿箱创建请求：script_id={request.script_id}")

        # 1. 获取文案和房源信息
        async with AsyncSessionLocal() as session:
            script = await session.get(Script, request.script_id)
            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")

            house = await session.get(House, script.house_id)
            if not house:
                raise HTTPException(status_code=404, detail="房源不存在")

        # 2. 解析标签和亮点
        script_tags = _parse_json_field(script.tags)
        script_highlights = _parse_json_field(script.highlights)

        # 3. 解析房源图片路径，转为绝对路径（草稿箱需要至少一张封面图）
        image_paths = _resolve_image_paths(house)
        if not image_paths:
            logger.warning(f"房源 {house.id} 无图片，公众号草稿箱创建可能失败")

        # 4. 调用微信公众号服务（草稿箱 API 模式）
        result = await wechat_service.create_draft(
            title=script.title,
            body=script.body,
            images=image_paths,
            tags=script_tags,
            highlights=script_highlights,
        )

        # 5. 记录发布日志
        async with AsyncSessionLocal() as session:
            log = PublishLog(
                house_id=script.house_id,
                script_id=request.script_id,
                platform="wechat",
                status="draft_created" if result["success"] else "failed",
                error_msg=result.get("error"),
                wechat_media_id=result.get("media_id"),
            )

            session.add(log)
            await session.commit()

        # 6. 返回结果
        return PublishResponse(
            success=result["success"],
            platform="wechat",
            media_id=result.get("media_id"),
            content=result.get("content"),
            editor_url=result.get("editor_url"),
            error=result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建公众号草稿失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"创建草稿失败：{str(e)}")


@router.get("/logs", response_model=List[PublishLogResponse])
async def get_publish_logs(
    house_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """
    获取发布记录

    - **house_id**: 筛选指定房源的记录（可选）

    返回：发布记录列表
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            query = select(PublishLog)
            if house_id:
                query = query.where(PublishLog.house_id == house_id)

            query = query.order_by(PublishLog.created_at.desc())
            result = await session.execute(query)
            logs = result.scalars().all()

            # 转换为响应对象
            responses = []
            for log in logs:
                responses.append(PublishLogResponse(
                    id=log.id,
                    house_id=log.house_id,
                    script_id=log.script_id,
                    platform=log.platform,
                    status=log.status,
                    error_msg=log.error_msg,
                    xhs_note_id=log.xhs_note_id,
                    wechat_media_id=log.wechat_media_id,
                    published_at=log.published_at,
                    created_at=log.created_at,
                ))

            return responses

    except Exception as e:
        logger.error(f"获取发布记录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取记录失败：{str(e)}")
