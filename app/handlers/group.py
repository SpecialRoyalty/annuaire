from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from app.config import get_settings
from app.db.session import SessionLocal
from app.services import repo

router = Router()
settings = get_settings()

PIN_TEXT = (
    "🔗 <b>Lien de secours officiel</b>\n\n"
    "Si ce groupe saute ou change de lien, retrouve le nouveau lien ici :\n"
    f"👉 @{settings.BOT_USERNAME}"
)


@router.message(Command("connect"), F.chat.type.in_({"group", "supergroup"}))
async def connect_group(message: Message, bot: Bot):
    member = await bot.get_chat_member(message.chat.id, bot.id)
    if not member or member.status not in {"administrator", "creator"}:
        await message.reply("Je dois être admin du groupe avec le droit d’épingler les messages.")
        return
    async with SessionLocal() as session:
        project = await repo.set_project_group(session, message.chat.id, message.chat.title, settings.BOT_USERNAME)
    if not project:
        await message.reply("Aucun projet en attente trouvé. Crée d’abord le listing dans le bot en privé.")
        return
    sent = await message.answer(PIN_TEXT)
    try:
        await bot.pin_chat_message(message.chat.id, sent.message_id, disable_notification=True)
    except Exception:
        await message.reply("Projet lié, mais je n’ai pas réussi à épingler. Vérifie mes permissions.")
        return
    await message.reply("✅ Groupe connecté. Le projet passe en validation super admin.")


@router.message(F.pinned_message)
async def pinned_changed(message: Message, bot: Bot):
    # Si un humain remplace le pin, on reposte le message de secours.
    async with SessionLocal() as session:
        from sqlalchemy import select
        from app.db.models import Project
        result = await session.execute(select(Project).where(Project.group_chat_id == message.chat.id))
        project = result.scalar_one_or_none()
        if not project:
            return
        project.pin_attempts += 1
        await session.commit()
        if project.pin_attempts >= 3:
            project.status = "banned"
            await session.commit()
            await message.answer("🚫 Le message de secours a été modifié 3 fois. Le groupe est retiré du listing.")
            try:
                await bot.leave_chat(message.chat.id)
            except Exception:
                pass
            return
    sent = await message.answer(PIN_TEXT)
    try:
        await bot.pin_chat_message(message.chat.id, sent.message_id, disable_notification=True)
    except Exception:
        pass
