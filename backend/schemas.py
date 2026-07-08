"""
Pydantic Schemas定义
负责：请求/响应数据验证、与ORM模型转换、API文档生成
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ========== 房源相关Schemas ==========

class HouseCreate(BaseModel):
    """
    房源创建请求Schema
    用于：上传房源时接收基本信息（图片通过multipart/form-data单独处理）
    """
    title: Optional[str] = Field(None, description="房源标题")
    address: Optional[str] = Field(None, description="地址")
    rent: Optional[float] = Field(None, description="月租金（元）")
    rooms: Optional[str] = Field(None, description="户型（如：2室1厅）")
    area: Optional[float] = Field(None, description="面积（平米）")
    floor: Optional[str] = Field(None, description="楼层")
    tags: List[str] = Field(default=[], description="标签列表")
    highlights: List[str] = Field(default=[], description="特色亮点列表")

    model_config = ConfigDict(
        str_strip_whitespace=True,  # 自动去除字符串前后空格
    )


class HouseResponse(BaseModel):
    """
    房源响应Schema
    用于：返回房源详细信息（包含图片路径）
    """
    id: int
    title: Optional[str] = None
    address: Optional[str] = None
    rent: Optional[float] = None
    rooms: Optional[str] = None
    area: Optional[float] = None
    floor: Optional[str] = None
    tags: List[str] = []
    highlights: List[str] = []
    images: List[str] = []  # 图片路径列表
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,  # 支持从ORM模型转换
    )


class HouseListResponse(BaseModel):
    """
    房源列表响应Schema
    """
    items: List[HouseResponse]
    total: int


# ========== 文案相关Schemas ==========

class ScriptGenerateRequest(BaseModel):
    """
    文案生成请求Schema
    用于：请求AI生成文案
    """
    house_id: int = Field(..., description="房源ID")
    template_style: str = Field(default="professional", description="模板风格（professional/friendly/urgent）")

    @field_validator("template_style")
    def validate_template_style(cls, v):
        """验证模板风格是否合法"""
        allowed = ["professional", "friendly", "urgent"]
        if v not in allowed:
            raise ValueError(f"模板风格必须是以下之一：{allowed}")
        return v


class ScriptResponse(BaseModel):
    """
    文案响应Schema
    用于：返回文案详情
    """
    id: int
    house_id: int
    title: str
    body: str
    tags: List[str] = []
    highlights: List[str] = []
    platform: Optional[str] = None
    template_style: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ScriptUpdateRequest(BaseModel):
    """
    文案更新请求Schema
    用于：编辑文案后保存
    """
    title: Optional[str] = Field(None, description="文案标题")
    body: Optional[str] = Field(None, description="文案正文")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    highlights: Optional[List[str]] = Field(None, description="特色亮点列表")


class ScriptListResponse(BaseModel):
    """
    文案列表响应Schema
    """
    items: List[ScriptResponse]
    total: int


# ========== 发布相关Schemas ==========

class PublishRequest(BaseModel):
    """
    发布请求Schema
    用于：发布文案到各平台
    """
    script_id: int = Field(..., description="文案ID")
    images: List[str] = Field(..., description="图片路径列表")
    wechat_account_id: Optional[int] = Field(
        None, description="目标公众号账号ID（多账号发布选号；为空则回落默认账号或 .env 兜底）"
    )


class PublishResponse(BaseModel):
    """
    发布响应Schema
    用于：返回发布结果
    """
    success: bool
    platform: str
    note_id: Optional[str] = None  # 小红书笔记ID
    media_id: Optional[str] = None  # 微信公众号素材ID
    content: Optional[str] = None  # 格式化文案内容（公众号复制模式）
    editor_url: Optional[str] = None  # 编辑器链接（公众号）
    error: Optional[str] = None


class PublishLogResponse(BaseModel):
    """
    发布记录响应Schema
    """
    id: int
    house_id: int
    script_id: int
    platform: str
    status: str
    error_msg: Optional[str] = None
    xhs_note_id: Optional[str] = None
    wechat_media_id: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# ========== 微信公众号多账号 Schemas ==========

class WechatAccountCreate(BaseModel):
    """
    公众号账号新增请求Schema

    安全约束：app_secret 为明文入参，后端入库前加密，绝不回传前端。
    """
    name: str = Field(..., min_length=1, max_length=50, description="账号名称")
    app_id: str = Field(..., description="AppID（wx 开头，唯一）")
    app_secret: str = Field(..., min_length=1, description="AppSecret（新增时必填）")
    remark: Optional[str] = Field(None, max_length=200, description="备注")
    is_active: bool = True
    is_default: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("app_id")
    @classmethod
    def _validate_app_id(cls, v: str) -> str:
        """校验 AppID 必须以 wx 开头且长度合理。"""
        if not v.startswith("wx"):
            raise ValueError("AppID 必须以 wx 开头")
        if not (6 <= len(v) <= 64):
            raise ValueError("AppID 长度不合法（应为 6-64 个字符）")
        return v


class WechatAccountUpdate(BaseModel):
    """
    公众号账号编辑请求Schema

    安全约束：app_secret 为空表示不修改（保留原密文）。
    """
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="账号名称")
    app_id: Optional[str] = Field(None, description="AppID（wx 开头，唯一）")
    app_secret: Optional[str] = Field(None, description="AppSecret（留空表示不修改）")
    remark: Optional[str] = Field(None, max_length=200, description="备注")
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("app_id")
    @classmethod
    def _validate_app_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith("wx"):
            raise ValueError("AppID 必须以 wx 开头")
        if not (6 <= len(v) <= 64):
            raise ValueError("AppID 长度不合法（应为 6-64 个字符）")
        return v


class WechatAccountResponse(BaseModel):
    """
    公众号账号响应Schema（脱敏）

    安全红线：仅返回 app_id_masked，绝不返回 app_secret 与 app_id 明文。
    """
    id: int
    name: str
    app_id_masked: str
    remark: Optional[str] = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WechatAccountListResponse(BaseModel):
    """公众号账号列表响应Schema。"""
    items: List[WechatAccountResponse]
    total: int


class WechatTestResponse(BaseModel):
    """公众号账号连通性测试响应Schema。"""
    success: bool
    message: str


# ========== 通用响应Schemas ==========

class ErrorResponse(BaseModel):
    """
    错误响应Schema
    """
    detail: str


class SuccessResponse(BaseModel):
    """
    成功响应Schema

    包含 success 字段以与前端 TypeScript 类型定义保持一致，
    前端通过 res.success 判断请求是否成功。
    """
    success: bool = True
    message: str
    data: Optional[dict] = None
