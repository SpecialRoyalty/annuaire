import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings
from app.keyboards.common import kb

async def check_pending_bot(bot):
    async with SessionLocal() as session:
        limit = datetime.utcnow() - timedelta(hours=settings.PENDING_CONNECT_HOURS)
        projects = list((await session.scalars(select(Project).where(Project.status == "pending_bot", Project.listed_at < limit))).all())
        for p in projects:
            p.bot_warning_count += 1
            owner = await session.get(User, p.owner_user_id)
            if p.bot_warning_count >= settings.MAX_BOT_WARNINGS:
                p.status = "banned"
                if owner:
                    owner.can_list = False
                msg = f"Ton groupe {p.title} a été retiré. Motif : bot non ajouté après plusieurs rappels."
            else:
                msg = f"Le bot n’a toujours pas été ajouté pour {p.title}. Avertissement {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}. Ajoute le bot admin puis /connect {p.id}."
            if owner:
                try: await bot.send_message(owner.telegram_id, msg)
                except Exception: pass
            for aid in settings.SUPER_ADMIN_IDS:
                try: await bot.send_message(aid, f"Projet sans bot depuis +1h : {p.title} — warning {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}")
                except Exception: pass
        await session.commit()

async def send_daily_votes(bot):
    async with SessionLocal() as session:
        projects = list((await session.scalars(select(Project).where(Project.status == "active", Project.group_id.is_not(None)))).all())
        for p in projects:
            text = "⭐ Donne ton avis sur le groupe\n\nTa note aide le groupe à monter dans le classement Tous Les Liens."
            try:
                msg = await bot.send_message(
                    p.group_id,
                    text,
                    reply_markup=kb([
                        [("1 ⭐", f"daily_vote:{p.id}:1"), ("2 ⭐", f"daily_vote:{p.id}:2")],
                        [("3 ⭐", f"daily_vote:{p.id}:3"), ("4 ⭐", f"daily_vote:{p.id}:4")],
                        [("5 ⭐", f"daily_vote:{p.id}:5")]
                    ])
                )
                asyncio.create_task(delete_later(bot, p.group_id, msg.message_id))
            except Exception:
                pass

async def delete_later(bot, chat_id, message_id):
    await asyncio.sleep(7200)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def setup_jobs(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_pending_bot, "interval", minutes=30, args=[bot])
    scheduler.add_job(send_daily_votes, "interval", hours=24, args=[bot])
    scheduler.start()
    return scheduler
