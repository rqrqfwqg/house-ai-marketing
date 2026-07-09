"""
platform_rules 单元测试。

验证平台约束源（backend/services/platform_rules.py）的核心能力：
1. ``count_title`` —— 按平台口径计数（微信=UTF-8 字节 / 小红书=字符）。
2. ``count_body`` —— 正文字符计数（微信无硬上限）。
3. ``validate_script`` —— 标题/正文/话题/违禁词各维度校验。
4. ``Platform`` 枚举与 ``PLATFORM_RULES`` 结构完整性。

运行（在 backend 目录下）：
    pytest test_platform_rules.py -v
"""
import os
import sys

import pytest

# 确保 backend 根目录在 sys.path，使 `from services...` 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.platform_rules import (  # noqa: E402
    Platform,
    PLATFORM_RULES,
    count_title,
    count_body,
    validate_script,
)


# ----------------------------------------------------------------------
# Platform 枚举 & PLATFORM_RULES 结构
# ----------------------------------------------------------------------

def test_platform_values_match_existing_code():
    """平台枚举值必须与现有 DB / 前端 / 路由一致，且无新别名。"""
    assert Platform.values() == ["xiaohongshu", "wechat"]
    assert Platform.is_valid("xiaohongshu")
    assert Platform.is_valid("wechat")
    assert not Platform.is_valid("xhs")
    assert not Platform.is_valid("wechat_public")
    assert not Platform.is_valid(None)


def test_platform_rules_structure():
    """PLATFORM_RULES 应覆盖两个平台且字段合理。"""
    assert set(PLATFORM_RULES.keys()) == {"xiaohongshu", "wechat"}
    wechat = PLATFORM_RULES["wechat"]
    xhs = PLATFORM_RULES["xiaohongshu"]
    # 微信：字节口径 + 摘要 120 + 图片 ≤2MB + 无违禁词
    assert wechat.title_unit == "byte"
    assert wechat.title_max == 64
    assert wechat.digest_max == 120
    assert wechat.image_max_bytes == 2 * 1024 * 1024
    assert wechat.forbidden_words == []
    # 小红书：字符口径 + 标题 20 + 正文 1000 + 话题 10/20 + 违禁词
    assert xhs.title_unit == "char"
    assert xhs.title_max == 20
    assert xhs.body_max == 1000
    assert xhs.max_topics == 10
    assert xhs.max_topic_len == 20
    assert "出租" in xhs.forbidden_words


# ----------------------------------------------------------------------
# count_title：微信按字节
# ----------------------------------------------------------------------

def test_count_title_wechat_byte_exact_21_chinese():
    """微信：21 个中文 = 63 字节，未超限。"""
    title = "测" * 21  # 63 字节
    info = count_title(title, "wechat")
    assert info["unit"] == "byte"
    assert info["count"] == 63
    assert info["max"] == 64
    assert info["remaining"] == 1
    assert info["over_limit"] is False


def test_count_title_wechat_byte_over_limit_22_chinese():
    """微信：22 个中文 = 66 字节，超限。"""
    title = "测" * 22  # 66 字节
    info = count_title(title, "wechat")
    assert info["count"] == 66
    assert info["over_limit"] is True
    assert info["remaining"] == -2


def test_count_title_wechat_byte_ascii():
    """微信：64 个 ASCII = 64 字节，未超限。"""
    info = count_title("a" * 64, "wechat")
    assert info["count"] == 64
    assert info["over_limit"] is False


def test_count_title_wechat_byte_emoji():
    """微信：emoji 占 4 字节，应计入。"""
    info = count_title("🏠", "wechat")
    assert info["count"] == 4
    # 20 个 emoji = 80 字节 > 64
    over = count_title("🏠" * 20, "wechat")
    assert over["count"] == 80
    assert over["over_limit"] is True


# ----------------------------------------------------------------------
# count_title：小红书按字符
# ----------------------------------------------------------------------

def test_count_title_xhs_char_exact_20():
    """小红书：20 字符，未超限。"""
    info = count_title("字" * 20, "xiaohongshu")
    assert info["unit"] == "char"
    assert info["count"] == 20
    assert info["max"] == 20
    assert info["over_limit"] is False


def test_count_title_xhs_char_over_limit_21():
    """小红书：21 字符，超限（与字符数而非字节比较）。"""
    info = count_title("字" * 21, "xiaohongshu")
    assert info["count"] == 21
    assert info["over_limit"] is True


