"""
AI文案生成服务
负责：调用DeepSeek API、构造提示词、解析JSON响应
"""
import json
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from config import settings
from models import House, Script
from services.house_service import house_service


class AIService:
    """
    AI文案生成服务类
    功能：调用DeepSeek API生成房源营销文案
    """
    
    def __init__(self):
        """初始化HTTP客户端"""
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        self.temperature = settings.AI_TEMPERATURE
        
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY未配置，AI功能将不可用")
    
    async def generate_script(
        self,
        house_id: int,
        template_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        为房源生成AI营销文案
        
        Args:
            house_id: 房源ID
            template_style: 模板风格（professional/friendly/urgent）
        
        Returns:
            包含title、body、tags的字典
        """
        try:
            # 1. 获取房源信息
            house_response = await house_service.get_house(house_id)
            if not house_response:
                raise ValueError(f"房源不存在：ID={house_id}")
            
            # 2. 构造提示词
            prompt = self._build_prompt(house_response, template_style)
            
            # 3. 调用DeepSeek API
            response = await self._call_deepseek(prompt)
            
            # 4. 解析响应
            script_data = self._parse_response(response)
            
            logger.info(f"AI文案生成成功：house_id={house_id}")
            return script_data
            
        except Exception as e:
            logger.error(f"AI文案生成失败：{str(e)}")
            raise
    
    def _build_prompt(self, house: Any, template_style: str) -> str:
        """
        构造AI提示词
        
        Args:
            house: 房源响应对象
            template_style: 模板风格
        
        Returns:
            完整的提示词字符串
        """
        # 好物分享风格映射
        style_descriptions = {
            "professional": "种草推荐风，像博主真心推荐一个好住的窝，突出居住体验和生活品质",
            "friendly": "生活日记风，像记录自己搬新家的日常，温馨自然地分享居住感受",
            "urgent": "心动安利风，像发现宝藏一样激动地安利这个空间，表达强烈的心动和喜爱",
        }

        style_desc = style_descriptions.get(template_style, style_descriptions["professional"])

        # 构造好物分享风格提示词
        prompt = f"""你是一位小红书好物分享博主，擅长用生活化、种草风格的文字分享居住体验。

房源参考信息：
- 位置：{house.address or '暂无'}
- 户型：{house.rooms or '暂无'}
- 面积：{house.area or '暂无'}平米
- 楼层：{house.floor or '暂无'}
- 标签：{', '.join(house.tags) if house.tags else '暂无'}
- 特色亮点：{', '.join(house.highlights) if house.highlights else '暂无'}
- 预算参考：{house.rent or '暂无'}元/月

写作风格：{style_desc}

请按以下要求生成一篇好物分享风格的文案：

1. **标题**：根据房源的亮点和特色自动生成一个吸引人的标题，像小红书爆款标题，要带emoji，20字以内
2. **正文**：300-500字，好物分享/种草风格，要求：
   - 用第一人称"我"的视角，像在分享自己发现的好住所
   - 绝对不能出现"出租""租房""月租""租金""招租""房东"等直接租赁词汇
   - 用隐晦方式暗示这个空间可以入住，如"搬进来""住进""我的新窝""这个宝藏小屋"等
   - 适当使用emoji表情（如🏠✨🌿💡🛋️☀️等），但不要过多
   - 分段清晰，每段2-3句
   - 突出居住体验、生活便利、空间感受，而非价格交易
3. **特色亮点**：3-5个简短卖点，每个不超过8个字，如"近地铁""南北通透""采光超好"
4. **标签**：3个适合小红书的标签

请输出JSON格式（不要包含markdown代码块标记）：
{{
  "title": "自动生成的标题（带emoji，20字以内）",
  "body": "好物分享风格正文（300-500字，含emoji，分段清晰）",
  "highlights": ["亮点1", "亮点2", "亮点3"],
  "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 必须返回纯JSON格式，不要有任何其他文字
2. 标题必须是根据内容自动生成的，不要直接使用"房源参考信息"中的原始描述
3. 正文严禁出现"出租""租房""月租""租金""招租""房东"等词汇
4. 预算参考信息仅用于内部参考，不要在正文中直接写出具体金额
"""

        return prompt
    
    async def _call_deepseek(self, prompt: str) -> str:
        """
        调用DeepSeek API（OpenAI兼容格式）
        
        Args:
            prompt: 提示词
        
        Returns:
            AI响应的文本内容
        """
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY未配置")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 构造请求体（OpenAI兼容格式）
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一位小红书好物分享博主，擅长用生活化、种草风格的文字分享居住体验，文笔自然真实，善用emoji，绝不使用直接的租赁销售用语。"},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "response_format": {"type": "json_object"},  # 强制返回JSON
                }
                
                # 发送请求
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                
                response.raise_for_status()
                result = response.json()
                
                # 提取生成的内容
                content = result["choices"][0]["message"]["content"]
                
                logger.debug(f"DeepSeek API响应：{content[:200]}...")
                return content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API请求失败：{e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"调用DeepSeek API失败：{str(e)}")
            raise
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析AI响应（JSON格式）
        
        Args:
            response: AI返回的字符串
        
        Returns:
            解析后的字典
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
            
            # 验证必要字段
            required_fields = ["title", "body", "tags"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"AI响应缺少必要字段：{field}")
            
            # 确保tags是列表
            if not isinstance(data["tags"], list):
                data["tags"] = [data["tags"]]
            
            # 确保highlights是列表（可选字段，默认空列表）
            if "highlights" not in data or data["highlights"] is None:
                data["highlights"] = []
            elif not isinstance(data["highlights"], list):
                data["highlights"] = [data["highlights"]]
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"解析AI响应失败：{response}")
            raise ValueError(f"AI响应格式错误：{str(e)}")


# 创建全局实例
ai_service = AIService()
