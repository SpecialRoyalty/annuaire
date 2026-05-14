from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) if not str(data).startswith("http") else InlineKeyboardButton(text=text, url=data) for text, data in row]
        for row in rows
    ])

def main_menu(is_owner=False, is_moderator=False, demo_active=False):
    rows = [[("🔎 Trouver un groupe","cats")]]
    if demo_active:
        rows += [[("🎭 Voir la démo utilisateur","demo:user")],[("📊 Voir la démo listeur","demo:lister")]]
    if is_owner:
        rows.append([("📊 Espace listeur","owner:menu")])
    rows += [[("➕ Lister mon groupe gratuitement","list:start")],[("⭐ Top groupes","top:0")],[("ℹ️ Infos","info")]]
    if is_moderator:
        rows.append([("🛠️ Modération","mod:menu")])
    return kb(rows)

def cancel_kb():
    return kb([[("❌ Annuler","cancel")]])
