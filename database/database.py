from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
from config import settings

Base = declarative_base()

# SQLite with aiosqlite uses StaticPool by default
# For other databases (PostgreSQL, MySQL), you might want connection pooling
if "sqlite" in settings.database_url:
    async_engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # For production databases, use connection pooling
    async_engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True
    )

async_session = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    """Initialize database and create all tables."""
    from .models import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
