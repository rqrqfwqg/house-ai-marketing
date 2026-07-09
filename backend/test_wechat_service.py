"""
微信公众号服务（wechat_service.py）回归测试。

验证本次 Bug 修复的两处核心改动：
1. ``_truncate_title_by_bytes`` —— 按 UTF-8 字节（而非字符数）截断标题，
   避免超长中文标题触发微信 ``[45003] title size out of limit``。
2. ``_classify_wechat_error`` —— 把微信错误码转成可读中文，
   未知码剔除 hint/rid 内部调试串。

运行：在 backend 目录下执行
    pytest test_wechat_service.py -v
"""

import os
import sys

import pytest

# 确保 backend 根目录在 sys.path，使 `from services...` 与 `from config import settings` 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.wechat_service import WechatService  # noqa: E402

# 微信标题字节上限（与源码 WECHAT_TITLE_MAX_LEN 保持一致）
TITLE_MAX_BYTES = 64
# 省略号「…」的 UTF-8 字节数
ELLIPSIS = "…"
ELLIPSIS_BYTES = len(ELLIPSIS.encode("utf-8"))


def _svc() -> WechatService:
    """构造一个不触发「未配置」告警的实例（显式传入 appid/secret）。"""
    return WechatService(app_id="test_appid", app_secret="test_secret")


def _byte_len(s: str) -> int:
    """返回字符串的 UTF-8 字节长度。"""
    return len(s.encode("utf-8"))


# ----------------------------------------------------------------------
# _truncate_title_by_bytes 测试
# ----------------------------------------------------------------------

# 参数化用例：(名称, 输入标题, 是否应被截断/带省略号)
TRUNCATE_CASES = [
    ("纯中文超长", "测" * 30, True),          # 30*3=90 字节 > 64
    ("英文超长", "a" * 100, True),            # 100 字节 > 64
    ("中英混合", "测" * 10 + "a" * 50, True),  # 30+50=80 字节 > 64
    ("emoji超长", "🏠" * 20, True),           # 20*4=80 字节 > 64
    ("短标题", "中文短标题", False),           # 15 字节 < 64
    ("恰好64字节", "测" * 21 + "a", False),     # 21*3+1=64 字节，不截断
]


def test_truncate_short_title_unchanged():
    """短标题不应被截断，且不加省略号。"""
    svc = _svc()
    title = "北京海淀两居出售"
    result = svc._truncate_title_by_bytes(title)
    assert result == title
    assert not result.endswith(ELLIPSIS)
    assert _byte_len(result) <= TITLE_MAX_BYTES


@pytest.mark.parametrize("name,title,should_truncate", TRUNCATE_CASES)
def test_truncate_byte_limit(name, title, should_truncate):
    """所有结果字节长度必须 ≤64；超长用例应以省略号结尾。"""
    svc = _svc()
    result = svc._truncate_title_by_bytes(title)

    # 关键断言：结果字节长度严格不超过微信上限
    assert _byte_len(result) <= TITLE_MAX_BYTES, (
        f"[{name}] 结果字节长度 {_byte_len(result)} 超过上限 {TITLE_MAX_BYTES}"
    )

    if should_truncate:
        assert result.endswith(ELLIPSIS), f"[{name}] 超长标题应以省略号结尾"
    else:
        assert not result.endswith(ELLIPSIS), f"[{name}] 未超长标题不应加省略号"


def test_truncate_no_broken_multibyte_chinese():
    """纯中文截断后不得出现残缺字符（逐字符累计，绝不切断多字节）。"""
    svc = _svc()
    result = svc._truncate_title_by_bytes("测" * 30)
    # 去掉末尾省略号，剩余应全是完整中文字符
    body = result[: -len(ELLIPSIS)]
    assert body == "测" * len(body), "结果末尾出现残缺字符"
    # 字节累计应为整数倍的 3 字节（纯中文）
    assert _byte_len(body) == len(body) * 3
    # 总长 = 正文中文字节 + 省略号字节，且 ≤ 64
    assert _byte_len(result) == _byte_len(body) + ELLIPSIS_BYTES <= TITLE_MAX_BYTES


