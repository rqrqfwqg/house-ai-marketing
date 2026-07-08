"""
AppSecret 加密工具

使用 `cryptography` 的 Fernet（AES-128-CBC + HMAC）对微信公众号 AppSecret 进行对称加密。

密钥读取顺序：
1. 环境变量 ``ENCRYPTION_KEY``（Fernet 合法 key，44 字符 urlsafe base64）。
2. 回退文件 ``backend/.encryption_key``（首次运行自动生成并 ``chmod 600``，已加入 .gitignore）。

安全红线：
- 明文仅在 ``decrypt_secret`` 调用后、传入 ``WechatService`` 构造时短暂存在；
- 绝不写库、绝不回传前端（列表/详情接口只返回 ``app_id_masked``）。
"""
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from config import settings


# backend 目录（.encryption_key 回退文件所在目录）
_BACKEND_DIR: Path = Path(__file__).resolve().parent
_FALLBACK_KEY_PATH: Path = _BACKEND_DIR / ".encryption_key"

# 模块级 Fernet 实例（延迟初始化并缓存）
_fernet: Optional[Fernet] = None


def _load_key() -> bytes:
    """
    加载 Fernet 密钥。

    优先使用环境变量 ``ENCRYPTION_KEY``；为空则回退到 ``backend/.encryption_key``
    文件（首次运行自动生成并设置仅属主可读写权限 ``chmod 600``）。

    Returns:
        Fernet 密钥字节。

    Raises:
        RuntimeError: 无法获取或生成有效密钥。
    """
    env_key: str = (settings.ENCRYPTION_KEY or "").strip()
    if env_key:
        return env_key.encode("utf-8")

    # 回退：读取已存在的 .encryption_key 文件
    if _FALLBACK_KEY_PATH.exists():
        try:
            key = _FALLBACK_KEY_PATH.read_text(encoding="utf-8").strip().encode("utf-8")
            if key:
                return key
        except Exception as exc:  # pragma: no cover - 文件读取异常
            logger.warning(f"读取 .encryption_key 失败，将尝试重新生成：{exc}")

    # 首次生成并落盘（权限 600，避免其他用户读取密钥）
    try:
        key = Fernet.generate_key()
        _FALLBACK_KEY_PATH.write_text(key.decode("utf-8"), encoding="utf-8")
        try:
            os.chmod(_FALLBACK_KEY_PATH, 0o600)
        except Exception:  # pragma: no cover - 权限设置失败不影响功能
            pass
        logger.info("已自动生成 backend/.encryption_key 作为加密密钥回退")
        return key
    except Exception as exc:
        raise RuntimeError(f"无法生成加密密钥：{exc}") from exc


def _get_fernet() -> Fernet:
    """
    获取（并缓存）Fernet 实例。

    Returns:
        可用的 ``Fernet`` 实例。

    Raises:
        RuntimeError: 密钥非法（如 ENCRYPTION_KEY 格式错误）。
    """
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_key())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """
    加密 AppSecret 明文为 Fernet 密文（字符串）。

    Args:
        plaintext: 待加密的明文（AppSecret）。

    Returns:
        Fernet 密文字符串。

    Raises:
        ValueError: 入参为 None。
    """
    if plaintext is None:
        raise ValueError("待加密内容不能为 None")
    token: bytes = _get_fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """
    解密 Fernet 密文为 AppSecret 明文。

    明文仅在调用方（如 ``WechatService`` 构造）短暂持有，绝不应落库或回传前端。

    Args:
        ciphertext: Fernet 密文字符串。

    Returns:
        AppSecret 明文。

    Raises:
        RuntimeError: 密文无效或密钥不匹配（InvalidToken）。
    """
    if not ciphertext:
        return ""
    try:
        plain: bytes = _get_fernet().decrypt(ciphertext.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "AppSecret 解密失败：密文无效或加密密钥不匹配"
        ) from exc
    except Exception as exc:  # pragma: no cover - 兜底异常
        raise RuntimeError(f"AppSecret 解密失败：{exc}") from exc
