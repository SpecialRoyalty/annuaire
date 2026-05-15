from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from app.db.session import SessionLocal
from app.models.models import CategorySuggestion
from app.services.user_service import get_or_create_user
from app.services.notify_service import notify_admins
from app.keyboards.common import kb, cancel_kb
router=Router()
class SuggestCat(StatesGroup): name=State()

@router.callback_query(F.data=="suggest_cat:start")
async def start(call:CallbackQuery,state:FSMContext):
    await state.set_state(SuggestCat.name); await call.message.edit_text("💡 Quelle catégorie veux-tu suggérer ?", reply_markup=cancel_kb()); await call.answer()

@router.message(SuggestCat.name)
async def save(message:Message,state:FSMContext):
    async with SessionLocal() as session:
        user=await get_or_create_user(session,message.from_user); s=CategorySuggestion(user_id=user.id,name=message.text.strip()); session.add(s); await session.commit(); await session.refresh(s)
    await notify_admins(message.bot, f"💡 Nouvelle suggestion catégorie\n\nPar : @{message.from_user.username or message.from_user.id}\nCatégorie : {s.name}", reply_markup=kb([[('✅ Valider',f'mod:sug_accept:{s.id}')],[('❌ Refuser',f'mod:sug_reject:{s.id}')],[('🛠️ Modération','mod:menu')]]))
    await state.clear(); await message.answer("✅ Suggestion envoyée à la modération.", reply_markup=kb([[('🏠 Menu','home')]]))
