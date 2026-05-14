from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, User, Category, CategorySuggestion
from app.services.user_service import get_or_create_user
from app.services.settings_service import get_setting, set_setting
from app.config import settings
from app.keyboards.common import kb, cancel_kb

router = Router()

class AdminState(StatesGroup):
    reject_project=State(); reject_category=State(); add_category=State(); edit_warning=State()

async def admin_only(session,tg_user):
    user=await get_or_create_user(session,tg_user); return user.is_super_admin

async def mod_kb():
    async with SessionLocal() as session: demo=await get_setting(session,"demo_mode","false")
    return kb([[("🕓 Demandes listing","mod:pending")],[("📂 Suggestions catégories","mod:suggestions")],[("➕ Ajouter catégorie","mod:add_cat")],[("🗑️ Supprimer catégorie","mod:delete_cat_menu")],[("⚠️ Warnings catégories","mod:warning_menu")],[("🎭 Mode démo : "+("ON" if demo=="true" else "OFF"),"mod:toggle_demo")],[("🏠 Menu","home")]])

@router.message(Command("moderation"))
async def moderation(message:Message):
    async with SessionLocal() as session:
        if not await admin_only(session,message.from_user): return
    await message.answer("🛠️ Modération", reply_markup=await mod_kb())

@router.callback_query(F.data=="mod:menu")
async def mod_menu(call:CallbackQuery):
    async with SessionLocal() as session:
        if not await admin_only(session,call.from_user): await call.answer("Accès refusé",show_alert=True); return
    await call.message.edit_text("🛠️ Modération", reply_markup=await mod_kb()); await call.answer()

@router.callback_query(F.data=="mod:toggle_demo")
async def toggle(call:CallbackQuery):
    async with SessionLocal() as session:
        if not await admin_only(session,call.from_user): await call.answer("Accès refusé",show_alert=True); return
        current=await get_setting(session,"demo_mode","false"); await set_setting(session,"demo_mode","false" if current=="true" else "true")
    await call.message.edit_text("🎭 Mode démo modifié.", reply_markup=await mod_kb()); await call.answer()

@router.callback_query(F.data=="mod:pending")
async def pending(call:CallbackQuery):
    async with SessionLocal() as session:
        projects=list((await session.scalars(select(Project).where(Project.status.in_(["pending_review","pending_bot"])))).all())
    text="🕓 Demandes listing\n\n"; rows=[]
    if not projects: text+="Aucune demande."
    for p in projects:
        text += f"#{p.id} — {p.title} — {p.status}\n"; rows.append([(f"📌 {p.title}",f"mod:project:{p.id}")])
    rows.append([("⬅️ Retour","mod:menu")]); await call.message.edit_text(text, reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("mod:project:"))
