from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.user_service import get_or_create_user

router = Router()

@router.message(Command("dbcheck"))
async def dbcheck(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        if not user.is_super_admin:
            return

        result = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        tables = [row[0] for row in result.fetchall()]

    if not tables:
        await message.answer("Aucune table trouvée dans le schema public.")
    else:
        await message.answer("Tables DB trouvées :\n\n" + "\n".join(f"• {t}" for t in tables))
