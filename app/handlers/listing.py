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
            await call.message.edit_text(
                "🚫 Votre accès au listing a été suspendu.\n\nMotif : retrait répété du bot administrateur.\n\nContact support.",
                reply_markup=kb([[("🏠 Menu", "home")]])
            )
            await call.answer(); return
    text = (
        "➕ Lister mon groupe\n\n"
        "Tous Les Liens permet aux utilisateurs de retrouver les liens de leurs groupes Telegram préférés.\n\n"
        "Le listing et le service sont 100% gratuits.\n\n"
        "Conditions :\n"
        "• Être propriétaire ou administrateur du groupe\n"
        "• Ajouter le bot comme administrateur\n"
        "• Garder le message de secours épinglé\n"
        "• Pas de scam, spam ou contenu interdit\n\n"
        "Le non-respect peut entraîner le retrait du listing."
    )
    await call.message.edit_text(text, reply_markup=kb([[("✅ Continuer", "list:continue")], [("❌ Annuler", "cancel")]]))
    await call.answer()

@router.callback_query(F.data == "list:continue")
async def list_continue(call: CallbackQuery, state: FSMContext):
    await state.set_state(Listing.title)
    await call.message.edit_text("Quel est le nom du groupe ?", reply_markup=cancel_kb())
    await call.answer()

@router.message(Listing.title)
async def list_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(Listing.description)
    await message.answer("Ajoute une courte description attractive du groupe.", reply_markup=cancel_kb())

@router.message(Listing.description)
async def list_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    async with SessionLocal() as session:
        cats = list((await session.scalars(select(Category).order_by(Category.position, Category.name))).all())
    rows = [[(c.name, f"list:cat:{c.id}")] for c in cats]
    rows.append([("💡 Suggérer une catégorie", "suggest_cat:start")])
    rows.append([("❌ Annuler", "cancel")])
    await state.set_state(Listing.category)
    await message.answer("Choisis la catégorie du groupe :", reply_markup=kb(rows))

@router.callback_query(Listing.category, F.data.startswith("list:cat:"))
async def list_category(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split(":")[2])
    await state.update_data(category_id=cat_id)
    await state.set_state(Listing.link)
    await call.message.edit_text("Envoie maintenant le lien Telegram du groupe.", reply_markup=cancel_kb())
    await call.answer()

@router.message(Listing.link)
async def list_link(message: Message, state: FSMContext):
    link = message.text.strip()
    if "t.me/" not in link and "telegram.me/" not in link:
        await message.answer("Le lien doit être un lien Telegram valide, exemple : https://t.me/mon_groupe")
        return
    await state.update_data(invite_link=link)
    await state.set_state(Listing.moderation)
    await message.answer(
        "🛡 Souhaites-tu activer gratuitement la modération automatique ?\n\n"
        "Fonctions :\n"
        "• Suppression des mots interdits\n"
        "• Mute automatique : 1 jour, puis 7 jours si récidive\n"
        "• Anti-liens : ban direct\n\n"
        "100% gratuit.",
        reply_markup=kb([[("✅ Oui, activer", "list:mod:yes")], [("❌ Non merci", "list:mod:no")], [("❌ Annuler", "cancel")]])
    )

@router.callback_query(Listing.moderation, F.data.startswith("list:mod:"))
async def list_finish(call: CallbackQuery, state: FSMContext):
    wants_mod = call.data.endswith(":yes")
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        project = Project(
            owner_user_id=user.id,
            category_id=data["category_id"],
            title=data["title"],
            description=data["description"],
            invite_link=data["invite_link"],
            wants_moderation=wants_mod,
            status="pending_bot"
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
    await state.clear()
    await call.message.edit_text(
        f"✅ Demande créée.\n\n"
        f"ID projet : {project.id}\n\n"
        f"Étape suivante : ajoute @{call.bot.username} comme administrateur du groupe, puis envoie cette commande dans le groupe :\n\n"
        f"/connect {project.id}\n\n"
        "Permissions nécessaires : messages, suppression, bannissement et épinglage.\n\n"
        "Tu as 1 heure pour le faire avant le premier avertissement.",
        reply_markup=kb([[("🏠 Menu", "home")]])
    )
    await call.answer()
