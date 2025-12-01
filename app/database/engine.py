"""Настройка подключения к базе данных."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import Config

# Создание async engine
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False,  # Установить True для отладки SQL запросов
    future=True,
)

# Создание session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)



