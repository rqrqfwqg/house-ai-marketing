"""
PUT /{script_id} 标题截断回归测试（针对 45003 修复新增的入库前截断路径）。

测试对象：``routes/script.py::update_script`` 中 181-188 行的入库前截断逻辑
（编辑超长标题时优先截断落库，而非 400）。

做法：用内存 SQLite（StaticPool 共享单库）替换 ``database.AsyncSessionLocal``，
在导入路由**之前**完成替换，使路由内部 ``async with AsyncSessionLocal()``
直接命中测试库；随后调用真实 ``update_script``，断言返回（=落库）标题已截断。

运行（backend 目录下）：
    pytest test_script_put_truncation.py -v
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# 1) 先准备好内存引擎与测试 session 工厂
ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(
    ENGINE, class_=AsyncSession, expire_on_commit=False
)

# 2) 覆盖 database 模块里的 AsyncSessionLocal（路由内部直接用它）
import database  # noqa: E402

database.AsyncSessionLocal = TestSessionLocal

# 3) 导入模型 / schema（models 共用 database.Base，表结构一致）
from database import Base  # noqa: E402
from models import Script, House  # noqa: E402
from schemas import ScriptUpdateRequest  # noqa: E402

# 4) 最后再导入路由，使其 ``from database import AsyncSessionLocal`` 绑定到测试工厂
from routes.script import update_script  # noqa: E402

WECHAT_MAX_BYTES = 64
XHS_MAX_CHARS = 20


def _blen(s: str) -> int:
    return len(s.encode("utf-8"))


async def _seed(platform: str, title: str, body: str = "正文内容") -> int:
    """清空并建表 + 写入一个 House 与一个绑定平台的 Script，返回 script_id。

    由于 StaticPool 让内存库跨 asyncio.run 复用，每个用例开头都先
    drop_all + create_all 保证干净环境，避免跨用例主键冲突。
    """
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as s:
        house = House(id=1)
        s.add(house)
        await s.flush()
        script = Script(
            id=1, house_id=1, title=title, body=body, platform=platform
        )
        s.add(script)
        await s.commit()
    return 1


async def _put(script_id: int, title: str) -> str:
    """调用真实 update_script，返回落库后的标题。"""
    req = ScriptUpdateRequest(title=title)
    resp = await update_script(script_id, req)  # db 参数路由内部未使用
    return resp.title


# ----------------------------------------------------------------------
# 微信：超长中文标题编辑入库 -> 截断且 ≤64 字节（核心回归点）
# ----------------------------------------------------------------------
def test_put_wechat_oversized_title_truncated():
    asyncio.run(_seed("wechat", "原始标题"))
    stored = asyncio.run(_put(1, "测" * 30))
    assert _blen(stored) <= WECHAT_MAX_BYTES, (
        f"落库微信标题 {_blen(stored)} 字节，超出 64 上限"
    )
    # 超长 30 中文必被截断并带省略号
    assert stored.endswith("…")


# ----------------------------------------------------------------------
# 微信：正常标题编辑入库 -> 保持原样，不截断
# ----------------------------------------------------------------------
def test_put_wechat_normal_title_unchanged():
    asyncio.run(_seed("wechat", "原始标题"))
    stored = asyncio.run(_put(1, "北京海淀两居精装出售"))
    assert stored == "北京海淀两居精装出售"


# ----------------------------------------------------------------------
# 微信：超长 emoji 标题编辑入库 -> 不残缺且 ≤64 字节
# ----------------------------------------------------------------------
def test_put_wechat_emoji_title_not_broken():
    asyncio.run(_seed("wechat", "原始标题"))
    stored = asyncio.run(_put(1, "🏠" * 20))
    body = stored.rsplit("…", 1)[0]
    assert stored.count("🏠") == len(body), "emoji 被切断，出现残缺字符"
    assert _blen(stored) <= WECHAT_MAX_BYTES


# ----------------------------------------------------------------------
# 小红书：超长标题编辑入库 -> 按字符截断至 20 字
# ----------------------------------------------------------------------
def test_put_xiaohongshu_oversized_title_truncated():
    asyncio.run(_seed("xiaohongshu", "原始标题"))
    stored = asyncio.run(_put(1, "字" * 30))
    assert len(stored) == XHS_MAX_CHARS, f"落库小红书标题长度 {len(stored)}，应为 20"
