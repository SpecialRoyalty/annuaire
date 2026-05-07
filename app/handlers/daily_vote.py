from sqlalchemy import select
from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import SessionLocal
from app.models.models import Project, DailyVote

router = Router()

@router.callback_query(F.data.startswith("daily_vote:"))
async def daily_vote(call: CallbackQuery):
    _, pid, value = call.data.split(":")
    pid, value = int(pid), int(value)
    async with SessionLocal() as session:
        p = await session.get(Project, pid)
        if not p:
            await call.answer("Groupe introuvable.", show_alert=True)
            return
        exists = await session.scalar(select(DailyVote).where(DailyVote.project_id == pid, DailyVote.telegram_id == call.from_user.id))
        if exists:
            await call.answer("Tu as déjà voté.", show_alert=True)
            return
        p.rating_sum += value
        p.rating_count += 1
        session.add(DailyVote(project_id=pid, telegram_id=call.from_user.id))
        await session.commit()
    await call.answer("Merci pour ton vote.", show_alert=True)
