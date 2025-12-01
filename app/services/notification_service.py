"""Сервис для отправки уведомлений."""
from typing import Optional
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User, Match
from app.database.repositories.match_repo import MatchRepository
from app.utils.helpers import send_profile
from app.keyboards.inline import match_kb
from app.utils.text_templates import TEXTS


class NotificationService:
    """Сервис для отправки уведомлений."""
    
    @staticmethod
    async def notify_match(
        bot: Bot,
        session: AsyncSession,
        user1: User,
        user2: User
    ) -> None:
        """Отправить уведомление о мэтче обоим пользователям."""
        from app.keyboards.inline import match_write_only_kb
        from app.keyboards.reply import main_menu_kb
        
        # Уведомление первому пользователю
        if user2.username:
            await bot.send_message(
                chat_id=user1.telegram_id,
                text=TEXTS["new_match"],
                reply_markup=match_write_only_kb(user2.username)
            )
        else:
            await bot.send_message(
                chat_id=user1.telegram_id,
                text=TEXTS["new_match"]
            )
        
        # Отправляем главное меню (без удаления, так как это уведомление)
        await bot.send_message(
            chat_id=user1.telegram_id,
            text=TEXTS["main_menu"],
            reply_markup=main_menu_kb(user1.show_in_search)
        )
        
        # Уведомление второму пользователю
        if user1.username:
            await bot.send_message(
                chat_id=user2.telegram_id,
                text=TEXTS["new_match"],
                reply_markup=match_write_only_kb(user1.username)
            )
        else:
            await bot.send_message(
                chat_id=user2.telegram_id,
                text=TEXTS["new_match"]
            )
        
        # Отправляем главное меню (без удаления, так как это уведомление)
        await bot.send_message(
            chat_id=user2.telegram_id,
            text=TEXTS["main_menu"],
            reply_markup=main_menu_kb(user2.show_in_search)
        )
    
    @staticmethod
    async def notify_like(
        bot: Bot,
        session: AsyncSession,
        user: User
    ) -> None:
        """Отправить уведомление о новом лайке с количеством."""
        from app.database.repositories.like_repo import LikeRepository
        from app.keyboards.reply import yes_no_kb
        
        # Не отправляем уведомления фейковым пользователям и тем, у кого нет валидного чата
        if getattr(user, "is_fake", False) or not user.telegram_id or user.telegram_id <= 0:
            return
        
        # Получаем количество входящих лайков
        incoming_likes = await LikeRepository.get_incoming_likes(session, user.id)
        likes_count = len(incoming_likes)
        
        if likes_count == 0:
            return
        
        # Формируем текст уведомления
        if likes_count == 1:
            text = "💌 У тебя 1 лайк!\nПоказать?"
        else:
            text = f"💌 У тебя {likes_count} лайк(ов)!\nПоказать?"
        
        # Отправляем новое уведомление
        await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=yes_no_kb()
        )
    
    @staticmethod
    async def notify_ban(
        bot: Bot,
        user: User
    ) -> None:
        """Отправить уведомление о бане."""
        await bot.send_message(
            chat_id=user.telegram_id,
            text=TEXTS["banned"]
        )

