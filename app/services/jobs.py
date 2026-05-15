import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings
from app.keyboards.common import kb
from app.services.notify_service import notify_admins

async def cancel_projects_without_bot(bot):
    async with SessionLocal() as session:
        limit = datetime.utcnow() - timedelta(hours=settings.PENDING_CONNECT_HOURS)
        projects = list((await session.scalars(
            select(Project).where(
                Project.status == "approved_waiting_bot",
                Project.group_id.is_(None),
                Project.approved_at < limit
            )
        )).all())
        for p in projects:
            p.status = "cancelled_no_bot"
            owner = await session.get(User, p.owner_user_id)
            if owner:
                try: await bot.send_message(owner.telegram_id, f"❌ Listing annulé : le bot n’a pas été ajouté dans les {settings.PENDING_CONNECT_HOURS} heures.")
                except Exception: pass
            await notify_admins(bot, f"❌ Listing annulé automatiquement\n\nProjet : {p.title}\nMotif : bot non ajouté dans les {settings.PENDING_CONNECT_HOURS}h.")
        await session.commit()

async def refresh_member_counts(bot):
    async with SessionLocal() as session:
        projects = list((await session.scalars(select(Project).where(Project.status == "active", Project.group_id.is_not(None)))).all())
        for p in projects:
            try:
                new_count = await bot.get_chat_member_count(p.group_id)
                old = p.member_count or new_count
                p.member_count_previous = old
                p.member_count = new_count
                p.growth_last_sync = new_count - old
                p.last_member_sync_at = datetime.utcnow()
            except Exception:
                pass
        await session.commit()

async def send_daily_votes(bot):
    async with SessionLocal() as session:
        projects = list((await session.scalars(select(Project).where(Project.status == "active", Project.group_id.is_not(None)))).all())
    for p in projects:
        try:
            msg = await bot.send_message(
                p.group_id,
                "⭐ Donne ton avis sur le groupe\n\nTa note aide le groupe à monter dans le classement Tous Les Liens.",
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
    try: await bot.delete_message(chat_id, message_id)
    except Exception: pass

def setup_jobs(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cancel_projects_without_bot, "interval", minutes=15, args=[bot])
    scheduler.add_job(refresh_member_counts, "interval", minutes=30, args=[bot])
    scheduler.add_job(send_daily_votes, "interval", hours=24, args=[bot])
    scheduler.start()
    return scheduler
