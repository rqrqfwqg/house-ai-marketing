"""
文案相关路由
定义：生成文案、获取文案详情、更新文案、获取文案列表
"""
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_db
from schemas import (
    ScriptGenerateRequest,
    ScriptResponse,
    ScriptUpdateRequest,
    ScriptListResponse,
)
from services.ai_service import ai_service
from models import Script
from database import AsyncSessionLocal

# 创建路由
router = APIRouter(
    prefix="/scripts",
    tags=["文案生成"],
)


@router.post("/generate", response_model=ScriptResponse, status_code=201)
async def generate_script(
    request: ScriptGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    生成AI文案
    
    - **house_id**: 房源ID
    - **template_style**: 模板风格（professional/friendly/urgent）
    
    返回：生成的文案对象
    """
    try:
        logger.info(f"收到文案生成请求：house_id={request.house_id}, style={request.template_style}")
        
        # 1. 调用AI服务生成文案
        script_data = await ai_service.generate_script(
            request.house_id,
            request.template_style
        )
        
        # 2. 保存到数据库
        async with AsyncSessionLocal() as session:
            script = Script(
                house_id=request.house_id,
                title=script_data["title"],
                body=script_data["body"],
                tags=json.dumps(script_data["tags"], ensure_ascii=False),
                highlights=json.dumps(script_data.get("highlights", []), ensure_ascii=False),
                template_style=request.template_style,
            )
            
            session.add(script)
            await session.commit()
            await session.refresh(script)
            
            logger.info(f"文案保存成功：ID={script.id}")
            
            # 3. 返回响应
            return ScriptResponse(
                id=script.id,
                house_id=script.house_id,
                title=script.title,
                body=script.body,
                tags=script_data["tags"],
                highlights=script_data.get("highlights", []),
                platform=script.platform,
                template_style=script.template_style,
                created_at=script.created_at,
            )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文案生成失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"生成失败：{str(e)}")


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取文案详情
    
    - **script_id**: 文案ID
    
    返回：文案详细信息
    """
    try:
        async with AsyncSessionLocal() as session:
            script = await session.get(Script, script_id)
            
            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")
            
            # 解析tags和highlights
            tags = json.loads(script.tags) if script.tags else []
            highlights = json.loads(script.highlights) if script.highlights else []
            
            return ScriptResponse(
                id=script.id,
                house_id=script.house_id,
                title=script.title,
                body=script.body,
                tags=tags,
                highlights=highlights,
                platform=script.platform,
                template_style=script.template_style,
                created_at=script.created_at,
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文案详情失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取详情失败：{str(e)}")


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(
    script_id: int,
    request: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    更新文案（编辑后保存）
    
    - **script_id**: 文案ID
    - **request**: 更新内容（title, body, tags）
    
    返回：更新后的文案对象
    """
    try:
        async with AsyncSessionLocal() as session:
            script = await session.get(Script, script_id)
            
            if not script:
                raise HTTPException(status_code=404, detail="文案不存在")
            
            # 更新字段
            if request.title is not None:
                script.title = request.title
            if request.body is not None:
                script.body = request.body
            if request.tags is not None:
                script.tags = json.dumps(request.tags, ensure_ascii=False)
            if request.highlights is not None:
                script.highlights = json.dumps(request.highlights, ensure_ascii=False)
            
            await session.commit()
            await session.refresh(script)
            
            logger.info(f"文案更新成功：ID={script.id}")
            
            # 解析tags和highlights
            tags = json.loads(script.tags) if script.tags else []
            highlights = json.loads(script.highlights) if script.highlights else []
            
            return ScriptResponse(
                id=script.id,
                house_id=script.house_id,
                title=script.title,
                body=script.body,
                tags=tags,
                highlights=highlights,
                platform=script.platform,
                template_style=script.template_style,
                created_at=script.created_at,
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文案失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败：{str(e)}")


@router.get("", response_model=ScriptListResponse)
async def get_scripts(
    house_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取文案列表
    
    - **house_id**: 筛选指定房源的文案（可选）
    - **skip**: 跳过记录数
    - **limit**: 返回记录数
    
    返回：文案列表和总数
    """
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select, func
            
            # 构建查询
            query = select(Script)
            if house_id:
                query = query.where(Script.house_id == house_id)
            
            # 查询总数
            count_query = select(func.count(Script.id))
            if house_id:
                count_query = count_query.where(Script.house_id == house_id)
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # 查询列表（按创建时间倒序）
            query = query.order_by(Script.created_at.desc()).offset(skip).limit(limit)
            result = await session.execute(query)
            scripts = result.scalars().all()
            
            # 转换为响应对象
            items = []
            for script in scripts:
                tags = json.loads(script.tags) if script.tags else []
                highlights = json.loads(script.highlights) if script.highlights else []
                items.append(ScriptResponse(
                    id=script.id,
                    house_id=script.house_id,
                    title=script.title,
                    body=script.body,
                    tags=tags,
                    highlights=highlights,
                    platform=script.platform,
                    template_style=script.template_style,
                    created_at=script.created_at,
                ))
            
            return ScriptListResponse(items=items, total=total)
        
    except Exception as e:
        logger.error(f"获取文案列表失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取列表失败：{str(e)}")
