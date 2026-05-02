from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Project, ProjectStatus
from app.keyboards import main_menu, categories_keyboard, rating_keyboard, back_home, cancel_keyboard
from app.services import repo

router = Router()
settings = get_settings()

class SuggestCategory(StatesGroup):
    name = State()


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
        f"🔥 Popularité : {project.click_count + project.start_count}\n"
    )

async def show_home(target, user):
    async with SessionLocal() as session:
        db_user = await repo.get_or_create_user(session, user if not hasattr(user, 'telegram_id') else target.from_user, settings.super_admin_ids) if False else None
    async with SessionLocal() as session:
        u = await repo.get_or_create_user(session, target.from_user if hasattr(target, 'from_user') else user, settings.super_admin_ids)
        has_projects = await repo.user_has_projects(session, u)
        total = await repo.total_users(session)
    social = f"\n\n🔥 Déjà {total:,} utilisateurs ont lancé le bot.".replace(',', ' ') if total >= 1000 else ""
    text = (
        "🔗 <b>Tous Les Liens</b>\n\n"
        "Retrouve les liens des groupes Telegram préférés.\n"
        "Listing et service 100% gratuits." + social
    )
    markup = main_menu(u, has_projects)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)

@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("group_"):
            try:
                project_id = int(parts[1].replace("group_", ""))
                await repo.add_start(session, project_id)
            except ValueError:
                pass
    await show_home(message, message.from_user)

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_home(call, call.from_user)
    await call.answer()

@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("✅ Action annulée.", reply_markup=back_home())
    await call.answer()

@router.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>Comment ça marche ?</b>\n\n"
        "Tous Les Liens est un recueil gratuit de groupes Telegram.\n\n"
        "Tu cherches un groupe ? Parcours les catégories et entre directement.\n\n"
        "Tu ne trouves pas ton groupe ? Demande au propriétaire de le lister ici : @touslesliens_bot\n\n"
        "Les groupes les mieux notés, les plus actifs et ceux qui envoient le plus d’utilisateurs montent dans le classement.",
        reply_markup=back_home(),
    )
    await call.answer()

@router.callback_query(F.data == "browse:categories")
async def categories(call: CallbackQuery):
    async with SessionLocal() as session:
        cats = await repo.list_categories(session)
    await call.message.edit_text("📂 Choisis une catégorie :", reply_markup=categories_keyboard(cats))
    await call.answer()

@router.callback_query(F.data == "cat:suggest")
async def suggest_category(call: CallbackQuery, state: FSMContext):
    await state.set_state(SuggestCategory.name)
    await call.message.edit_text("💡 Quelle catégorie veux-tu suggérer ?", reply_markup=cancel_keyboard())
    await call.answer()

@router.message(SuggestCategory.name)
async def suggest_category_save(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Envoie un vrai nom de catégorie.", reply_markup=cancel_keyboard())
        return
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        await repo.suggest_category(session, user, name)
    await state.clear()
    await message.answer("✅ Suggestion envoyée aux modérateurs. Merci !", reply_markup=back_home())

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
        text += "Aucun groupe actif ici pour l’instant.\n\nTu ne trouves pas ton groupe ? Demande au propriétaire de le lister gratuitement ici : @touslesliens_bot"
    for p in projects:
        text += project_text(p) + "\n"
        kb_rows.append([InlineKeyboardButton(text=f"🚀 Entrer : {p.title[:25]}", callback_data=f"click:{p.id}")])
        kb_rows.append([InlineKeyboardButton(text=f"⭐ Noter", callback_data=f"rate:menu:{p.id}"), InlineKeyboardButton(text="⚠️ Signaler", callback_data=f"report:{p.id}")])
    if rows:
        kb_rows.append(rows)
    kb_rows.append([InlineKeyboardButton(text="💡 Suggérer une catégorie", callback_data="cat:suggest")])
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
    if not projects:
        text += "Aucun groupe actif pour l’instant."
    for p in projects:
        text += project_text(p) + "\n"
        kb_rows.append([InlineKeyboardButton(text=f"🚀 Entrer : {p.title[:25]}", callback_data=f"click:{p.id}")])
        kb_rows.append([InlineKeyboardButton(text="⭐ Noter", callback_data=f"rate:menu:{p.id}"), InlineKeyboardButton(text="⚠️ Signaler", callback_data=f"report:{p.id}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"browse:top:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"browse:top:{page+1}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
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
    await call.answer("Lien ouvert ✅", show_alert=False)
    await call.message.edit_text(f"🚀 <b>Lien du groupe</b>\n\n{link}\n\nPense à noter le groupe après l’avoir visité.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Noter ce groupe", callback_data=f"rate:menu:{project_id}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))

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
        await call.answer("Tu ne peux pas noter ton propre groupe.", show_alert=True)
    else:
        await call.message.edit_text("✅ Merci pour ta note. Ton avis aide les meilleurs groupes à monter.", reply_markup=back_home())
        await call.answer()

@router.callback_query(F.data.startswith("report:"))
async def report(call: CallbackQuery):
    project_id = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        project = await repo.get_project(session, project_id)
        if project:
            await repo.report_project(session, user, project)
    await call.answer("Signalement envoyé aux modérateurs.", show_alert=True)
