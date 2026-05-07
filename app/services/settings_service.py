from sqlalchemy import select
from app.models.models import AppSetting

async def get_setting(session, key: str, default: str = "") -> str:
    row = await session.get(AppSetting, key)
    return row.value if row else default

async def set_setting(session, key: str, value: str):
    row = await session.get(AppSetting, key)
    if row:
        row.value = value
    else:
        session.add(AppSetting(key=key, value=value))
    await session.commit()

async def is_demo(session) -> bool:
    return (await get_setting(session, "demo_mode", "false")) == "true"

async def increment_starts(session) -> int:
    row = await session.get(AppSetting, "total_starts")
    if not row:
        row = AppSetting(key="total_starts", value="0")
        session.add(row)
    total = int(row.value) + 1
    row.value = str(total)
    await session.commit()
    return total

async def get_total_starts(session) -> int:
    return int(await get_setting(session, "total_starts", "0"))
