import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.db.init_db import init_db
from app.services.jobs import setup_jobs
from app.handlers import start, info, browse, listing, suggestions, owner, admin, group_events, moderation_auto, daily_vote, demo, dbcheck

async def main():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN manquant")
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL manquant")

    bot = Bot(settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(dbcheck.router)
    dp.include_router(demo.router)
    dp.include_router(browse.router)
    dp.include_router(listing.router)
    dp.include_router(suggestions.router)
    dp.include_router(owner.router)
    dp.include_router(admin.router)
    dp.include_router(group_events.router)
    dp.include_router(daily_vote.router)
    dp.include_router(moderation_auto.router)

    await init_db()
    setup_jobs(bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
