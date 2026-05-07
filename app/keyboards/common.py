from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in rows
    ])

def main_menu(is_owner=False, is_moderator=False):
    rows = [
        [("🔎 Trouver un groupe", "cats:0")],
        [("➕ Lister mon groupe", "list:start")],
        [("⭐ Top groupes", "top:0")],
        [("ℹ️ Infos", "info")],
    ]
    if is_owner:
        rows.insert(2, [("📊 Espace listeur", "owner:menu")])
    if is_moderator:
        rows.append([("🛠 Modération", "mod:menu")])
    return kb(rows)

def back_home(extra_back=None):
    rows = []
    if extra_back:
        rows.append([extra_back])
    rows.append([("🏠 Menu", "home")])
    return kb(rows)

def cancel_kb():
    return kb([[("❌ Annuler", "cancel")]])
