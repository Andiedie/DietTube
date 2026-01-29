from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pathlib import Path
import os


class Base(DeclarativeBase):
    pass


def get_db_path() -> Path:
    config_dir = Path(os.environ.get("DIETTUBE_CONFIG_DIR", "/config"))
    return config_dir / "diettube.db"


engine = create_async_engine(
    f"sqlite+aiosqlite:///{get_db_path()}",
    echo=False,
)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_maker() as session:
        yield session
