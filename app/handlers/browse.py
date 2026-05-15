from sqlalchemy import select, desc
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import SessionLocal
from app.config import settings
from app.models.models import Category, Project, Click, Rating, Report
from app.services.user_service import get_or_create_user
from app.services.settings_service import is_demo
from app.services.demo_data import DEMO_CATEGORIES, DEMO_PROJECTS
from app.keyboards.common import kb

router = Router()

@router.callback_query(F.data == "cats")
async def cats(call: CallbackQuery):
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            rows = [[(f"📂 {c['name']}", f"cat:{c['id']}:0")] for c in DEMO_CATEGORIES]
        else:
            cats = list((await session.scalars(select(Category).order_by(Category.position, Category.name))).all())
            rows = [[(f"📂 {c.name}", f"cat:{c.id}:0")] for c in cats]
    rows += [[("💡 Suggérer une catégorie","suggest_cat:start")],[("🏠 Menu","home")]]
    await call.message.edit_text("📂 Choisis une catégorie :", reply_markup=kb(rows))
    await call.answer()

async def render_cat(call, cid:int, page:int, skip_warning=False):
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            cat = next((c for c in DEMO_CATEGORIES if c["id"]==cid), None)
            projects = [p for p in DEMO_PROJECTS if p["category_id"]==cid]
            if cat and cat.get("warning_enabled") and cat.get("warning_text") and not skip_warning:
                await call.message.edit_text(cat["warning_text"], reply_markup=kb([[("➡️ Continuer",f"catgo:{cid}:{page}")],[("⬅️ Retour","cats")]])); return
            cat_name = cat["name"] if cat else "Catégorie"
        else:
            cat = await session.get(Category, cid)
            if not cat: await call.answer("Introuvable", show_alert=True); return
            if cat.warning_enabled and cat.warning_text and not skip_warning:
                await call.message.edit_text(cat.warning_text, reply_markup=kb([[("➡️ Continuer",f"catgo:{cid}:{page}")],[("⬅️ Retour","cats")]])); return
            projects = list((await session.scalars(select(Project).where(Project.category_id==cid, Project.status=="active").order_by(desc(Project.rating_sum), desc(Project.click_count)))).all())
            cat_name = cat.name

    size = settings.PAGE_SIZE
    chunk = projects[page*size:(page+1)*size]
    text = f"📂 {cat_name} — page {page+1}\n\n"
    rows = []
    if not chunk:
        text += f"Aucun groupe ici.\n\nTu ne trouves pas ton groupe ? Demande au propriétaire de le lister ici : @{settings.BOT_USERNAME}"
    for p in chunk:
        if isinstance(p, dict):
            text += f"🟢 {p['title']}\n⭐ {p['rating']}/5 — 👥 {p['members']:,} membres\n📈 +{p['growth']} récemment\n\n".replace(",", " ")
            rows.append([(f"📌 {p['title']}", f"project:{p['id']}:{cid}:{page}")])
        else:
            avg = p.rating_sum/p.rating_count if p.rating_count else 0
            text += f"{'🟢' if p.is_link_active else '🔴'} {p.title}\n⭐ {avg:.1f}/5 — 👥 {p.member_count:,} membres\n📈 {(p.growth_last_sync or 0):+} depuis la dernière sync\n\n".replace(",", " ")
            rows.append([(f"📌 {p.title}", f"project:{p.id}:{cid}:{page}")])
    nav=[]
    if page>0: nav.append(("⬅️ Précédent",f"catgo:{cid}:{page-1}"))
    if (page+1)*size < len(projects): nav.append(("➡️ Suivant",f"catgo:{cid}:{page+1}"))
    if nav: rows.append(nav)
    rows += [[("⬅️ Catégories","cats")],[("🏠 Menu","home")]]
    await call.message.edit_text(text, reply_markup=kb(rows))

@router.callback_query(F.data.startswith("cat:"))
async def cat(call: CallbackQuery):
    _, cid, page = call.data.split(":")
    await render_cat(call, int(cid), int(page), False)
    await call.answer()

@router.callback_query(F.data.startswith("catgo:"))
async def catgo(call: CallbackQuery):
    _, cid, page = call.data.split(":")
    await render_cat(call, int(cid), int(page), True)
    await call.answer()

@router.callback_query(F.data.startswith("project:"))
async def project(call: CallbackQuery):
    parts = call.data.split(":")
    pid = int(parts[1]); back = f"catgo:{parts[2]}:{parts[3]}" if len(parts)>=4 else "cats"
    async with SessionLocal() as session:
        demo = await is_demo(session)
        if demo:
            p = next((x for x in DEMO_PROJECTS if x["id"]==pid), None)
            if not p: await call.answer("Introuvable", show_alert=True); return
            text = f"🟢 {p['title']}\n\n{p['description']}\n\n⭐ Note : {p['rating']}/5 — {p['reviews']} avis\n👥 Membres : {p['members']:,}\n📈 +{p['growth']} récemment\n🔥 Popularité : {p['clicks']:,}\n🟢 Lien actif\n\nQue veux-tu faire ?".replace(",", " ")
            rows = [[("🚀 Entrer dans le groupe",f"demo_join:{pid}")],[("⭐ Noter",f"rate:{pid}:demo")],[("⚠️ Signaler",f"report_menu:{pid}:demo")],[("⬅️ Retour",back)],[("🏠 Menu","home")]]
        else:
            p = await session.get(Project, pid)
            if not p or p.status!="active": await call.answer("Introuvable", show_alert=True); return
            avg = p.rating_sum/p.rating_count if p.rating_count else 0
            text = f"{'🟢' if p.is_link_active else '🔴'} {p.title}\n\n{p.description}\n\n⭐ Note : {avg:.1f}/5 — {p.rating_count} avis\n👥 Membres : {p.member_count:,}\n📈 {(p.growth_last_sync or 0):+} depuis la dernière sync\n🔥 Popularité : {p.click_count:,}\n{'🟢 Lien actif' if p.is_link_active else '🔴 Lien inactif'}\n\nQue veux-tu faire ?".replace(",", " ")
            rows = [[("🚀 Entrer dans le groupe",f"join:{pid}")],[("⭐ Noter",f"rate:{pid}:real")],[("⚠️ Signaler",f"report_menu:{pid}:real")],[("⬅️ Retour",back)],[("🏠 Menu","home")]]
    await call.message.edit_text(text, reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("demo_join:"))
