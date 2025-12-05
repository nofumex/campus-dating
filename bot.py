"""Точка входа для бота."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import Config
from app.middlewares.db_middleware import DbSessionMiddleware
from app.middlewares.ban_middleware import BanCheckMiddleware
from app.handlers import (
    start, registration, profile, viewing, likes, matches, messages, reports, admin
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция для запуска бота."""
    # Валидация конфигурации
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Используем MemoryStorage для FSM (можно заменить на Redis)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware (порядок важен!)
    # Сначала сессия БД, потом проверка бана
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.inline_query.middleware(DbSessionMiddleware())
    dp.chosen_inline_result.middleware(DbSessionMiddleware())
    # Проверка бана после создания сессии БД
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())
    
    # Регистрация роутеров (порядок важен - более специфичные обработчики должны быть раньше)
    dp.include_router(start.router)
    dp.include_router(profile.router)  # Переместили выше, чтобы обработчик выбора университета срабатывал
    dp.include_router(registration.router)
    dp.include_router(viewing.router)
    dp.include_router(likes.router)
    dp.include_router(matches.router)
    dp.include_router(messages.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)
    
    logger.info("Бот запущен")
    
    # Запуск polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")





