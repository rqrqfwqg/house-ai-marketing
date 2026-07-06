"""
SQLAlchemy ORM模型定义
定义：House（房源）、Script（文案）、PublishLog（发布记录）三张表
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base


class House(Base):
    """
    房源表模型
    存储：房源基本信息、图片路径、标签
    """
    __tablename__ = "houses"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 房源基本信息
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="房源标题")
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="地址")
    rent: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="月租金（元）")
    rooms: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="户型（如：2室1厅）")
    area: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="面积（平米）")
    floor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="楼层")

    # 图片路径（JSON数组存储）
    images: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="图片路径列表（JSON格式）")

    # 标签（JSON数组存储）
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签列表（JSON格式）")

    # 特色亮点（JSON数组存储）
    highlights: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="特色亮点列表（JSON格式）")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：一个房源可以生成多个文案
    scripts: Mapped[List["Script"]] = relationship("Script", back_populates="house", cascade="all, delete-orphan")

    # 关系：一个房源可以有多个发布记录
    publish_logs: Mapped[List["PublishLog"]] = relationship("PublishLog", back_populates="house", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<House(id={self.id}, title={self.title})>"


class Script(Base):
    """
    文案表模型
    存储：AI生成的文案（标题、正文、标签）、关联房源ID、平台、模板风格
    """
    __tablename__ = "scripts"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 外键：关联房源
    house_id: Mapped[int] = mapped_column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, comment="关联房源ID")

    # 文案内容
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="文案标题")
    body: Mapped[str] = mapped_column(Text, nullable=False, comment="文案正文")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签列表（JSON格式）")

    # 特色亮点（JSON数组存储）
    highlights: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="特色亮点列表（JSON格式）")

    # 发布平台和模板风格
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="发布平台（xiaohongshu/wechat）")
    template_style: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="模板风格（professional/friendly/urgent）")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：关联房源
    house: Mapped["House"] = relationship("House", back_populates="scripts")

    # 关系：一个文案可以对应多个发布记录
    publish_logs: Mapped[List["PublishLog"]] = relationship("PublishLog", back_populates="script", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Script(id={self.id}, house_id={self.house_id}, title={self.title})>"


class PublishLog(Base):
    """
    发布记录表模型
    存储：发布到各平台的结果、状态、错误信息
    """
    __tablename__ = "publish_logs"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 外键：关联房源和文案
    house_id: Mapped[int] = mapped_column(Integer, ForeignKey("houses.id", ondelete="CASCADE"), nullable=False, comment="关联房源ID")
    script_id: Mapped[int] = mapped_column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False, comment="关联文案ID")

    # 发布信息
    platform: Mapped[str] = mapped_column(String(50), nullable=False, comment="发布平台（xiaohongshu/wechat）")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", comment="发布状态（pending/success/failed/draft_created）")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    # 平台返回ID
    xhs_note_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="小红书笔记ID")
    wechat_media_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="微信公众号素材ID")

    # 时间戳
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="发布时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：关联房源和文案
    house: Mapped["House"] = relationship("House", back_populates="publish_logs")
    script: Mapped["Script"] = relationship("Script", back_populates="publish_logs")

    def __repr__(self) -> str:
        return f"<PublishLog(id={self.id}, platform={self.platform}, status={self.status})>"
