from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.models import Project, User, NetworkBanLog
from app.services.notify_service import notify_admins

async def ban_user_from_all_connected_groups(bot, telegram_id: int, reason: str = "Banni du réseau"):
    async with SessionLocal() as session:
        projects = list((await session.scalars(select(Project).where(Project.status=="active", Project.group_id.is_not(None)))).all())

    banned_count = 0
    failed_count = 0
    for p in projects:
        try:
            await bot.ban_chat_member(p.group_id, telegram_id)
            banned_count += 1
        except Exception:
            failed_count += 1

    await notify_admins(bot, f"🚫 Ban réseau exécuté\n\nUtilisateur : {telegram_id}\nGroupes bannis : {banned_count}\nÉchecs : {failed_count}\nMotif : {reason}")

async def register_group_ban(bot, telegram_id: int, source_group_id: int | None=None, source_project_id: int | None=None, reason: str="ban_group"):
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.flush()
        session.add(NetworkBanLog(telegram_id=telegram_id, source_group_id=source_group_id, source_project_id=source_project_id, reason=reason))
        user.global_ban_count += 1
        should = user.global_ban_count >= 3 and not user.global_banned
        if should:
            user.global_banned = True
        await session.commit()

    if should:
        await ban_user_from_all_connected_groups(bot, telegram_id, "3 bans dans 3 groupes du réseau")
