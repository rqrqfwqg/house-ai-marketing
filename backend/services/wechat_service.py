"""
微信公众号发布服务
模式：真实调用微信公众号草稿箱 API 上传草稿

流程：
1. 获取 access_token（带缓存，过期前 5 分钟刷新）
2. 上传封面图（永久素材 add_material），获取 thumb_media_id
3. 上传正文图片（uploadimg），获取可嵌入 HTML 的 URL
4. 构建 HTML 正文
5. 调用 draft/add 新建草稿
"""
import os
import re
import time
import mimetypes
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

import httpx
from loguru import logger

from config import settings


# 微信公众号 API 基础地址
WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"

# access_token 提前刷新时间（秒），过期前 5 分钟刷新
TOKEN_REFRESH_AHEAD = 300

# 模块级 access_token 缓存：按 appid 隔离，跨实例共享，彻底解决多账号互相覆盖。
# 结构: { appid: (token, expires_at_unix_ts) }
TOKEN_CACHE: dict[str, tuple[str, float]] = {}

# 图片大小上限（2MB，微信素材接口限制）
IMAGE_MAX_SIZE = 2 * 1024 * 1024

# 微信图文标题最大长度（注意：微信按「字节」限制，64 字节；
# 中文 UTF-8 占 3 字节，因此纯中文标题最多约 21 字）。
WECHAT_TITLE_MAX_LEN = 64

# 摘要最大长度（微信按字符限制，120 字符）
WECHAT_DIGEST_MAX_LEN = 120

# 标题截断时附加的省略号（UTF-8 占 3 字节）
WECHAT_TITLE_ELLIPSIS = "…"

# 微信常见错误码 → 可读中文说明（参考 xhs_service._classify_error 的做法）
WECHAT_ERROR_MESSAGES = {
    40001: "微信公众号 access_token 无效或已过期，请检查 AppID/AppSecret 或重新授权",
    40013: "微信公众号 AppID 无效，请检查「公众号配置」中的 AppID",
    40014: "微信公众号 access_token 无效，请重新授权",
    41001: "微信接口缺少必要参数，请检查请求后重试",
    42001: "微信公众号 access_token 已过期，请稍后重试",
    45003: "标题长度超出微信限制（最多 64 字节，约 21 个中文），已自动截断仍超限，请缩短标题后重试",
    45009: "公众号接口调用频次超限，请稍后重试",
    48001: "公众号未开通该接口权限，请确认账号已完成微信认证",
    48004: "公众号未认证，无权限调用该接口，请先完成微信认证",
    50001: "公众号未获得该接口的权限",
    50002: "用户未授权该 API 权限",
    61023: "请确认公众号已成功授权",
}


