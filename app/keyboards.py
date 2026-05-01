from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu(is_super_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔎 Trouver un groupe", callback_data="browse:categories")],
        [InlineKeyboardButton(text="➕ Lister mon groupe", callback_data="project:add")],
        [InlineKeyboardButton(text="⭐ Top groupes", callback_data="browse:top:1")],
        [InlineKeyboardButton(text="📊 Mes projets", callback_data="owner:projects")],
        [InlineKeyboardButton(text="ℹ️ Infos", callback_data="info")],
    ]
    if is_super_admin:
        rows.append([InlineKeyboardButton(text="👑 Super admin", callback_data="sa:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Menu", callback_data="home")]])


def categories_keyboard(categories) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"browse:cat:{c.id}:1")] for c in categories]
    rows.append([InlineKeyboardButton(text="🏠 Menu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def project_card_keyboard(project_id: int, invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Entrer dans le groupe", callback_data=f"click:{project_id}")],
        [InlineKeyboardButton(text="⭐ Noter", callback_data=f"rate:menu:{project_id}"), InlineKeyboardButton(text="⚠️ Signaler", callback_data=f"report:{project_id}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def pagination(prefix: str, page: int, has_next: bool) -> list[InlineKeyboardButton]:
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️ Précédent", callback_data=f"{prefix}:{page-1}"))
    if has_next:
        row.append(InlineKeyboardButton(text="➡️ Suivant", callback_data=f"{prefix}:{page+1}"))
    return row


def rating_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:set:{project_id}:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def owner_project_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Stats", callback_data=f"owner:stats:{project_id}")],
        [InlineKeyboardButton(text="🔗 Modifier le lien", callback_data=f"owner:editlink:{project_id}")],
        [InlineKeyboardButton(text="📌 Vérifier pin", callback_data=f"owner:pin:{project_id}")],
        [InlineKeyboardButton(text="🗑 Supprimer", callback_data=f"owner:delete:{project_id}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def super_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕓 Demandes en attente", callback_data="sa:pending")],
        [InlineKeyboardButton(text="🔴 Liens inactifs", callback_data="sa:inactive")],
        [InlineKeyboardButton(text="📋 Tous les projets", callback_data="sa:projects")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])


def super_admin_project_keyboard(project_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Valider", callback_data=f"sa:approve:{project_id}"), InlineKeyboardButton(text="❌ Refuser", callback_data=f"sa:reject:{project_id}")],
        [InlineKeyboardButton(text="🚫 Bannir", callback_data=f"sa:ban:{project_id}")],
        [InlineKeyboardButton(text="🏠 Menu", callback_data="home")],
    ])
