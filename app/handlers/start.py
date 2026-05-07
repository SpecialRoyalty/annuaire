from sqlalchemy import select, func
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from app.db.session import SessionLocal
from app.config import settings
from app.models.models import Project, User
from app.services.user_service import get_or_create_user
from app.services.settings_service import increment_starts, get_total_starts, is_demo
from app.keyboards.common import main_menu

router = Router()

async def build_home(session, user):
    total = await get_total_starts(session)
    count_line = f"\n👥 {total:,} utilisateurs connectés\n".replace(",", " ") if total >= settings.START_STATS_MIN else "\n"
    is_owner = bool(await session.scalar(select(Project.id).where(Project.owner_user_id == user.id).limit(1)))
    demo = await is_demo(session)
    demo_line = "\n🎭 Mode démo actif\n" if demo else ""
    text = (
        "🔗 Tous Les Liens\n\n"
        "Retrouve les liens des groupes Telegram préférés."
        f"{count_line}"
        "Listing et service 100% gratuits."
        f"{demo_line}"
    )
    return text, main_menu(is_owner=is_owner, is_moderator=user.is_super_admin)

async def deny_if_banned(event, user):
    if user.global_banned:
        msg = f"🚫 Vous êtes banni du réseau Tous Les Liens.\n\nContact support : @{settings.SUPPORT_USERNAME}"
        if isinstance(event, Message):
            await event.answer(msg)
        else:
            await event.answer("Accès refusé", show_alert=True)
            await event.message.edit_text(msg)
        return True
    return False

@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        if await deny_if_banned(message, user):
            return
        await increment_starts(session)
        text, markup = await build_home(session, user)
        await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if await deny_if_banned(call, user):
            return
        text, markup = await build_home(session, user)
        await call.message.edit_text(text, reply_markup=markup)
        await call.answer()

@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        text, markup = await build_home(session, user)
        await call.message.edit_text("Action annulée.\n\n" + text, reply_markup=markup)
        await call.answer("Annulé")