class WechatService:
    """微信公众号服务类 - 草稿箱 API 模式"""

    def __init__(self, app_id: Optional[str] = None, app_secret: Optional[str] = None):
        """
        初始化：支持按账号构造实例，无参时退化为读取全局 settings（向后兼容）。

        Args:
            app_id: 指定公众号 AppID；为空则使用 ``settings.WECHAT_APPID``。
            app_secret: 指定公众号 AppSecret（明文，仅在内存短暂存在）；为空则使用
                ``settings.WECHAT_APPSECRET``。

        若 AppID/AppSecret 均未配置，仅记录警告，调用时再抛出异常，
        以保证服务实例可正常创建（不影响其他平台功能）。

        Note:
            access_token 缓存已改为模块级 ``TOKEN_CACHE`` 按 appid 隔离，
            不再持有实例级缓存，避免多账号互相覆盖。
        """
        self.appid: str = (app_id or settings.WECHAT_APPID or "").strip()
        self.appsecret: str = (app_secret or settings.WECHAT_APPSECRET or "").strip()

        if not self.appid or not self.appsecret:
            logger.warning(
                "WECHAT_APPID 或 WECHAT_APPSECRET 未配置，"
                "公众号草稿箱功能将不可用"
            )

    # ------------------------------------------------------------------
    # access_token 管理
    # ------------------------------------------------------------------
    async def _get_access_token(self) -> str:
        """
        获取 access_token（按 appid 隔离的模块级缓存，过期前 5 分钟自动刷新）。

        Returns:
            有效的 access_token 字符串。

        Raises:
            RuntimeError: AppID/Secret 未配置，或获取 token 失败。
        """
        if not self.appid or not self.appsecret:
            raise RuntimeError(
                "未配置 WECHAT_APPID 或 WECHAT_APPSECRET，无法调用微信公众号 API"
            )

        # 命中模块级缓存（按 appid 隔离）：在过期前 TOKEN_REFRESH_AHEAD 秒刷新
        now = time.time()
        cached = TOKEN_CACHE.get(self.appid)
        if cached:
            token, expires_at = cached
            if token and (now + TOKEN_REFRESH_AHEAD) < expires_at:
                return token

        # 重新获取 access_token
        url = f"{WECHAT_API_BASE}/token"
        params = {
            "grant_type": "client_credential",
            "appid": self.appid,
            "secret": self.appsecret,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

        if "access_token" not in data:
            errcode = data.get("errcode")
            errmsg = data.get("errmsg", "未知错误")
            # token 失效需清除缓存以便下次重新获取
            TOKEN_CACHE.pop(self.appid, None)
            raise RuntimeError(f"获取 access_token 失败：[{errcode}] {errmsg}")

        token = data["access_token"]
        expires_in = int(data.get("expires_in", 7200))
        TOKEN_CACHE[self.appid] = (token, now + expires_in)
        logger.info(
            f"获取微信 access_token 成功（appid={self.appid}），有效期 {expires_in} 秒"
        )
        return token

    # ------------------------------------------------------------------
    # 图片上传
    # ------------------------------------------------------------------
    def _guess_content_type(self, image_path: str) -> str:
        """根据文件扩展名推断 MIME 类型，默认 image/jpeg。"""
        ct, _ = mimetypes.guess_type(image_path)
        return ct or "image/jpeg"

    def _check_image(self, image_path: str) -> None:
        """
        校验图片文件是否存在且大小合规。

        Raises:
            FileNotFoundError: 文件不存在。
            ValueError: 文件大小超过 2MB 限制。
        """
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"图片文件不存在：{image_path}")
        size = path.stat().st_size
        if size > IMAGE_MAX_SIZE:
            raise ValueError(
                f"图片 {path.name} 大小 {size / 1024 / 1024:.2f}MB 超过微信限制 2MB"
            )

    def _read_image_bytes(self, image_path: str) -> Tuple[str, bytes, str]:
        """
        读取图片字节并返回上传所需三元组。

        Returns:
            (filename, file_bytes, content_type)
        """
        self._check_image(image_path)
        filename = os.path.basename(image_path)
        content_type = self._guess_content_type(image_path)
        with open(image_path, "rb") as f:
            file_bytes = f.read()
        return filename, file_bytes, content_type

    async def _upload_thumb_image(self, access_token: str, image_path: str) -> str:
        """
        上传封面图（永久素材 add_material），获取 thumb_media_id。

        Args:
            access_token: 有效的 access_token。
            image_path: 图片绝对路径。

        Returns:
            media_id（作为草稿的 thumb_media_id）。

        Raises:
            RuntimeError: 上传失败或微信返回错误。
        """
        filename, file_bytes, content_type = self._read_image_bytes(image_path)
        url = f"{WECHAT_API_BASE}/material/add_material"
        params = {"access_token": access_token, "type": "image"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"media": (filename, file_bytes, content_type)}
            resp = await client.post(url, params=params, files=files)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

        if "media_id" not in data:
            errcode = data.get("errcode")
            errmsg = data.get("errmsg", "未知错误")
            raise RuntimeError(f"上传封面图失败：[{errcode}] {errmsg}")

        media_id = data["media_id"]
        logger.info(f"封面图上传成功：media_id={media_id}")
        return media_id

    async def _upload_content_image(self, access_token: str, image_path: str) -> str:
        """
        上传正文图片（uploadimg），获取可嵌入 HTML 的 URL。

        该 URL 可在 content 中用 <img src> 引用，不占用素材配额。

        Args:
            access_token: 有效的 access_token。
            image_path: 图片绝对路径。

        Returns:
            图片在微信服务器上的 URL。

        Raises:
            RuntimeError: 上传失败或微信返回错误。
        """
        filename, file_bytes, content_type = self._read_image_bytes(image_path)
        url = f"{WECHAT_API_BASE}/media/uploadimg"
        params = {"access_token": access_token}

        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"media": (filename, file_bytes, content_type)}
            resp = await client.post(url, params=params, files=files)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

        if "url" not in data:
            errcode = data.get("errcode")
            errmsg = data.get("errmsg", "未知错误")
            raise RuntimeError(f"上传正文图片失败：[{errcode}] {errmsg}")

        img_url = data["url"]
        logger.info(f"正文图片上传成功：{img_url}")
        return img_url

    # ------------------------------------------------------------------
    # HTML 内容构建
    # ------------------------------------------------------------------
    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符，防止 XSS / 内容错乱。"""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _build_html_content(
        self,
        body: str,
        highlights: Optional[List[str]],
        tags: Optional[List[str]],
        image_urls: List[str],
    ) -> str:
        """
        构建公众号正文 HTML 内容。

        - body 纯文本按行转为 <p> 段落
        - highlights 转为 <ul><li> 列表
        - tags 转为带颜色的标签段
        - image_urls 用 <img> 嵌入

        Args:
            body: 正文纯文本。
            highlights: 特色亮点列表。
            tags: 标签列表。
            image_urls: 正文图片 URL 列表。

        Returns:
            完整 HTML 字符串。
        """
        parts: List[str] = []

        # 正文：按行分段，每行一个 <p>
        body = (body or "").strip()
        if body:
            paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
            for p in paragraphs:
                parts.append(f"<p>{self._escape_html(p)}</p>")

        # 特色亮点
        if highlights:
            parts.append('<p><strong>✨ 特色亮点</strong></p>')
            parts.append("<ul>")
            for h in highlights:
                parts.append(f"<li>{self._escape_html(h)}</li>")
            parts.append("</ul>")

        # 正文图片（用微信返回的 URL 引用）
        for img_url in image_urls:
            parts.append(
                f'<p><img src="{img_url}" alt="" style="max-width:100%;"/></p>'
            )

        # 标签
        if tags:
            tag_html = " ".join(
                f'<span style="color:#576b95;">#{self._escape_html(t)}</span>'
                for t in tags
            )
            parts.append(f"<p>{tag_html}</p>")

        return "".join(parts)

    def _build_digest(self, body: str, max_len: int = WECHAT_DIGEST_MAX_LEN) -> str:
        """
        从正文生成摘要（一句话，最多 max_len 字）。

        按句号/换行等分隔符截取第一句，超长则截断并补省略号。

        Args:
            body: 正文文本。
            max_len: 最大长度。

        Returns:
            摘要字符串。
        """
        text = (body or "").strip()
        if not text:
            return "房源推荐"
        # 按常见句末标点和换行截取第一句
        for sep in ["。", "！", "？", "\n", "；", "!", "?", ";"]:
            idx = text.find(sep)
            if 0 < idx < max_len:
                text = text[: idx + 1]
                break
        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text

    # ------------------------------------------------------------------
    # 标题/错误工具
    # ------------------------------------------------------------------
    def _truncate_title_by_bytes(
        self, title: str, max_bytes: int = WECHAT_TITLE_MAX_LEN
    ) -> str:
        """
        按 UTF-8 字节长度安全截断标题，避免把多字节字符切断。

        微信图文 ``title`` 字段限制为 64 **字节**（中文 UTF-8 占 3 字节），
        因此纯中文标题最多约 21 字。原先按字符数 ``title[:64]`` 截断会得到 64 个中文字
        （192 字节），远超限制，触发 ``45003 title size out of limit``。

        本方法按字节截断，并在超出时附加省略号「…」（3 字节），保证结果严格
        ≤ max_bytes 字节且不以残缺的多字节字符结尾。

        Args:
            title: 原始标题。
            max_bytes: 最大字节数（默认 ``WECHAT_TITLE_MAX_LEN``=64）。

        Returns:
            截断后的安全标题；为空时回退为「无标题」。
        """
        fallback = "无标题"
        if not title:
            return fallback
        title = title.strip()
        if not title:
            return fallback

        encoded = title.encode("utf-8")
        if len(encoded) <= max_bytes:
            return title

        # 需要截断：预留省略号（…，UTF-8 占 3 字节）的空间
        ellipsis = WECHAT_TITLE_ELLIPSIS
        ellipsis_bytes = len(ellipsis.encode("utf-8"))
        budget = max(0, max_bytes - ellipsis_bytes)

        truncated_chars: List[str] = []
        used = 0
        for ch in title:
            ch_bytes = len(ch.encode("utf-8"))
            if used + ch_bytes > budget:
                break
            truncated_chars.append(ch)
            used += ch_bytes
        return "".join(truncated_chars) + ellipsis

    def _classify_wechat_error(self, errcode: Any, errmsg: str) -> str:
        """
        将微信接口返回的错误码翻译为可读的中文提示。

        参考 ``xhs_service._classify_error`` 的做法：对已知错误码提供友好说明，
        未知错误则保留原始 errmsg（并剔除 ``hint``/``rid`` 等内部调试串）便于排查，
        避免把裸错误码（如 45003）直接暴露给用户。

        Args:
            errcode: 微信返回的错误码（可能为 None / 字符串 / 数字）。
            errmsg: 微信返回的原始错误信息。

        Returns:
            清晰可读的中文错误描述。
        """
        try:
            code = int(errcode) if errcode is not None else 0
        except (TypeError, ValueError):
            code = 0

        # 40164：服务器出口 IP 不在公众号 IP 白名单中（属于运维配置问题，
        # 需用户到公众号后台把服务器出网 IP 加入「IP白名单」）。errmsg 形如：
        # "invalid ip 38.47.118.9 ipv6 ::ffff:38.47.118.9, not in whitelist"。
        # 该错误码涉及动态 IP，不放入静态字典，在此做专门处理。
        if code == 40164:
            ip_match = re.search(r"(\d{1,3}\.){3}\d{1,3}", errmsg or "")
            if ip_match:
                ip = ip_match.group(0)
                return (
                    f"服务器出口 IP 不在公众号 IP 白名单中：请将 IP {ip} 加入公众号后台"
                    "「设置与开发 → 基本配置 → IP白名单」，保存后重试"
                    "（若服务器使用 NAT 出口，需确认实际出网 IP）"
                )
            return (
                "服务器 IP 不在公众号 IP 白名单中，请到公众号后台"
                "「设置与开发 → 基本配置 → IP白名单」添加当前服务器出口 IP 后重试"
            )

        if code in WECHAT_ERROR_MESSAGES:
            return WECHAT_ERROR_MESSAGES[code]

        # 未知错误：剔除内部调试信息（hint / rid），保留可读部分
        raw = (errmsg or "未知错误").strip()
        # errmsg 形如 "title size out of limit hint: [...] rid: ..."
        cleaned = raw.split("hint")[0].strip().rstrip(":").strip()
        if not cleaned:
            cleaned = raw
        return f"微信接口返回错误（错误码 {code}）：{cleaned}"

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    async def create_draft(
        self,
        title: str,
        body: str,
        images: List[str],
        tags: List[str] = None,
        highlights: List[str] = None,
    ) -> Dict[str, Any]:
        """
        上传公众号草稿到草稿箱。

        主流程：
        1. 校验 AppID/AppSecret 配置
        2. 校验图片（至少一张作为封面）
        3. 获取 access_token
        4. 上传第一张图为封面，获取 thumb_media_id
        5. 上传其余图片为正文图，获取 URL
        6. 构建 HTML 正文
        7. 调用 draft/add 创建草稿
        8. 返回结果

        Args:
            title: 文章标题。
            body: 文章正文。
            images: 图片绝对路径列表（至少 1 张作为封面）。
            tags: 标签列表。
            highlights: 特色亮点列表。

        Returns:
            包含 success、media_id、content、editor_url、error 的字典。
        """
        try:
            # 1. 配置校验
            if not self.appid or not self.appsecret:
                raise RuntimeError("未配置 WECHAT_APPID 或 WECHAT_APPSECRET")

            # 2. 图片校验与过滤
            raw_images = [img for img in (images or []) if img]
            if not raw_images:
                raise RuntimeError("草稿箱需要至少一张封面图，请先为房源上传图片")

            valid_images: List[str] = []
            for img in raw_images:
                if Path(img).is_file():
                    valid_images.append(img)
                else:
                    logger.warning(f"图片不存在，已跳过：{img}")
            if not valid_images:
                raise RuntimeError("没有可用的图片文件，草稿箱需要至少一张封面图")

            # 3. 获取 access_token
            access_token = await self._get_access_token()

            # 4. 上传封面图（第一张），获取 thumb_media_id
            cover_path = valid_images[0]
            thumb_media_id = await self._upload_thumb_image(access_token, cover_path)
            logger.info(f"封面图 thumb_media_id={thumb_media_id}")

            # 5. 上传正文图片（其余图片），获取可嵌入 URL
            content_image_urls: List[str] = []
            for img_path in valid_images[1:]:
                try:
                    img_url = await self._upload_content_image(access_token, img_path)
                    content_image_urls.append(img_url)
                except Exception as e:
                    # 单张正文图片失败不阻断整体流程
                    logger.warning(f"正文图片上传失败，已跳过 {img_path}：{e}")

            # 6. 构建 HTML 正文
            html_content = self._build_html_content(
                body=body,
                highlights=highlights,
                tags=tags,
                image_urls=content_image_urls,
            )

            # 摘要
            digest = self._build_digest(body)

            # 7. 新建草稿
            url = f"{WECHAT_API_BASE}/draft/add"
            params = {"access_token": access_token}
            payload = {
                "articles": [
                    {
                        "title": self._truncate_title_by_bytes(title),
                        "author": "房屋推荐",
                        "digest": digest,
                        "content": html_content,
                        "thumb_media_id": thumb_media_id,
                        "content_source_url": "",
                        "need_open_comment": 0,
                        "only_fans_can_comment": 0,
                    }
                ]
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, params=params, json=payload)
                resp.raise_for_status()
                data: Dict[str, Any] = resp.json()

            if "media_id" not in data:
                errcode = data.get("errcode")
                errmsg = data.get("errmsg", "未知错误")
                readable = self._classify_wechat_error(errcode, errmsg)
                raise RuntimeError(readable)

            draft_media_id = data["media_id"]
            logger.info(f"公众号草稿创建成功：media_id={draft_media_id}")

            # 8. 返回成功结果
            return {
                "success": True,
                "media_id": draft_media_id,
                "content": None,  # 草稿箱模式不返回纯文本内容
                "editor_url": "https://mp.weixin.qq.com",
                "error": None,
            }

        except Exception as e:
            error_msg = f"创建公众号草稿失败：{str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "media_id": None,
                "content": None,
                "editor_url": None,
                "error": error_msg,
            }


# 创建全局实例
wechat_service = WechatService()
