from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from app.db.session import SessionLocal
from app.config import settings
from app.models.models import Project, CategorySuggestion, Category, User
from app.services.user_service import get_or_create_user
from app.services.settings_service import get_setting, set_setting
from app.keyboards.common import kb, cancel_kb

router = Router()

class AdminReason(StatesGroup):
    reject_project = State()
    reject_category = State()
    add_category = State()

async def is_admin(session, tg_user):
    user = await get_or_create_user(session, tg_user)
    return user.is_super_admin

@router.message(Command("moderation"))
async def moderation_cmd(message: Message):
    async with SessionLocal() as session:
        if not await is_admin(session, message.from_user):
            return
    await message.answer("🛠 Modération", reply_markup=await mod_keyboard())

async def mod_keyboard():
    async with SessionLocal() as session:
        demo = await get_setting(session, "demo_mode", "false")
    return kb([
        [("🕓 Demandes listing", "mod:pending")],
        [("📂 Suggestions catégories", "mod:cat_suggestions")],
        [("➕ Ajouter catégorie", "mod:add_cat")],
        [("🗑 Supprimer catégorie", "mod:delete_cat_menu")],
        [("🎭 Mode démo : " + ("ON" if demo == "true" else "OFF"), "mod:toggle_demo")],
        [("🏠 Menu", "home")]
    ])

@router.callback_query(F.data == "mod:menu")
async def mod_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
    await call.message.edit_text("🛠 Modération", reply_markup=await mod_keyboard())
    await call.answer()