async def demo_join(call: CallbackQuery):
    pid=int(call.data.split(":")[1]); p=next(x for x in DEMO_PROJECTS if x["id"]==pid)
    await call.message.edit_text(f"🎭 Démo : voici le lien.\n\n{p['url']}", reply_markup=kb([[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("join:"))
async def join(call: CallbackQuery):
    pid=int(call.data.split(":")[1])
    async with SessionLocal() as session:
        user=await get_or_create_user(session, call.from_user); p=await session.get(Project,pid)
        if not p: await call.answer("Introuvable", show_alert=True); return
        p.click_count += 1; session.add(Click(user_id=user.id, project_id=p.id, source="bot")); await session.commit()
    await call.message.edit_text(f"🚀 Voici le lien du groupe :\n\n{p.invite_link}", reply_markup=kb([[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("rate:"))
async def rate(call: CallbackQuery):
    _,pid,mode=call.data.split(":")
    await call.message.edit_text("⭐ Choisis une note :", reply_markup=kb([[("1 ⭐",f"rate_do:{pid}:{mode}:1"),("2 ⭐",f"rate_do:{pid}:{mode}:2")],[("3 ⭐",f"rate_do:{pid}:{mode}:3"),("4 ⭐",f"rate_do:{pid}:{mode}:4")],[("5 ⭐",f"rate_do:{pid}:{mode}:5")],[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("rate_do:"))
async def rate_do(call: CallbackQuery):
    _,pid,mode,val=call.data.split(":")
    if mode=="demo": await call.answer("🎭 Note simulée.", show_alert=True); return
    async with SessionLocal() as session:
        user=await get_or_create_user(session, call.from_user); p=await session.get(Project,int(pid))
        if not p: await call.answer("Introuvable", show_alert=True); return
        if p.owner_user_id==user.id: await call.answer("Tu ne peux pas noter ton propre groupe.", show_alert=True); return
        exists=await session.scalar(select(Rating).where(Rating.user_id==user.id, Rating.project_id==p.id))
        if exists: await call.answer("Tu as déjà noté.", show_alert=True); return
        p.rating_sum += int(val); p.rating_count += 1; session.add(Rating(user_id=user.id, project_id=p.id, rating=int(val))); await session.commit()
    await call.answer("Merci pour ta note ⭐", show_alert=True)

@router.callback_query(F.data.startswith("report_menu:"))
async def report_menu(call: CallbackQuery):
    _,pid,mode=call.data.split(":")
    await call.message.edit_text("Pourquoi signaler ?", reply_markup=kb([[("🔴 Lien mort",f"report:{pid}:{mode}:lien_mort")],[("⚠️ Scam / arnaque",f"report:{pid}:{mode}:scam")],[("🚫 Contenu interdit",f"report:{pid}:{mode}:contenu_interdit")],[("🏠 Menu","home")]])); await call.answer()

@router.callback_query(F.data.startswith("report:"))
async def report(call: CallbackQuery):
    _,pid,mode,reason=call.data.split(":")
    if mode=="demo": await call.answer("🎭 Signalement simulé.", show_alert=True); return
    async with SessionLocal() as session:
        user=await get_or_create_user(session, call.from_user); session.add(Report(user_id=user.id, project_id=int(pid), reason=reason)); await session.commit()
    await call.answer("Signalement envoyé.", show_alert=True)

@router.callback_query(F.data.startswith("top:"))
async def top(call: CallbackQuery):
    async with SessionLocal() as session:
        demo=await is_demo(session)
        projects=sorted(DEMO_PROJECTS,key=lambda x:(x["rating"],x["clicks"]), reverse=True) if demo else list((await session.scalars(select(Project).where(Project.status=="active").order_by(desc(Project.rating_sum), desc(Project.click_count)))).all())
    text="⭐ Top groupes\n\n"; rows=[]
    for p in projects[:settings.PAGE_SIZE]:
        if isinstance(p,dict):
            text += f"🟢 {p['title']} — ⭐ {p['rating']}/5\n"; rows.append([(f"📌 {p['title']}",f"project:{p['id']}")])
        else:
            avg=p.rating_sum/p.rating_count if p.rating_count else 0; text += f"🟢 {p.title} — ⭐ {avg:.1f}/5\n"; rows.append([(f"📌 {p.title}",f"project:{p.id}")])
    rows.append([("🏠 Menu","home")]); await call.message.edit_text(text, reply_markup=kb(rows)); await call.answer()
