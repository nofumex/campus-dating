"""Middleware для проверки бана пользователей."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.database.repositories.user_repo import UserRepository
from app.utils.text_templates import TEXTS


class BanCheckMiddleware(BaseMiddleware):
    """Middleware для проверки, не забанен ли пользователь."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        # Пропускаем админа
        if user_id and user_id == Config.ADMIN_ID:
            return await handler(event, data)
        
        # Проверяем бан только для зарегистрированных пользователей
        if user_id:
            session: AsyncSession = data.get("session")
            if session:
                user = await UserRepository.get_by_telegram_id(session, user_id)
                if user and user.is_banned:
                    # Пользователь забанен - отправляем сообщение и не обрабатываем запрос
                    if isinstance(event, Message):
                        await event.answer(TEXTS.get("banned", "⚠️ Твоя анкета была заблокирована за нарушение правил."))
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⚠️ Твоя анкета была заблокирована", show_alert=True)
                    return  # Не обрабатываем запрос
        
        return await handler(event, data)
