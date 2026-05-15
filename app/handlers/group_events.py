from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings
from app.services.notify_service import notify_admins

router = Router()

PIN_TEXT = (
    "⚠️ Ne perds jamais l’accès au groupe\n\n"
    "Si ce groupe saute ou change de lien :\n"
    f"le nouveau lien sera toujours disponible sur @{settings.BOT_USERNAME}\n\n"
    "Rejoins aussi les meilleurs groupes Telegram classés par catégorie."
)

async def connect_project_to_group(bot, chat_id: int, chat_title: str | None, owner_telegram_id: int | None = None, project_id: int | None = None):
    async with SessionLocal() as session:
        project = None
        if project_id is not None:
            project = await session.get(Project, project_id)
        elif owner_telegram_id is not None:
            owner = await session.scalar(select(User).where(User.telegram_id == owner_telegram_id))
            if owner:
                project = await session.scalar(
                    select(Project).where(
                        Project.owner_user_id == owner.id,
                        Project.status == "approved_waiting_bot",
                        Project.group_id.is_(None)
                    ).order_by(Project.approved_at.desc())
                )
        if not project:
            return False, "Aucun listing approuvé en attente trouvé pour ce compte."
        member = await bot.get_chat_member(chat_id, bot.id)
        if member.status not in ("administrator", "creator"):
            return False, "Le bot doit être administrateur."
        project.group_id = chat_id
        project.group_title = chat_title
        project.status = "active"
        project.moderation_enabled = project.wants_moderation
        try:
            count = await bot.get_chat_member_count(chat_id)
            project.member_count_previous = project.member_count or count
            project.member_count = count
            project.growth_last_sync = 0
        except Exception:
            pass
        sent = await bot.send_message(chat_id, PIN_TEXT)
        project.pin_message_id = sent.message_id
        try:
            await bot.pin_chat_message(chat_id, sent.message_id, disable_notification=True)
        except Exception:
            pass
        owner = await session.get(User, project.owner_user_id)
        await session.commit()
        if owner:
            try: await bot.send_message(owner.telegram_id, f"✅ Tout est prêt.\n\nVotre groupe {project.title} est maintenant listé sur Tous Les Liens.")
            except Exception: pass
        await notify_admins(bot, f"🤖 Groupe connecté automatiquement\n\nProjet : {project.title}\nGroupe : {chat_title}\nID : {chat_id}")
    return True, "✅ Groupe connecté et listé."

@router.my_chat_member()
async def bot_status(event: ChatMemberUpdated):
    if event.chat.type not in ("group", "supergroup"):
        return
    new_status = event.new_chat_member.status
    if new_status in ("administrator", "member"):
        ok, msg = await connect_project_to_group(event.bot, event.chat.id, event.chat.title, owner_telegram_id=event.from_user.id)
        if ok:
            try: await event.bot.send_message(event.chat.id, msg)
            except Exception: pass
        return
    if new_status in ("left", "kicked"):
        async with SessionLocal() as session:
            p = await session.scalar(select(Project).where(Project.group_id == event.chat.id, Project.status.in_(["active", "approved_waiting_bot"])))
            if not p: return
            p.bot_warning_count += 1
            owner = await session.get(User, p.owner_user_id)
            if p.bot_warning_count >= settings.MAX_BOT_WARNINGS:
                p.status = "deleted_bot_removed"
                if owner: owner.can_list = False
                msg = f"🚫 Ton groupe {p.title} a été retiré définitivement. Motif : retrait répété du bot."
                staff = f"🚫 Projet supprimé automatiquement : {p.title}\nOwner blacklisté."
                try: await event.bot.leave_chat(event.chat.id)
                except Exception: pass
            else:
                msg = f"⚠️ Le bot n’est plus administrateur de {p.title}. Warning {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}."
                staff = f"⚠️ Bot retiré : {p.title} — {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}"
            await session.commit()
            if owner:
                try: await event.bot.send_message(owner.telegram_id, msg)
                except Exception: pass
            await notify_admins(event.bot, staff)

@router.message(Command("connect"))
async def connect_fallback(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Cette commande doit être envoyée dans le groupe."); return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Utilise : /connect ID_PROJET"); return
    ok, msg = await connect_project_to_group(message.bot, message.chat.id, message.chat.title, project_id=int(parts[1]))
    await message.answer(msg)
