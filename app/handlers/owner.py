from sqlalchemy import select, desc
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.db.session import SessionLocal
from app.models.models import Project, ForbiddenWord
from app.services.user_service import get_or_create_user
from app.services.settings_service import is_demo
from app.services.demo_data import DEMO_PROJECTS
from app.keyboards.common import kb, cancel_kb
router=Router()
class OwnerState(StatesGroup): edit_link=State(); add_word=State()

@router.callback_query(F.data=="owner:menu")
async def menu(call:CallbackQuery):
    async with SessionLocal() as session:
        user=await get_or_create_user(session,call.from_user); demo=await is_demo(session); projects=list((await session.scalars(select(Project).where(Project.owner_user_id==user.id).order_by(desc(Project.id)))).all())
    if demo and not projects:
        rows=[[(f"📌 {p['title']}",f"owner:demo:{p['id']}")] for p in DEMO_PROJECTS[:3]]+[[("🏠 Menu","home")]]
        await call.message.edit_text("📊 Interface listeur — Démo", reply_markup=kb(rows)); await call.answer(); return
    if not projects:
        await call.message.edit_text("Tu n’as pas encore listé de groupe.", reply_markup=kb([[("➕ Lister mon groupe gratuitement","list:start")],[("🏠 Menu","home")]])); await call.answer(); return
    rows=[[(f"📌 {p.title}",f"owner:project:{p.id}")] for p in projects]+[[("🏠 Menu","home")]]
    await call.message.edit_text("📊 Espace listeur :", reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("owner:demo:"))
async def demo(call:CallbackQuery):
    p=next((x for x in DEMO_PROJECTS if x["id"]==int(call.data.split(":")[2])), DEMO_PROJECTS[0])
    await call.message.edit_text(f"📊 Démo — {p['title']}\n\n🔗 Clics : {p['clicks']}\n🚀 Utilisateurs envoyés : {p['clicks']//3}\n⭐ Note : {p['rating']}/5\n👥 Membres : {p['members']}\n📈 Croissance : +{p['growth']}\n⚠️ Warnings : 0/3\n🛡️ Modération : activée", reply_markup=kb([[("🔗 Simuler modification","owner:demo_action")],[("🛡️ Simuler modération","owner:demo_action")],[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data=="owner:demo_action")
async def demo_action(call:CallbackQuery): await call.answer("🎭 Action simulée.", show_alert=True)

@router.callback_query(F.data.startswith("owner:project:"))
async def project(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    async with SessionLocal() as session:
        user=await get_or_create_user(session,call.from_user); p=await session.get(Project,pid)
        if not p or p.owner_user_id!=user.id: await call.answer("Accès refusé",show_alert=True); return
        avg=p.rating_sum/p.rating_count if p.rating_count else 0
        text=f"📊 {p.title}\n\nStatut : {p.status}\n🔗 Clics : {p.click_count}\n⭐ Note : {avg:.1f}/5\n👥 Membres : {p.member_count}\n📈 Croissance : {p.growth_last_sync:+}\n⚠️ Warnings : {p.bot_warning_count}/3\n🛡️ Modération : {'activée' if p.moderation_enabled else 'désactivée'}"
    await call.message.edit_text(text, reply_markup=kb([[("🔗 Modifier lien",f"owner:edit_link:{pid}")],[("🛡️ Modération",f"owner:mod:{pid}")],[("🗑️ Supprimer",f"owner:delete:{pid}")],[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("owner:edit_link:"))
async def edit(call:CallbackQuery,state:FSMContext):
    await state.update_data(project_id=int(call.data.split(":")[2])); await state.set_state(OwnerState.edit_link); await call.message.edit_text("Envoie le nouveau lien :", reply_markup=cancel_kb()); await call.answer()

@router.message(OwnerState.edit_link)
async def save_link(message:Message,state:FSMContext):
    data=await state.get_data()
    async with SessionLocal() as session:
        user=await get_or_create_user(session,message.from_user); p=await session.get(Project,data["project_id"])
        if p and p.owner_user_id==user.id: p.invite_link=message.text.strip(); p.is_link_active=True; await session.commit()
    await state.clear(); await message.answer("✅ Lien mis à jour.", reply_markup=kb([[("📊 Espace listeur","owner:menu")],[("🏠 Menu","home")]]))

@router.callback_query(F.data.startswith("owner:delete:"))
async def delete(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    async with SessionLocal() as session:
        user=await get_or_create_user(session,call.from_user); p=await session.get(Project,pid)
        if p and p.owner_user_id==user.id: p.status="deleted"; await session.commit()
    await call.message.edit_text("🗑️ Projet supprimé.", reply_markup=kb([[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("owner:mod:"))
async def mod(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    await call.message.edit_text("🛡️ Modération\n\nMots interdits : suppression + mute.\nLiens externes : ban direct.", reply_markup=kb([[("👀 Voir mots",f"owner:words:{pid}")],[("➕ Ajouter mot",f"owner:add_word:{pid}")],[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("owner:words:"))
async def words(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    async with SessionLocal() as session: words=list((await session.scalars(select(ForbiddenWord).where(ForbiddenWord.project_id==pid))).all())
    await call.message.edit_text("🚫 Mots interdits :\n\n"+("\n".join(f"• {w.word}" for w in words) if words else "Aucun."), reply_markup=kb([[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("owner:add_word:"))
async def add_word(call:CallbackQuery,state:FSMContext):
    await state.update_data(project_id=int(call.data.split(":")[2])); await state.set_state(OwnerState.add_word); await call.message.edit_text("Mot à interdire :", reply_markup=cancel_kb()); await call.answer()

@router.message(OwnerState.add_word)
async def save_word(message:Message,state:FSMContext):
    data=await state.get_data()
    async with SessionLocal() as session: session.add(ForbiddenWord(project_id=data["project_id"], word=message.text.strip().lower())); await session.commit()
    await state.clear(); await message.answer("✅ Mot ajouté.", reply_markup=kb([[("📊 Espace listeur","owner:menu")],[("🏠 Menu","home")]]))
