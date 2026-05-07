from sqlalchemy import select, desc
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from app.db.session import SessionLocal
from app.models.models import Project, ForbiddenWord
from app.services.user_service import get_or_create_user
from app.keyboards.common import kb, cancel_kb

router = Router()

class OwnerEdit(StatesGroup):
    link = State()
    word_add = State()
    word_delete = State()

@router.callback_query(F.data == "owner:menu")
async def owner_menu(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        projects = list((await session.scalars(select(Project).where(Project.owner_user_id == user.id).order_by(desc(Project.id)))).all())
    if not projects:
        await call.message.edit_text("Tu n'as pas encore listé de groupe.", reply_markup=kb([[("➕ Lister mon groupe", "list:start")], [("🏠 Menu", "home")]]))
        await call.answer(); return
    rows = [[(f"📌 {p.title}", f"owner:project:{p.id}")] for p in projects]
    rows.append([("🏠 Menu", "home")])
    await call.message.edit_text("📊 Espace listeur\n\nChoisis un groupe :", reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("owner:project:"))
async def owner_project(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        p = await session.get(Project, pid)
        user = await get_or_create_user(session, call.from_user)
        if not p or p.owner_user_id != user.id:
            await call.answer("Accès refusé", show_alert=True); return
        avg = p.rating_sum / p.rating_count if p.rating_count else 0
        text = (
            f"📊 {p.title}\n\n"
            f"Statut : {p.status}\n"
            f"👁 Clics : {p.click_count}\n"
            f"🚀 Starts générés : {p.start_count}\n"
            f"⭐ Note : {avg:.1f}/5 — {p.rating_count} avis\n"
            f"👥 Membres : {p.member_count}\n"
            f"⚠️ Warnings bot : {p.bot_warning_count}/3\n"
            f"🛡 Modération : {'activée' if p.moderation_enabled else 'désactivée'}"
        )
        rows = [
            [("🔗 Modifier le lien", f"owner:edit_link:{p.id}")],
            [("🗑 Supprimer le projet", f"owner:delete:{p.id}")]
        ]
        if p.wants_moderation or p.moderation_enabled:
            rows.append([("🛡 Modération", f"owner:mod:{p.id}")])
        rows.append([("⬅️ Retour", "owner:menu"), ("🏠 Menu", "home")])
    await call.message.edit_text(text, reply_markup=kb(rows))
    await call.answer()

@router.callback_query(F.data.startswith("owner:edit_link:"))
async def owner_edit_link(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[2])
    await state.update_data(project_id=pid)
    await state.set_state(OwnerEdit.link)
    await call.message.edit_text("Envoie le nouveau lien Telegram :", reply_markup=cancel_kb())
    await call.answer()

@router.message(OwnerEdit.link)
async def owner_save_link(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        p = await session.get(Project, data["project_id"])
        if p and p.owner_user_id == user.id:
            p.invite_link = message.text.strip()
            p.is_link_active = True
            await session.commit()
    await state.clear()
    await message.answer("✅ Lien mis à jour.", reply_markup=kb([[("📊 Espace listeur", "owner:menu")], [("🏠 Menu", "home")]]))

@router.callback_query(F.data.startswith("owner:delete:"))
async def owner_delete(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = await session.get(Project, pid)
        if p and p.owner_user_id == user.id:
            p.status = "deleted"
            await session.commit()
    await call.message.edit_text("🗑 Projet supprimé.", reply_markup=kb([[("🏠 Menu", "home")]]))
    await call.answer()

@router.callback_query(F.data.startswith("owner:mod:"))
async def owner_mod(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    rows = [
        [("👀 Voir mots interdits", f"owner:words:{pid}")],
        [("➕ Ajouter un mot", f"owner:add_word:{pid}")],
        [("🗑 Supprimer un mot", f"owner:del_word:{pid}")],
        [("⬅️ Retour", f"owner:project:{pid}"), ("🏠 Menu", "home")]
    ]
    await call.message.edit_text(
        "🛡 Modération automatique\n\n"
        "Mots interdits : suppression + mute 1 jour, puis 7 jours si récidive.\n"
        "Liens externes : suppression + ban direct.",
        reply_markup=kb(rows)
    )
    await call.answer()

@router.callback_query(F.data.startswith("owner:words:"))
async def owner_words(call: CallbackQuery):
    pid = int(call.data.split(":")[2])
    async with SessionLocal() as session:
        words = list((await session.scalars(select(ForbiddenWord).where(ForbiddenWord.project_id == pid))).all())
    text = "🚫 Mots interdits :\n\n" + ("\n".join(f"• {w.word}" for w in words) if words else "Aucun mot interdit.")
    await call.message.edit_text(text, reply_markup=kb([[("⬅️ Retour", f"owner:mod:{pid}")], [("🏠 Menu", "home")]]))
    await call.answer()

@router.callback_query(F.data.startswith("owner:add_word:"))
async def owner_add_word(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[2])
    await state.update_data(project_id=pid)
    await state.set_state(OwnerEdit.word_add)
    await call.message.edit_text("Envoie le mot à interdire :", reply_markup=cancel_kb())
    await call.answer()

@router.message(OwnerEdit.word_add)
async def owner_add_word_save(message: Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        session.add(ForbiddenWord(project_id=data["project_id"], word=message.text.strip().lower()))
        await session.commit()
    await state.clear()
    await message.answer("✅ Mot ajouté.", reply_markup=kb([[("📊 Espace listeur", "owner:menu")], [("🏠 Menu", "home")]]))
