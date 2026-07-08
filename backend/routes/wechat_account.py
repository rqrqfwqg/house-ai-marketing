"""
公众号多账号管理路由

提供能力：
- 账号列表（GET /wechat-accounts，支持 ?active_only=true）
- 新增（POST /wechat-accounts）
- 编辑（PUT /wechat-accounts/{id}，app_secret 留空不修改）
- 删除（DELETE /wechat-accounts/{id}）
- 测试连通（POST /wechat-accounts/{id}/test）
- 启动种子（seed_wechat_accounts_from_env，供 main.py lifespan 调用）

安全约定：
- 所有响应均脱敏：不返回 app_secret 与 app_id 明文，仅返回 app_id_masked。
- 鉴权：API_BEARER_TOKEN 非空时校验 Bearer；为空则放行（开发友好）。
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from database import AsyncSessionLocal, get_db
from schemas import (
    SuccessResponse,
    WechatAccountCreate,
    WechatAccountListResponse,
    WechatAccountResponse,
    WechatAccountUpdate,
    WechatTestResponse,
)
from models import WechatAccount
from crypto_utils import decrypt_secret, encrypt_secret
from config import settings
from services.wechat_service import WechatService


router = APIRouter(
    prefix="/wechat-accounts",
    tags=["公众号账号管理"],
)


# ----------------------------------------------------------------------
# 鉴权：Bearer Token（API_BEARER_TOKEN 为空则放行，开发友好）
# ----------------------------------------------------------------------
def _verify_bearer(request: Request) -> None:
    """
    轻量 Bearer 鉴权。

    - ``settings.API_BEARER_TOKEN`` 为空：放行（本地开发未配 token 不被锁死）。
    - 非空：校验 ``Authorization: Bearer <token>``，非法则返回 401。
    """
    token = (settings.API_BEARER_TOKEN or "").strip()
    if not token:
        return
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少或非法的 Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ----------------------------------------------------------------------
# 辅助：维护 is_default 唯一性（事务内清除其他默认）
# ----------------------------------------------------------------------
async def _clear_other_defaults(db: AsyncSession, except_id: Optional[int] = None) -> None:
    """
    将除 ``except_id`` 之外的账号 is_default 置为 False，保证至多一个默认账号。

    Args:
        db: 数据库会话。
        except_id: 被豁免（保持默认）的账号 id。
    """
    stmt = select(WechatAccount).where(WechatAccount.is_default == True)  # noqa: E712
    if except_id is not None:
        stmt = stmt.where(WechatAccount.id != except_id)
    result = await db.execute(stmt)
    for acc in result.scalars().all():
        acc.is_default = False


def _to_response(acc: WechatAccount) -> WechatAccountResponse:
    """将 ORM 模型转换为脱敏响应对象。"""
    return WechatAccountResponse(
        id=acc.id,
        name=acc.name,
        app_id_masked=acc.masked_app_id(),
        remark=acc.remark,
        is_active=acc.is_active,
        is_default=acc.is_default,
        created_at=acc.created_at,
        updated_at=acc.updated_at,
    )


# ----------------------------------------------------------------------
# 列表
# ----------------------------------------------------------------------
@router.get("", response_model=WechatAccountListResponse)
async def list_accounts(
    request: Request,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """获取公众号账号列表；active_only=true 仅返回启用账号。响应全部脱敏。"""
    _verify_bearer(request)
    stmt = select(WechatAccount)
    if active_only:
        stmt = stmt.where(WechatAccount.is_active == True)  # noqa: E712
    stmt = stmt.order_by(WechatAccount.id.asc())
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    items = [_to_response(a) for a in accounts]
    return WechatAccountListResponse(items=items, total=len(items))


# ----------------------------------------------------------------------
# 新增
# ----------------------------------------------------------------------
@router.post("", response_model=WechatAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: WechatAccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """新增公众号账号。AppSecret 入库前加密；若为默认账号则清除其他默认。"""
    _verify_bearer(request)

    # AppID 唯一性校验
    existing = await db.execute(
        select(WechatAccount).where(WechatAccount.app_id == payload.app_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该 AppID 已存在，请勿重复添加",
        )

    # 加密 AppSecret（明文仅在此短暂存在，绝不落库/回传）
    try:
        secret_enc = encrypt_secret(payload.app_secret)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AppSecret 加密失败：{exc}",
        )

    acc = WechatAccount(
        name=payload.name,
        app_id=payload.app_id,
        app_secret_encrypted=secret_enc,
        remark=payload.remark,
        is_active=payload.is_active,
        is_default=payload.is_default,
    )
    db.add(acc)
    await db.flush()  # 拿到自增 id，便于 is_default 唯一维护

    if payload.is_default:
        await _clear_other_defaults(db, except_id=acc.id)

    await db.commit()
    await db.refresh(acc)
    return _to_response(acc)


# ----------------------------------------------------------------------
# 编辑
# ----------------------------------------------------------------------
@router.put("/{account_id}", response_model=WechatAccountResponse)
async def update_account(
    account_id: int,
    payload: WechatAccountUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """编辑公众号账号。app_secret 为空则保留原密文；is_default 唯一维护。"""
    _verify_bearer(request)

    acc = await db.get(WechatAccount, account_id)
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    # AppID 唯一性（仅当变更时校验）
    if payload.app_id is not None and payload.app_id != acc.app_id:
        dup = await db.execute(
            select(WechatAccount).where(WechatAccount.app_id == payload.app_id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该 AppID 已存在，请勿与其他账号重复",
            )

    # 应用字段更新
    if payload.name is not None:
        acc.name = payload.name
    if payload.app_id is not None:
        acc.app_id = payload.app_id
    if payload.remark is not None:
        acc.remark = payload.remark
    if payload.is_active is not None:
        acc.is_active = payload.is_active
    if payload.app_secret:  # 非空才重新加密；空表示不修改
        try:
            acc.app_secret_encrypted = encrypt_secret(payload.app_secret)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AppSecret 加密失败：{exc}",
            )

    if payload.is_default is not None:
        acc.is_default = payload.is_default

    # 终态若为本账号默认，则清除其他默认（幂等）
    if acc.is_default:
        await _clear_other_defaults(db, except_id=acc.id)

    await db.commit()
    await db.refresh(acc)
    return _to_response(acc)


# ----------------------------------------------------------------------
# 删除
# ----------------------------------------------------------------------
@router.delete("/{account_id}", response_model=SuccessResponse)
async def delete_account(
    account_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """删除公众号账号。若该账号原为默认，删除即清空默认标记（行级自然移除）。"""
    _verify_bearer(request)

    acc = await db.get(WechatAccount, account_id)
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    await db.delete(acc)
    await db.commit()
    return SuccessResponse(success=True, message="账号已删除")


# ----------------------------------------------------------------------
# 测试连通
# ----------------------------------------------------------------------
@router.post("/{account_id}/test", response_model=WechatTestResponse)
async def test_account(
    account_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """测试账号连通性：用解密后的凭证拉取一次 access_token 验证，不泄露明文。"""
    _verify_bearer(request)

    acc = await db.get(WechatAccount, account_id)
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    # 解密（明文仅在此短暂存在）
    try:
        secret = decrypt_secret(acc.app_secret_encrypted)
    except Exception as exc:
        return WechatTestResponse(success=False, message=f"AppSecret 解密失败：{exc}")

    try:
        svc = WechatService(app_id=acc.app_id, app_secret=secret)
        token = await svc._get_access_token()
    except Exception as exc:
        return WechatTestResponse(success=False, message=f"连接失败：{exc}")

    if token:
        return WechatTestResponse(success=True, message="连接成功，凭证有效")
    return WechatTestResponse(success=False, message="未能获取 access_token")


# ----------------------------------------------------------------------
# 启动种子（供 main.py lifespan 调用）
# ----------------------------------------------------------------------
async def seed_wechat_accounts_from_env() -> None:
    """
    启动种子：若 wechat_accounts 表为空，且 .env 配置了 WECHAT_APPID/SECRET，
    则加密写入首个默认账号（is_default=True, is_active=True）。幂等：表非空则跳过。
    """
    try:
        async with AsyncSessionLocal() as session:
            count = await session.scalar(select(func.count()).select_from(WechatAccount))
            if count and count > 0:
                logger.info("wechat_accounts 已有数据，跳过种子导入")
                return

            appid = (settings.WECHAT_APPID or "").strip()
            secret = (settings.WECHAT_APPSECRET or "").strip()
            if not appid or not secret:
                logger.info("未配置 WECHAT_APPID/WECHAT_APPSECRET，跳过种子账号")
                return

            try:
                secret_enc = encrypt_secret(secret)
            except Exception as exc:
                logger.error(f"种子账号 AppSecret 加密失败：{exc}")
                return

            acc = WechatAccount(
                name="默认公众号（来自 .env）",
                app_id=appid,
                app_secret_encrypted=secret_enc,
                remark="系统启动时由 .env 自动导入",
                is_active=True,
                is_default=True,
            )
            session.add(acc)
            await session.commit()
            logger.info(f"种子账号已写入：app_id={appid[:6]}****（默认账号）")
    except Exception as exc:
        logger.error(f"种子账号初始化失败：{exc}")