@router.callback_query(F.data == "mod:toggle_demo")
async def toggle_demo(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        current = await get_setting(session, "demo_mode", "false")
        await set_setting(session, "demo_mode", "false" if current == "true" else "true")
    await call.message.edit_text("🎭 Mode démo modifié.", reply_markup=await mod_keyboard())
    await call.answer()

@router.callback_query(F.data == "mod:pending")
async def mod_pending(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        projects = list((await session.scalars(select(Project).where(Project.status.in_(["pending_bot", "pending_review"])))).all())
    text = "🕓 Demandes de listing\n\n"
    rows = []
    if not projects:
        text += "Aucune demande."
    for p in projects:
        text += f"• #{p.id} — {p.title} — {p.status}\n"
        rows.append([(f"📌 {p.title}", f"mod:project:{p.id}")])
    rows.append([("⬅️ Retour", "mod:menu")])
    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("mod:project:"))
async def mod_project(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        p = await session.get(Project, pid)
        if not p:
            await call.answer("Introuvable", show_alert=True); return
        text = f"📌 #{p.id} {p.title}\n\n{p.description}\n\nLien : {p.invite_link}\nStatut : {p.status}\nBot warnings : {p.bot_warning_count}/3"
    rows = [
        [("✅ Approuver", f"mod:approve:{pid}")],
        [("❌ Refuser avec motif", f"mod:reject:{pid}")],
        [("⬅️ Retour", "mod:pending")]
    ]
    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("mod:approve:"))
async def mod_approve(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        p = await session.get(Project, pid)
        if p:
            p.status = "active"
            p.moderation_enabled = p.wants_moderation
            owner = await session.get(User, p.owner_user_id)
            await session.commit()
            if owner:
                try:
                    await call.bot.send_message(owner.telegram_id, f"✅ Ton groupe {p.title} a été approuvé et listé.")
                except Exception:
                    pass
    await call.message.edit_text("✅ Projet approuvé.", reply_markup=kb([[("⬅️ Retour", "mod:pending")]]))
    await call.answer()

@router.callback_query(F.data.startswith("mod:reject:"))
async def mod_reject_start(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[2])
    await state.update_data(project_id=pid)
    await state.set_state(AdminReason.reject_project)
    await call.message.edit_text("Écris le motif du refus :", reply_markup=cancel_kb())
    await call.answer()

@router.message(AdminReason.reject_project)
async def mod_reject_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        if not await is_admin(session, message.from_user):
            return
        p = await session.get(Project, data["project_id"])
        if p:
            p.status = "rejected"
            owner = await session.get(User, p.owner_user_id)
            await session.commit()
            if owner:
                try:
                    await message.bot.send_message(owner.telegram_id, f"❌ Ton listing {p.title} a été refusé.\n\nMotif :\n{message.text}")
                except Exception:
                    pass
    await state.clear()
    await message.answer("Refus envoyé.", reply_markup=kb([[("🛠 Modération", "mod:menu")]]))

@router.callback_query(F.data == "mod:cat_suggestions")
async def mod_cat_suggestions(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        suggestions = list((await session.scalars(select(CategorySuggestion).where(CategorySuggestion.status == "pending"))).all())
    text = "📂 Suggestions catégories\n\n"
    rows = []
    if not suggestions:
        text += "Aucune suggestion."
    for s in suggestions:
        text += f"• #{s.id} — {s.name}\n"
        rows.append([(f"📂 {s.name}", f"mod:cat_sug:{s.id}")])
    rows.append([("⬅️ Retour", "mod:menu")])
    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("mod:cat_sug:"))
async def mod_cat_sug(call: CallbackQuery):
    sid = int(call.data.split(":")[2])
    await call.message.edit_text("Que faire avec cette catégorie ?", reply_markup=kb([
        [("✅ Valider", f"mod:cat_accept:{sid}")],
        [("❌ Refuser avec motif", f"mod:cat_reject:{sid}")],
        [("⬅️ Retour", "mod:cat_suggestions")]
    ]))
    await call.answer()

@router.callback_query(F.data.startswith("mod:cat_accept:"))
async def mod_cat_accept(call: CallbackQuery):
    sid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        s = await session.get(CategorySuggestion, sid)
        if s:
            exists = await session.scalar(select(Category).where(Category.name == s.name))
            if not exists:
                session.add(Category(name=s.name))
            s.status = "accepted"
            user = await session.get(User, s.user_id)
            await session.commit()
            if user:
                try: await call.bot.send_message(user.telegram_id, f"✅ Ta catégorie « {s.name} » a été acceptée.")
                except Exception: pass
    await call.message.edit_text("✅ Catégorie acceptée.", reply_markup=kb([[("⬅️ Retour", "mod:cat_suggestions")]]))
    await call.answer()

@router.callback_query(F.data.startswith("mod:cat_reject:"))
async def mod_cat_reject(call: CallbackQuery, state: FSMContext):
    sid = int(call.data.split(":")[2])
    await state.update_data(suggestion_id=sid)
    await state.set_state(AdminReason.reject_category)
    await call.message.edit_text("Écris le motif de refus de la catégorie :", reply_markup=cancel_kb())
    await call.answer()

@router.message(AdminReason.reject_category)
async def mod_cat_reject_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        if not await is_admin(session, message.from_user):
            return
        s = await session.get(CategorySuggestion, data["suggestion_id"])
        if s:
            s.status = "rejected"
            s.refusal_reason = message.text
            user = await session.get(User, s.user_id)
            await session.commit()
            if user:
                try: await message.bot.send_message(user.telegram_id, f"❌ Ta catégorie « {s.name} » a été refusée.\n\nMotif :\n{message.text}")
                except Exception: pass
    await state.clear()
    await message.answer("Refus envoyé.", reply_markup=kb([[("🛠 Modération", "mod:menu")]]))

@router.callback_query(F.data == "mod:add_cat")
async def add_cat_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminReason.add_category)
    await call.message.edit_text("Nom de la nouvelle catégorie :", reply_markup=cancel_kb())
    await call.answer()

@router.message(AdminReason.add_category)
async def add_cat_finish(message: Message, state: FSMContext):
    async with SessionLocal() as session:
        if not await is_admin(session, message.from_user):
            return
        session.add(Category(name=message.text.strip()))
        await session.commit()
    await state.clear()
    await message.answer("✅ Catégorie ajoutée.", reply_markup=kb([[("🛠 Modération", "mod:menu")]]))

@router.callback_query(F.data == "mod:delete_cat_menu")
async def delete_cat_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        cats = list((await session.scalars(select(Category).order_by(Category.name))).all())
    rows = [[(f"🗑 {c.name}", f"mod:delete_cat:{c.id}")] for c in cats]
    rows.append([("⬅️ Retour", "mod:menu")])
    await call.message.edit_text("⚠️ Supprimer une catégorie supprimera aussi tous les groupes liés.", reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("mod:delete_cat:"))
async def delete_cat(call: CallbackQuery):
    cid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        if not await is_admin(session, call.from_user):
            await call.answer("Accès refusé", show_alert=True); return
        cat = await session.get(Category, cid)
        if cat:
            await session.delete(cat)
            await session.commit()
    await call.message.edit_text("🗑 Catégorie supprimée avec ses groupes liés.", reply_markup=kb([[("🛠 Modération", "mod:menu")]]))
    await call.answer()
