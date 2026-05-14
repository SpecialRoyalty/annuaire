from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards.common import kb
router = Router()

@router.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ Comment ça marche ?\n\nTous Les Liens est un recueil de groupes Telegram.\n\nLes utilisateurs retrouvent les liens de leurs groupes préférés facilement.\n\nLes propriétaires peuvent lister leur groupe gratuitement, modifier leur lien si besoin et suivre leurs statistiques.\n\nLes groupes les mieux notés, les plus actifs et ceux qui envoient le plus d’utilisateurs montent dans le classement.",
        reply_markup=kb([[("➕ Lister mon groupe gratuitement","list:start")],[("🏠 Menu","home")]])
    )
    await call.answer()
