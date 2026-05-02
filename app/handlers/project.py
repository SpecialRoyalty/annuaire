from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import UserRole
from app.keyboards import categories_keyboard, owner_project_keyboard, back_home, cancel_keyboard
from app.services import repo

router = Router()
settings = get_settings()


class AddProject(StatesGroup):
    title = State()
    description = State()
    category = State()
    invite_link = State()


class EditLink(StatesGroup):
    waiting_link = State()


@router.callback_query(F.data == "project:add")
async def add_project(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddProject.title)
    await call.message.edit_text("➕ <b>Listing gratuit</b>\n\nNom du groupe ?", reply_markup=cancel_keyboard())
    await call.answer()


@router.message(AddProject.title)
async def add_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text[:120])
    await state.set_state(AddProject.description)
    await message.answer("Description courte du groupe ?\n\nExplique en 1 phrase pourquoi les gens doivent rejoindre.", reply_markup=cancel_keyboard())


@router.message(AddProject.description)
async def add_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text[:800])
    async with SessionLocal() as session:
        cats = await repo.list_categories(session)
    await state.set_state(AddProject.category)
    await message.answer("Choisis une catégorie :", reply_markup=categories_keyboard(cats, for_listing=True))


@router.callback_query(AddProject.category, F.data.startswith("project:cat:"))
async def add_category(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split(":")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(AddProject.invite_link)
    await call.message.edit_text("Envoie le lien d’invitation du groupe.\n\nExemple : https://t.me/ton_groupe", reply_markup=cancel_keyboard())
    await call.answer()


@router.message(AddProject.invite_link)
async def add_link(message: Message, state: FSMContext):
    link = (message.text or "").strip()
    if not (link.startswith("https://t.me/") or link.startswith("http://t.me/")):
        await message.answer("Envoie un vrai lien Telegram qui commence par https://t.me/", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        project = await repo.create_project(session, user, data["title"], data["description"], data["category_id"], link)
    await state.clear()
    await message.answer(
        "✅ Groupe créé gratuitement.\n\n"
        "Maintenant ajoute le bot comme admin dans ton groupe avec le droit d’épingler les messages.\n"
        "Ensuite envoie /connect dans le groupe.\n\n"
        "Tu as 1 heure avant rappel automatique.",
        reply_markup=back_home(),
    )


@router.callback_query(F.data == "owner:projects")
async def my_projects(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        projects = await repo.owner_projects(session, user)
    if not projects:
        await call.message.edit_text("Tu n’as pas encore listé de projet.", reply_markup=back_home())
    else:
        rows = [[InlineKeyboardButton(text=f"{p.title} — {p.status}", callback_data=f"owner:open:{p.id}")] for p in projects]
        rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
        await call.message.edit_text("📊 Tes projets :", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("owner:open:"))
async def owner_open(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        p = await repo.get_project(session, project_id)
        if not p or (p.owner_user_id != user.id and user.role != UserRole.SUPER_ADMIN.value):
            await call.answer("Accès refusé.", show_alert=True)
            return
    await call.message.edit_text(f"⚙️ <b>{p.title}</b>\nStatut : {p.status}", reply_markup=owner_project_keyboard(p.id))
    await call.answer()


@router.callback_query(F.data.startswith("owner:stats:"))
async def owner_stats(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        p = await repo.get_project(session, project_id)
        if not p or (p.owner_user_id != user.id and user.role != UserRole.SUPER_ADMIN.value):
            await call.answer("Accès refusé.", show_alert=True)
            return
    text = (
        f"📊 <b>Stats — {p.title}</b>\n\n"
        f"🔗 Clics lien : {p.click_count}\n"
        f"🚀 Starts générés : {p.start_count}\n"
        f"⭐ Note : {p.rating_avg:.1f}/5 ({p.rating_count} avis)\n"
        f"👥 Membres : {p.member_count or 'N/A'}\n"
        f"📌 Tentatives dépin/retrait : {p.pin_attempts}/3\n"
        f"📅 Listé depuis : {p.listed_at.strftime('%d/%m/%Y')}\n"
        f"État lien : {'🟢 actif' if p.is_link_active else '🔴 inactif'}"
    )
    await call.message.edit_text(text, reply_markup=owner_project_keyboard(p.id))
    await call.answer()


@router.callback_query(F.data.startswith("owner:editlink:"))
async def edit_link(call: CallbackQuery, state: FSMContext):
    project_id = int(call.data.split(":")[-1])
    await state.update_data(project_id=project_id)
    await state.set_state(EditLink.waiting_link)
    await call.message.edit_text("Envoie le nouveau lien Telegram.", reply_markup=cancel_keyboard())
    await call.answer()


@router.message(EditLink.waiting_link)
async def edit_link_save(message: Message, state: FSMContext):
    link = (message.text or "").strip()
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        p = await repo.get_project(session, int(data["project_id"]))
        if not p or (p.owner_user_id != user.id and user.role != UserRole.SUPER_ADMIN.value):
            await message.answer("Accès refusé.")
            await state.clear()
            return
        p.invite_link = link
        p.is_link_active = True
        p.inactive_since = None
        await session.commit()
    await state.clear()
    await message.answer("✅ Lien modifié.", reply_markup=back_home())


@router.callback_query(F.data.startswith("owner:delete:"))
async def owner_delete(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        p = await repo.get_project(session, project_id)
        if not p or p.owner_user_id != user.id:
            await call.answer("Accès refusé.", show_alert=True)
            return
        p.status = "deleted"
        await session.commit()
    await call.message.edit_text("🗑 Projet supprimé du listing.", reply_markup=back_home())
    await call.answer()
