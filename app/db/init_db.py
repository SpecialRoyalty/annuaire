from sqlalchemy import select
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.models import Category, AppSetting

DEFAULT_CATEGORIES = [
    "Business", "Crypto", "Paris sportifs", "Bons plans", "Gaming",
    "Formation", "Tech", "Divertissement", "Communauté", "Autre"
]

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        for i, name in enumerate(DEFAULT_CATEGORIES):
            exists = await session.scalar(select(Category).where(Category.name == name))
            if not exists:
                session.add(Category(name=name, position=i))

        for key, value in {
            "demo_mode": "false",
            "total_starts": "0"
        }.items():
            exists = await session.get(AppSetting, key)
            if not exists:
                session.add(AppSetting(key=key, value=value))
        await session.commit()
