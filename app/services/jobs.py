from datetime import datetime, timedelta
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import SessionLocal
from app.models.models import Project, User
from app.config import settings

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
                msg = f"🚫 Ton groupe {p.title} a été retiré.\n\nMotif : bot non ajouté après plusieurs rappels."
            else:
                msg = f"⏰ Le bot n’a toujours pas été ajouté pour {p.title}.\n\nAvertissement : {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}\n\nAjoute le bot admin puis envoie /connect {p.id} dans le groupe."
            if owner:
                try:
                    await bot.send_message(owner.telegram_id, msg)
                except Exception:
                    pass
            for admin_id in settings.SUPER_ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, f"⏰ Projet sans bot depuis +1h : {p.title} — warning {p.bot_warning_count}/{settings.MAX_BOT_WARNINGS}")
                except Exception:
                    pass
        await session.commit()

def setup_jobs(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_pending_bot, "interval", minutes=30, args=[bot])
    scheduler.start()
    return scheduler
