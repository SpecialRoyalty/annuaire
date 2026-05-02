from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.config import get_settings
from app.db.session import SessionLocal
from app.db.models import Project, ProjectStatus
from app.keyboards import main_menu, categories_keyboard, rating_keyboard, back_home, cancel_keyboard
from app.services import repo, demo

router = Router()
settings = get_settings()

class SuggestCategory(StatesGroup):
    name = State()


def status_icon(project: Project) -> str:
    if project.status != ProjectStatus.ACTIVE.value:
        return "🟠"
    return "🟢" if project.is_link_active else "🔴"


def short_project_line(project: Project) -> str:
    members = f"{project.member_count:,}".replace(",", " ") if project.member_count else "N/A"
    return (
        f"{status_icon(project)} <b>{project.title}</b>\n"
        f"⭐ {project.rating_avg:.1f}/5 — 👥 {members} membres\n"
    )


def project_detail_text(project: Project, category_name: str | None = None) -> str:
    members = f"{project.member_count:,}".replace(",", " ") if project.member_count else "N/A"
    popularity = f"{project.click_count + project.start_count:,}".replace(",", " ")
    category = f"\n📂 Catégorie : {category_name}" if category_name else ""
    link_status = "🟢 Lien actif" if project.is_link_active else "🔴 Lien inactif"
    return (
        f"{status_icon(project)} <b>{project.title}</b>\n\n"
        f"{project.description or 'Aucune description.'}\n\n"
        f"⭐ Note : {project.rating_avg:.1f}/5 — {project.rating_count} avis\n"
        f"👥 Membres : {members}\n"
        f"🔥 Popularité : {popularity}{category}\n"
        f"{link_status}\n\n"
        "Choisis une action :"
    )


