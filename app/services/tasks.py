from datetime import datetime, timezone
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import ProjectStatus, User
from app.services import repo

settings = get_settings()

async def notify_super_admins(bot: Bot, text: str):
    for admin_id in settings.super_admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass

async def hourly_checks(bot: Bot):
    async with SessionLocal() as session:
        stale = await repo.stale_needs_bot(session)
        for p in stale:
            await notify_super_admins(bot, f"⏰ Projet sans bot depuis +1h : {p.title} #{p.id}")
            try:
                owner = await session.get(User, p.owner_user_id)
                if owner:
                    await bot.send_message(owner.telegram_id, "⏰ Rappel : ajoute @{} comme admin dans ton groupe puis envoie /connect dans le groupe.".format(settings.BOT_USERNAME))
            except Exception:
                pass

        to_delist = await repo.inactive_too_long(session)
        for p in to_delist:
            p.status = ProjectStatus.INACTIVE.value
            await notify_super_admins(bot, f"🔴 Délisting automatique : {p.title} lien inactif depuis 10 jours.")
        await session.commit()


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    scheduler.add_job(hourly_checks, "interval", hours=1, args=[bot], id="hourly_checks", replace_existing=True)
    scheduler.start()
    return scheduler
