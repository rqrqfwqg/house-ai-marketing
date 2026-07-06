"""
历史记录路由
定义：获取历史记录、删除历史记录
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_db, AsyncSessionLocal
from models import House, Script, PublishLog
from schemas import HouseResponse, ScriptResponse, PublishLogResponse
import json

# 创建路由
router = APIRouter(
    prefix="/history",
    tags=["历史记录"],
)


@router.get("", response_model=List[dict])
async def get_history(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取历史记录（整合房源、文案、发布记录）
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数
    
    返回：历史记录列表（包含房源、文案、发布状态）
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, func, desc
            
            # 查询房源列表（按创建时间倒序）
            query = (
                select(House)
                .order_by(desc(House.created_at))
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(query)
            houses = result.scalars().all()
            
            # 构建历史记录
            history_items = []
            
            for house in houses:
                # 解析JSON字段
                images = json.loads(house.images) if house.images else []
                tags = json.loads(house.tags) if house.tags else []
                
                # 查询关联的文案
                scripts_query = select(Script).where(Script.house_id == house.id)
                scripts_result = await session.execute(scripts_query)
                scripts = scripts_result.scalars().all()
                
                scripts_data = []
                for script in scripts:
                    script_tags = json.loads(script.tags) if script.tags else []
                    scripts_data.append({
                        "id": script.id,
                        "title": script.title,
                        "body": script.body,
                        "tags": script_tags,
                        "template_style": script.template_style,
                        "created_at": script.created_at.isoformat(),
                    })
                
                # 查询关联的发布记录
                logs_query = select(PublishLog).where(PublishLog.house_id == house.id)
                logs_result = await session.execute(logs_query)
                logs = logs_result.scalars().all()
                
                logs_data = []
                for log in logs:
                    logs_data.append({
                        "id": log.id,
                        "platform": log.platform,
                        "status": log.status,
                        "note_id": log.xhs_note_id,
                        "media_id": log.wechat_media_id,
                        "published_at": log.published_at.isoformat() if log.published_at else None,
                        "created_at": log.created_at.isoformat(),
                    })
                
                # 构建历史记录项
                history_items.append({
                    "house": {
                        "id": house.id,
                        "title": house.title,
                        "address": house.address,
                        "rent": house.rent,
                        "rooms": house.rooms,
                        "images": images,
                        "tags": tags,
                        "created_at": house.created_at.isoformat(),
                    },
                    "scripts": scripts_data,
                    "publish_logs": logs_data,
                })
            
            return history_items
            
    except Exception as e:
        logger.error(f"获取历史记录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取历史记录失败：{str(e)}")


@router.delete("/{house_id}", status_code=204)
async def delete_history(
    house_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除历史记录（同时删除房源、文案、发布记录）
    
    - **house_id**: 房源ID
    
    返回：204 No Content
    """
    try:
        async with AsyncSessionLocal() as session:
            house = await session.get(House, house_id)
            
            if not house:
                raise HTTPException(status_code=404, detail="房源不存在")
            
            # 删除房源（关联的子记录会通过CASCADE自动删除）
            await session.delete(house)
            await session.commit()
            
            logger.info(f"历史记录删除成功：house_id={house_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除历史记录失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"删除历史记录失败：{str(e)}")