def category_list_keyboard(projects, cat_id: int, page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    for p in projects:
        rows.append([InlineKeyboardButton(text=f"📌 {p.title[:45]}", callback_data=f"project:detail:{p.id}:cat:{cat_id}:{page}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Précédent", callback_data=f"browse:cat:{cat_id}:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ Suivant", callback_data=f"browse:cat:{cat_id}:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="💡 Suggérer une catégorie", callback_data="cat:suggest")])
    rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def top_list_keyboard(projects, page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    for p in projects:
        rows.append([InlineKeyboardButton(text=f"📌 {p.title[:45]}", callback_data=f"project:detail:{p.id}:top:0:{page}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Précédent", callback_data=f"browse:top:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡️ Suivant", callback_data=f"browse:top:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def project_detail_keyboard(project_id: int, origin: str, cat_id: int, page: int) -> InlineKeyboardMarkup:
    back_cb = f"browse:cat:{cat_id}:{page}" if origin == "cat" else f"browse:top:{page}"
    back_text = "⬅️ Retour à la catégorie" if origin == "cat" else "⬅️ Retour au top"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Entrer dans le groupe", callback_data=f"click:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="⭐ Noter", callback_data=f"rate:menu:{project_id}:{origin}:{cat_id}:{page}"), InlineKeyboardButton(text="⚠️ Signaler", callback_data=f"report:menu:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text=back_text, callback_data=back_cb)],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])

async def show_home(target, user):
    async with SessionLocal() as session:
        u = await repo.get_or_create_user(session, target.from_user if hasattr(target, 'from_user') else user, settings.super_admin_ids)
        has_projects = await repo.user_has_projects(session, u)
        total = await repo.total_users(session)
        demo_mode = await repo.is_demo_mode(session)
    social = f"\n\n🔥 Déjà {total:,} utilisateurs ont lancé le bot.".replace(',', ' ') if total >= 1000 else ""
    demo_banner = "\n\n🎭 Mode démo actif : explore les deux côtés du bot." if demo_mode else ""
    text = (
        "🔗 <b>Tous Les Liens</b>\n\n"
        "Retrouve les liens des groupes Telegram préférés.\n"
        "Listing et service 100% gratuits." + social + demo_banner
    )
    markup = main_menu(u, has_projects, demo_mode=demo_mode)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)

@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        await repo.get_or_create_user(session, message.from_user, settings.super_admin_ids)
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("group_"):
            try:
                await repo.add_start(session, int(parts[1].replace("group_", "")))
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
        cats = demo.demo_categories() if await repo.is_demo_mode(session) else await repo.list_categories(session)
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
        if await repo.is_demo_mode(session):
            cats = demo.demo_categories()
            cat = next((c for c in cats if c.id == cat_id), None)
            projects, has_next = demo.demo_projects_by_category(cat_id, page)
        else:
            cat = await repo.get_category(session, cat_id)
            projects, has_next = await repo.active_projects_by_category(session, cat_id, page)
    text = f"📂 <b>{cat.name if cat else 'Catégorie'}</b> — page {page}\n\n"
    if not projects:
        text += "Aucun groupe actif ici pour l’instant.\n\nTu ne trouves pas ton groupe ? Demande au propriétaire de le lister gratuitement ici : @touslesliens_bot"
    else:
        text += "Clique sur un groupe pour voir les détails, entrer, noter ou signaler.\n\n"
        for p in projects:
            text += short_project_line(p) + "\n"
    await call.message.edit_text(text, reply_markup=category_list_keyboard(projects, cat_id, page, has_next))
    await call.answer()

@router.callback_query(F.data.startswith("browse:top:"))
async def top(call: CallbackQuery):
    page = int(call.data.split(":")[-1])
    async with SessionLocal() as session:
        projects, has_next = demo.demo_top_projects(page) if await repo.is_demo_mode(session) else await repo.top_projects(session, page)
    text = f"⭐ <b>Top groupes</b> — page {page}\n\n"
    if not projects:
        text += "Aucun groupe actif pour l’instant."
    else:
        text += "Les groupes les mieux notés et les plus actifs montent ici.\n\n"
        for p in projects:
            text += short_project_line(p) + "\n"
    await call.message.edit_text(text, reply_markup=top_list_keyboard(projects, page, has_next))
    await call.answer()

@router.callback_query(F.data.startswith("project:detail:"))
async def project_detail(call: CallbackQuery):
    # project:detail:{id}:{origin}:{cat_id}:{page}
    _, _, project_id, origin, cat_id, page = call.data.split(":")
    project_id, cat_id, page = int(project_id), int(cat_id), int(page)
    async with SessionLocal() as session:
        if await repo.is_demo_mode(session):
            project = demo.get_demo_project(project_id)
            category_name = next((c.name for c in demo.demo_categories() if project and c.id == project.category_id), None)
        else:
            project = await repo.get_project(session, project_id)
            category = await repo.get_category(session, project.category_id) if project else None
            category_name = category.name if category else None
    if not project:
        await call.answer("Groupe introuvable.", show_alert=True)
        return
    await call.message.edit_text(project_detail_text(project, category_name), reply_markup=project_detail_keyboard(project_id, origin, cat_id, page))
    await call.answer()

@router.callback_query(F.data.startswith("click:"))
async def click_project(call: CallbackQuery):
    parts = call.data.split(":")
    project_id = int(parts[1])
    origin = parts[2] if len(parts) > 2 else "top"
    cat_id = int(parts[3]) if len(parts) > 3 else 0
    page = int(parts[4]) if len(parts) > 4 else 1
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        if await repo.is_demo_mode(session):
            project = demo.get_demo_project(project_id)
            if not project:
                await call.answer("Démo indisponible.", show_alert=True)
                return
            link = project.invite_link
        else:
            project = await repo.get_project(session, project_id)
            if not project or project.status != ProjectStatus.ACTIVE.value or not project.is_link_active:
                await call.answer("Lien indisponible pour le moment.", show_alert=True)
                return
            await repo.add_click(session, project, user)
            link = project.invite_link
    await call.answer("Lien ouvert ✅", show_alert=False)
    await call.message.edit_text(f"🚀 <b>Lien du groupe</b>\n\n{link}\n\nPense à noter le groupe après l’avoir visité.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Noter ce groupe", callback_data=f"rate:menu:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="⬅️ Retour aux détails", callback_data=f"project:detail:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))

@router.callback_query(F.data.startswith("rate:menu:"))
async def rate_menu(call: CallbackQuery):
    parts = call.data.split(":")
    project_id = int(parts[2])
    origin = parts[3] if len(parts) > 3 else "top"
    cat_id = int(parts[4]) if len(parts) > 4 else 0
    page = int(parts[5]) if len(parts) > 5 else 1
    await call.message.edit_text("Choisis une note :", reply_markup=rating_keyboard(project_id, origin, cat_id, page))
    await call.answer()

@router.callback_query(F.data.startswith("rate:set:"))
async def rate_set(call: CallbackQuery):
    parts = call.data.split(":")
    project_id, value = int(parts[2]), int(parts[3])
    origin = parts[4] if len(parts) > 4 else "top"
    cat_id = int(parts[5]) if len(parts) > 5 else 0
    page = int(parts[6]) if len(parts) > 6 else 1
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        if await repo.is_demo_mode(session):
            project = demo.get_demo_project(project_id)
            ok = project is not None
        else:
            project = await repo.get_project(session, project_id)
            if not project:
                await call.answer("Projet introuvable.", show_alert=True)
                return
            ok = await repo.set_rating(session, user, project, value)
    if not ok:
        await call.answer("Tu ne peux pas noter ton propre groupe.", show_alert=True)
    else:
        await call.message.edit_text("✅ Merci pour ta note. Ton avis aide les meilleurs groupes à monter.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Retour aux détails", callback_data=f"project:detail:{project_id}:{origin}:{cat_id}:{page}")],
            [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
        ]))
        await call.answer()

@router.callback_query(F.data.startswith("report:menu:"))
async def report_menu(call: CallbackQuery):
    # report:menu:{id}:{origin}:{cat_id}:{page}
    _, _, project_id, origin, cat_id, page = call.data.split(":")
    await call.message.edit_text("⚠️ <b>Signaler ce groupe</b>\n\nPourquoi veux-tu le signaler ?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 Lien mort", callback_data=f"report:set:{project_id}:Lien mort:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="⚠️ Scam / arnaque", callback_data=f"report:set:{project_id}:Scam:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="🚫 Contenu interdit", callback_data=f"report:set:{project_id}:Contenu interdit:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="⬅️ Retour aux détails", callback_data=f"project:detail:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))
    await call.answer()

@router.callback_query(F.data.startswith("report:set:"))
async def report_set(call: CallbackQuery):
    # report:set:{id}:{reason}:{origin}:{cat_id}:{page}
    _, _, project_id, reason, origin, cat_id, page = call.data.split(":")
    project_id, cat_id, page = int(project_id), int(cat_id), int(page)
    async with SessionLocal() as session:
        user = await repo.get_or_create_user(session, call.from_user, settings.super_admin_ids)
        if not await repo.is_demo_mode(session):
            project = await repo.get_project(session, project_id)
            if project:
                await repo.report_project(session, user, project, reason)
    await call.message.edit_text(f"✅ Signalement envoyé aux modérateurs.\n\nMotif : {reason}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Retour aux détails", callback_data=f"project:detail:{project_id}:{origin}:{cat_id}:{page}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))
    await call.answer()

@router.callback_query(F.data == "demo:user")
async def demo_user(call: CallbackQuery):
    text = (
        "🎭 <b>Démo côté utilisateur</b>\n\n"
        "Voici ce que verront les membres : ils choisissent une catégorie, cliquent sur un groupe, voient une fiche propre, puis peuvent entrer, noter ou signaler.\n\n"
        "Objectif commercial : plus ton groupe est bien noté et actif, plus il monte dans le classement."
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Voir les catégories démo", callback_data="browse:categories")],
        [InlineKeyboardButton(text="⭐ Voir le top démo", callback_data="browse:top:1")],
        [InlineKeyboardButton(text="📊 Démo côté listeur", callback_data="demo:owner")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))
    await call.answer()

@router.callback_query(F.data == "demo:owner")
async def demo_owner(call: CallbackQuery):
    p = demo.DEMO_OWNER_PROJECT
    text = (
        f"📊 <b>Démo côté listeur — {p.title}</b>\n\n"
        "Voilà ce que verra un propriétaire qui liste son groupe gratuitement :\n\n"
        f"🔗 Clics vers le groupe : {p.click_count}\n"
        f"🚀 Utilisateurs envoyés au bot : {p.start_count}\n"
        f"⭐ Note : {p.rating_avg:.1f}/5 ({p.rating_count} avis)\n"
        f"👥 Membres : {p.member_count}\n"
        f"📅 Listé depuis : 12 jours\n"
        "🟢 Lien actif\n\n"
        "Le propriétaire peut modifier son lien si le groupe saute, suivre ses stats et garder un point de secours pour ses membres."
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Simuler modification du lien", callback_data="demo:editlink")],
        [InlineKeyboardButton(text="🗑 Simuler suppression du projet", callback_data="demo:delete")],
        [InlineKeyboardButton(text="🚀 Lister mon groupe gratuitement", callback_data="project:add")],
        [InlineKeyboardButton(text="🎭 Démo utilisateur", callback_data="demo:user")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ]))
    await call.answer()

@router.callback_query(F.data == "demo:editlink")
async def demo_editlink(call: CallbackQuery):
    await call.answer("Démo : dans le vrai mode, le propriétaire envoie simplement son nouveau lien Telegram.", show_alert=True)

@router.callback_query(F.data == "demo:delete")
async def demo_delete(call: CallbackQuery):
    await call.answer("Démo : dans le vrai mode, le propriétaire peut retirer son groupe du listing.", show_alert=True)
