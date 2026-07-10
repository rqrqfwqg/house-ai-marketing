"""
微信公众号大图压缩（Bug 修复）回归测试。

背景：房源手机直出图常 >2MB，原 ``_check_image`` 直接 ``raise ValueError``
（“图片 ... 超过微信限制 2MB”），导致 ``create_draft`` 失败。本次修复在
上传前自动压缩到微信限制内（封面 ~1.9MB / 正文 ~0.95MB），不再硬拒。

覆盖：
1. ``_compress_image_bytes``：>2MB 图压缩后 ≤ 目标字节，且原图文件不被改写。
2. ``_compress_image_bytes``：≤ 限制的图直接返回原样字节（不压缩、不损质）。
3. ``_upload_thumb_image``（封面，走 material/add_material）：传入 2.41MB 图片
   时先压缩到 ≤2MB 再发出，不抛 ValueError；发出的字节/MIME/文件名正确。
4. ``_upload_content_image``（正文，走 media/uploadimg）：同样先压缩再发出。
5. 小图上传路径不压缩：文件名/MIME/字节保持原样（含 PNG 场景）。
6. 文件不存在仍抛出 ``FileNotFoundError``（保留该校验）。

运行（backend 目录下）：
    pytest test_wechat_image_compress.py -v
"""

import asyncio
import os
import sys

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

# 确保 backend 根目录在 sys.path，使 `from services...` 与 `from config import settings` 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.wechat_service import (  # noqa: E402
    WechatService,
    WECHAT_THUMB_MAX_BYTES,
    WECHAT_CONTENT_MAX_BYTES,
)


def _svc() -> WechatService:
    """构造一个不触发「未配置」告警的实例（显式传入 appid/secret）。"""
    return WechatService(app_id="test_appid", app_secret="test_secret")


def _make_image(path: str, width: int, height: int, fmt: str = "JPEG", quality: int = 100) -> int:
    """
    生成一张带噪点的测试图（噪点防止 JPEG 高压缩率导致体积过小），返回文件字节数。

    默认 RGB + 噪点块，确保大尺寸图在 quality=100 时稳定 >2MB。
    """
    img = Image.new("RGB", (width, height), (123, 200, 80))
    px = img.load()
    step = 7
    for y in range(0, height, step):
        for x in range(0, width, step):
            r = (x * 7) % 256
            g = (y * 13) % 256
            b = (x + y) % 256
            for dy in range(step):
                for dx in range(step):
                    nx, ny = x + dx, y + dy
                    if nx < width and ny < height:
                        px[nx, ny] = (r, g, b)
    img.save(path, format=fmt, quality=quality)
    return os.path.getsize(path)


def _mock_httpx_client(post_side_effect) -> AsyncMock:
    """
    构造一个 ``httpx.AsyncClient`` 的异步 Mock（作为上下文管理器），
    post 请求交由 ``post_side_effect(url, params, files)`` 处理。
    """
    client = AsyncMock()
    client.post = AsyncMock(side_effect=post_side_effect)
    cm = AsyncMock()
    cm.__aenter__.return_value = client
    cm.__aexit__.return_value = False
    return cm


# ----------------------------------------------------------------------
# _compress_image_bytes 测试
# ----------------------------------------------------------------------

def test_compress_large_image_under_target(tmp_path):
    """>2MB 图压缩后应 ≤ 封面目标字节，且原图文件不被改写。"""
    svc = _svc()
    p = tmp_path / "big.jpg"
    size = _make_image(str(p), 2200, 2200, quality=100)
    assert size > 2 * 1024 * 1024  # 模拟 2.41MB 真实场景

    out = svc._compress_image_bytes(str(p), WECHAT_THUMB_MAX_BYTES)

    assert isinstance(out, bytes)
    assert len(out) <= WECHAT_THUMB_MAX_BYTES
    # 原图零副作用：文件大小不变
    assert os.path.getsize(str(p)) == size


def test_compress_small_image_returns_original_bytes(tmp_path):
    """≤ 限制的图应直接返回原样字节（不压缩、不损质）。"""
    svc = _svc()
    p = tmp_path / "small.jpg"
    size = _make_image(str(p), 200, 200, quality=85)
    assert size <= WECHAT_THUMB_MAX_BYTES

    out = svc._compress_image_bytes(str(p), WECHAT_THUMB_MAX_BYTES)
    original = open(str(p), "rb").read()

    assert out == original
    assert len(out) == size


