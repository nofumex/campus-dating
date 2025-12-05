"""Вспомогательные функции."""
import re
from typing import List, Optional
from aiogram.types import InputMediaPhoto, FSInputFile
from aiogram import Bot

from app.database.models import User


def validate_name(name: str) -> bool:
    """Валидация имени."""
    if not (2 <= len(name) <= 50):
        return False
    return bool(re.match(r'^[а-яА-ЯёЁa-zA-Z\s]+$', name))


def validate_age(age_str: str) -> Optional[int]:
    """Валидация возраста."""
    try:
        age = int(age_str)
        if 16 <= age <= 99:
            return age
    except ValueError:
        pass
    return None


def validate_bio(bio: str) -> bool:
    """Валидация описания."""
    return len(bio) <= 500


def validate_message(message: str) -> bool:
    """Валидация сообщения при лайке."""
    return len(message) <= 200


async def send_profile(
    bot: Bot,
    chat_id: int,
    user: User,
    keyboard=None,
    caption_prefix: str = "",
    caption_suffix: str = ""
):
    """
    Отправить анкету пользователю.

    ВАЖНО: теперь в анкетах используется только ОДНО фото (photo_1).
    Даже если в базе сохранены photo_2/photo_3, при показе анкеты они игнорируются.
    Это полностью убирает медиагруппы и все проблемы с точками/отдельными сообщениями.
    """
    caption = f"{caption_prefix}{user.name}, {user.age}, {user.university.short_name} 🎓\n\n{user.bio}{caption_suffix}"

    # Проверяем наличие и валидность фото
    if not user.photo_1:
        # Если фото нет, отправляем только текст
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=keyboard
        )
        return msg
    
    try:
        # Пытаемся отправить фото
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=user.photo_1,
            caption=caption,
            reply_markup=keyboard
        )
        return msg
    except Exception as e:
        # Если file_id невалиден, отправляем только текст
        # Логируем ошибку для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось отправить фото для пользователя {user.id}: {e}")
        
        msg = await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=keyboard
        )
        return msg

