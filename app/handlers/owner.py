from sqlalchemy import select, desc
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.db.session import SessionLocal
from app.models.models import Project, ForbiddenWord
from app.services.user_service import get_or_create_user
from app.services.settings_service import is_demo
from app.services.demo_data import DEMO_PROJECTS
from app.keyboards.common import kb, cancel_kb

router = Router()

class OwnerState(StatesGroup):
    edit_link = State()
    add_word = State()
    del_word = State()

@router.callback_query(F.data == "owner:menu")
async def owner_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        demo = await is_demo(session)
        projects = list((await session.scalars(select(Project).where(Project.owner_user_id == user.id).order_by(desc(Project.id)))).all())
    if demo and not projects:
        rows = [[(p["title"], f"owner:demo:{p['id']}")] for p in DEMO_PROJECTS[:3]]
        rows.append([("Menu", "home")])
        await call.message.edit_text("Interface listeur — Démo\n\nChoisis un groupe fictif :", reply_markup=kb(rows))
        await call.answer()
        return
    if not projects:
        await call.message.edit_text("Tu n’as pas encore listé de groupe.", reply_markup=kb([[("Lister mon groupe", "list:start")], [("Menu", "home")]]))
        await call.answer(); return
    rows = [[(p.title, f"owner:project:{p.id}")] for p in projects]
    rows.append([("Menu", "home")])
    await call.message.edit_text("Espace listeur :", reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("owner:demo:"))
async def owner_demo(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    p = next((x for x in DEMO_PROJECTS if x["id"] == pid), DEMO_PROJECTS[0])
    await call.message.edit_text(
        f"Interface listeur — Démo\n\n"
        f"{p['title']}\n\n"
        f"Vues : {p['clicks'] * 2}\n"
        f"Clics : {p['clicks']}\n"
        f"Starts générés : {p['clicks'] // 3}\n"
        f"Note : {p['rating']}/5 — {p['reviews']} avis\n"
        f"Membres : {p['members']}\n"
        f"Warnings bot : 0/3\n"
        f"Modération : activée",
        reply_markup=kb([
            [("Modifier lien démo", "owner:demo_action")],
            [("Modération démo", "owner:demo_action")],
            [("Retour", "owner:menu"), ("Menu", "home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "owner:demo_action")
async def owner_demo_action(call: CallbackQuery):
    await call.answer("Action simulée en mode démo.", show_alert=True)

@router.callback_query(F.data.startswith("owner:project:"))
async def owner_project(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = await session.get(Project, pid)
        if not p or p.owner_user_id != user.id:
            await call.answer("Accès refusé", show_alert=True); return
        avg = p.rating_sum / p.rating_count if p.rating_count else 0
        text = (
            f"{p.title}\n\n"
            f"Statut : {p.status}\n"
            f"Clics : {p.click_count}\n"
            f"Starts : {p.start_count}\n"
            f"Note : {avg:.1f}/5 — {p.rating_count} avis\n"
            f"Membres : {p.member_count}\n"
            f"Warnings bot : {p.bot_warning_count}/3\n"
            f"Modération : {'activée' if p.moderation_enabled else 'désactivée'}"
        )
    rows = [
        [("Modifier lien", f"owner:edit_link:{pid}")],
        [("Supprimer projet", f"owner:delete:{pid}")],
        [("Modération", f"owner:mod:{pid}")],
        [("Retour", "owner:menu"), ("Menu", "home")]
    ]
    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("owner:edit_link:"))
async def edit_link(call: CallbackQuery, state: FSMContext):
    await state.update_data(project_id=int(call.data.split(":")[2]))
    await state.set_state(OwnerState.edit_link)
    await call.message.edit_text("Envoie le nouveau lien :", reply_markup=cancel_kb())
    await call.answer()

@router.message(OwnerState.edit_link)
async def save_link(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        p = await session.get(Project, data["project_id"])
        if p and p.owner_user_id == user.id:
            p.invite_link = message.text.strip()
            p.is_link_active = True
            await session.commit()
    await state.clear()
    await message.answer("Lien mis à jour.", reply_markup=kb([[("Espace listeur", "owner:menu")], [("Menu", "home")]]))

@router.callback_query(F.data.startswith("owner:delete:"))
async def delete_project(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = await session.get(Project, pid)
        if p and p.owner_user_id == user.id:
            p.status = "deleted"
            await session.commit()
    await call.message.edit_text("Projet supprimé.", reply_markup=kb([[("Menu", "home")]]))
    await call.answer()

@router.callback_query(F.data.startswith("owner:mod:"))
async def owner_mod(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    await call.message.edit_text(
        "Modération automatique\n\n"
        "Mots interdits : suppression + mute.\n"
        "Liens externes : ban direct.",
        reply_markup=kb([
            [("Voir mots interdits", f"owner:words:{pid}")],
            [("Ajouter un mot", f"owner:add_word:{pid}")],
            [("Retour", f"owner:project:{pid}")]
        ])
    )
    await call.answer()

@router.callback_query(F.data.startswith("owner:words:"))
async def words(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        words = list((await session.scalars(select(ForbiddenWord).where(ForbiddenWord.project_id == pid))).all())
    text = "Mots interdits :\n\n" + ("\n".join(f"- {x.word}" for x in words) if words else "Aucun.")
    await call.message.edit_text(text, reply_markup=kb([[("Retour", f"owner:mod:{pid}")]]))
    await call.answer()

@router.callback_query(F.data.startswith("owner:add_word:"))
async def add_word(call: CallbackQuery, state: FSMContext):
    await state.update_data(project_id=int(call.data.split(":")[2]))
    await state.set_state(OwnerState.add_word)
    await call.message.edit_text("Mot à interdire :", reply_markup=cancel_kb())
    await call.answer()

@router.message(OwnerState.add_word)
async def save_word(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        session.add(ForbiddenWord(project_id=data["project_id"], word=message.text.strip().lower()))
        await session.commit()
    await state.clear()
    await message.answer("Mot ajouté.", reply_markup=kb([[("Espace listeur", "owner:menu")], [("Menu", "home")]]))
