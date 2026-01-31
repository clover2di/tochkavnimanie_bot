from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from .models import (
    User, Application, Nomination, Admin, BotContent, Settings,
    ApplicationStatus, AdminRole, Broadcast, BroadcastStatus
)


# ==================== USER CRUD ====================

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: int, **kwargs) -> Optional[User]:
    await db.execute(
        update(User).where(User.id == user_id).values(**kwargs)
    )
    await db.commit()
    return await get_user_by_id(db, user_id)


async def get_or_create_user(db: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
    """Get existing user or create new one."""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        user = await create_user(db, telegram_id, username)
    return user


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    return result.scalars().all()


async def get_users_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(User.id)))
    return result.scalar()


async def get_unique_cities(db: AsyncSession) -> List[str]:
    """Get unique cities from users who have applications."""
    result = await db.execute(
        select(User.city)
        .distinct()
        .where(User.id.in_(select(Application.user_id).distinct()))
        .where(User.city.isnot(None))
        .where(User.city != "")
        .order_by(User.city)
    )
    return [row[0] for row in result.all()]


async def get_participants_with_stats(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 50,
    search: Optional[str] = None
) -> List[dict]:
    """Get participants with their application count and last application date in one query."""
    # Build subquery for application stats
    query = (
        select(
            User,
            func.count(Application.id).label('app_count'),
            func.max(Application.created_at).label('last_app_date')
        )
        .join(Application, User.id == Application.user_id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_filter)) |
            (User.full_name.ilike(search_filter)) |
            (User.city.ilike(search_filter)) |
            (User.school.ilike(search_filter))
        )
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    
    participants = []
    for row in result.all():
        participants.append({
            'user': row[0],
            'application_count': row[1],
            'last_application_date': row[2]
        })
    
    return participants


async def get_participants_count(db: AsyncSession, search: Optional[str] = None) -> int:
    """Get count of participants (users with at least one application)."""
    query = (
        select(func.count(func.distinct(Application.user_id)))
    )
    
    if search:
        search_filter = f"%{search}%"
        query = query.join(User, Application.user_id == User.id).where(
            (User.username.ilike(search_filter)) |
            (User.full_name.ilike(search_filter)) |
            (User.city.ilike(search_filter)) |
            (User.school.ilike(search_filter))
        )
    
    result = await db.scalar(query)
    return result or 0


# ==================== NOMINATION CRUD ====================

async def get_nomination_by_id(db: AsyncSession, nomination_id: int) -> Optional[Nomination]:
    result = await db.execute(
        select(Nomination).where(Nomination.id == nomination_id)
    )
    return result.scalar_one_or_none()


async def get_active_nominations(db: AsyncSession) -> List[Nomination]:
    """Get active nominations that are within their time period."""
    result = await db.execute(
        select(Nomination)
        .where(Nomination.is_active == True)
        .order_by(Nomination.id)
    )
    return result.scalars().all()


async def get_available_nominations(db: AsyncSession) -> List[Nomination]:
    """Get nominations available for submission (active + within time period)."""
    now = datetime.now()
    result = await db.execute(
        select(Nomination)
        .where(Nomination.is_active == True)
        .order_by(Nomination.id)
    )
    nominations = result.scalars().all()
    
    # Filter by time period
    available = []
    for nom in nominations:
        # Check start_date
        if nom.start_date and now < nom.start_date:
            continue
        # Check deadline
        if nom.deadline and now > nom.deadline:
            continue
        available.append(nom)
    
    return available


async def get_all_nominations(db: AsyncSession) -> List[Nomination]:
    result = await db.execute(
        select(Nomination).order_by(Nomination.id)
    )
    return result.scalars().all()


async def create_nomination(
    db: AsyncSession, 
    name: str,
    description: Optional[str] = None,
    start_date: Optional[datetime] = None,
    deadline: Optional[datetime] = None
) -> Nomination:
    nomination = Nomination(
        name=name, 
        description=description, 
        start_date=start_date,
        deadline=deadline
    )
    db.add(nomination)
    await db.commit()
    await db.refresh(nomination)
    return nomination


