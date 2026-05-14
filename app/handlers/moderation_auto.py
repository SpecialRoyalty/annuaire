from datetime import timedelta
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, ForbiddenWord, ModerationStrike
from app.services.network_ban import register_group_ban
router=Router()
def has_link(t:str)->bool:
    s=t.lower(); return "t.me/" in s or "telegram.me/" in s or "http://" in s or "https://" in s

@router.message(F.chat.type.in_({"group","supergroup"}))
async def auto(message:Message):
    if not message.text or not message.from_user: return
    async with SessionLocal() as session:
        p=await session.scalar(select(Project).where(Project.group_id==message.chat.id, Project.status=="active", Project.moderation_enabled==True))
        if not p: return
        if has_link(message.text):
            try: await message.delete(); await message.bot.ban_chat_member(message.chat.id,message.from_user.id)
            except Exception: pass
            await register_group_ban(message.bot,message.from_user.id,source_group_id=message.chat.id,source_project_id=p.id,reason="lien_externe")
            return
        words=list((await session.scalars(select(ForbiddenWord).where(ForbiddenWord.project_id==p.id))).all())
        if any(w.word in message.text.lower() for w in words):
            try: await message.delete()
            except Exception: pass
            strike=await session.scalar(select(ModerationStrike).where(ModerationStrike.project_id==p.id, ModerationStrike.telegram_id==message.from_user.id))
            days=1
            if not strike: session.add(ModerationStrike(project_id=p.id,telegram_id=message.from_user.id,count=1))
            else: strike.count += 1; days=7
            await session.commit()
            try: await message.bot.restrict_chat_member(message.chat.id,message.from_user.id,permissions={"can_send_messages":False},until_date=int((message.date+timedelta(days=days)).timestamp()))
            except Exception: pass
