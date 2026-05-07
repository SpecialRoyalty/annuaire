from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Category, Project
from app.services.user_service import get_or_create_user
from app.keyboards.common import kb, cancel_kb

router = Router()

class Listing(StatesGroup):
    title = State()
    description = State()
    category = State()
    link = State()
    moderation = State()

@router.callback_query(F.data == "list:start")
async def list_start(call: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if not user.can_list:
            await call.message.edit_text("Votre accès au listing a été suspendu. Contact support.", reply_markup=kb([[("Menu", "home")]]))
            await call.answer(); return
    await call.message.edit_text(
        "Lister mon groupe\n\n"
        "Tous Les Liens permet aux utilisateurs de retrouver les liens de leurs groupes Telegram préférés.\n\n"
        "Listing et service 100% gratuits.\n\n"
        "Conditions :\n"
        "• être owner/admin du groupe\n"
        "• ajouter le bot comme admin\n"
        "• garder le message épinglé\n"
        "• pas de scam ou contenu interdit",
        reply_markup=kb([[("Continuer", "list:continue")], [("Annuler", "cancel")]])
    )
    await call.answer()

@router.callback_query(F.data == "list:continue")
async def list_continue(call: CallbackQuery, state: FSMContext):
    await state.set_state(Listing.title)
    await call.message.edit_text("Nom du groupe ?", reply_markup=cancel_kb())
    await call.answer()

@router.message(Listing.title)
async def list_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(Listing.description)
    await message.answer("Description courte du groupe ?", reply_markup=cancel_kb())

@router.message(Listing.description)
async def list_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    async with SessionLocal() as session:
        cats = list((await session.scalars(select(Category).order_by(Category.position, Category.name))).all())
    rows = [[(c.name, f"list:cat:{c.id}")] for c in cats]
    rows.append([("Suggérer une catégorie", "suggest_cat:start")])
    rows.append([("Annuler", "cancel")])
    await state.set_state(Listing.category)
    await message.answer("Choisis une catégorie :", reply_markup=kb(rows))

@router.callback_query(Listing.category, F.data.startswith("list:cat:"))
async def list_category(call: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(call.data.split(":")[2]))
    await state.set_state(Listing.link)
    await call.message.edit_text("Envoie le lien Telegram du groupe :", reply_markup=cancel_kb())
    await call.answer()

@router.message(Listing.link)
async def list_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if "t.me/" not in link and "telegram.me/" not in link:
        await message.answer("Envoie un lien Telegram valide.")
        return
    await state.update_data(invite_link=link)
    await state.set_state(Listing.moderation)
    await message.answer(
        "Souhaites-tu activer gratuitement la modération automatique ?\n\n"
        "Mots interdits : suppression + mute.\n"
        "Liens externes : ban direct.",
        reply_markup=kb([[("Oui", "list:mod:yes")], [("Non", "list:mod:no")], [("Annuler", "cancel")]])
    )

@router.callback_query(Listing.moderation, F.data.startswith("list:mod:"))
async def list_finish(call: CallbackQuery, state: FSMContext):
    wants_mod = call.data.endswith(":yes")
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        p = Project(
            owner_user_id=user.id,
            category_id=data["category_id"],
            title=data["title"],
            description=data["description"],
            invite_link=data["invite_link"],
            wants_moderation=wants_mod,
            status="pending_bot"
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
    await state.clear()
    await call.message.edit_text(
        f"Demande créée.\n\nID projet : {p.id}\n\n"
        f"Ajoute @{call.bot.username} comme administrateur du groupe puis envoie dans le groupe :\n\n/connect {p.id}\n\n"
        "Ensuite la modération validera ou refusera le listing.",
        reply_markup=kb([[("Menu", "home")]])
    )
    await call.answer()
