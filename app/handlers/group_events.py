from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings

router = Router()

@router.message(Command("connect"))
async def connect_group(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Cette commande doit être envoyée dans le groupe à connecter.")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Utilise : /connect ID_PROJET")
        return
    pid = int(parts[1])
    async with SessionLocal() as session:
        p = await session.get(Project, pid)
        if not p:
            await message.answer("Projet introuvable.")
            return
        member = await message.bot.get_chat_member(message.chat.id, message.bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Le bot doit être administrateur du groupe.")
            return
        p.group_id = message.chat.id
        p.group_title = message.chat.title
        p.status = "pending_review"
        try:
            p.member_count = await message.bot.get_chat_member_count(message.chat.id)
        except Exception:
            pass
        await session.commit()
    pin_text = f"🔗 Lien officiel du groupe\n\nSi le lien change ou saute, retrouve l’accès ici : @{settings.BOT_USERNAME}"
    sent = await message.answer(pin_text)
    try:
        await message.bot.pin_chat_message(message.chat.id, sent.message_id, disable_notification=True)
    except Exception:
        await message.answer("⚠️ Je n’ai pas réussi à épingler le message. Vérifie mes permissions.")
    await message.answer("✅ Groupe connecté. La demande passe maintenant en validation.")

@router.my_chat_member()
async def bot_status_changed(event: ChatMemberUpdated):
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    if event.chat.type not in ("group", "supergroup"):
        return
    if old in ("administrator", "member") and new in ("left", "kicked"):
        async with SessionLocal() as session:
            p = await session.scalar(select(Project).where(Project.group_id == event.chat.id, Project.status.in_(["active", "pending_review", "pending_bot"])))
            if not p:
                return
            p.bot_warning_count += 1
            owner = await session.get(User, p.owner_user_id)
            if p.bot_warning_count >= settings.MAX_BOT_WARNINGS:
                p.status = "banned"
                if owner:
                    owner.can_list = False
                msg = f"🚫 Ton groupe {p.title} a été retiré définitivement.\n\nMotif : retrait répété du bot administrateur."
            else:
                msg = f"⚠️ Le bot n’est plus administrateur de ton groupe {p.title}.\n\nAvertissement : {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}"
            await session.commit()
            if owner:
                try:
                    await event.bot.send_message(owner.telegram_id, msg)
                except Exception:
                    pass
