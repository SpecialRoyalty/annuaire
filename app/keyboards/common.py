from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in rows
    ])

def main_menu(is_owner=False, is_moderator=False):
    rows = [
        [("🔎 Trouver un groupe", "cats")],
        [("🎭 Voir la démo utilisateur", "demo:user")],
        [("📊 Voir la démo listeur", "demo:lister")],
        [("➕ Lister mon groupe gratuitement", "list:start")],
        [("⭐ Top groupes", "top:0")],
        [("ℹ️ Infos", "info")],
    ]

    if is_owner:
        rows.insert(4, [("📊 Espace listeur", "owner:menu")])

    if is_moderator:
        rows.append([("🛠️ Modération", "mod:menu")])

    return kb(rows)

def cancel_kb():
    return kb([[("❌ Annuler", "cancel")]])

def back_menu():
    return kb([[("🏠 Menu", "home")]])
