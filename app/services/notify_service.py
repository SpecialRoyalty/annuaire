from app.config import settings

async def notify_admins(bot, text: str, reply_markup=None):
    for admin_id in settings.SUPER_ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=reply_markup)
        except Exception:
            pass
