"""
小红书发布集成服务
通过 MCP 协议（JSON-RPC 2.0 over HTTP）调用 xiaohongshu-mcp 服务
"""
import httpx
import json
from typing import Dict, Any, Optional
from loguru import logger
from pathlib import Path

from config import settings


class XhsService:
    """小红书发布服务类 - 基于 MCP 协议"""

    def __init__(self):
        """初始化 MCP 配置"""
        self.mcp_url = settings.XHS_MCP_URL  # 如 http://localhost:18060
        self.mcp_endpoint = f"{self.mcp_url}/mcp"  # MCP 端点
        if not self.mcp_url:
            logger.warning("XHS_MCP_URL未配置，小红书发布功能将不可用")

    async def _mcp_call(self, tool_name: str, arguments: dict = None) -> dict:
        """
        MCP 协议调用工具（完整流程：初始化→通知→调用）

        返回结构：
        - 文本内容 → 解析 JSON 或返回 {"raw_text": ...}
        - 图片内容 → 返回 {"image_base64": ..., "mime_type": ...}
        - 混合内容 → 合并返回
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # 1. 初始化 MCP 会话
            init_resp = await client.post(
                self.mcp_endpoint,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "house-ai", "version": "1.0"},
                    },
                },
            )
            init_resp.raise_for_status()

            session_id = init_resp.headers.get("mcp-session-id", "")
            if not session_id:
                raise ValueError("MCP初始化失败：未获取到 session_id")

            headers["Mcp-Session-Id"] = session_id

            # 2. 发送 initialized 通知
            await client.post(
                self.mcp_endpoint,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                },
            )

            # 3. 调用工具
            call_resp = await client.post(
                self.mcp_endpoint,
                headers=headers,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {},
                    },
                },
            )
            call_resp.raise_for_status()

            # 解析响应（兼容 JSON 和 SSE 格式）
            result = self._parse_mcp_response(call_resp)

            logger.debug(f"MCP原始响应: {json.dumps(result, ensure_ascii=False)[:500]}")

            # 检查 MCP 错误
            if "error" in result:
                error_msg = result["error"].get("message", str(result["error"]))
                raise ValueError(f"MCP工具调用错误：{error_msg}")

            # 解析工具返回结果
            mcp_result = result.get("result", {})
            content_items = mcp_result.get("content", [])

            # 检测 MCP 工具执行错误（isError: true）
            if mcp_result.get("isError"):
                error_text = ""
                for item in content_items:
                    if item.get("type") == "text":
                        error_text += item.get("text", "")
                raise ValueError(f"MCP工具执行错误：{error_text}")

            # 提取内容（支持 text 和 image 类型）
            parsed = {}
            for item in content_items:
                item_type = item.get("type")
                if item_type == "text":
                    text_val = item.get("text", "")
                    try:
                        text_data = json.loads(text_val)
                        if isinstance(text_data, dict):
                            parsed.update(text_data)
                        else:
                            parsed["raw_text"] = text_val
                    except (json.JSONDecodeError, TypeError):
                        parsed["raw_text"] = text_val
                elif item_type == "image":
                    # MCP image 格式：{"type":"image","data":"base64...","mimeType":"image/png"}
                    parsed["image_base64"] = item.get("data", "")
                    parsed["mime_type"] = item.get("mimeType", "image/png")

            if parsed:
                return parsed

            # fallback: 返回原始 mcp_result
            return mcp_result

    def _parse_mcp_response(self, response: httpx.Response) -> dict:
        """
        解析 MCP 响应，兼容 JSON 和 text/event-stream 格式

        Args:
            response: httpx 响应对象

        Returns:
            解析后的 JSON dict
        """
        content_type = response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # SSE 格式：解析 data: 行
            text = response.text
            for line in text.strip().split("\n"):
                line = line.strip()
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            return json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
            # 如果没解析到，尝试整体 JSON
            return response.json()

        # 标准 JSON 格式
        return response.json()

    async def get_login_qrcode(self) -> Dict[str, Any]:
        """
        获取小红书登录二维码

        支持多种返回格式：
        - image_base64: MCP image 类型，直接 base64 数据
        - qr_code / qrcode / base64: JSON 文本中的字段
        - qr_code_url: URL 格式
        """
        try:
            if not self.mcp_url:
                raise ValueError("XHS_MCP_URL未配置")

            result = await self._mcp_call("get_login_qrcode")

            logger.info(f"二维码MCP返回字段: {list(result.keys())}")
            logger.debug(f"二维码MCP完整返回: {json.dumps(result, ensure_ascii=False)[:800]}")

            # 1. 优先检查 image_base64（MCP image 类型内容）
            if result.get("image_base64"):
                mime = result.get("mime_type", "image/png")
                qr_code = f"data:{mime};base64,{result['image_base64']}"
                logger.info("从 image_base64 提取二维码成功")
                return {
                    "success": True,
                    "qr_code": qr_code,
                    "qr_code_url": None,
                    "expire_in": result.get("expire_in") or result.get("timeout") or 120,
                    "error": None,
                }

            # 2. 检查文本字段中的二维码数据
            qr_code = (
                result.get("qr_code")
                or result.get("qrcode")
                or result.get("base64")
                or result.get("qr_image")
                or result.get("image")
            )
            qr_code_url = result.get("qr_code_url") or result.get("qrcode_url") or result.get("url")

            if qr_code or qr_code_url:
                logger.info(f"从文本字段提取二维码: qr_code={'有' if qr_code else '无'}, url={'有' if qr_code_url else '无'}")
                return {
                    "success": True,
                    "qr_code": qr_code,
                    "qr_code_url": qr_code_url,
                    "expire_in": result.get("expire_in") or result.get("timeout") or 120,
                    "error": None,
                }

            # 3. 检查 raw_text（可能是非 JSON 文本）
            raw_text = result.get("raw_text", "")
            if raw_text:
                logger.warning(f"MCP返回未解析文本: {raw_text[:200]}")
                # 尝试从文本中提取 base64 或 URL
                if raw_text.startswith("http"):
                    return {
                        "success": True,
                        "qr_code": None,
                        "qr_code_url": raw_text,
                        "expire_in": 120,
                        "error": None,
                    }
                if len(raw_text) > 100 and not raw_text.startswith("{"):
                    # 可能是纯 base64
                    return {
                        "success": True,
                        "qr_code": f"data:image/png;base64,{raw_text}",
                        "qr_code_url": None,
                        "expire_in": 120,
                        "error": None,
                    }

            # 4. 所有方式都失败
            logger.error(f"无法从MCP返回中提取二维码，返回字段: {list(result.keys())}, 内容预览: {json.dumps(result, ensure_ascii=False)[:300]}")
            return {
                "success": True,  # MCP调用本身成功了，但数据为空
                "qr_code": None,
                "qr_code_url": None,
                "expire_in": 120,
                "error": "二维码数据为空，可能浏览器未启动或登录已过期",
            }

        except Exception as e:
            error_msg = f"获取登录二维码失败：{str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "qr_code": None,
                "qr_code_url": None,
                "error": error_msg,
            }

    async def check_login_status(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        Returns:
            包含 logged_in（bool）、error 的字典
        """
        try:
            if not self.mcp_url:
                raise ValueError("XHS_MCP_URL未配置")

            result = await self._mcp_call("check_login_status")

            return {
                "logged_in": result.get("logged_in", False) or result.get("is_logged_in", False),
                "error": None,
            }

        except Exception as e:
            logger.error(f"检查登录状态失败：{str(e)}")
            return {
                "logged_in": False,
                "error": str(e),
            }

    async def publish_note(
        self,
        title: str,
        body: str,
        images: list,
        tags: list = None,
    ) -> Dict[str, Any]:
        """
        发布笔记到小红书

        Args:
            title: 笔记标题（最多20个中文字）
            body: 笔记正文
            images: 图片本地绝对路径列表（至少1张）
            tags: 话题标签列表（可选）

        Returns:
            包含 success、note_id、error 的字典
        """
        try:
            if not self.mcp_url:
                raise ValueError("XHS_MCP_URL未配置")

            if not images:
                raise ValueError("发布小红书笔记至少需要1张图片")

            # 标题截断到20字
            title = title[:20] if title else "无标题"

            arguments = {
                "title": title,
                "content": body,
                "images": images,
            }
            if tags:
                arguments["tags"] = tags

            result = await self._mcp_call("publish_content", arguments)

            logger.info(f"小红书发布成功：{result}")
            return {
                "success": True,
                "note_id": result.get("note_id") or result.get("id"),
                "error": None,
            }

        except Exception as e:
            error_msg = f"小红书发布失败：{str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "note_id": None,
                "error": error_msg,
            }


# 创建全局实例
xhs_service = XhsService()
