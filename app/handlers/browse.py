from math import ceil
from sqlalchemy import select, desc
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import SessionLocal
from app.config import settings
from app.models.models import Category, Project, Click, Report, Rating
from app.services.user_service import get_or_create_user
from app.services.settings_service import is_demo
from app.services.demo_data import DEMO_CATEGORIES, DEMO_PROJECTS
from app.keyboards.common import kb

router = Router()

def rating_text(p):
    if isinstance(p, dict):
        return f"{p['rating']:.1f}/5 — {p['reviews']} avis"
    return f"{(p.rating_sum / p.rating_count if p.rating_count else 0):.1f}/5 — {p.rating_count} avis"

@router.callback_query(F.data.startswith("cats:"))
async def categories(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            cats = DEMO_CATEGORIES
            rows = [[(f"📂 {c['name']}", f"cat:{c['id']}:0")] for c in cats]
        else:
            cats = list((await session.scalars(select(Category).order_by(Category.position, Category.name))).all())
            rows = [[(f"📂 {c.name}", f"cat:{c.id}:0")] for c in cats]
        rows.append([("💡 Suggérer une catégorie", "suggest_cat:start")])
        rows.append([("🏠 Menu", "home")])
        await call.message.edit_text("📂 Choisis une catégorie :", reply_markup=kb(rows))
        await call.answer()

@router.callback_query(F.data.startswith("cat:"))
async def category_projects(call: CallbackQuery):
    _, cat_id, page = call.data.split(":")
    cat_id, page = int(cat_id), int(page)
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            cat = next((c for c in DEMO_CATEGORIES if c["id"] == cat_id), None)
            projects = [p for p in DEMO_PROJECTS if p["category_id"] == cat_id]
            cat_name = cat["name"] if cat else "Catégorie"
        else:
            cat = await session.get(Category, cat_id)
            cat_name = cat.name if cat else "Catégorie"
            projects = list((await session.scalars(
                select(Project).where(Project.category_id == cat_id, Project.status == "active")
                .order_by(desc(Project.rating_sum), desc(Project.click_count))
            )).all())

        size = settings.PAGE_SIZE
        chunk = projects[page*size:(page+1)*size]
        if not chunk:
            text = f"📂 {cat_name}\n\nAucun groupe listé ici pour le moment.\n\nTu ne trouves pas ton groupe ? Demande au propriétaire de le lister ici : @{settings.BOT_USERNAME}"
            rows = [[("💡 Suggérer une catégorie", "suggest_cat:start")], [("⬅️ Catégories", "cats:0")], [("🏠 Menu", "home")]]
        else:
            text = f"📂 {cat_name} — page {page+1}\n\n"
            rows = []
            for p in chunk:
                if isinstance(p, dict):
                    text += f"🟢 {p['title']}\n⭐ {p['rating']:.1f}/5 — 👥 {p['members']:,} membres\n\n".replace(",", " ")
                    rows.append([(f"📌 {p['title']}", f"project:{p['id']}:cat:{cat_id}:{page}")])
                else:
                    avg = p.rating_sum / p.rating_count if p.rating_count else 0
                    status = "🟢" if p.is_link_active else "🔴"
                    text += f"{status} {p.title}\n⭐ {avg:.1f}/5 — 👥 {p.member_count:,} membres\n\n".replace(",", " ")
                    rows.append([(f"📌 {p.title}", f"project:{p.id}:cat:{cat_id}:{page}")])
            nav = []
            if page > 0:
                nav.append(("⬅️ Précédent", f"cat:{cat_id}:{page-1}"))
            if (page + 1) * size < len(projects):
                nav.append(("➡️ Suivant", f"cat:{cat_id}:{page+1}"))
            if nav:
                rows.append(nav)
            rows += [[("💡 Suggérer une catégorie", "suggest_cat:start")], [("⬅️ Catégories", "cats:0")], [("🏠 Menu", "home")]]
        await call.message.edit_text(text, reply_markup=kb(rows))
        await call.answer()

@router.callback_query(F.data.startswith("project:"))
async def project_detail(call: CallbackQuery):
    parts = call.data.split(":")
    pid = int(parts[1])
    back = "home"
    if len(parts) >= 5 and parts[2] == "cat":
        back = f"cat:{parts[3]}:{parts[4]}"
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            p = next((x for x in DEMO_PROJECTS if x["id"] == pid), None)
            if not p:
                await call.answer("Introuvable", show_alert=True); return
            status = "🟢 Lien actif" if p["active"] else "🔴 Lien inactif"
            text = (
                f"🟢 {p['title']}\n\n"
                f"{p['description']}\n\n"
                f"⭐ Note : {p['rating']:.1f}/5 — {p['reviews']} avis\n"
                f"👥 Membres : {p['members']:,}\n"
                f"🔥 Popularité : {p['clicks']:,}\n"
                f"{status}\n\n"
                "Que veux-tu faire ?"
            ).replace(",", " ")
            rows = [
                [("🚀 Entrer dans le groupe", f"demo_join:{pid}")],
                [("⭐ Noter", f"rate:{pid}:demo")],
                [("⚠️ Signaler", f"report_menu:{pid}:demo")],
                [("⬅️ Retour", back), ("🏠 Menu", "home")]
            ]
        else:
            p = await session.get(Project, pid)
            if not p or p.status != "active":
                await call.answer("Introuvable", show_alert=True); return
            avg = p.rating_sum / p.rating_count if p.rating_count else 0
            status = "🟢 Lien actif" if p.is_link_active else "🔴 Lien inactif"
            text = (
                f"{'🟢' if p.is_link_active else '🔴'} {p.title}\n\n"
                f"{p.description}\n\n"
                f"⭐ Note : {avg:.1f}/5 — {p.rating_count} avis\n"
                f"👥 Membres : {p.member_count:,}\n"
                f"🔥 Popularité : {p.click_count:,}\n"
                f"{status}\n\n"
                "Que veux-tu faire ?"
            ).replace(",", " ")
            rows = [
                [("🚀 Entrer dans le groupe", f"join:{pid}")],
                [("⭐ Noter", f"rate:{pid}:real")],
                [("⚠️ Signaler", f"report_menu:{pid}:real")],
                [("⬅️ Retour", back), ("🏠 Menu", "home")]
            ]
        await call.message.edit_text(text, reply_markup=kb(rows))
        await call.answer()

@router.callback_query(F.data.startswith("join:"))
async def join_real(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = await session.get(Project, pid)
        if not p:
            await call.answer("Introuvable", show_alert=True); return
        p.click_count += 1
        session.add(Click(user_id=user.id, project_id=p.id, source="bot"))
        await session.commit()
        await call.message.edit_text(f"🚀 Voici le lien du groupe :\n\n{p.invite_link}", reply_markup=kb([[("⬅️ Retour", f"project:{pid}"), ("🏠 Menu", "home")]]))
        await call.answer()

@router.callback_query(F.data.startswith("demo_join:"))
async def join_demo(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    p = next((x for x in DEMO_PROJECTS if x["id"] == pid), None)
    await call.message.edit_text(f"🎭 Démo : voici où l'utilisateur recevrait le lien.\n\n{p['url']}", reply_markup=kb([[("⬅️ Retour", f"project:{pid}"), ("🏠 Menu", "home")]]))
    await call.answer()

@router.callback_query(F.data.startswith("rate:"))
async def rate_menu(call: CallbackQuery):
    _, pid, mode = call.data.split(":")
    rows = [[(f"{i} ⭐", f"rate_do:{pid}:{mode}:{i}") for i in range(1, 6)], [("⬅️ Retour", f"project:{pid}"), ("🏠 Menu", "home")]]
    await call.message.edit_text("⭐ Choisis une note :", reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("rate_do:"))
async def rate_do(call: CallbackQuery):
    _, pid, mode, rating = call.data.split(":")
    if mode == "demo":
        await call.answer("🎭 Note enregistrée en simulation", show_alert=True)
        return
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = await session.get(Project, int(pid))
        if not p:
            await call.answer("Introuvable", show_alert=True); return
        if p.owner_user_id == user.id:
            await call.answer("Tu ne peux pas noter ton propre projet.", show_alert=True); return
        existing = await session.scalar(select(Rating).where(Rating.user_id == user.id, Rating.project_id == p.id))
        if existing:
            await call.answer("Tu as déjà noté ce groupe.", show_alert=True); return
        r = int(rating)
        p.rating_sum += r
        p.rating_count += 1
        session.add(Rating(user_id=user.id, project_id=p.id, rating=r))
        await session.commit()
        await call.answer("Merci pour ta note ⭐", show_alert=True)

@router.callback_query(F.data.startswith("report_menu:"))
async def report_menu(call: CallbackQuery):
    _, pid, mode = call.data.split(":")
    rows = [
        [("🔴 Lien mort", f"report:{pid}:{mode}:lien_mort")],
        [("⚠️ Scam / arnaque", f"report:{pid}:{mode}:scam")],
        [("🚫 Contenu interdit", f"report:{pid}:{mode}:contenu_interdit")],
        [("⬅️ Retour", f"project:{pid}"), ("🏠 Menu", "home")]
    ]
    await call.message.edit_text("Pourquoi veux-tu signaler ce groupe ?", reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("report:"))
async def report_do(call: CallbackQuery):
    _, pid, mode, reason = call.data.split(":")
    if mode == "demo":
        await call.answer("🎭 Signalement simulé", show_alert=True)
        return
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        session.add(Report(user_id=user.id, project_id=int(pid), reason=reason))
        await session.commit()
    await call.answer("Signalement envoyé à la modération.", show_alert=True)

@router.callback_query(F.data.startswith("top:"))
async def top(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            projects = sorted(DEMO_PROJECTS, key=lambda p: (p["rating"], p["clicks"]), reverse=True)
        else:
            projects = list((await session.scalars(
                select(Project).where(Project.status == "active").order_by(desc(Project.rating_sum), desc(Project.click_count))
            )).all())
        size = settings.PAGE_SIZE
        chunk = projects[page*size:(page+1)*size]
        text = f"⭐ Top groupes — page {page+1}\n\n"
        rows = []
        for p in chunk:
            if isinstance(p, dict):
                text += f"🟢 {p['title']}\n⭐ {p['rating']:.1f}/5 — 👥 {p['members']:,}\n\n".replace(",", " ")
                rows.append([(f"📌 {p['title']}", f"project:{p['id']}")])
            else:
                avg = p.rating_sum / p.rating_count if p.rating_count else 0
                text += f"🟢 {p.title}\n⭐ {avg:.1f}/5 — 👥 {p.member_count:,}\n\n".replace(",", " ")
                rows.append([(f"📌 {p.title}", f"project:{p.id}")])
        nav = []
        if page > 0:
            nav.append(("⬅️ Précédent", f"top:{page-1}"))
        if (page+1)*size < len(projects):
            nav.append(("➡️ Suivant", f"top:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([("🏠 Menu", "home")])
        await call.message.edit_text(text or "Aucun groupe.", reply_markup=kb(rows))
        await call.answer()
