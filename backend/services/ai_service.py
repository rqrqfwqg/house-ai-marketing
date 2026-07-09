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
from services.platform_rules import PLATFORM_RULES, Platform


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
        template_style: str = "professional",
        platform: str = Platform.XIAOHONGSHU.value,
    ) -> Dict[str, Any]:
        """
        为房源生成AI营销文案（按目标平台约束分支）

        Args:
            house_id: 房源ID
            template_style: 模板风格（professional/friendly/urgent）
            platform: 目标发布平台（xiaohongshu / wechat），决定提示词风格与约束

        Returns:
            包含title、body、tags、highlights的字典

        Raises:
            ValueError: 房源不存在或平台非法。
        """
        try:
            # 0. 校验平台合法性（与 schema 校验互补，保证服务层自身健壮）
            if not Platform.is_valid(platform):
                raise ValueError(
                    f"未知平台：{platform!r}，合法值为 {Platform.values()}"
                )

            # 1. 获取房源信息
            house_response = await house_service.get_house(house_id)
            if not house_response:
                raise ValueError(f"房源不存在：ID={house_id}")

            # 2. 构造提示词（按平台分支：微信图文 / 小红书种草）
            prompt = self._build_prompt(house_response, template_style, platform)

            # 2.1 平台专属系统角色设定
            system_prompt = (
                "你是一位专业的房产公众号编辑，擅长把房源写成干货实用、信息清晰、"
                "可信赖的图文内容，可正常使用出租/租房/月租/租金等合规词汇，"
                "标题严格按字节控制。"
                if platform == Platform.WECHAT.value
                else "你是一位小红书好物分享博主，擅长用生活化、种草风格的文字分享居住体验，"
                "文笔自然真实，善用emoji，绝不使用直接的租赁销售用语。"
            )

            # 3. 调用DeepSeek API
            response = await self._call_deepseek(prompt, system_prompt=system_prompt)

            # 4. 解析响应
            script_data = self._parse_response(response)

            logger.info(f"AI文案生成成功：house_id={house_id}, platform={platform}")
            return script_data

        except Exception as e:
            logger.error(f"AI文案生成失败：{str(e)}")
            raise

    def _build_prompt(self, house: Any, template_style: str, platform: str) -> str:
        """
        构造AI提示词（按平台分支注入约束）

        微信（wechat）：图文干货风，标题按 UTF-8 **字节** ≤64（约21中文字），
        摘要 ≤120 字符，可正常出现「出租/租房」等合规词，适配公众号图文结构。
        小红书（xiaohongshu）：种草风，标题 ≤20 字符、正文 ≤1000 字符、
        带 #话题#、规避直白租赁词。

        Args:
            house: 房源响应对象
            template_style: 模板风格
            platform: 目标平台（xiaohongshu / wechat）

        Returns:
            完整的提示词字符串。
        """
        # 好物分享 / 种草风格映射（小红书用）
        style_descriptions = {
            "professional": "种草推荐风，像博主真心推荐一个好住的窝，突出居住体验和生活品质",
            "friendly": "生活日记风，像记录自己搬新家的日常，温馨自然地分享居住感受",
            "urgent": "心动安利风，像发现宝藏一样激动地安利这个空间，表达强烈的心动和喜爱",
        }
        style_desc = style_descriptions.get(template_style, style_descriptions["professional"])

        # 从平台规则真源读取约束，注入提示词（前后端口径一致）
        rule = PLATFORM_RULES[platform]

        # 房源信息块（两平台共用）
        house_block = f"""房源参考信息：
- 位置：{house.address or '暂无'}
- 户型：{house.rooms or '暂无'}
- 面积：{house.area or '暂无'}平米
- 楼层：{house.floor or '暂无'}
- 标签：{', '.join(house.tags) if house.tags else '暂无'}
- 特色亮点：{', '.join(house.highlights) if house.highlights else '暂无'}
- 预算参考：{house.rent or '暂无'}元/月"""

        if platform == Platform.WECHAT.value:
            return self._build_wechat_prompt(house_block, rule)
        return self._build_xhs_prompt(house_block, style_desc, rule)

    def _build_wechat_prompt(self, house_block: str, rule: Any) -> str:
        """
        构造微信公众号（图文干货风）提示词。

        约束（来自 PLATFORM_RULES[wechat]）：
        - 标题 ≤64 **字节**（UTF-8，纯中文约 21 字，emoji 占 3–4 字节须计入）。
        - 摘要 ≤120 字符（由正文首句自动截取，无需单独生成）。
        - 可正常出现「出租/租房/月租/租金」等合规词（官方号）。
        - 适配图文结构（标题 + 正文分段 + 亮点 + 标签）。
        """
        title_max = rule.title_max  # 64（字节）
        digest_max = rule.digest_max  # 120（字符）
        return f"""你是一位专业的房产公众号编辑，擅长把房源写成干货实用、信息清晰的图文内容。

{house_block}

写作要求：
1. **标题**：根据房源亮点自动生成一个吸引目标租客的标题，可带少量 emoji，但必须**严格控制在 {title_max} 个 UTF-8 字节以内**（中文每字约 3 字节，纯中文约 21 字；emoji 占 3–4 字节也要计入）。标题要具体、有信息量（如体现地铁/户型/价格区间），不要空泛。
2. **正文**：300-600字，图文干货风，要求：
   - 用专业、清晰、可信的口吻介绍房源，可正常出现"出租""租房""月租""租金""招租"等合规词（这是官方房产号，无需回避）。
   - 结构清晰：开篇点明核心卖点，中间分段讲交通/户型/配套/居住体验，结尾引导咨询看房。
   - 适当使用 emoji（如🏠🚇✨📐）点缀，但不要过多。
   - 突出居住体验、生活便利、性价比，而非单纯堆砌参数。
3. **特色亮点**：3-5个简短卖点，每个不超过8个字，如"近地铁""南北通透""采光超好"。
4. **标签**：3个适合公众号的标签（会以 #标签 形式附在文末，无需在标签里加 # 号）。
5. 摘要：系统会自动截取正文首句作为摘要（≤{digest_max} 字符），你无需单独输出摘要字段，只需保证正文首句精炼、有吸引力。

请输出JSON格式（不要包含markdown代码块标记）：
{{
  "title": "自动生成的标题（带emoji，≤{title_max}字节）",
  "body": "图文干货风格正文（300-600字，分段清晰，含emoji）",
  "highlights": ["亮点1", "亮点2", "亮点3"],
  "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 必须返回纯JSON格式，不要有任何其他文字。
2. 标题必须是根据内容自动生成的，不要直接使用房源参考信息中的原始描述。
3. 标题务必注意字节数限制（中文约21字、emoji 算 3–4 字节），超出会被截断。
4. 预算参考信息仅用于内部参考，正文中可写价格区间但不要直接照搬"X元/月"原文，可自然表述如"月租友好""性价比高"。
"""

    def _build_xhs_prompt(self, house_block: str, style_desc: str, rule: Any) -> str:
        """
        构造小红书（种草风）提示词。

        约束（来自 PLATFORM_RULES[xiaohongshu]，标 unconfirmed 待核实）：
        - 标题 ≤20 **字符**（汉字/字母/数字/标点各算 1）。
        - 正文 ≤1000 字符。
        - 带 #话题#（≤10 个，每个 ≤20 字符）。
        - 规避「出租/租房/月租/租金/招租/房东」等直白租赁词。
        """
        title_max = rule.title_max  # 20（字符）
        body_max = rule.body_max  # 1000（字符）
        max_topics = rule.max_topics  # 10
        max_topic_len = rule.max_topic_len  # 20
        return f"""你是一位小红书好物分享博主，擅长用生活化、种草风格的文字分享居住体验。

{house_block}

写作风格：{style_desc}

请按以下要求生成一篇好物分享风格的文案：

1. **标题**：根据房源的亮点和特色自动生成一个吸引人的标题，像小红书爆款标题，要带emoji，**严格控制在 {title_max} 字以内**（汉字/字母/数字/标点各算 1 字）。
2. **正文**：{body_max}字以内，好物分享/种草风格，要求：
   - 用第一人称"我"的视角，像在分享自己发现的好住所
   - 绝对不能出现"出租""租房""月租""租金""招租""房东"等直接租赁词汇
   - 用隐晦方式暗示这个空间可以入住，如"搬进来""住进""我的新窝""这个宝藏小屋"等
   - 适当使用emoji表情（如🏠✨🌿💡🛋️☀️等），但不要过多
   - 分段清晰，每段2-3句
   - 突出居住体验、生活便利、空间感受，而非价格交易
3. **特色亮点**：3-5个简短卖点，每个不超过8个字，如"近地铁""南北通透""采光超好"
4. **标签**：{max_topics}个以内适合小红书的话题标签，每个不超过{max_topic_len}字；格式如"近地铁租房""精装小窝""租房日常"（系统会自动加 # 号），不要自己加 #。

请输出JSON格式（不要包含markdown代码块标记）：
{{
  "title": "自动生成的标题（带emoji，{title_max}字以内）",
  "body": "好物分享风格正文（{body_max}字以内，含emoji，分段清晰）",
  "highlights": ["亮点1", "亮点2", "亮点3"],
  "tags": ["标签1", "标签2", "标签3"]
}}

注意：
1. 必须返回纯JSON格式，不要有任何其他文字
2. 标题必须是根据内容自动生成的，不要直接使用"房源参考信息"中的原始描述
3. 正文严禁出现"出租""租房""月租""租金""招租""房东"等词汇
4. 预算参考信息仅用于内部参考，不要在正文中直接写出具体金额
"""
    
    async def _call_deepseek(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        调用DeepSeek API（OpenAI兼容格式）

        Args:
            prompt: 提示词
            system_prompt: 系统角色设定；为 None 时使用小红书种草博主默认设定。
                平台优先模式下由 ``generate_script`` 按平台传入对应角色。

        Returns:
            AI响应的文本内容
        """
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY未配置")

        # 默认（向后兼容）为小红书种草博主；微信公众号使用专业编辑角色。
        if system_prompt is None:
            system_prompt = (
                "你是一位小红书好物分享博主，擅长用生活化、种草风格的文字分享居住体验，"
                "文笔自然真实，善用emoji，绝不使用直接的租赁销售用语。"
            )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # 构造请求体（OpenAI兼容格式）
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
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
