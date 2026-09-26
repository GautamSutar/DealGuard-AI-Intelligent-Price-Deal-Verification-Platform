import ssl
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Neon (and other hosted PG) requires SSL. asyncpg needs an ssl context
# rather than the sslmode= query param that psycopg2 uses.
# We detect Neon by checking for ".neon.tech" in the DATABASE_URL.
_db_url = settings.database_url

# Normalise URL scheme for asyncpg
if _db_url.startswith("postgresql://"):
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Strip params asyncpg does not accept; SSL is handled via connect_args
_is_neon = ".neon.tech" in _db_url
if _is_neon:
    # Remove sslmode, channel_binding from the URL — asyncpg ignores them
    # and raises an error on unknown params.
    import re
    _db_url = re.sub(r"[?&]sslmode=[^&]*", "", _db_url)
    _db_url = re.sub(r"[?&]channel_binding=[^&]*", "", _db_url)
    # Ensure query string starts with ? not &
    _db_url = re.sub(r"&", "?", _db_url, count=1)

_connect_args = {}
if _is_neon:
    _ssl_ctx = ssl.create_default_context()
    _connect_args = {"ssl": _ssl_ctx}

engine = create_async_engine(
    _db_url,
    echo=settings.is_development,
    pool_pre_ping=True,
    pool_size=5,       # Neon pooler already manages connections
    max_overflow=10,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