async def mod_project(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    async with SessionLocal() as session: p=await session.get(Project,pid)
    if not p: await call.answer("Introuvable",show_alert=True); return
    await call.message.edit_text(f"📌 #{p.id} {p.title}\n\n{p.description}\n\nLien : {p.invite_link}\nStatut : {p.status}", reply_markup=kb([[("✅ Approuver",f"mod:approve:{pid}")],[("❌ Refuser avec motif",f"mod:reject:{pid}")],[("⬅️ Retour","mod:pending")]])); await call.answer()

@router.callback_query(F.data.startswith("mod:approve:"))
async def approve(call:CallbackQuery):
    pid=int(call.data.split(":")[2])
    async with SessionLocal() as session:
        p=await session.get(Project,pid)
        if p:
            owner=await session.get(User,p.owner_user_id)
            await session.commit()
            if owner:
                try:
                    add_url=f"https://t.me/{settings.BOT_USERNAME}?startgroup=connect_{p.id}"
                    await call.bot.send_message(owner.telegram_id, f"✅ Votre groupe a été approuvé.\n\nDernière étape : ajoutez @{settings.BOT_USERNAME} comme administrateur dans votre groupe.\n\nLe bot sert à :\n• analyser les statistiques du groupe ;\n• suivre le nombre de membres ;\n• mesurer la croissance ;\n• vérifier que le lien reste actif ;\n• garder un accès de secours pour vos membres.\n\nCliquez ci-dessous pour ajouter automatiquement le bot au groupe.", reply_markup=kb([[("🤖 Ajouter le bot au groupe", add_url)]]))
                except Exception: pass
    await call.message.edit_text("✅ Projet approuvé. En attente d’ajout du bot au groupe.", reply_markup=kb([[("⬅️ Retour","mod:pending")]])); await call.answer()

@router.callback_query(F.data.startswith("mod:reject:"))
async def reject_start(call:CallbackQuery,state:FSMContext):
    await state.update_data(project_id=int(call.data.split(":")[2])); await state.set_state(AdminState.reject_project); await call.message.edit_text("Écris le motif du refus :", reply_markup=cancel_kb()); await call.answer()

@router.message(AdminState.reject_project)
async def reject_finish(message:Message,state:FSMContext):
    data=await state.get_data()
    async with SessionLocal() as session:
        p=await session.get(Project,data["project_id"])
        if p:
            p.status="rejected"; owner=await session.get(User,p.owner_user_id); await session.commit()
            if owner:
                try: await message.bot.send_message(owner.telegram_id, f"❌ Votre demande a été refusée.\n\nMotif :\n{message.text}")
                except Exception: pass
    await state.clear(); await message.answer("Refus envoyé.", reply_markup=kb([[("🛠️ Modération","mod:menu")]]))

@router.callback_query(F.data=="mod:add_cat")
async def add_cat_start(call:CallbackQuery,state:FSMContext):
    await state.set_state(AdminState.add_category); await call.message.edit_text("Nom de la catégorie :", reply_markup=cancel_kb()); await call.answer()

@router.message(AdminState.add_category)
async def add_cat_finish(message:Message,state:FSMContext):
    async with SessionLocal() as session: session.add(Category(name=message.text.strip())); await session.commit()
    await state.clear(); await message.answer("✅ Catégorie ajoutée.", reply_markup=kb([[("🛠️ Modération","mod:menu")]]))

@router.callback_query(F.data=="mod:delete_cat_menu")
async def del_cat_menu(call:CallbackQuery):
    async with SessionLocal() as session: cats=list((await session.scalars(select(Category).order_by(Category.name))).all())
    rows=[[(f"🗑️ {c.name}",f"mod:delete_cat:{c.id}")] for c in cats]+[[("⬅️ Retour","mod:menu")]]
    await call.message.edit_text("⚠️ Supprimer une catégorie supprimera les groupes liés.", reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("mod:delete_cat:"))
async def del_cat(call:CallbackQuery):
    cid=int(call.data.split(":")[2])
    async with SessionLocal() as session:
        cat=await session.get(Category,cid)
        if cat: await session.delete(cat); await session.commit()
    await call.message.edit_text("🗑️ Catégorie supprimée.", reply_markup=kb([[("🛠️ Modération","mod:menu")]])); await call.answer()

@router.callback_query(F.data=="mod:warning_menu")
async def warn_menu(call:CallbackQuery):
    async with SessionLocal() as session: cats=list((await session.scalars(select(Category).order_by(Category.name))).all())
    rows=[[(f"⚠️ {c.name} [{'ON' if c.warning_enabled else 'OFF'}]",f"mod:warning:{c.id}")] for c in cats]+[[("⬅️ Retour","mod:menu")]]
    await call.message.edit_text("⚠️ Warnings catégories :", reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("mod:warning:"))
async def warn_config(call:CallbackQuery):
    cid=int(call.data.split(":")[2])
    async with SessionLocal() as session: c=await session.get(Category,cid)
    await call.message.edit_text(f"⚠️ Catégorie : {c.name}\nActivé : {'Oui' if c.warning_enabled else 'Non'}\n\nMessage :\n{c.warning_text or 'Aucun'}", reply_markup=kb([[("✅ Activer",f"mod:warning_enable:{cid}")],[("❌ Désactiver",f"mod:warning_disable:{cid}")],[("✏️ Modifier texte",f"mod:warning_edit:{cid}")],[("⬅️ Retour","mod:warning_menu")]])); await call.answer()

@router.callback_query(F.data.startswith("mod:warning_enable:"))
async def warn_enable(call:CallbackQuery):
    cid=int(call.data.split(":")[2])
    async with SessionLocal() as session: c=await session.get(Category,cid); c.warning_enabled=True; await session.commit()
    await call.answer("Activé",show_alert=True)

@router.callback_query(F.data.startswith("mod:warning_disable:"))
async def warn_disable(call:CallbackQuery):
    cid=int(call.data.split(":")[2])
    async with SessionLocal() as session: c=await session.get(Category,cid); c.warning_enabled=False; await session.commit()
    await call.answer("Désactivé",show_alert=True)

@router.callback_query(F.data.startswith("mod:warning_edit:"))
async def warn_edit(call:CallbackQuery,state:FSMContext):
    await state.update_data(category_id=int(call.data.split(":")[2])); await state.set_state(AdminState.edit_warning); await call.message.edit_text("Envoie le texte warning :", reply_markup=cancel_kb()); await call.answer()

@router.message(AdminState.edit_warning)
async def warn_save(message:Message,state:FSMContext):
    data=await state.get_data()
    async with SessionLocal() as session: c=await session.get(Category,data["category_id"]); c.warning_text=message.text; c.warning_enabled=True; await session.commit()
    await state.clear(); await message.answer("✅ Warning enregistré.", reply_markup=kb([[("🛠️ Modération","mod:menu")]]))

@router.callback_query(F.data=="mod:suggestions")
async def suggestions(call:CallbackQuery):
    async with SessionLocal() as session: sug=list((await session.scalars(select(CategorySuggestion).where(CategorySuggestion.status=="pending"))).all())
    text="📂 Suggestions catégories\n\n"; rows=[]
    if not sug: text+="Aucune."
    for s in sug: text += f"#{s.id} — {s.name}\n"; rows.append([(f"📂 {s.name}",f"mod:sug_accept:{s.id}")])
    rows.append([("⬅️ Retour","mod:menu")]); await call.message.edit_text(text, reply_markup=kb(rows)); await call.answer()

@router.callback_query(F.data.startswith("mod:sug_accept:"))
async def sug_accept(call:CallbackQuery):
    sid=int(call.data.split(":")[2])
    async with SessionLocal() as session:
        s=await session.get(CategorySuggestion,sid)
        if s:
            exists=await session.scalar(select(Category).where(Category.name==s.name))
            if not exists: session.add(Category(name=s.name))
            s.status="accepted"; user=await session.get(User,s.user_id); await session.commit()
            if user:
                try: await call.bot.send_message(user.telegram_id, f"✅ Ta catégorie « {s.name} » a été acceptée.")
                except Exception: pass
    await call.message.edit_text("✅ Suggestion acceptée.", reply_markup=kb([[("⬅️ Retour","mod:suggestions")]])); await call.answer()
