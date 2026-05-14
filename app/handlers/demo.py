from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards.common import kb
from app.services.demo_data import DEMO_PROJECTS

router = Router()

@router.callback_query(F.data == "demo:user")
async def demo_user(call: CallbackQuery):
    await call.message.edit_text("🎭 Démo utilisateur\n\nClique sur « Trouver un groupe » pour voir la navigation utilisateur avec données fictives.", reply_markup=kb([[("🔎 Trouver un groupe","cats")],[("📊 Démo listeur","demo:lister")],[("🏠 Menu","home")]]))
    await call.answer()

@router.callback_query(F.data == "demo:lister")
async def demo_lister(call: CallbackQuery):
    p=DEMO_PROJECTS[0]
    text=f"📊 Démo côté listeur — {p['title']}\n\n🔗 Clics : {p['clicks']}\n🚀 Utilisateurs envoyés : {p['clicks']//3}\n⭐ Note : {p['rating']}/5 ({p['reviews']} avis)\n👥 Membres : {p['members']}\n📈 Croissance : +{p['growth']}\n⚠️ Warnings bot : 0/3\n🛡️ Modération : activée\n\nLe propriétaire peut modifier son lien, suivre ses stats et gérer sa modération."
    await call.message.edit_text(text, reply_markup=kb([[("🔗 Simuler modification lien","demo:action")],[("🛡️ Simuler modération","demo:action")],[("➕ Lister mon groupe gratuitement","list:start")],[("🏠 Menu","home")]]))
    await call.answer()

@router.callback_query(F.data == "demo:action")
async def demo_action(call: CallbackQuery):
    await call.answer("🎭 Action simulée.", show_alert=True)
