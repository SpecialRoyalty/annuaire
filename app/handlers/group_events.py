from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings
from app.services.notify_service import notify_admins
router=Router()
PIN_TEXT=("⚠️ Ne perds jamais l’accès au groupe\n\nSi ce groupe saute ou change de lien :\n"+f"le nouveau lien sera toujours disponible sur @{settings.BOT_USERNAME}\n\n"+"Rejoins aussi les meilleurs groupes Telegram classés par catégorie.")

async def connect_project_to_group(bot,chat_id:int,chat_title:str|None,project_id:int):
    async with SessionLocal() as session:
        p=await session.get(Project,project_id)
        if not p: return False,"Projet introuvable."
        member=await bot.get_chat_member(chat_id,bot.id)
        if member.status not in ("administrator","creator"): return False,"Le bot doit être administrateur."
        p.group_id=chat_id; p.group_title=chat_title; p.status="active"; p.moderation_enabled=p.wants_moderation
        try:
            count=await bot.get_chat_member_count(chat_id); p.member_count_previous=p.member_count or count; p.member_count=count
        except Exception: pass
        sent=await bot.send_message(chat_id,PIN_TEXT); p.pin_message_id=sent.message_id
        try: await bot.pin_chat_message(chat_id,sent.message_id,disable_notification=True)
        except Exception: pass
        owner=await session.get(User,p.owner_user_id); await session.commit()
        if owner:
            try: await bot.send_message(owner.telegram_id,f"✅ Tout est prêt.\n\nVotre groupe {p.title} est maintenant listé sur Tous Les Liens.")
            except Exception: pass
        await notify_admins(bot,f"🤖 Groupe connecté et actif\n\nProjet : {p.title}\nGroupe : {chat_title}\nID : {chat_id}")
    return True,"✅ Groupe connecté et listé."

@router.message(Command("start"))
async def startgroup(message:Message):
    if message.chat.type not in ("group","supergroup"): return
    parts=message.text.split(maxsplit=1)
    if len(parts)<2 or not parts[1].startswith("connect_"): return
    raw=parts[1].replace("connect_","",1)
    if not raw.isdigit(): return
    ok,msg=await connect_project_to_group(message.bot,message.chat.id,message.chat.title,int(raw)); await message.answer(msg)

@router.message(Command("connect"))
async def connect(message:Message):
    if message.chat.type not in ("group","supergroup"): await message.answer("Cette commande doit être envoyée dans le groupe."); return
    parts=message.text.split()
    if len(parts)<2 or not parts[1].isdigit(): await message.answer("Utilise : /connect ID_PROJET"); return
    ok,msg=await connect_project_to_group(message.bot,message.chat.id,message.chat.title,int(parts[1])); await message.answer(msg)

@router.my_chat_member()
async def status(event:ChatMemberUpdated):
    if event.chat.type not in ("group","supergroup"): return
    if event.new_chat_member.status in ("left","kicked"):
        async with SessionLocal() as session:
            p=await session.scalar(select(Project).where(Project.group_id==event.chat.id, Project.status.in_(["active","pending_review","pending_bot"])))
            if not p: return
            p.bot_warning_count += 1; owner=await session.get(User,p.owner_user_id)
            if p.bot_warning_count>=settings.MAX_BOT_WARNINGS:
                p.status="banned"
                if owner: owner.can_list=False
                msg=f"🚫 Ton groupe {p.title} a été retiré définitivement."; staff=f"🚫 Projet supprimé automatiquement : {p.title}"
            else:
                msg=f"⚠️ Le bot n’est plus administrateur de {p.title}. Warning {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}."; staff=f"⚠️ Bot retiré : {p.title} — {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}"
            await session.commit()
            if owner:
                try: await event.bot.send_message(owner.telegram_id,msg)
                except Exception: pass
            await notify_admins(event.bot,staff)
