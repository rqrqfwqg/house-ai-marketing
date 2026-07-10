"""
图片字节级压缩工具（内存处理，绝不回写磁盘）。

提供两套入口，构成「上传图片压缩」与「微信大图自动压缩」的单一真源：

- ``compress_image_bytes_data(data, max_bytes, ...)``
    对内存中的图片字节做无损判断 + 有损压缩（JPEG）。原图已 ≤ ``max_bytes``
    时直接原样返回（不重新编码、不损质、零额外 IO）；否则转 RGB、按最长边等比
    缩放，并以 JPEG 逐步下调 quality 直到 ≤ ``max_bytes``；质量降到下限仍超限则
    进一步缩小最长边重试；极端情况（几乎不可能）抛出 ``ValueError``。
- ``compress_image_bytes(image_path, max_bytes, ...)``
    基于路径的薄封装：读取文件字节后委托 ``compress_image_bytes_data``，
    签名与行为与原 ``wechat_service._compress_image_bytes`` 完全一致，
    供 wechat_service 复用，保证既有用例不回归。

设计目标：
1. 房源照片在落盘前统一压缩到 ``settings.UPLOAD_IMAGE_MAX_BYTES``（500KB）以内；
2. 微信大图自动压缩到 2MB / 1MB 限制内也复用同一实现，消除重复逻辑；
3. 任何路径都不会改写磁盘上的原图文件（零副作用）。
"""
import io
from typing import Optional

from PIL import Image


# ---------------------------------------------------------------------------
# 压缩参数（集中定义，便于调参；与原 wechat_service 实现保持一致）
# ---------------------------------------------------------------------------
COMPRESS_MAX_EDGE = 1280       # 最长边目标像素
COMPRESS_MIN_EDGE = 160        # 最小边长下限，避免无限缩小
COMPRESS_QUALITY_START = 85    # 起始质量
COMPRESS_QUALITY_STEP = 5      # 质量下调步进
COMPRESS_QUALITY_MIN = 20      # 质量下限


def compress_image_bytes_data(
    data: bytes,
    max_bytes: int,
    *,
    max_edge: int = COMPRESS_MAX_EDGE,
    min_quality: int = COMPRESS_QUALITY_MIN,
) -> bytes:
    """
    对内存中的图片字节做压缩，使其 ≤ ``max_bytes``，返回压缩后字节。

    **绝不改写任何磁盘文件**，仅返回内存字节，保证原图零损质、零副作用。

    压缩策略（防御性与不损质兼顾）：
    1. 若原图字节已 ≤ max_bytes，直接返回原 ``data``（不压缩、不损质、无额外 IO）；
    2. 否则用 ``PIL.Image`` 打开并统一转 RGB，先按最长边 ≤ ``max_edge`` 等比缩放，
       再以 JPEG 保存并逐步下调 ``quality``（从 ``COMPRESS_QUALITY_START`` 起，
       步进 ``COMPRESS_QUALITY_STEP``）直到字节 ≤ max_bytes；
    3. 若 ``quality`` 降到 ``min_quality`` 仍超限，则进一步缩小最长边
       （每次 ×0.8）重试；
    4. 极端情况（已缩到 ``COMPRESS_MIN_EDGE`` 仍超限，几乎不可能）则抛出
       ``ValueError``，附带极限大小，便于排查。

    Args:
        data: 原图二进制数据（内存字节，可为任意 PIL 可打开的格式）。
        max_bytes: 目标字节上限（如 500KB / 1.9MB / 0.95MB）。
        max_edge: 最长边缩放目标像素（关键字参数，默认 1280）。
        min_quality: 质量下限（关键字参数，默认 20）。

    Returns:
        压缩后的 JPEG 字节；原图已达标时返回原样 ``data``。

    Raises:
        ValueError: 压缩后仍超过 max_bytes（极端情况，已缩到最小尺寸）。
    """
    # 1. 已达标直接返回，零损质、零额外 CPU/IO（关键：不重新编码，避免无故损质）
    if len(data) <= max_bytes:
        return data

    # 2. 在内存中打开并统一为 RGB（JPEG 不支持透明通道 / 调色板）
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")

    quality_start = COMPRESS_QUALITY_START
    quality_step = COMPRESS_QUALITY_STEP

    def _resize_to_edge(edge: int) -> None:
        """将图片最长边等比缩放到 ``edge`` 像素以内（原地修改）。"""
        w, h = img.size
        longest = max(w, h)
        if longest <= edge:
            return
        scale = edge / float(longest)
        img.thumbnail(
            (max(1, int(w * scale)), max(1, int(h * scale))),
            Image.LANCZOS,
        )

    # 先按默认最长边缩放
    edge = max_edge
    _resize_to_edge(edge)

    quality = quality_start
    buf = io.BytesIO()
    while True:
        buf.seek(0)
        buf.truncate(0)
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        out = buf.getvalue()
        if len(out) <= max_bytes:
            return out

        if quality > min_quality:
            # 仅下调质量，尺寸不变，再次尝试
            quality -= quality_step
            continue

        # quality 已到下限仍超限：缩小尺寸后再从高质量尝试
        new_edge = int(edge * 0.8)
        if new_edge < COMPRESS_MIN_EDGE:
            raise ValueError(
                f"图片压缩后仍超过限制：极限尺寸 {edge}px、"
                f"质量 {min_quality} 时 {len(out)} 字节 "
                f"> 目标 {max_bytes} 字节"
            )
        edge = new_edge
        _resize_to_edge(edge)
        quality = quality_start


def compress_image_bytes(
    image_path: str,
    max_bytes: int,
    *,
    max_edge: int = COMPRESS_MAX_EDGE,
    min_quality: int = COMPRESS_QUALITY_MIN,
    **kw,
) -> bytes:
    """
    基于路径的薄封装：读取文件字节后委托 ``compress_image_bytes_data``。

    签名与行为与原 ``wechat_service._compress_image_bytes(image_path, max_bytes)``
    保持一致（额外关键字参数透传），供 wechat_service 复用，保证既有测试不回归。
    原图文件绝不被改写。

    Args:
        image_path: 原图绝对路径。
        max_bytes: 目标字节上限。
        max_edge: 最长边缩放目标像素（透传）。
        min_quality: 质量下限（透传）。
        **kw: 其余透传给 ``compress_image_bytes_data`` 的关键字参数。

    Returns:
        压缩后的 JPEG 字节；原图已达标时返回原样字节。

    Raises:
        ValueError: 压缩后仍超过 max_bytes（极端情况）。
        FileNotFoundError: 图片不存在（由 ``open`` 抛出）。
    """
    with open(image_path, "rb") as f:
        data = f.read()
    return compress_image_bytes_data(
        data,
        max_bytes,
        max_edge=max_edge,
        min_quality=min_quality,
        **kw,
    )
