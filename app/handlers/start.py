from sqlalchemy import select
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from app.db.session import SessionLocal
from app.config import settings
from app.models.models import Project
from app.services.user_service import get_or_create_user
from app.services.settings_service import increment_starts, get_total_starts, is_demo
from app.keyboards.common import main_menu

router = Router()

async def home_content(session, tg_user):
    user = await get_or_create_user(session, tg_user)
    total = await get_total_starts(session)
    demo_active = await is_demo(session)
    is_owner = bool(await session.scalar(select(Project.id).where(Project.owner_user_id == user.id).limit(1)))
    count_line = f"\n\n👥 {total:,} utilisateurs connectés".replace(",", " ") if total >= settings.START_STATS_MIN else ""
    demo_line = "\n\n🎭 Mode démo actif : explore les deux côtés du bot." if demo_active else ""
    text = f"🔗 Tous Les Liens\n\nRetrouve les liens des groupes Telegram préférés.{count_line}\n\nListing et service 100% gratuits.{demo_line}"
    return user, text, main_menu(is_owner=is_owner, is_moderator=user.is_super_admin, demo_active=demo_active)

async def deny_if_banned(event, user):
    if user.global_banned:
        msg = f"🚫 Vous êtes banni du réseau Tous Les Liens.\n\nContact support : @{settings.SUPPORT_USERNAME}"
        if isinstance(event, Message):
            await event.answer(msg)
        else:
            await event.message.edit_text(msg)
        return True
    return False

@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        if await deny_if_banned(message, user): return
        await increment_starts(session)
        user, text, markup = await home_content(session, message.from_user)
        await message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    async with SessionLocal() as session:
        user, text, markup = await home_content(session, call.from_user)
        if await deny_if_banned(call, user): return
        await call.message.edit_text(text, reply_markup=markup)
        await call.answer()

@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery):
    async with SessionLocal() as session:
        _, text, markup = await home_content(session, call.from_user)
    await call.message.edit_text("Action annulée.\n\n" + text, reply_markup=markup)
    await call.answer()
