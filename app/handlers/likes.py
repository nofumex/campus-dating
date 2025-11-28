"""Обработчики входящих лайков."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.repositories.like_repo import LikeRepository
from app.database.repositories.match_repo import MatchRepository
from app.services.notification_service import NotificationService
from app.keyboards.reply import main_menu_kb, yes_no_kb, likes_action_kb
from app.keyboards.inline import match_write_only_kb
from app.utils.text_templates import TEXTS
from app.utils.helpers import send_profile
from app.states.states import LikesStates

router = Router()


@router.message(F.text == "3")
async def show_incoming_likes(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать входящие лайки."""
    # Проверяем, что пользователь не в других состояниях
    current_state = await state.get_state()
    from app.states.states import ProfileMenuStates, ViewingStates, MatchesStates
    if current_state in [ProfileMenuStates.in_profile_menu, ViewingStates.viewing_profiles, 
                         ViewingStates.writing_message, MatchesStates.viewing_matches]:
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    await UserRepository.update_last_active(session, user.id)
    await session.commit()
    
    # Получаем входящие лайки
    likes = await LikeRepository.get_incoming_likes(session, user.id)
    
    if not likes:
        # Отправляем сообщение об отсутствии лайков
        await message.answer(TEXTS["no_likes"])
        # Отправляем главное меню отдельным сообщением с удалением предыдущих
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    # Сохраняем ID пользователей, которые лайкнули
    liked_user_ids = [like.from_user_id for like in likes]
    await state.update_data(liked_user_ids=liked_user_ids, current_like_index=0)
    await state.set_state(LikesStates.confirming_view)
    
    # Показываем сообщение с подтверждением
    await message.answer(
        TEXTS["has_likes"].format(count=len(likes)),
        reply_markup=yes_no_kb()
    )


@router.message(F.text == "Да", LikesStates.confirming_view)
async def start_viewing_likes(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать просмотр лайков."""
    # Удаляем уведомление о лайках
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    except:
        pass
    
    await state.set_state(LikesStates.viewing_likes)
    await show_current_like(message, session, state)


@router.message(F.text == "Нет", LikesStates.confirming_view)
async def cancel_viewing_likes(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Отменить просмотр лайков."""
    # Удаляем уведомление о лайках
    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
    except:
        pass
    
    await state.clear()
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    await send_main_menu_with_cleanup(
        message.bot,
        message.chat.id,
        state,
        user.show_in_search
    )


async def show_current_like(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать текущий лайк."""
    data = await state.get_data()
    liked_user_ids = data.get("liked_user_ids", [])
    current_index = data.get("current_like_index", 0)
    
    # Удаляем предыдущие сообщения
    prev_messages = data.get("prev_like_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    if not liked_user_ids or current_index >= len(liked_user_ids):
        # Лайки закончились
        await state.clear()
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    # Получаем пользователя, который лайкнул
    from_user_id = liked_user_ids[current_index]
    from_user = await UserRepository.get_by_id(session, from_user_id)
    if not from_user:
        # Если пользователь не найден, удаляем его из списка и показываем следующего
        liked_user_ids.remove(from_user_id)
        await state.update_data(liked_user_ids=liked_user_ids)
        await show_current_like(message, session, state)
        return
    
    from_user = await UserRepository.get_with_university(session, from_user.id)
    
    # Сохраняем ID текущего пользователя
    await state.update_data(current_liked_user_id=from_user.id)
    
    # Показываем анкету
    profile_msgs = await send_profile(
        message.bot,
        message.chat.id,
        from_user,
        keyboard=likes_action_kb()
    )
    
    # Сохраняем ID сообщений для последующего удаления
    message_ids = []
    if isinstance(profile_msgs, list):
        message_ids.extend([msg.message_id for msg in profile_msgs])
    elif profile_msgs:
        message_ids.append(profile_msgs.message_id)
    await state.update_data(prev_like_messages=message_ids)


@router.message(F.text == "❤️", LikesStates.viewing_likes)
async def handle_like_back(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка ответного лайка."""
    data = await state.get_data()
    current_liked_user_id = data.get("current_liked_user_id")
    current_index = data.get("current_like_index", 0)
    
    if not current_liked_user_id:
        await message.answer("❌ Ошибка")
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    # Создаем ответный лайк
    await LikeRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_liked_user_id,
        is_like=True
    )
    
    # Проверяем, есть ли уже мэтч
    match_exists = await MatchRepository.check_match_exists(
        session,
        user.id,
        current_liked_user_id
    )
    
    if not match_exists:
        await MatchRepository.create(session, user.id, current_liked_user_id)
        # Делаем commit сразу после создания мэтча, чтобы он был доступен
        await session.commit()
        
        liked_user = await UserRepository.get_by_id(session, current_liked_user_id)
        liked_user = await UserRepository.get_with_university(session, liked_user.id)
        
        # Уведомление уже отправляется в NotificationService.notify_match
        await NotificationService.notify_match(
            message.bot,
            session,
            user,
            liked_user
        )
    else:
        await session.commit()
    
    # Удаляем обработанного пользователя из списка
    liked_user_ids = data.get("liked_user_ids", [])
    if current_liked_user_id in liked_user_ids:
        liked_user_ids.remove(current_liked_user_id)
        await state.update_data(liked_user_ids=liked_user_ids)
    
    # Удаляем предыдущие сообщения перед показом следующего
    prev_messages = data.get("prev_like_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    # Переходим к следующему лайку (индекс не увеличиваем, так как удалили элемент)
    await show_current_like(message, session, state)


@router.message(F.text == "👎", LikesStates.viewing_likes)
async def handle_dislike_back(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка дизлайка."""
    data = await state.get_data()
    current_liked_user_id = data.get("current_liked_user_id")
    current_index = data.get("current_like_index", 0)
    
    if not current_liked_user_id:
        await message.answer("❌ Ошибка")
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    # Создаем дизлайк
    await LikeRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_liked_user_id,
        is_like=False
    )
    
    await session.commit()
    
    # Удаляем обработанного пользователя из списка
    liked_user_ids = data.get("liked_user_ids", [])
    if current_liked_user_id in liked_user_ids:
        liked_user_ids.remove(current_liked_user_id)
        await state.update_data(liked_user_ids=liked_user_ids)
    
    # Удаляем предыдущие сообщения перед показом следующего
    prev_messages = data.get("prev_like_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    # Переходим к следующему лайку (индекс не увеличиваем, так как удалили элемент)
    await show_current_like(message, session, state)


@router.message(F.text == "🏠", LikesStates.viewing_likes)
async def handle_go_home_from_likes(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться в меню из просмотра лайков."""
    # Удаляем предыдущие сообщения
    data = await state.get_data()
    prev_messages = data.get("prev_like_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    await state.clear()
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    await send_main_menu_with_cleanup(
        message.bot,
        message.chat.id,
        state,
        user.show_in_search
    )
