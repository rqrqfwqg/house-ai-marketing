"""
现场验证脚本：针对 45003 修复新增行为做独立验证（不依赖 DB / 网络）。

覆盖：
1. truncate_title 边界：微信字节口径(21中文/emoji/空)、小红书字符口径(25→20)。
2. PUT 路由截断逻辑（services.platform_rules.truncate_title 直接复用）：
   模拟「编辑超长标题入库前被截断」行为，断言落库标题 ≤ 平台上限。
3. _build_digest 超长正文 → 摘要 ≤ 120 字符（防御 45004）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.platform_rules import Platform, truncate_title
from services.wechat_service import WechatService, WECHAT_DIGEST_MAX_LEN

WECHAT_MAX_BYTES = 64


def blen(s: str) -> int:
    return len(s.encode("utf-8"))


def _check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label} {detail}")
    return cond


# ----------------------------------------------------------------------
# 1. truncate_title 边界
# ----------------------------------------------------------------------
ok = True

# 微信 21 中文 -> 63 字节，不截断，≤64
t21 = "测" * 21
r = truncate_title(t21, Platform.WECHAT.value)
ok &= _check("微信21中文不截断且≤64B",
             r == t21 and blen(r) == 63, f"got bytes={blen(r)}")

# 微信 22 中文 -> 66 字节超长 -> 截断 + 省略号，且 ≤64
t22 = "测" * 22
r = truncate_title(t22, Platform.WECHAT.value)
ok &= _check("微信22中文截断且≤64B",
             blen(r) <= WECHAT_MAX_BYTES and r.endswith("…"), f"bytes={blen(r)}")

# emoji 串 -> 不残缺且 ≤64B
emoji_title = "🏠" * 20  # 80 字节
r = truncate_title(emoji_title, Platform.WECHAT.value)
body = r[: -len("…")]
no_broken = (body.count("🏠") == len(body)) and blen(r) <= WECHAT_MAX_BYTES
ok &= _check("微信emoji不残缺且≤64B", no_broken, f"bytes={blen(r)} emoji_count={body.count('🏠')}")

# 空标题 -> 「无标题」
r = truncate_title("", Platform.WECHAT.value)
ok &= _check("微信空标题回退无标题", r == "无标题", f"got={r!r}")
r = truncate_title("   \n ", Platform.WECHAT.value)
ok &= _check("微信纯空白回退无标题", r == "无标题", f"got={r!r}")

# 小红书 25 字 -> 20 字
x25 = "字" * 25
r = truncate_title(x25, Platform.XIAOHONGSHU.value)
ok &= _check("小红书25字→20字", len(r) == 20, f"len={len(r)}")

# 小红书 20 字 -> 不变
x20 = "字" * 20
r = truncate_title(x20, Platform.XIAOHONGSHU.value)
ok &= _check("小红书20字不变", r == x20)


# ----------------------------------------------------------------------
# 2. PUT 路由截断逻辑（复用 truncate_title，模拟落库前截断）
# ----------------------------------------------------------------------
def simulate_put_truncation(platform: str, incoming_title: str) -> str:
    """复刻 routes/script.py:181-188 的入库前截断逻辑。"""
    new_title = incoming_title
    if platform and Platform.is_valid(platform):
        new_title = truncate_title(new_title, platform)
    # 此处 new_title 即「落库标题」
    return new_title


# 微信：超长中文编辑入库 -> 截断
db_title = simulate_put_truncation("wechat", "测" * 30)
ok &= _check("PUT微信超长落库标题≤64B", blen(db_title) <= WECHAT_MAX_BYTES,
             f"bytes={blen(db_title)}")

# 微信：正常标题编辑入库 -> 不变
db_title = simulate_put_truncation("wechat", "北京海淀两居出售")
ok &= _check("PUT微信正常标题保持", db_title == "北京海淀两居出售")

# 微信：超长带 emoji 编辑入库 -> 不残缺且 ≤64B
db_title = simulate_put_truncation("wechat", "🏠" * 20)
emoji_body = db_title.rsplit("…", 1)[0]  # 去掉末尾省略号后只剩完整 emoji
ok &= _check("PUT微信emoji落库不残缺≤64B",
             db_title.count("🏠") == len(emoji_body) and blen(db_title) <= WECHAT_MAX_BYTES,
             f"bytes={blen(db_title)} emoji_count={db_title.count('🏠')}")

# 小红书：超长编辑入库 -> 20 字符
db_title = simulate_put_truncation("xiaohongshu", "字" * 30)
ok &= _check("PUT小红书超长落库→20字", len(db_title) == 20, f"len={len(db_title)}")

# 非法平台不应抛异常（路由里 is_valid 守卫），原样落库
db_title = simulate_put_truncation("unknown", "测" * 30)
ok &= _check("PUT非法平台不抛异常原样", db_title == "测" * 30)


# ----------------------------------------------------------------------
# 3. _build_digest 超长正文 → ≤120 字符（防御 45004）
# ----------------------------------------------------------------------
svc = WechatService(app_id="t", app_secret="t")
long_body = "这是一段非常长的房源正文内容，" * 50  # 远超 120 字符，且无句末标点
digest = svc._build_digest(long_body)
ok &= _check("_build_digest超长正文≤120字符",
             len(digest) <= WECHAT_DIGEST_MAX_LEN, f"len={len(digest)}")

# 短正文不变
short_body = "三居室，南北通透，近地铁。"
digest = svc._build_digest(short_body)
ok &= _check("_build_digest短正文不变", digest == short_body)

# 含句末标点截断到第一句
sentence_body = "今天推荐一套好房。这套房子采光极佳，适合家庭居住。"
digest = svc._build_digest(sentence_body)
ok &= _check("_build_digest按句截断", digest == "今天推荐一套好房。", f"got={digest!r}")

# 空正文回退
digest = svc._build_digest("")
ok &= _check("_build_digest空正文回退", digest == "房源推荐")

print("\n=== 现场验证结果:", "ALL PASS" if ok else "HAS FAILURES", "===")
sys.exit(0 if ok else 1)
