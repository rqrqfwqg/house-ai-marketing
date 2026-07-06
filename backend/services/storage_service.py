"""
临时文件存储与清理服务
负责：图片保存、路径生成、过期文件清理
"""
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from loguru import logger

from config import settings


class StorageService:
    """
    文件存储服务类
    功能：保存上传的图片、生成访问URL、清理过期文件
    """
    
    def __init__(self):
        """初始化存储目录"""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"文件存储目录：{self.upload_dir.absolute()}")
    
    def save_image(self, file_data: bytes, filename: str, house_id: Optional[int] = None) -> str:
        """
        保存图片到本地目录
        
        Args:
            file_data: 图片二进制数据
            filename: 原始文件名
            house_id: 房源ID（用于组织目录）
        
        Returns:
            保存的相对路径（用于数据库存储）
        """
        try:
            # 生成唯一文件名（时间戳 + 原始文件名）
            timestamp = int(time.time() * 1000)
            safe_filename = self._sanitize_filename(filename)
            new_filename = f"{timestamp}_{safe_filename}"
            
            # 确定保存目录
            if house_id:
                save_dir = self.upload_dir / str(house_id)
            else:
                save_dir = self.upload_dir / "temp"
            
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            file_path = save_dir / new_filename
            with open(file_path, "wb") as f:
                f.write(file_data)
            
            # 返回相对路径（用于数据库存储和前端访问）
            relative_path = f"/uploads/{house_id}/{new_filename}" if house_id else f"/uploads/temp/{new_filename}"
            
            logger.info(f"图片保存成功：{relative_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"保存图片失败：{str(e)}")
            raise
    
    def get_image_url(self, relative_path: str) -> str:
        """
        获取图片的完整访问URL
        
        Args:
            relative_path: 数据库存储的相对路径
        
        Returns:
            完整的URL（用于前端<img>标签）
        """
        # 开发环境：通过后端静态文件服务访问
        base_url = f"http://localhost:{settings.BACKEND_PORT}"
        return f"{base_url}{relative_path}"
    
    def delete_image(self, relative_path: str) -> bool:
        """
        删除图片文件
        
        Args:
            relative_path: 数据库存储的相对路径
        
        Returns:
            是否删除成功
        """
        try:
            # 将URL路径转换为本地路径
            file_path = self.upload_dir.parent / relative_path.lstrip("/")
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"图片删除成功：{relative_path}")
                return True
            else:
                logger.warning(f"图片不存在：{relative_path}")
                return False
                
        except (Exception, SystemExit) as e:
            logger.warning(f"删除图片失败（已跳过）：{str(e)}")
            return False
    
    def cleanup_expired_files(self) -> int:
        """
        清理超过保留天数的文件
        
        Returns:
            清理的文件数量
        """
        try:
            expiry_days = settings.IMAGE_RETENTION_DAYS
            expiry_time = datetime.now() - timedelta(days=expiry_days)
            
            cleaned_count = 0
            
            # 遍历所有文件
            for file_path in self.upload_dir.rglob("*"):
                if file_path.is_file():
                    # 检查文件修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if mtime < expiry_time:
                        # 删除过期文件
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"清理过期文件：{file_path}")
            
            logger.info(f"清理完成，共清理 {cleaned_count} 个过期文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期文件失败：{str(e)}")
            return 0
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名（移除非法字符）
        
        Args:
            filename: 原始文件名
        
        Returns:
            清理后的文件名
        """
        # 移除路径分隔符和特殊字符
        illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        safe_name = filename
        
        for char in illegal_chars:
            safe_name = safe_name.replace(char, '_')
        
        # 限制文件名长度
        if len(safe_name) > 100:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:96] + ext
        
        return safe_name
    
    def get_storage_stats(self) -> dict:
        """
        获取存储统计信息
        
        Returns:
            存储统计字典（文件数量、总大小等）
        """
        try:
            total_files = 0
            total_size = 0
            
            for file_path in self.upload_dir.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "upload_dir": str(self.upload_dir.absolute()),
            }
            
        except Exception as e:
            logger.error(f"获取存储统计失败：{str(e)}")
            return {}


# 创建全局实例
storage_service = StorageService()
