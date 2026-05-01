from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import UserRole
from app.keyboards import super_admin_menu, super_admin_project_keyboard, back_home
from app.services import repo

router = Router()
settings = get_settings()

async def is_sa(session, tg_user) -> bool:
    user = await repo.get_or_create_user(session, tg_user, settings.super_admin_ids)
    return user.role == UserRole.SUPER_ADMIN.value

@router.callback_query(F.data == "sa:menu")
async def sa_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        if not await is_sa(session, call.from_user):
            await call.answer("Accès refusé.", show_alert=True)
            return
    await call.message.edit_text("👑 Super admin", reply_markup=super_admin_menu())
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
        rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
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
    await call.message.edit_text("✅ Projet validé.", reply_markup=super_admin_menu())
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
    await call.message.edit_text("❌ Projet refusé.", reply_markup=super_admin_menu())
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
            await repo.ban_project(session, p, "Banni par super admin")
    await call.message.edit_text("🚫 Projet banni.", reply_markup=super_admin_menu())
    await call.answer()
