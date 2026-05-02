from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.models import UserRole


def main_menu(user=None, has_projects: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔎 Trouver un groupe", callback_data="browse:categories")],
        [InlineKeyboardButton(text="➕ Lister mon groupe gratuitement", callback_data="project:add")],
        [InlineKeyboardButton(text="⭐ Top groupes", callback_data="browse:top:1")],
        [InlineKeyboardButton(text="ℹ️ Infos", callback_data="info")],
    ]
    if has_projects:
        rows.insert(2, [InlineKeyboardButton(text="📊 Mes projets", callback_data="owner:projects")])
    if user and user.role == UserRole.SUPER_ADMIN.value:
        rows.append([InlineKeyboardButton(text="🛠 Modération", callback_data="sa:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Menu", callback_data="home")]])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Annuler", callback_data="cancel")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def categories_keyboard(categories, for_listing: bool = False) -> InlineKeyboardMarkup:
    prefix = "project:cat" if for_listing else "browse:cat"
    rows = [[InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"{prefix}:{c.id}:1")] for c in categories]
    rows.append([InlineKeyboardButton(text="💡 Suggérer une catégorie", callback_data="cat:suggest")])
    rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:set:{project_id}:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text="❌ Annuler", callback_data=f"browse:top:1")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def owner_project_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data=f"owner:stats:{project_id}")],
        [InlineKeyboardButton(text="🔗 Modifier le lien", callback_data=f"owner:editlink:{project_id}")],
        [InlineKeyboardButton(text="📌 Vérifier pin", callback_data=f"owner:pin:{project_id}")],
        [InlineKeyboardButton(text="🗑 Supprimer", callback_data=f"owner:delete:{project_id}")],
        [InlineKeyboardButton(text="⬅️ Mes projets", callback_data="owner:projects")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def super_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕓 Demandes en attente", callback_data="sa:pending")],
        [InlineKeyboardButton(text="🔴 Liens inactifs", callback_data="sa:inactive")],
        [InlineKeyboardButton(text="📋 Tous les projets", callback_data="sa:projects")],
        [InlineKeyboardButton(text="📂 Ajouter catégorie", callback_data="sa:cat:add")],
        [InlineKeyboardButton(text="🗑 Supprimer catégorie", callback_data="sa:cat:delete_menu")],
        [InlineKeyboardButton(text="💡 Suggestions catégories", callback_data="sa:cat:suggestions")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def super_admin_project_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Valider", callback_data=f"sa:approve:{project_id}"), InlineKeyboardButton(text="❌ Refuser", callback_data=f"sa:reject:{project_id}")],
        [InlineKeyboardButton(text="🚫 Bannir", callback_data=f"sa:ban:{project_id}")],
        [InlineKeyboardButton(text="⬅️ Modération", callback_data="sa:menu")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])
