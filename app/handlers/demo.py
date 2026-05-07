from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.keyboards.common import kb
from app.services.demo_data import DEMO_CATEGORIES, DEMO_PROJECTS

router = Router()

@router.callback_query(F.data == "demo:user")
async def demo_user(call: CallbackQuery):
    text = (
        "🎭 Démo utilisateur\n\n"
        "Voici ce qu’un utilisateur voit quand il cherche un groupe.\n\n"
        "Il peut choisir une catégorie, voir les groupes, ouvrir une fiche, entrer, noter ou signaler."
    )

    rows = []
    for cat in DEMO_CATEGORIES:
        rows.append([(f"📂 {cat['name']}", f"demo:cat:{cat['id']}:0")])

    rows.append([("🏠 Menu", "home")])

    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("demo:cat:"))
async def demo_cat(call: CallbackQuery):
    _, _, cid, page = call.data.split(":")
    cid = int(cid)
    page = int(page)

    cat = next((c for c in DEMO_CATEGORIES if c["id"] == cid), None)
    if not cat:
        await call.answer("Catégorie introuvable", show_alert=True)
        return

    if cat.get("warning_enabled") and cat.get("warning_text") and call.data.startswith("demo:cat:"):
        await call.message.edit_text(
            f"⚠️ {cat['warning_text']}",
            reply_markup=kb([
                [("➡️ Continuer", f"demo:catgo:{cid}:{page}")],
                [("⬅️ Retour", "demo:user")],
                [("🏠 Menu", "home")]
            ])
        )
        await call.answer()
        return

@router.callback_query(F.data.startswith("demo:catgo:"))
async def demo_catgo(call: CallbackQuery):
    _, _, cid, page = call.data.split(":")
    cid = int(cid)
    page = int(page)

    cat = next((c for c in DEMO_CATEGORIES if c["id"] == cid), None)
    projects = [p for p in DEMO_PROJECTS if p["category_id"] == cid]

    size = 3
    chunk = projects[page * size:(page + 1) * size]

    text = f"📂 {cat['name']} — page {page + 1}\n\n"

    rows = []

    if not chunk:
        text += "Aucun groupe dans cette catégorie."
    else:
        for p in chunk:
            text += (
                f"🟢 {p['title']}\n"
                f"⭐ {p['rating']}/5 — 👥 {p['members']:,} membres\n\n"
            ).replace(",", " ")
            rows.append([(f"📌 {p['title']}", f"demo:project:{p['id']}:{cid}:{page}")])

    nav = []
    if page > 0:
        nav.append(("⬅️ Précédent", f"demo:catgo:{cid}:{page-1}"))
    if (page + 1) * size < len(projects):
        nav.append(("➡️ Suivant", f"demo:catgo:{cid}:{page+1}"))

    if nav:
        rows.append(nav)

    rows.append([("⬅️ Catégories démo", "demo:user")])
    rows.append([("🏠 Menu", "home")])

    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("demo:project:"))