def test_truncate_no_broken_multibyte_emoji():
    """4 字节 emoji 截断后同样不被切断（证明多字节安全）。"""
    svc = _svc()
    result = svc._truncate_title_by_bytes("🏠" * 20)
    body = result[: -len(ELLIPSIS)]
    # 去掉省略号后，所有 emoji 必须完整（count 应为整数）
    assert body.count("🏠") == len(body), "emoji 被切断，出现残缺字符"
    assert _byte_len(body) == len(body) * 4  # 每个 emoji 4 字节
    assert result.endswith(ELLIPSIS)
    assert _byte_len(result) <= TITLE_MAX_BYTES


def test_truncate_exactly_64_bytes_kept_intact():
    """恰好 64 字节的输入原样返回（不截断、不加省略号）。"""
    svc = _svc()
    title = "测" * 21 + "a"  # 63 + 1 = 64 字节
    result = svc._truncate_title_by_bytes(title)
    assert result == title
    assert _byte_len(result) == TITLE_MAX_BYTES
    assert not result.endswith(ELLIPSIS)


def test_truncate_empty_string_fallback():
    """空字符串应回退为「无标题」。"""
    svc = _svc()
    result = svc._truncate_title_by_bytes("")
    assert result == "无标题"
    assert _byte_len(result) <= TITLE_MAX_BYTES


def test_truncate_whitespace_only_fallback():
    """纯空白标题应回退为「无标题」。"""
    svc = _svc()
    result = svc._truncate_title_by_bytes("   \t\n  ")
    assert result == "无标题"
    assert _byte_len(result) <= TITLE_MAX_BYTES


def test_truncate_custom_max_bytes():
    """自定义 max_bytes 参数应生效（保留字节截断语义）。"""
    svc = _svc()
    # 16 字节上限，省略号占 3 字节，预算 13 字节 -> 4 个中文(12)+省略号(3)=15
    result = svc._truncate_title_by_bytes("测" * 10, max_bytes=16)
    assert _byte_len(result) <= 16
    assert result.endswith(ELLIPSIS)


# ----------------------------------------------------------------------
# _classify_wechat_error 测试
# ----------------------------------------------------------------------

def test_classify_45003_title_too_long():
    """45003 应给出清晰的「标题超长」中文提示。"""
    svc = _svc()
    msg = svc._classify_wechat_error(45003, "title size out of limit")
    assert "标题" in msg
    assert "64" in msg  # 应说明 64 字节限制
    assert "截断" in msg


def test_classify_40001_auth_error():
    """40001 应给出鉴权类中文提示。"""
    svc = _svc()
    msg = svc._classify_wechat_error(40001, "invalid access_token")
    assert "access_token" in msg
    assert "无效" in msg or "过期" in msg


def test_classify_unknown_code_strips_hint_and_rid():
    """未知错误码应剔除 hint/rid 内部串，只保留可读内容。"""
    svc = _svc()
    raw = "title size out of limit hint: [internal debug info] rid: abc123xyz"
    msg = svc._classify_wechat_error(99999, raw)
    assert "hint" not in msg
    assert "rid" not in msg
    assert "99999" in msg  # 错误码应保留便于排查
    assert "title size out of limit" in msg  # 可读部分应保留


def test_classify_unknown_code_plain_message():
    """未知码且无 hint/rid 时，原样保留可读信息并带错误码。"""
    svc = _svc()
    msg = svc._classify_wechat_error(88888, "some readable error")
    assert "88888" in msg
    assert "some readable error" in msg
    assert "错误码" in msg


def test_classify_none_errcode():
    """errcode 为 None 时按未知码（0）处理并保留原始 errmsg。"""
    svc = _svc()
    msg = svc._classify_wechat_error(None, "network timeout")
    assert "错误码 0" in msg
    assert "network timeout" in msg


def test_classify_string_errcode_matches_known():
    """errcode 传入字符串 "45003" 时仍应命中已知码映射。"""
    svc = _svc()
    msg = svc._classify_wechat_error("45003", "title size out of limit")
    assert "标题" in msg
    assert "64" in msg


def test_classify_48001_permission_error():
    """48001 权限类错误应给出认证提示。"""
    svc = _svc()
    msg = svc._classify_wechat_error(48001, "api unauthorized")
    assert "权限" in msg or "认证" in msg
