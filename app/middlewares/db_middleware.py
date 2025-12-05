"""Middleware для работы с сессией БД."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.engine import async_session_maker


class DbSessionMiddleware(BaseMiddleware):
    """Middleware для создания сессии БД для каждого запроса."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            finally:
                await session.close()