async def demo_project(call: CallbackQuery):
    parts = call.data.split(":")
    pid = int(parts[2])
    cid = int(parts[3]) if len(parts) > 3 else 1
    page = int(parts[4]) if len(parts) > 4 else 0

    p = next((x for x in DEMO_PROJECTS if x["id"] == pid), None)
    if not p:
        await call.answer("Groupe introuvable", show_alert=True)
        return

    text = (
        f"🟢 {p['title']}\n\n"
        f"{p['description']}\n\n"
        f"⭐ Note : {p['rating']}/5 — {p['reviews']} avis\n"
        f"👥 Membres : {p['members']:,}\n"
        f"🔥 Popularité : {p['clicks']:,}\n"
        f"🟢 Lien actif\n\n"
        "Que veux-tu faire ?"
    ).replace(",", " ")

    await call.message.edit_text(
        text,
        reply_markup=kb([
            [("🚀 Entrer dans le groupe", f"demo:join:{pid}")],
            [("⭐ Noter", f"demo:rate:{pid}")],
            [("⚠️ Signaler", f"demo:report_menu:{pid}")],
            [("⬅️ Retour", f"demo:catgo:{cid}:{page}")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("demo:join:"))
async def demo_join(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    p = next((x for x in DEMO_PROJECTS if x["id"] == pid), None)

    await call.message.edit_text(
        f"🚀 Démo : l’utilisateur reçoit ici le lien du groupe.\n\n{p['url']}",
        reply_markup=kb([
            [("⬅️ Retour fiche", f"demo:project:{pid}:1:0")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("demo:rate:"))
async def demo_rate(call: CallbackQuery):
    pid = int(call.data.split(":")[2])

    await call.message.edit_text(
        "⭐ Démo notation\n\nChoisis une note pour voir l’expérience utilisateur :",
        reply_markup=kb([
            [("1 ⭐", f"demo:rate_done:{pid}:1"), ("2 ⭐", f"demo:rate_done:{pid}:2")],
            [("3 ⭐", f"demo:rate_done:{pid}:3"), ("4 ⭐", f"demo:rate_done:{pid}:4")],
            [("5 ⭐", f"demo:rate_done:{pid}:5")],
            [("⬅️ Retour fiche", f"demo:project:{pid}:1:0")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("demo:rate_done:"))
async def demo_rate_done(call: CallbackQuery):
    await call.answer("🎭 Démo : note enregistrée en simulation.", show_alert=True)

@router.callback_query(F.data.startswith("demo:report_menu:"))
async def demo_report_menu(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    await call.message.edit_text(
        "⚠️ Démo signalement\n\nPourquoi veux-tu signaler ce groupe ?",
        reply_markup=kb([
            [("🔴 Lien mort", f"demo:report_done:{pid}")],
            [("⚠️ Scam / arnaque", f"demo:report_done:{pid}")],
            [("🚫 Contenu interdit", f"demo:report_done:{pid}")],
            [("⬅️ Retour fiche", f"demo:project:{pid}:1:0")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("demo:report_done:"))
async def demo_report_done(call: CallbackQuery):
    await call.answer("🎭 Démo : signalement envoyé en simulation.", show_alert=True)

@router.callback_query(F.data == "demo:lister")
async def demo_lister(call: CallbackQuery):
    p = DEMO_PROJECTS[0]

    text = (
        f"📊 Démo côté listeur — {p['title']}\n\n"
        "Voilà ce que verra un propriétaire qui liste son groupe gratuitement :\n\n"
        f"🔗 Clics vers le groupe : {p['clicks']}\n"
        f"🚀 Utilisateurs envoyés au bot : {p['clicks'] // 3}\n"
        f"⭐ Note : {p['rating']}/5 ({p['reviews']} avis)\n"
        f"👥 Membres : {p['members']}\n"
        "📅 Listé depuis : 12 jours\n"
        "🟢 Lien actif\n"
        "⚠️ Warnings bot : 0/3\n"
        "🛡️ Modération : activée\n\n"
        "Le propriétaire peut modifier son lien, suivre ses stats, gérer sa modération et garder un point de secours pour ses membres."
    )

    await call.message.edit_text(
        text,
        reply_markup=kb([
            [("🔗 Simuler modification du lien", "demo:lister_action")],
            [("🛡️ Simuler modération", "demo:lister_mod")],
            [("🗑️ Simuler suppression du projet", "demo:lister_action")],
            [("➕ Lister mon groupe gratuitement", "list:start")],
            [("🎭 Démo utilisateur", "demo:user")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "demo:lister_action")
async def demo_lister_action(call: CallbackQuery):
    await call.answer("🎭 Démo : action simulée.", show_alert=True)

@router.callback_query(F.data == "demo:lister_mod")
async def demo_lister_mod(call: CallbackQuery):
    await call.message.edit_text(
        "🛡️ Démo modération listeur\n\n"
        "Le listeur peut gérer les protections de son groupe :\n\n"
        "🚫 Mots interdits\n"
        "🔗 Anti-liens\n"
        "🔇 Sanctions automatiques\n"
        "📜 Historique des actions\n\n"
        "Exemple : lien externe détecté = suppression + ban.",
        reply_markup=kb([
            [("➕ Simuler ajout mot interdit", "demo:lister_action")],
            [("👀 Voir mots interdits démo", "demo:lister_action")],
            [("⬅️ Retour démo listeur", "demo:lister")],
            [("🏠 Menu", "home")]
        ])
    )
    await call.answer()
