from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in rows
    ])

def main_menu(is_owner=False, is_moderator=False, demo_active=False):
    rows = [
        [("🔎 Trouver un groupe", "cats")],
    ]

    if demo_active:
        rows.append([("🎭 Voir la démo utilisateur", "demo:user")])
        rows.append([("📊 Voir la démo listeur", "demo:lister")])

    rows.extend([
        [("➕ Lister mon groupe gratuitement", "list:start")],
        [("⭐ Top groupes", "top:0")],
        [("ℹ️ Infos", "info")],
    ])

    if is_owner:
        rows.insert(2 if demo_active else 1, [("📊 Espace listeur", "owner:menu")])

    if is_moderator:
        rows.append([("🛠️ Modération", "mod:menu")])

    return kb(rows)

def cancel_kb():
    return kb([[("❌ Annuler", "cancel")]])

def back_menu():
    return kb([[("🏠 Menu", "home")]])
