from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards.common import kb

router = Router()

@router.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    text = (
        "ℹ️ Comment ça marche ?\n\n"
        "Tous Les Liens est un recueil de groupes Telegram.\n\n"
        "Les utilisateurs retrouvent les liens de leurs groupes préférés facilement.\n\n"
        "Les propriétaires peuvent lister leur groupe gratuitement, modifier leur lien si besoin, suivre leurs statistiques et profiter d’un lien de secours visible depuis le bot.\n\n"
        "Les groupes les mieux notés, les plus actifs et ceux qui envoient le plus d’utilisateurs montent dans le classement.\n\n"
        "Listing et service 100% gratuits."
    )
    await call.message.edit_text(text, reply_markup=kb([[("➕ Lister mon groupe", "list:start")], [("🏠 Menu", "home")]]))
    await call.answer()
