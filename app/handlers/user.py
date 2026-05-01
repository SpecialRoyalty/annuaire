from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Project, UserRole, ProjectStatus
from app.keyboards import main_menu, categories_keyboard, rating_keyboard, back_home
from app.services import repo

router = Router()
settings = get_settings()


def status_icon(project: Project) -> str:
    if project.status != ProjectStatus.ACTIVE.value:
        return "🟠"
    return "🟢" if project.is_link_active else "🔴"


def project_text(project: Project) -> str:
    return (
        f"{status_icon(project)} <b>{project.title}</b>\n"
        f"{project.description or ''}\n\n"
        f"⭐ {project.rating_avg:.1f}/5 ({project.rating_count} avis)\n"
        f"👥 {project.member_count or 'N/A'} membres\n"
        f"🔗 Clics : {project.click_count}\n"
    )


async def show_home(target, user):
    is_sa = user.role == UserRole.SUPER_ADMIN.value
    text = "🔗 <b>Tous Les Liens</b>\n\nRetrouve les liens de secours des groupes Telegram."
    if isinstance(target, Message):
        await target.answer(text, reply_markup=main_menu(is_sa))
    else:
        await target.message.edit_text(text, reply_markup=main_menu(is_sa))


@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("group_"):
            project_id = int(parts[1].replace("group_", ""))
            await repo.add_start(session, project_id)
        await show_home(message, user)


@router.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        await show_home(call, user)
    await call.answer()


@router.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>Comment ça marche ?</b>\n\n"
        "Les groupes listés gardent un lien de secours ici. "
        "Si leur groupe saute, ils peuvent modifier le lien et leurs membres retrouvent l'accès via le bot.\n\n"
        "Les groupes les mieux notés, les plus actifs et ceux qui envoient le plus d'utilisateurs montent dans le classement.",
        reply_markup=back_home(),
    )
    await call.answer()


@router.callback_query(F.data == "browse:categories")
async def categories(call: CallbackQuery):
    async with SessionLocal() as session:
        cats = await repo.list_categories(session)
    await call.message.edit_text("📂 Choisis une catégorie :", reply_markup=categories_keyboard(cats))
    await call.answer()


@router.callback_query(F.data.startswith("browse:cat:"))
async def browse_category(call: CallbackQuery):
    _, _, cat_id, page = call.data.split(":")
    cat_id, page = int(cat_id), int(page)
    async with SessionLocal() as session:
        cat = await repo.get_category(session, cat_id)
        projects, has_next = await repo.active_projects_by_category(session, cat_id, page)
    rows = []
    if page > 1:
        rows.append(InlineKeyboardButton(text="⬅️ Précédent", callback_data=f"browse:cat:{cat_id}:{page-1}"))
    if has_next:
        rows.append(InlineKeyboardButton(text="➡️ Suivant", callback_data=f"browse:cat:{cat_id}:{page+1}"))
    kb_rows = []
    text = f"📂 <b>{cat.name if cat else 'Catégorie'}</b> — page {page}\n\n"
    if not projects:
        text += "Aucun groupe actif pour l'instant."
    for p in projects:
        text += project_text(p) + "\n"
        kb_rows.append([InlineKeyboardButton(text=f"🚀 Entrer : {p.title[:25]}", callback_data=f"click:{p.id}")])
        kb_rows.append([InlineKeyboardButton(text=f"⭐ Noter {p.title[:20]}", callback_data=f"rate:menu:{p.id}"), InlineKeyboardButton(text="⚠️ Signaler", callback_data=f"report:{p.id}")])
    if rows:
        kb_rows.append(rows)
    kb_rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@router.callback_query(F.data.startswith("browse:top:"))
async def top(call: CallbackQuery):
    page = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        projects, has_next = await repo.top_projects(session, page)
    text = f"⭐ <b>Top groupes</b> — page {page}\n\n"
    kb_rows = []
    for p in projects:
        text += project_text(p) + "\n"
        kb_rows.append([InlineKeyboardButton(text=f"🚀 Entrer : {p.title[:25]}", callback_data=f"click:{p.id}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"browse:top:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"browse:top:{page+1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    await call.message.edit_text(text or "Aucun groupe.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@router.callback_query(F.data.startswith("click:"))
async def click_project(call: CallbackQuery):
    project_id = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        project = await repo.get_project(session, project_id)
        if not project or project.status != ProjectStatus.ACTIVE.value or not project.is_link_active:
            await call.answer("Lien indisponible pour le moment.", show_alert=True)
            return
        await repo.add_click(session, project, user)
        link = project.invite_link
    await call.message.answer(f"🚀 Voici le lien :\n{link}")
    await call.answer()


@router.callback_query(F.data.startswith("rate:menu:"))
async def rate_menu(call: CallbackQuery):
    project_id = int(call.data.split(":")[-1])
    await call.message.edit_text("Choisis une note :", reply_markup=rating_keyboard(project_id))
    await call.answer()


@router.callback_query(F.data.startswith("rate:set:"))
async def rate_set(call: CallbackQuery):
    _, _, project_id, value = call.data.split(":")
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        project = await repo.get_project(session, int(project_id))
        if not project:
            await call.answer("Projet introuvable.", show_alert=True)
            return
        ok = await repo.set_rating(session, user, project, int(value))
    if not ok:
        await call.answer("Tu ne peux pas noter ton propre projet.", show_alert=True)
    else:
        await call.message.edit_text("✅ Merci pour ta note.", reply_markup=back_home())
        await call.answer()


@router.callback_query(F.data.startswith("report:"))
async def report(call: CallbackQuery):
    project_id = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        project = await repo.get_project(session, project_id)
        if project:
            await repo.report_project(session, user, project)
    await call.answer("Signalement envoyé.", show_alert=True)
