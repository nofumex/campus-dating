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
    """Отправить анкету пользователю. Возвращает сообщение(я) или None."""
    caption = f"{caption_prefix}{user.name}, {user.age}, {user.university.short_name} 🎓\n\n{user.bio}{caption_suffix}"
    
    photos = [user.photo_1]
    if user.photo_2:
        photos.append(user.photo_2)
    if user.photo_3:
        photos.append(user.photo_3)
    
    if len(photos) == 1:
        msg = await bot.send_photo(
            chat_id=chat_id,
            photo=photos[0],
            caption=caption,
            reply_markup=keyboard
        )
        return msg
    else:
        # Для медиагруппы счетчик добавляем в caption последнего фото
        media = []
        for i, photo in enumerate(photos):
            if i == len(photos) - 1:
                # Последнее фото - с полным caption и счетчиком
                media.append(InputMediaPhoto(media=photo, caption=caption))
            else:
                # Остальные фото - без caption
                media.append(InputMediaPhoto(media=photo))
        
        messages = await bot.send_media_group(chat_id=chat_id, media=media)
        # Клавиатуру отправить отдельным сообщением (если нужна)
        if keyboard:
            # Отправляем кнопки отдельным сообщением
            msg = await bot.send_message(
                chat_id=chat_id,
                text=".",
                reply_markup=keyboard
            )
            # Удаляем сообщение с точкой через небольшую задержку
            import asyncio
            async def delete_temp_msg():
                await asyncio.sleep(0.2)
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                except:
                    pass
            asyncio.create_task(delete_temp_msg())
            return messages
        return messages

