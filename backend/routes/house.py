"""
房源相关路由
定义：上传房源、获取列表、获取详情、删除房源
"""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import get_db
from schemas import HouseResponse, HouseListResponse
from services.house_service import house_service
from services.storage_service import storage_service
from config import settings

# 创建路由
router = APIRouter(
    prefix="/houses",
    tags=["房源管理"],
)


@router.post("/upload", response_model=HouseResponse, status_code=201)
async def upload_house(
    images: List[UploadFile] = File(..., description="房源图片（多张）"),
    house_info: str = Form(None, description="房源信息（JSON格式）"),
    db: AsyncSession = Depends(get_db),
):
    """
    上传房源图片和基本信息
    
    - **images**: 房源图片文件列表（multipart/form-data）
    - **house_info**: 房源基本信息（JSON字符串，可选）
    
    返回：创建的房源对象
    """
    try:
        logger.info(f"收到房源上传请求：{len(images)} 张图片")
        
        # 1. 解析房源信息（如果有）
        house_data = {}
        if house_info:
            try:
                house_data = json.loads(house_info)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="房源信息JSON格式错误")
        
        # 2. 验证图片
        if not images:
            raise HTTPException(status_code=400, detail="请至少上传一张图片")
        
        # 3. 保存图片
        image_paths = []
        for image in images:
            # 验证图片格式
            if image.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的图片格式：{image.content_type}，仅支持JPEG、PNG、WebP"
                )
            
            # 验证图片大小
            file_data = await image.read()
            if len(file_data) > settings.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"图片大小超过限制（最大{settings.MAX_IMAGE_SIZE // (1024*1024)}MB）"
                )
            
            # 保存图片（先保存到temp目录，创建房源后再移动到对应目录）
            # 注意：这里需要先创建房源获取ID，所以先保存到temp
            temp_path = storage_service.save_image(file_data, image.filename)
            image_paths.append(temp_path)
        
        # 4. 创建房源记录
        from schemas import HouseCreate
        house_create = HouseCreate(**house_data) if house_data else HouseCreate()
        house_response = await house_service.create_house(house_create, image_paths)
        
        # 5. 将图片从temp目录移动到以house_id命名的目录
        # TODO: 实现图片目录迁移逻辑
        
        logger.info(f"房源上传成功：ID={house_response.id}")
        return house_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"房源上传失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")


@router.get("", response_model=HouseListResponse)
async def get_houses(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    获取房源列表
    
    - **skip**: 跳过记录数（分页）
    - **limit**: 返回记录数（分页）
    
    返回：房源列表和总数
    """
    try:
        houses, total = await house_service.get_houses(skip, limit)
        return HouseListResponse(items=houses, total=total)
        
    except Exception as e:
        logger.error(f"获取房源列表失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取列表失败：{str(e)}")


@router.get("/{house_id}", response_model=HouseResponse)
async def get_house(
    house_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取房源详情
    
    - **house_id**: 房源ID
    
    返回：房源详细信息
    """
    try:
        house = await house_service.get_house(house_id)
        
        if not house:
            raise HTTPException(status_code=404, detail="房源不存在")
        
        return house
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取房源详情失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"获取详情失败：{str(e)}")


@router.delete("/{house_id}", status_code=204)
async def delete_house(
    house_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除房源
    
    - **house_id**: 房源ID
    
    返回：204 No Content
    """
    try:
        success = await house_service.delete_house(house_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="房源不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除房源失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败：{str(e)}")
