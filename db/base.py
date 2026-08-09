"""SQLAlchemy base configuration for PostgreSQL async engine."""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DB_URL = os.getenv(
    "DB_URL",
    f"postgresql+asyncpg://{os.getenv('DB_USER', 'torob')}:{os.getenv('DB_PASSWORD', 'torob')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'torob_intel')}"
)

engine = create_async_engine(DB_URL, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
