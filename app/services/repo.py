from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Category, Project, Rating, Click, Report, ProjectStatus, UserRole, Ban


async def get_or_create_user(session: AsyncSession, tg_user, super_admin_ids: set[int]) -> User:
    result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
    user = result.scalar_one_or_none()
    role = UserRole.SUPER_ADMIN.value if tg_user.id in super_admin_ids else UserRole.USER.value
    if user:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        if tg_user.id in super_admin_ids:
            user.role = role
        await session.commit()
        return user
    user = User(telegram_id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def list_categories(session: AsyncSession):
    return (await session.execute(select(Category).order_by(Category.position))).scalars().all()


async def get_category(session: AsyncSession, category_id: int):
    return await session.get(Category, category_id)


async def create_project(session: AsyncSession, owner: User, title: str, description: str, category_id: int, invite_link: str) -> Project:
    owner.role = UserRole.ADMIN.value if owner.role == UserRole.USER.value else owner.role
    project = Project(owner_user_id=owner.id, title=title, description=description, category_id=category_id, invite_link=invite_link, status=ProjectStatus.NEEDS_BOT.value)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def get_project(session: AsyncSession, project_id: int):
    return await session.get(Project, project_id)


async def active_projects_by_category(session: AsyncSession, category_id: int, page: int, per_page: int = 5):
    offset = (page - 1) * per_page
    stmt = select(Project).where(Project.category_id == category_id, Project.status == ProjectStatus.ACTIVE.value).order_by(Project.rating_avg.desc(), Project.click_count.desc(), Project.created_at.desc()).offset(offset).limit(per_page + 1)
    items = (await session.execute(stmt)).scalars().all()
    return items[:per_page], len(items) > per_page


async def top_projects(session: AsyncSession, page: int, per_page: int = 5):
    offset = (page - 1) * per_page
    stmt = select(Project).where(Project.status == ProjectStatus.ACTIVE.value).order_by(Project.rating_avg.desc(), Project.start_count.desc(), Project.click_count.desc()).offset(offset).limit(per_page + 1)
    items = (await session.execute(stmt)).scalars().all()
    return items[:per_page], len(items) > per_page


async def owner_projects(session: AsyncSession, user: User):
    return (await session.execute(select(Project).where(Project.owner_user_id == user.id).order_by(Project.created_at.desc()))).scalars().all()


async def add_click(session: AsyncSession, project: Project, user: User | None, source: str = "bot"):
    project.click_count += 1
    session.add(Click(project_id=project.id, user_id=user.id if user else None, source=source))
    await session.commit()


async def add_start(session: AsyncSession, project_id: int):
    project = await session.get(Project, project_id)
    if project:
        project.start_count += 1
        await session.commit()


async def set_rating(session: AsyncSession, user: User, project: Project, value: int) -> bool:
    if project.owner_user_id == user.id:
        return False
    existing = (await session.execute(select(Rating).where(Rating.user_id == user.id, Rating.project_id == project.id))).scalar_one_or_none()
    if existing:
        existing.rating = value
    else:
        session.add(Rating(user_id=user.id, project_id=project.id, rating=value))
    await session.flush()
    avg, count = (await session.execute(select(func.avg(Rating.rating), func.count(Rating.id)).where(Rating.project_id == project.id))).one()
    project.rating_avg = float(avg or 0)
    project.rating_count = int(count or 0)
    await session.commit()
    return True


async def report_project(session: AsyncSession, user: User, project: Project, reason: str = "Lien mort"):
    session.add(Report(user_id=user.id, project_id=project.id, reason=reason))
    await session.commit()


async def pending_projects(session: AsyncSession):
    return (await session.execute(select(Project).where(Project.status.in_([ProjectStatus.PENDING.value, ProjectStatus.NEEDS_BOT.value])).order_by(Project.created_at.asc()))).scalars().all()


async def approve_project(session: AsyncSession, project: Project):
    project.status = ProjectStatus.ACTIVE.value
    project.is_link_active = True
    project.inactive_since = None
    await session.commit()


async def reject_project(session: AsyncSession, project: Project):
    project.status = ProjectStatus.DELETED.value
    await session.commit()


async def ban_project(session: AsyncSession, project: Project, reason: str):
    project.status = ProjectStatus.BANNED.value
    session.add(Ban(project_id=project.id, user_id=project.owner_user_id, reason=reason))
    await session.commit()


async def set_project_group(session: AsyncSession, group_chat_id: int, group_title: str | None, bot_username: str):
    # Lie automatiquement le dernier projet non configuré dont le lien contient le username du groupe si possible.
    project = (await session.execute(select(Project).where(Project.status == ProjectStatus.NEEDS_BOT.value).order_by(Project.created_at.desc()).limit(1))).scalar_one_or_none()
    if project:
        project.group_chat_id = group_chat_id
        project.status = ProjectStatus.PENDING.value
        await session.commit()
    return project


async def stale_needs_bot(session: AsyncSession):
    limit = datetime.now(timezone.utc) - timedelta(hours=1)
    return (await session.execute(select(Project).where(Project.status == ProjectStatus.NEEDS_BOT.value, Project.created_at <= limit))).scalars().all()


async def inactive_too_long(session: AsyncSession):
    limit = datetime.now(timezone.utc) - timedelta(days=10)
    return (await session.execute(select(Project).where(Project.status == ProjectStatus.ACTIVE.value, Project.is_link_active == False, Project.inactive_since <= limit))).scalars().all()
