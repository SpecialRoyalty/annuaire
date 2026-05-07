from sqlalchemy import select
from app.config import settings
from app.models.models import User

async def get_or_create_user(session, tg_user):
    user = await session.scalar(select(User).where(User.telegram_id == tg_user.id))
    if not user:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            is_super_admin=tg_user.id in settings.SUPER_ADMIN_IDS,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.is_super_admin = tg_user.id in settings.SUPER_ADMIN_IDS
        await session.commit()
    return user
