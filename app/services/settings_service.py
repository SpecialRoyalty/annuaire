from datetime import datetime
from app.models.models import AppSetting

async def get_setting(session, key: str, default: str = "") -> str:
    s = await session.get(AppSetting, key)
    return s.value if s else default

async def set_setting(session, key: str, value: str):
    s = await session.get(AppSetting, key)
    if s:
        s.value = value
        s.updated_at = datetime.utcnow()
    else:
        s = AppSetting(key=key, value=value)
        session.add(s)
    await session.commit()

async def is_demo(session) -> bool:
    return (await get_setting(session, "demo_mode", "false")) == "true"

async def increment_starts(session) -> int:
    s = await session.get(AppSetting, "total_starts")
    if not s:
        s = AppSetting(key="total_starts", value="0")
        session.add(s)
    total = int(s.value) + 1
    s.value = str(total)
    s.updated_at = datetime.utcnow()
    await session.commit()
    return total

async def get_total_starts(session) -> int:
    return int(await get_setting(session, "total_starts", "0"))
