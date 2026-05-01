from sqlalchemy import select
from app.db.models import Base, Category
from app.db.session import engine, SessionLocal

DEFAULT_CATEGORIES = [
    "Business", "Crypto", "Paris sportifs", "Bons plans", "Influenceurs",
    "Communautés privées", "Gaming", "Rencontre", "Formation", "Tech",
    "Divertissement", "Autre"
]

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        existing = (await session.execute(select(Category))).scalars().all()
        if not existing:
            for idx, name in enumerate(DEFAULT_CATEGORIES, start=1):
                session.add(Category(name=name, position=idx))
            await session.commit()
