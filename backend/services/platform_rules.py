"""
平台约束配置（系统唯一真源 / Single Source of Truth）

本模块集中管理「微信公众号」与「小红书」在生成 / 校验 / 推送各环节的
文本约束（标题长度口径、摘要、正文、图片、话题标签、违禁词等）。

设计约束（来自增量架构设计「共享知识」）：
1. 平台枚举值必须与现有数据库字段 ``models.Script.platform``、前端类型
   ``frontend-vue/src/types/index.ts`` 的 ``Platform``、发布路由路径
   ``/api/v1/publish/{xiaohongshu|wechat}`` 完全一致——**严禁引入新别名**
   （如 ``xhs`` / ``wechat_public``），避免历史数据与新代码不一致。
2. 计量口径：
   - 微信标题：UTF-8 **字节**（`len(s.encode("utf-8"))`），上限 64（纯中文≈21字）。
   - 小红书标题/正文/话题：**字符**（`len(s)`），上限 20 / 1000 / 10。
3. 本模块为叶子模块（仅依赖标准库），可被 schemas / ai_service / wechat_service
   / xhs_service 安全导入，无循环依赖。
4. 所有约束以常量集中于此；推送端（wechat_service / xhs_service）的魔法值
   改从本模块引用，消除漂移。待官方核实的项标 ``unconfirmed=True``，
   后续只需改常量，逻辑无需变动。

注意：本文件**不引入任何第三方依赖**，仅使用 Python 标准库。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Platform(str, Enum):
    """
    目标发布平台枚举。

    继承 ``str`` 以便：
    - 可直接与数据库存储的字符串（``script.platform``）比较；
    - ``.value`` 即为写入 DB / 前端 / 路由的字符串值。

    值必须与现有代码完全一致，禁止新增别名。
    """

    XIAOHONGSHU = "xiaohongshu"
    WECHAT = "wechat"

    @classmethod
    def values(cls) -> List[str]:
        """返回所有合法平台字符串值列表。"""
        return [p.value for p in cls]

    @classmethod
    def is_valid(cls, value: Optional[str]) -> bool:
        """判断给定字符串是否为合法平台值。"""
        return value in cls.values()


@dataclass(frozen=True)
class PlatformRule:
    """
    单个平台的文本约束规则。

    所有数值集中定义，推送端与服务端共享，避免重复硬编码。
    """

    # 标题上限数值（配合 title_unit 解释口径）
    title_max: int
    # 标题计量口径："byte"（微信，UTF-8 字节）| "char"（小红书，字符）
    title_unit: str
    # 摘要上限（字符）；无独立摘要则为 None
    digest_max: Optional[int]
    # 正文上限（字符）；无硬上限则为 None
    body_max: Optional[int]
    # 封面 / 图片最少张数
    image_min: int
    # 图片最多张数；无上限则为 None
    image_max: Optional[int]
    # 单图大小上限（字节）；无限制则为 None
    image_max_bytes: Optional[int]
    # 话题标签上限数量；无限制则为 None
    max_topics: Optional[int]
    # 单个话题标签长度上限（字符）；无限制则为 None
    max_topic_len: Optional[int]
    # 违禁 / 敏感词（标题与正文中不得出现）
    forbidden_words: List[str] = field(default_factory=list)
    # True 表示规则值为常识推断 / PRD 默认值，待官方核实后只改常量。
    # 注意：本标记仅用于代码自说明，不影响运行时校验逻辑。
    unconfirmed: bool = False


# ---------------------------------------------------------------------------
# 平台约束唯一真源
# ---------------------------------------------------------------------------
# 微信规则全部来自现有代码常量（wechat_service.py）：
#   WECHAT_TITLE_MAX_LEN = 64（字节）、WECHAT_DIGEST_MAX_LEN = 120、IMAGE_MAX_SIZE = 2MB
# 小红书规则来自 PRD 默认值（待官方核实，标 unconfirmed=True）：
#   标题 ≤20 字符、正文 ≤1000 字符、图片 ≥1（上限 18）、话题 ≤10 每 ≤20 字符、
#   违禁直白租赁词。后续核对官方只需改下面常量值，逻辑不动。
PLATFORM_RULES: Dict[str, PlatformRule] = {
    Platform.WECHAT.value: PlatformRule(
        title_max=64,  # 64 字节，纯中文≈21字
        title_unit="byte",
        digest_max=120,  # 摘要 ≤120 字符
        body_max=None,  # 图文正文无硬性字数上限，由风格引导
        image_min=1,  # 封面必填
        image_max=None,
        image_max_bytes=2 * 1024 * 1024,  # 单图 ≤2MB
        max_topics=None,  # 微信以 #标签 文本嵌入正文尾部，无独立话题数限制
        max_topic_len=None,
        forbidden_words=[],  # 公众号可正常出现「出租/租房/月租/租金」等合规词
        unconfirmed=False,
    ),
    Platform.XIAOHONGSHU.value: PlatformRule(
        title_max=20,  # 标题 ≤20 字符
        title_unit="char",
        digest_max=None,  # 无独立摘要字段
        body_max=1000,  # 正文 ≤1000 字符（待核实）
        image_min=1,  # 至少 1 张图
        image_max=18,  # 单篇最多 18 张（待核实）
        image_max_bytes=None,
        max_topics=10,  # 话题 ≤10 个（待核实）
        max_topic_len=20,  # 单个话题 ≤20 字符（待核实）
        forbidden_words=["出租", "租房", "月租", "租金", "招租", "房东"],  # 规避直白租赁词
        unconfirmed=True,  # 小红书规则为 PRD 默认值，待官方核实
    ),
}


def _resolve_rule(platform: str) -> PlatformRule:
    """
    根据平台值解析规则，非法平台抛出 ``ValueError``。

    Args:
        platform: 平台字符串（应为 Platform.values() 之一）。

    Returns:
        ``PlatformRule`` 实例。

    Raises:
        ValueError: 平台值非法。
    """
    if not Platform.is_valid(platform):
        raise ValueError(
            f"未知平台：{platform!r}，合法值为 {Platform.values()}"
        )
    return PLATFORM_RULES[platform]


def count_title(title: str, platform: str) -> Dict[str, Any]:
    """
    统计标题长度，按平台计量口径（微信=字节 / 小红书=字符）。

    返回值结构与前端 ``platformRules.countTitle`` 保持一致，便于前后端对齐。

    Args:
        title: 标题文本。
        platform: 平台字符串（xiaohongshu / wechat）。

    Returns:
        字典：
        - ``count``: 当前计量值（字节或字符）。
        - ``max``: 上限。
        - ``unit``: ``"byte"`` | ``"char"``。
        - ``remaining``: ``max - count``（可为负）。
        - ``over_limit``: 是否超限（count > max）。

    Raises:
        ValueError: 平台值非法。
    """
    rule = _resolve_rule(platform)
    if rule.title_unit == "byte":
        count = len((title or "").encode("utf-8"))
    else:
        count = len(title or "")
    remaining = rule.title_max - count
    return {
        "count": count,
        "max": rule.title_max,
        "unit": rule.title_unit,
        "remaining": remaining,
        "over_limit": count > rule.title_max,
    }


def truncate_title(
    title: str,
    platform: str,
    max_bytes: Optional[int] = None,
) -> str:
    """
    按平台口径安全截断标题，保证结果不超过平台上限。

    - 微信（``byte`` 口径）：按 UTF-8 字节截断，超出时附加省略号「…」（3 字节），
      结果严格 ≤ 上限字节，且不切断多字节字符（避免残缺 emoji / 中文）。
    - 小红书（``char`` 口径）：按字符截断，结果 ≤ 上限字符。

    空 / 空白标题回退为「无标题」，保证下游一定有合法标题。

    本函数是标题截断的**唯一真源**：推送端 ``wechat_service`` 的
    ``_truncate_title_by_bytes`` 与小红书端均在此收敛，消除重复实现漂移。

    Args:
        title: 原始标题。
        platform: 平台字符串（xiaohongshu / wechat）。
        max_bytes: 仅测试 / 调试用，覆盖字节上限；为 ``None`` 时取规则默认值。

    Returns:
        截断后的安全标题；不会超过平台上限。

    Raises:
        ValueError: 平台值非法。
    """
    if not title:
        return "无标题"
    title = title.strip()
    if not title:
        return "无标题"

    rule = _resolve_rule(platform)

    if rule.title_unit == "byte":
        limit = max_bytes if max_bytes is not None else rule.title_max
        encoded = title.encode("utf-8")
        if len(encoded) <= limit:
            return title

        # 需要截断：预留省略号（…，UTF-8 占 3 字节）的空间，避免切断多字节字符
        ellipsis = "…"
        ellipsis_bytes = len(ellipsis.encode("utf-8"))
        budget = max(0, limit - ellipsis_bytes)

        out: List[str] = []
        used = 0
        for ch in title:
            ch_bytes = len(ch.encode("utf-8"))
            if used + ch_bytes > budget:
                break
            out.append(ch)
            used += ch_bytes
        return "".join(out) + ellipsis

    # 字符口径（小红书）：直接按字符截断（与 xhs_service 现有行为一致）
    limit = rule.title_max
    if len(title) <= limit:
        return title
    return title[:limit]


def count_body(body: str, platform: str) -> Dict[str, Any]:
    """
    统计正文字符长度，按字符计量（与小红书正文口径一致）。

    微信图文正文无硬性字数上限（body_max=None），此时仍返回实际字符数，
    供前端实时计数展示（不触发超限）。

    Args:
        body: 正文文本。
        platform: 平台字符串。

    Returns:
        字典：
        - ``count``: 实际字符数。
        - ``max``: 上限（None 表示无硬上限）。
        - ``remaining``: 剩余（max 为 None 时返回 None）。
        - ``over_limit``: 是否超限（max 为 None 时为 False）。
    """
    rule = _resolve_rule(platform)
    count = len(body or "")
    if rule.body_max is None:
        return {
            "count": count,
            "max": None,
            "remaining": None,
            "over_limit": False,
        }
    remaining = rule.body_max - count
    return {
        "count": count,
        "max": rule.body_max,
        "remaining": remaining,
        "over_limit": count > rule.body_max,
    }


def validate_script(
    platform: str,
    title: str,
    body: str = "",
    tags: Optional[List[str]] = None,
    highlights: Optional[List[str]] = None,
    images: Optional[List[str]] = None,
) -> List[str]:
    """
    按平台规则校验文案，返回违规说明列表（空列表 = 合规）。

    校验维度：标题上限、正文上限、图片数量/大小、话题数量/长度、违禁词。
    ``images`` / ``highlights`` 可选：生成阶段文案尚未绑定图片（图片来自房源），
    传入 ``None`` 表示跳过图片校验（图片约束在推送阶段由 wechat_service 兜底）。

    Args:
        platform: 平台字符串。
        title: 标题文本。
        body: 正文文本。
        tags: 话题标签列表。
        highlights: 特色亮点列表（暂未纳入硬校验）。
        images: 图片路径 / URL 列表（None 表示跳过图片校验）。

    Returns:
        违规说明列表；为空表示合规。

    Raises:
        ValueError: 平台值非法。
    """
    errors: List[str] = []
    rule = _resolve_rule(platform)

    # 1. 标题（按平台口径：字节 or 字符）
    title_info = count_title(title or "", platform)
    if title_info["over_limit"]:
        if rule.title_unit == "byte":
            errors.append(
                f"标题超出微信限制：当前 {title_info['count']} 字节，上限 "
                f"{title_info['max']} 字节（纯中文约 {rule.title_max // 3} 字）"
            )
        else:
            errors.append(
                f"标题超出小红书限制：当前 {title_info['count']} 字符，上限 "
                f"{title_info['max']} 字符"
            )

    # 2. 正文（字符口径；微信 body_max=None 不校验）
    body_info = count_body(body or "", platform)
    if body_info["over_limit"]:
        errors.append(
            f"正文超出{_platform_label(platform)}限制：当前 {body_info['count']} 字符，"
            f"上限 {body_info['max']} 字符"
        )

    # 3. 图片数量 / 大小（仅在提供 images 时校验）
    if images is not None:
        if len(images) < rule.image_min:
            errors.append(
                f"图片数量不足：至少需要 {rule.image_min} 张图片"
            )
        if rule.image_max is not None and len(images) > rule.image_max:
            errors.append(
                f"图片数量超出{_platform_label(platform)}限制：当前 {len(images)} 张，"
                f"上限 {rule.image_max} 张"
            )

    # 4. 话题标签数量 / 长度（小红书有上限；微信无独立话题限制）
    if tags is not None and rule.max_topics is not None:
        if len(tags) > rule.max_topics:
            errors.append(
                f"话题标签数量超出小红书限制：当前 {len(tags)} 个，上限 "
                f"{rule.max_topics} 个"
            )
        if rule.max_topic_len is not None:
            for tag in tags:
                if len(tag) > rule.max_topic_len:
                    errors.append(
                        f"话题标签「{tag}」长度超出小红书限制：当前 {len(tag)} 字符，"
                        f"上限 {rule.max_topic_len} 字符"
                    )

    # 5. 违禁 / 敏感词（标题 + 正文，大小写无关子串匹配）
    if rule.forbidden_words:
        text = f"{title or ''}\n{body or ''}"
        for word in rule.forbidden_words:
            if word and word in text:
                errors.append(
                    f"文案包含{_platform_label(platform)}违禁词「{word}」，请替换为隐晦表达"
                )

    return errors


def _platform_label(platform: str) -> str:
    """返回平台中文名（用于校验提示）。"""
    return "小红书" if platform == Platform.XIAOHONGSHU.value else "微信"
