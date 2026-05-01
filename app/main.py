import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from app.config import get_settings
from app.db.init_db import init_db
from app.handlers import user, project, admin, group
from app.services.tasks import setup_scheduler

logging.basicConfig(level=logging.INFO)
settings = get_settings()

async def on_startup(bot: Bot):
    await init_db()
    if settings.WEBHOOK_URL:
        await bot.set_webhook(f"{settings.WEBHOOK_URL}/webhook", secret_token=settings.WEBHOOK_SECRET)
    setup_scheduler(bot)

async def on_shutdown(bot: Bot):
    if settings.WEBHOOK_URL:
        await bot.delete_webhook()

async def main():
    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(group.router)
    dp.include_router(project.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.WEBHOOK_URL:
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.WEBHOOK_SECRET).register(app, path="/webhook")
        setup_application(app, dp, bot=bot)
        web.run_app(app, host="0.0.0.0", port=settings.PORT)
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
