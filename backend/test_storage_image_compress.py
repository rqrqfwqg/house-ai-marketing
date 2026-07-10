"""
StorageService.save_image 落盘前压缩回归测试。

背景：房源照片在保存到磁盘前，需统一压缩到 ``settings.UPLOAD_IMAGE_MAX_BYTES``
（默认 500KB）以内；非图片（如 .txt）应原样写回，不做压缩。

覆盖：
1. 大 JPEG（>500KB）经 save_image 后，落盘文件 ≤ 500KB。
2. 小图（<500KB）经 save_image 后字节完全不变（不重新编码、不损质）。
3. 大 PNG（>500KB）经 save_image 后被压缩（JPEG）且 ≤ 500KB。
4. 大 WebP（>500KB）经 save_image 后被压缩且 ≤ 500KB。
5. 非图片（.txt 二进制 >500KB）经 save_image 原样写入，不被压缩。
6. image_utils.compress_image_bytes_data 单元行为：小图原样返回、大图达标、零副作用。

运行（backend 目录下）：
    pytest test_storage_image_compress.py -v
"""

import io
import os
import sys

import pytest
from PIL import Image

# 确保 backend 根目录在 sys.path，使 `from services...` 与 `from config import settings` 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings  # noqa: E402
from services.storage_service import StorageService  # noqa: E402
from services.image_utils import compress_image_bytes_data  # noqa: E402


# ----------------------------------------------------------------------
# 图片字节构造工具
# ----------------------------------------------------------------------

def _make_bytes(width: int, height: int, fmt: str = "JPEG", quality: int = 95) -> bytes:
    """生成高熵（随机像素）测试图字节。

    使用 ``os.urandom`` 逐像素随机填充，保证 PNG/WebP 等无损格式也无法被有效压缩、
    体积稳定偏大（>500KB，便于验证压缩路径）；JPEG 同样因此稳定偏大。
    """
    raw = os.urandom(width * height * 3)
    img = Image.frombytes("RGB", (width, height), raw)
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()


def _abs_path_from_relative(svc: StorageService, rel_path: str) -> str:
    """由 save_image 返回的相对路径反推本机绝对路径（默认落到 temp 目录）。"""
    fname = rel_path.rsplit("/", 1)[-1]
    sub = "temp" if "temp" in rel_path else rel_path.split("/")[2]
    return str(svc.upload_dir / sub / fname)


# ----------------------------------------------------------------------
# save_image 压缩行为
# ----------------------------------------------------------------------

def test_large_jpeg_compressed_under_limit(tmp_path, monkeypatch):
    """大 JPEG（>500KB）经 save_image 后，落盘文件 ≤ 500KB。"""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    svc = StorageService()

    max_bytes = settings.UPLOAD_IMAGE_MAX_BYTES
    data = _make_bytes(2000, 2000, fmt="JPEG", quality=95)
    assert len(data) > max_bytes  # 模拟明显超标的房源大图

    rel = svc.save_image(data, "big.jpg")
    abs_path = _abs_path_from_relative(svc, rel)

    assert os.path.exists(abs_path)
    assert os.path.getsize(abs_path) <= max_bytes
    # 压缩产物仍为有效 JPEG
    assert open(abs_path, "rb").read()[:2] == b"\xff\xd8"


def test_small_image_bytes_unchanged(tmp_path, monkeypatch):
    """小图（<500KB）经 save_image 后字节完全不变（不重新编码、不损质）。"""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    svc = StorageService()

    max_bytes = settings.UPLOAD_IMAGE_MAX_BYTES
    data = _make_bytes(150, 150, fmt="JPEG", quality=90)
    assert len(data) <= max_bytes

    rel = svc.save_image(data, "small.jpg")
    abs_path = _abs_path_from_relative(svc, rel)

    saved = open(abs_path, "rb").read()
    assert saved == data
    assert len(saved) == len(data)


def test_large_png_compressed_under_limit(tmp_path, monkeypatch):
    """大 PNG（>500KB）经 save_image 后被压缩（JPEG）且 ≤ 500KB。"""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    svc = StorageService()

    max_bytes = settings.UPLOAD_IMAGE_MAX_BYTES
    data = _make_bytes(2000, 2000, fmt="PNG")
    assert len(data) > max_bytes

    rel = svc.save_image(data, "big.png")
    abs_path = _abs_path_from_relative(svc, rel)

    assert os.path.getsize(abs_path) <= max_bytes
    # PIL 可正常打开压缩产物
    Image.open(abs_path).verify()


def test_large_webp_compressed_under_limit(tmp_path, monkeypatch):
    """大 WebP（>500KB）经 save_image 后被压缩且 ≤ 500KB。"""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    svc = StorageService()

    max_bytes = settings.UPLOAD_IMAGE_MAX_BYTES
    data = _make_bytes(2000, 2000, fmt="WEBP", quality=95)
    assert len(data) > max_bytes

    rel = svc.save_image(data, "big.webp")
    abs_path = _abs_path_from_relative(svc, rel)

    assert os.path.getsize(abs_path) <= max_bytes
    Image.open(abs_path).verify()


def test_non_image_passthrough(tmp_path, monkeypatch):
    """非图片（.txt 二进制 >500KB）经 save_image 原样写入，不被压缩。"""
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    svc = StorageService()

    max_bytes = settings.UPLOAD_IMAGE_MAX_BYTES
    data = os.urandom(max_bytes + 50 * 1024)  # 随机二进制，明显 > 500KB
    assert len(data) > max_bytes

    rel = svc.save_image(data, "note.txt")
    abs_path = _abs_path_from_relative(svc, rel)

    # 原样写入：大小与内容完全一致
    assert os.path.getsize(abs_path) == len(data)
    assert open(abs_path, "rb").read() == data


# ----------------------------------------------------------------------
# image_utils.compress_image_bytes_data 单元行为
# ----------------------------------------------------------------------

def test_image_utils_small_returns_original():
    """小图（≤ 目标）经 compress_image_bytes_data 原样返回，不重新编码。"""
    max_bytes = 500 * 1024
    data = _make_bytes(150, 150, fmt="JPEG", quality=90)
    assert len(data) <= max_bytes

    out = compress_image_bytes_data(data, max_bytes)
    assert out == data
    assert len(out) == len(data)


def test_image_utils_large_under_limit():
    """大 JPEG 经 compress_image_bytes_data 压缩后 ≤ 目标，且原输入字节不被改写。"""
    max_bytes = 500 * 1024
    data = _make_bytes(2000, 2000, fmt="JPEG", quality=95)
    assert len(data) > max_bytes

    out = compress_image_bytes_data(data, max_bytes)
    assert isinstance(out, bytes)
    assert len(out) <= max_bytes
    # 零副作用：原输入（内存字节）未被修改
    assert len(data) > max_bytes
