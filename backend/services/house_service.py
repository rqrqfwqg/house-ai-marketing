"""
房源业务逻辑服务
负责：房源CRUD、图片处理、与数据库交互
"""
import json
from typing import List, Optional, Tuple
from loguru import logger

from database import AsyncSessionLocal
from models import House
from schemas import HouseCreate, HouseResponse
from services.storage_service import storage_service


class HouseService:
    """
    房源服务类
    功能：创建房源、获取列表、删除房源、关联图片
    """
    
    async def create_house(
        self,
        house_data: HouseCreate,
        image_paths: List[str]
    ) -> HouseResponse:
        """
        创建房源记录
        
        Args:
            house_data: 房源基本信息
            image_paths: 图片路径列表
        
        Returns:
            创建的房源响应对象
        """
        async with AsyncSessionLocal() as session:
            try:
                # 创建ORM对象
                house = House(
                    title=house_data.title,
                    address=house_data.address,
                    rent=house_data.rent,
                    rooms=house_data.rooms,
                    area=house_data.area,
                    floor=house_data.floor,
                    tags=json.dumps(house_data.tags, ensure_ascii=False) if house_data.tags else None,
                    highlights=json.dumps(house_data.highlights, ensure_ascii=False) if house_data.highlights else None,
                    images=json.dumps(image_paths, ensure_ascii=False) if image_paths else None,
                )
                
                # 保存到数据库
                session.add(house)
                await session.commit()
                await session.refresh(house)
                
                logger.info(f"房源创建成功：ID={house.id}")
                
                # 转换为响应对象
                return self._to_response(house)
                
            except Exception as e:
                await session.rollback()
                logger.error(f"创建房源失败：{str(e)}")
                raise
    
    async def get_house(self, house_id: int) -> Optional[HouseResponse]:
        """
        获取单个房源详情
        
        Args:
            house_id: 房源ID
        
        Returns:
            房源响应对象，不存在则返回None
        """
        async with AsyncSessionLocal() as session:
            try:
                house = await session.get(House, house_id)
                
                if house:
                    return self._to_response(house)
                else:
                    logger.warning(f"房源不存在：ID={house_id}")
                    return None
                    
            except Exception as e:
                logger.error(f"获取房源失败：{str(e)}")
                raise
    
    async def get_houses(self, skip: int = 0, limit: int = 20) -> Tuple[List[HouseResponse], int]:
        """
        获取房源列表
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
        
        Returns:
            (房源列表, 总记录数)
        """
        async with AsyncSessionLocal() as session:
            try:
                # 查询房源列表
                from sqlalchemy import select, func
                
                # 查询总数
                total_result = await session.execute(select(func.count(House.id)))
                total = total_result.scalar()
                
                # 查询列表（按创建时间倒序）
                result = await session.execute(
                    select(House)
                    .order_by(House.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
                houses = result.scalars().all()
                
                # 转换为响应对象
                responses = [self._to_response(house) for house in houses]
                
                return responses, total
                
            except Exception as e:
                logger.error(f"获取房源列表失败：{str(e)}")
                raise
    
    async def delete_house(self, house_id: int) -> bool:
        """
        删除房源（同时删除关联的图片）
        
        Args:
            house_id: 房源ID
        
        Returns:
            是否删除成功
        """
        async with AsyncSessionLocal() as session:
            try:
                house = await session.get(House, house_id)
                
                if not house:
                    logger.warning(f"房源不存在：ID={house_id}")
                    return False
                
                # 删除关联的图片文件（尽力而为，失败不影响数据库记录删除）
                if house.images:
                    try:
                        image_paths = json.loads(house.images)
                        for path in image_paths:
                            try:
                                storage_service.delete_image(path)
                            except (Exception, SystemExit) as e:
                                logger.warning(f"删除图片文件失败，跳过：{path} - {str(e)}")
                    except (Exception, SystemExit) as e:
                        logger.warning(f"解析图片路径失败，跳过图片删除：{str(e)}")

                # 删除数据库记录（关联的子记录会通过CASCADE自动删除）
                await session.delete(house)
                await session.commit()
                
                logger.info(f"房源删除成功：ID={house_id}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"删除房源失败：{str(e)}")
                raise
    
    def _to_response(self, house: House) -> HouseResponse:
        """
        将ORM对象转换为响应对象
        
        Args:
            house: House ORM对象
        
        Returns:
            HouseResponse对象
        """
        # 解析JSON字段
        images = json.loads(house.images) if house.images else []
        tags = json.loads(house.tags) if house.tags else []
        highlights = json.loads(house.highlights) if house.highlights else []

        return HouseResponse(
            id=house.id,
            title=house.title,
            address=house.address,
            rent=house.rent,
            rooms=house.rooms,
            area=house.area,
            floor=house.floor,
            tags=tags,
            highlights=highlights,
            images=images,
            created_at=house.created_at,
            updated_at=house.updated_at,
        )


# 创建全局实例
house_service = HouseService()
