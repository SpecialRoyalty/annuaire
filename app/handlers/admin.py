from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import UserRole
from app.keyboards import super_admin_menu, super_admin_project_keyboard, back_home, cancel_keyboard
from app.services import repo

router = Router()
settings = get_settings()

class AdminCategory(StatesGroup):
    add_name = State()

async def is_sa(session, tg_user) -> bool:
    user = await repo.get_or_create_user(session, tg_user, settings.super_admin_ids)
    return user.role == UserRole.SUPER_ADMIN.value

@router.callback_query(F.data == "sa:menu")
async def sa_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
    await call.message.edit_text("🛠 <b>Modération</b>", reply_markup=super_admin_menu())
    await call.answer()

@router.callback_query(F.data == "sa:pending")
async def sa_pending(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        projects = await repo.pending_projects(session)
    if not projects:
        await call.message.edit_text("Aucune demande en attente.", reply_markup=super_admin_menu())
    else:
        rows = [[InlineKeyboardButton(text=f"{p.title} — {p.status}", callback_data=f"sa:open:{p.id}")] for p in projects]
        rows.append([InlineKeyboardButton(text="⬅️ Modération", callback_data="sa:menu")])
        await call.message.edit_text("🕓 Demandes en attente :", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()

@router.callback_query(F.data.startswith("sa:open:"))
async def sa_open(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        p = await repo.get_project(session, project_id)
    if not p:
        await call.answer("Introuvable.", show_alert=True)
        return
    await call.message.edit_text(
        f"<b>{p.title}</b>\n{p.description or ''}\n\nLien : {p.invite_link}\nStatut : {p.status}\nGroupe ID : {p.group_chat_id}",
        reply_markup=super_admin_project_keyboard(p.id),
    )
    await call.answer()

@router.callback_query(F.data.startswith("sa:approve:"))
async def sa_approve(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        p = await repo.get_project(session, project_id)
        if p:
            await repo.approve_project(session, p)
    await call.message.edit_text("✅ Groupe validé et listé.", reply_markup=super_admin_menu())
    await call.answer()

@router.callback_query(F.data.startswith("sa:reject:"))
async def sa_reject(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        p = await repo.get_project(session, project_id)
        if p:
            await repo.reject_project(session, p)
    await call.message.edit_text("❌ Groupe refusé.", reply_markup=super_admin_menu())
    await call.answer()

@router.callback_query(F.data.startswith("sa:ban:"))
async def sa_ban(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        p = await repo.get_project(session, project_id)
        if p:
            await repo.ban_project(session, p, "Banni par modération")
    await call.message.edit_text("🚫 Groupe banni.", reply_markup=super_admin_menu())
    await call.answer()

@router.callback_query(F.data == "sa:cat:add")
async def sa_cat_add(call: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
    await state.set_state(AdminCategory.add_name)
    await call.message.edit_text("📂 Nom de la nouvelle catégorie ?", reply_markup=cancel_keyboard())
    await call.answer()

@router.message(AdminCategory.add_name)
async def sa_cat_add_save(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    async with SessionLocal() as session:
        if not await is_sa(session, message.from_user):
            await message.answer("Accès refusé.")
            await state.clear()
            return
        await repo.add_category(session, name)
    await state.clear()
    await message.answer(f"✅ Catégorie ajoutée : {name}", reply_markup=super_admin_menu())

@router.callback_query(F.data == "sa:cat:delete_menu")
async def sa_cat_delete_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        cats = await repo.list_categories(session)
    rows = [[InlineKeyboardButton(text=f"🗑 {c.name}", callback_data=f"sa:cat:delete:{c.id}")] for c in cats]
    rows.append([InlineKeyboardButton(text="⬅️ Modération", callback_data="sa:menu")])
    await call.message.edit_text("⚠️ Supprimer une catégorie supprime aussi tous les groupes listés dedans.", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()

@router.callback_query(F.data.startswith("sa:cat:delete:"))
async def sa_cat_delete(call: CallbackQuery):
    cat_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        await repo.delete_category_and_projects(session, cat_id)
    await call.message.edit_text("🗑 Catégorie supprimée avec tous ses groupes et infos.", reply_markup=super_admin_menu())
    await call.answer()

@router.callback_query(F.data == "sa:cat:suggestions")
async def sa_cat_suggestions(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
        suggestions = await repo.list_category_suggestions(session)
    text = "💡 <b>Suggestions de catégories</b>\n\n"
    text += "Aucune suggestion." if not suggestions else "\n".join([f"• {s.name}" for s in suggestions])
    await call.message.edit_text(text, reply_markup=super_admin_menu())
    await call.answer()