def test_count_title_xhs_char_mixed_emoji():
    """小红书：emoji 按 1 字符计。"""
    info = count_title("🏠abc", "xiaohongshu")
    assert info["count"] == 4  # 🏠 + a + b + c


# ----------------------------------------------------------------------
# count_body
# ----------------------------------------------------------------------

def test_count_body_wechat_no_hard_limit():
    """微信正文无硬上限，永不过限。"""
    info = count_body("字" * 5000, "wechat")
    assert info["max"] is None
    assert info["over_limit"] is False
    assert info["count"] == 5000


def test_count_body_xhs_limit():
    """小红书正文 1000 为上限。"""
    assert count_body("字" * 1000, "xiaohongshu")["over_limit"] is False
    over = count_body("字" * 1001, "xiaohongshu")
    assert over["over_limit"] is True
    assert over["remaining"] == -1


def test_count_title_invalid_platform_raises():
    """非法平台应抛出 ValueError。"""
    with pytest.raises(ValueError):
        count_title("标题", "unknown")


# ----------------------------------------------------------------------
# validate_script：微信
# ----------------------------------------------------------------------

def test_validate_wechat_valid():
    """微信合规文案：标题 21 中文 + 正文 + 无标签 → 无违规。"""
    errors = validate_script(
        platform="wechat",
        title="测" * 21,
        body="这是一段合规的图文正文内容，信息清晰。",
        tags=None,
    )
    assert errors == []


def test_validate_wechat_title_over_byte():
    """微信标题超字节 → 报标题超限。"""
    errors = validate_script(
        platform="wechat",
        title="测" * 30,  # 90 字节
        body="正文",
    )
    assert any("标题" in e for e in errors)


def test_validate_wechat_allows_rent_words():
    """微信可正常出现「出租/租房」等合规词，不报违禁。"""
    errors = validate_script(
        platform="wechat",
        title="近地铁精装两居出租",
        body="月租友好，适合租房人群。",
    )
    assert not any("违禁" in e for e in errors)


# ----------------------------------------------------------------------
# validate_script：小红书
# ----------------------------------------------------------------------

def test_validate_xhs_valid():
    """小红书合规文案：标题 20 + 正文 500 + 3 标签（合规）+ 无违禁词。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="我的宝藏小窝分享",  # 8 字
        body="搬进来住进我的新窝，采光超好，生活便利，强烈安利给大家。",
        tags=["近地铁", "精装小窝", "租房日常"],
    )
    assert errors == []


def test_validate_xhs_title_over_char():
    """小红书标题 21 字符 → 报标题超限。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="字" * 21,
        body="正文",
    )
    assert any("标题" in e for e in errors)


def test_validate_xhs_body_over_limit():
    """小红书正文 1001 字符 → 报正文超限。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="标题",
        body="字" * 1001,
    )
    assert any("正文" in e for e in errors)


def test_validate_xhs_too_many_topics():
    """小红书话题 > 10 → 报话题数量超限。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="标题",
        body="正文",
        tags=["t" + str(i) for i in range(11)],
    )
    assert any("话题标签数量" in e for e in errors)


def test_validate_xhs_topic_too_long():
    """小红书单个话题 > 20 字符 → 报话题长度超限。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="标题",
        body="正文",
        tags=["这是一个超过二十个字符的超长话题标签内容x"],  # 21 字符
    )
    assert any("话题标签" in e and "长度" in e for e in errors)


def test_validate_xhs_forbidden_word_in_body():
    """小红书正文含「出租」→ 报违禁词。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="我的小窝",
        body="这里可以出租，月租很便宜。",
    )
    assert any("违禁词" in e for e in errors)


def test_validate_xhs_forbidden_word_in_title():
    """小红书标题含「租房」→ 报违禁词。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="租房推荐好房",
        body="我的新窝。",
    )
    assert any("违禁词" in e for e in errors)


def test_validate_xhs_images_skip_when_none():
    """images=None 时跳过图片校验（生成阶段文案尚未绑定图片）。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="我的小窝",
        body="正文",
        images=None,
    )
    assert not any("图片" in e for e in errors)


def test_validate_xhs_images_min_violation():
    """小红书图片数 < 1 → 报图片数量不足。"""
    errors = validate_script(
        platform="xiaohongshu",
        title="我的小窝",
        body="正文",
        images=[],
    )
    assert any("图片数量" in e for e in errors)


def test_validate_invalid_platform_raises():
    """非法平台应抛出 ValueError。"""
    with pytest.raises(ValueError):
        validate_script(platform="unknown", title="t", body="b")
