import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.db.init_db import init_db
from app.services.jobs import setup_jobs
from app.handlers import start, info, browse, demo, listing, suggestions, owner, admin, group_events, moderation_auto, daily_vote, dbcheck

async def main():
    if not settings.BOT_TOKEN: raise RuntimeError("BOT_TOKEN manquant")
    if not settings.DATABASE_URL: raise RuntimeError("DATABASE_URL manquant")
    bot=Bot(settings.BOT_TOKEN)
    dp=Dispatcher(storage=MemoryStorage())
    for r in [start.router, info.router, dbcheck.router, demo.router, browse.router, listing.router, suggestions.router, owner.router, admin.router, group_events.router, daily_vote.router, moderation_auto.router]:
        dp.include_router(r)
    await init_db()
    setup_jobs(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