async def update_nomination(db: AsyncSession, nomination_id: int, **kwargs) -> Optional[Nomination]:
    await db.execute(
        update(Nomination).where(Nomination.id == nomination_id).values(**kwargs)
    )
    await db.commit()
    return await get_nomination_by_id(db, nomination_id)


async def delete_nomination(db: AsyncSession, nomination_id: int) -> bool:
    await db.execute(
        delete(Nomination).where(Nomination.id == nomination_id)
    )
    await db.commit()
    return True


# ==================== APPLICATION CRUD ====================

async def get_application_by_id(db: AsyncSession, application_id: int) -> Optional[Application]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.user), selectinload(Application.nomination))
        .where(Application.id == application_id)
    )
    return result.scalar_one_or_none()


async def get_user_applications(db: AsyncSession, user_id: int) -> List[Application]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.user), selectinload(Application.nomination))
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    return result.scalars().all()


async def get_all_applications(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    nomination_id: Optional[int] = None,
    search: Optional[str] = None,
    city: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> List[Application]:
    query = select(Application).options(
        selectinload(Application.user), 
        selectinload(Application.nomination)
    )
    
    if nomination_id:
        query = query.where(Application.nomination_id == nomination_id)
    
    # Search filter (by user's full_name, username, school)
    if search:
        search_filter = f"%{search}%"
        query = query.join(Application.user).where(
            (User.full_name.ilike(search_filter)) |
            (User.username.ilike(search_filter)) |
            (User.school.ilike(search_filter))
        )
    
    # City filter
    if city:
        if not search:  # If search didn't join user already
            query = query.join(Application.user)
        query = query.where(User.city.ilike(f"%{city}%"))
    
    # Date range filter
    if date_from:
        query = query.where(Application.created_at >= date_from)
    if date_to:
        query = query.where(Application.created_at <= date_to)
    
    query = query.offset(skip).limit(limit).order_by(Application.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_applications_count(
    db: AsyncSession,
    nomination_id: Optional[int] = None,
    search: Optional[str] = None,
    city: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> int:
    """Get total count of applications with filters."""
    query = select(func.count(Application.id))
    
    if nomination_id:
        query = query.where(Application.nomination_id == nomination_id)
    
    if search:
        search_filter = f"%{search}%"
        query = query.join(Application.user).where(
            (User.full_name.ilike(search_filter)) |
            (User.username.ilike(search_filter)) |
            (User.school.ilike(search_filter))
        )
    
    if city:
        if not search:
            query = query.join(Application.user)
        query = query.where(User.city.ilike(f"%{city}%"))
    
    if date_from:
        query = query.where(Application.created_at >= date_from)
    if date_to:
        query = query.where(Application.created_at <= date_to)
    
    result = await db.scalar(query)
    return result or 0


async def create_application(
    db: AsyncSession,
    user_id: int,
    nomination_id: int,
    photos: Optional[str] = None,
    photos_remote_paths: Optional[str] = None,
    comment_text: Optional[str] = None,
    voice_file_id: Optional[str] = None,
    voice_remote_path: Optional[str] = None
) -> Application:
    application = Application(
        user_id=user_id,
        nomination_id=nomination_id,
        photos=photos,
        photos_remote_paths=photos_remote_paths,
        comment_text=comment_text,
        voice_file_id=voice_file_id,
        voice_remote_path=voice_remote_path
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


async def update_application(db: AsyncSession, application_id: int, **kwargs) -> Optional[Application]:
    await db.execute(
        update(Application).where(Application.id == application_id).values(**kwargs)
    )
    await db.commit()
    return await get_application_by_id(db, application_id)


async def delete_application(db: AsyncSession, application_id: int) -> bool:
    """Delete an application by ID."""
    result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application:
        await db.delete(application)
        await db.commit()
        return True
    return False


async def get_applications_count_by_nomination(db: AsyncSession) -> List[tuple]:
    """Returns list of (nomination_id, nomination_name, count)."""
    result = await db.execute(
        select(
            Nomination.id,
            Nomination.name,
            func.count(Application.id)
        )
        .outerjoin(Application)
        .group_by(Nomination.id)
        .order_by(Nomination.order)
    )
    return result.all()


# ==================== BOT CONTENT CRUD ====================

async def get_bot_content(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.execute(
        select(BotContent.value).where(BotContent.key == key)
    )
    value = result.scalar_one_or_none()
    return value


async def set_bot_content(db: AsyncSession, key: str, value: str, description: Optional[str] = None) -> BotContent:
    existing = await db.execute(
        select(BotContent).where(BotContent.key == key)
    )
    content = existing.scalar_one_or_none()
    
    if content:
        content.value = value
        if description:
            content.description = description
    else:
        content = BotContent(key=key, value=value, description=description)
        db.add(content)
    
    await db.commit()
    await db.refresh(content)
    return content


async def get_all_bot_content(db: AsyncSession) -> List[BotContent]:
    result = await db.execute(select(BotContent).order_by(BotContent.key))
    return result.scalars().all()


async def delete_bot_content(db: AsyncSession, key: str) -> bool:
    """Delete bot content by key (reset to default)."""
    await db.execute(
        delete(BotContent).where(BotContent.key == key)
    )
    await db.commit()
    return True


# ==================== SETTINGS CRUD ====================

async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(
        select(Settings.value).where(Settings.key == key)
    )
    value = result.scalar_one_or_none()
    return value if value is not None else default


async def set_setting(
    db: AsyncSession, 
    key: str, 
    value: str, 
    value_type: str = "string",
    description: Optional[str] = None
) -> Settings:
    existing = await db.execute(
        select(Settings).where(Settings.key == key)
    )
    setting = existing.scalar_one_or_none()
    
    if setting:
        setting.value = value
        setting.value_type = value_type
        if description:
            setting.description = description
    else:
        setting = Settings(key=key, value=value, value_type=value_type, description=description)
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    return setting


async def get_all_settings(db: AsyncSession) -> List[Settings]:
    result = await db.execute(select(Settings).order_by(Settings.key))
    return result.scalars().all()


# ==================== ADMIN CRUD ====================

async def get_admin_by_username(db: AsyncSession, username: str) -> Optional[Admin]:
    result = await db.execute(
        select(Admin).where(Admin.username == username)
    )
    return result.scalar_one_or_none()


async def create_admin(
    db: AsyncSession,
    username: str,
    password_hash: str,
    role: AdminRole = AdminRole.MODERATOR,
    telegram_id: Optional[int] = None
) -> Admin:
    admin = Admin(
        username=username,
        password_hash=password_hash,
        role=role,
        telegram_id=telegram_id
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    return admin


# ==================== BROADCAST CRUD ====================

async def create_broadcast(
    db: AsyncSession,
    text: str,
    image_path: Optional[str] = None
) -> Broadcast:
    """Create a new broadcast message."""
    broadcast = Broadcast(
        text=text,
        image_path=image_path,
        status=BroadcastStatus.DRAFT
    )
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)
    return broadcast


async def get_broadcast_by_id(db: AsyncSession, broadcast_id: int) -> Optional[Broadcast]:
    result = await db.execute(
        select(Broadcast).where(Broadcast.id == broadcast_id)
    )
    return result.scalar_one_or_none()


async def get_all_broadcasts(db: AsyncSession, limit: int = 50) -> List[Broadcast]:
    result = await db.execute(
        select(Broadcast).order_by(Broadcast.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def update_broadcast(db: AsyncSession, broadcast_id: int, **kwargs) -> Optional[Broadcast]:
    await db.execute(
        update(Broadcast).where(Broadcast.id == broadcast_id).values(**kwargs)
    )
    await db.commit()
    return await get_broadcast_by_id(db, broadcast_id)


async def delete_broadcast(db: AsyncSession, broadcast_id: int) -> bool:
    await db.execute(
        delete(Broadcast).where(Broadcast.id == broadcast_id)
    )
    await db.commit()
    return True


async def get_all_user_telegram_ids(db: AsyncSession) -> List[int]:
    """Get all user telegram IDs for broadcast."""
    result = await db.execute(
        select(User.telegram_id).where(User.is_blocked == False)
    )
    return [row[0] for row in result.fetchall()]