def test_compress_target_is_content_limit(tmp_path):
    """正文 0.95MB 上限同样可把 >1MB 图压到限制内。"""
    svc = _svc()
    p = tmp_path / "body.jpg"
    size = _make_image(str(p), 2200, 2200, quality=100)
    assert size > WECHAT_CONTENT_MAX_BYTES

    out = svc._compress_image_bytes(str(p), WECHAT_CONTENT_MAX_BYTES)
    assert len(out) <= WECHAT_CONTENT_MAX_BYTES
    assert os.path.getsize(str(p)) == size  # 原图不被改写


# ----------------------------------------------------------------------
# _upload_thumb_image 测试（封面，material/add_material，微信限制 2MB）
# ----------------------------------------------------------------------

def test_upload_thumb_compresses_oversize_image(tmp_path):
    """封面图 2.41MB 时，先压缩到 ≤1.9MB 再发出，不抛 ValueError。"""
    svc = _svc()
    p = tmp_path / "cover.jpg"
    size = _make_image(str(p), 2200, 2200, quality=100)
    assert size > 2 * 1024 * 1024

    captured = {}

    def _post(url, params=None, files=None, **kwargs):
        captured["files"] = files
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"media_id": "MEDIA_123"}
        return resp

    cm = _mock_httpx_client(_post)
    with patch("services.wechat_service.httpx.AsyncClient", return_value=cm):
        media_id = asyncio.run(svc._upload_thumb_image("TOKEN", str(p)))

    assert media_id == "MEDIA_123"

    sent_name, sent_bytes, sent_ct = captured["files"]["media"]
    assert isinstance(sent_bytes, bytes)
    assert len(sent_bytes) <= WECHAT_THUMB_MAX_BYTES
    assert sent_ct == "image/jpeg"
    assert sent_name.endswith(".jpg")
    # 原图文件未被改写
    assert os.path.getsize(str(p)) == size


def test_upload_thumb_small_image_unchanged(tmp_path):
    """小图（含 PNG）上传路径不压缩：文件名/MIME/字节保持原样。"""
    svc = _svc()
    p = tmp_path / "small.png"
    _make_image(str(p), 200, 200, fmt="PNG")

    captured = {}

    def _post(url, params=None, files=None, **kwargs):
        captured["files"] = files
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"media_id": "M"}
        return resp

    cm = _mock_httpx_client(_post)
    with patch("services.wechat_service.httpx.AsyncClient", return_value=cm):
        asyncio.run(svc._upload_thumb_image("TOKEN", str(p)))

    sent_name, sent_bytes, sent_ct = captured["files"]["media"]
    assert sent_name.endswith(".png")
    assert sent_ct == "image/png"
    assert sent_bytes == open(str(p), "rb").read()


# ----------------------------------------------------------------------
# _upload_content_image 测试（正文，media/uploadimg，微信限制 1MB）
# ----------------------------------------------------------------------

def test_upload_content_compresses_oversize_image(tmp_path):
    """正文图 >1MB 时，先压缩到 ≤0.95MB 再发出，不抛 ValueError。"""
    svc = _svc()
    p = tmp_path / "body.jpg"
    size = _make_image(str(p), 2200, 2200, quality=100)
    assert size > WECHAT_CONTENT_MAX_BYTES

    captured = {}

    def _post(url, params=None, files=None, **kwargs):
        captured["files"] = files
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"url": "https://example.com/img.jpg"}
        return resp

    cm = _mock_httpx_client(_post)
    with patch("services.wechat_service.httpx.AsyncClient", return_value=cm):
        url = asyncio.run(svc._upload_content_image("TOKEN", str(p)))

    assert url == "https://example.com/img.jpg"

    sent_name, sent_bytes, sent_ct = captured["files"]["media"]
    assert isinstance(sent_bytes, bytes)
    assert len(sent_bytes) <= WECHAT_CONTENT_MAX_BYTES
    assert sent_ct == "image/jpeg"
    assert sent_name.endswith(".jpg")
    assert os.path.getsize(str(p)) == size  # 原图未被改写


# ----------------------------------------------------------------------
# 校验类测试
# ----------------------------------------------------------------------

def test_read_image_bytes_missing_file_raises(tmp_path):
    """文件不存在仍抛出 FileNotFoundError（保留该校验，不被压缩逻辑吞掉）。"""
    svc = _svc()
    with pytest.raises(FileNotFoundError):
        svc._read_image_bytes(
            str(tmp_path / "nope.jpg"), max_bytes=WECHAT_THUMB_MAX_BYTES
        )
