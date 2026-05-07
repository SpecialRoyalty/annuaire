from datetime import timedelta
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, ForbiddenWord, ModerationStrike, User
from app.config import settings

router = Router()

def contains_link(text: str) -> bool:
    t = text.lower()
    return "t.me/" in t or "telegram.me/" in t or "http://" in t or "https://" in t

@router.message(F.chat.type.in_({"group", "supergroup"}))
async def auto_moderate(message: Message):
    if not message.text or not message.from_user:
        return
    async with SessionLocal() as session:
        p = await session.scalar(select(Project).where(Project.group_id == message.chat.id, Project.moderation_enabled == True, Project.status == "active"))
        if not p:
            return

        if contains_link(message.text):
            try:
                await message.delete()
                await message.bot.ban_chat_member(message.chat.id, message.from_user.id)
            except Exception:
                pass
            user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
            if user:
                user.global_ban_count += 1
                if user.global_ban_count >= 3:
                    user.global_banned = True
                await session.commit()
            return

        words = list((await session.scalars(select(ForbiddenWord).where(ForbiddenWord.project_id == p.id))).all())
        low = message.text.lower()
        if any(w.word.lower() in low for w in words):
            try:
                await message.delete()
            except Exception:
                pass
            strike = await session.scalar(select(ModerationStrike).where(ModerationStrike.project_id == p.id, ModerationStrike.telegram_id == message.from_user.id))
            if not strike:
                strike = ModerationStrike(project_id=p.id, telegram_id=message.from_user.id, count=1)
                session.add(strike)
                days = 1
            else:
                strike.count += 1
                days = 7 if strike.count >= 2 else 1
            await session.commit()
            try:
                until = int((message.date + timedelta(days=days)).timestamp())
                await message.bot.restrict_chat_member(message.chat.id, message.from_user.id, permissions={"can_send_messages": False}, until_date=until)
            except Exception:
                pass
