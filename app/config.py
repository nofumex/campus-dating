"""Конфигурация приложения."""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс для хранения конфигурации бота."""
    
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/dating_bot"
    )
    
    @classmethod
    def validate(cls) -> None:
        """Проверка наличия обязательных переменных окружения."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен в .env файле")
        if not cls.ADMIN_ID:
            raise ValueError("ADMIN_ID не установлен в .env файле")



