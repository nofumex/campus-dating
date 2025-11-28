"""Обработчики просмотра анкет."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.repositories.like_repo import LikeRepository
from app.database.repositories.match_repo import MatchRepository
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.keyboards.inline import report_button_kb, continue_viewing_kb
from app.keyboards.reply import main_menu_kb, viewing_profile_kb
from app.utils.text_templates import TEXTS
from app.utils.helpers import send_profile
from app.states.states import ViewingStates

router = Router()


@router.message(F.text == "1")
async def start_viewing(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать просмотр анкет."""
    # Проверяем, что мы не в меню профиля (там "1" означает "Смотреть анкеты" из меню профиля)
    from app.states.states import ProfileMenuStates
    current_state = await state.get_state()
    if current_state == ProfileMenuStates.in_profile_menu:
        # Это обрабатывается в profile.py
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    await UserRepository.update_last_active(session, user.id)
    await session.commit()
    
    # Отправляем сообщение с remove keyboard ДО начала просмотра
    from aiogram.types import ReplyKeyboardRemove
    import asyncio
    remove_msg = await message.answer(
        "🔍",  # Эмодзи лупы
        reply_markup=ReplyKeyboardRemove()
    )
    # Удаляем сообщение асинхронно
    async def delete_remove_msg():
        await asyncio.sleep(0.2)
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=remove_msg.message_id
            )
        except:
            pass
    asyncio.create_task(delete_remove_msg())
    
    await state.set_state(ViewingStates.viewing_profiles)
    # Клавиатура будет установлена в show_next_profile
    await show_next_profile(message, session, state)


async def show_next_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать следующую анкету."""
    # UserRepository уже импортирован в начале файла
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    
    next_profile = await MatchingService.get_next_profile(session, user)
    
    if not next_profile:
        await state.clear()
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        # Отправляем сообщение об окончании анкет
        await message.answer(TEXTS["no_profiles"])
        # Отправляем меню отдельным сообщением с удалением предыдущих
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    # НЕ помечаем как просмотренную здесь - только после действия пользователя
    # Сохраняем ID текущей анкеты в состоянии
    await state.update_data(current_profile_id=next_profile.id)
    
    # Удаляем предыдущие сообщения, если они есть
    data = await state.get_data()
    prev_messages = data.get("prev_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    # Отправляем анкету БЕЗ inline кнопки жалобы, с reply клавиатурой
    # Определяем количество фото
    photos_count = sum([
        1 if next_profile.photo_1 else 0,
        1 if next_profile.photo_2 else 0,
        1 if next_profile.photo_3 else 0
    ])
    
    message_ids = []
    if photos_count == 1:
        # Одно фото - прикрепляем reply клавиатуру напрямую
        profile_msgs = await send_profile(
            message.bot,
            message.chat.id,
            next_profile,
            keyboard=viewing_profile_kb()  # Прикрепляем reply клавиатуру
        )
        if profile_msgs:
            message_ids.append(profile_msgs.message_id)
    else:
        # Медиагруппа - отправляем без клавиатуры, затем отдельное сообщение
        profile_msgs = await send_profile(
            message.bot,
            message.chat.id,
            next_profile,
            keyboard=None
        )
        if isinstance(profile_msgs, list):
            message_ids.extend([msg.message_id for msg in profile_msgs])
            # Отправляем reply клавиатуру отдельным сообщением
            # Используем минимальный текст, который будет удален при следующем показе
            action_msg = await message.answer(
                ".",  # Минимальный видимый текст (будет удален при следующем показе)
                reply_markup=viewing_profile_kb()
            )
            if action_msg:
                message_ids.append(action_msg.message_id)
    
    await state.update_data(prev_messages=message_ids)


@router.message(F.text == "❤️", ViewingStates.viewing_profiles)
async def handle_like_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка лайка через reply кнопку."""
    await handle_like_callback(message, session, state)


async def handle_like_callback(
    message_or_callback,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Внутренняя функция обработки лайка."""
    user = await UserRepository.get_by_telegram_id(session, message_or_callback.from_user.id)
    data = await state.get_data()
    current_profile_id = data.get("current_profile_id")
    
    if not current_profile_id:
        await message_or_callback.answer("❌ Ошибка")
        return
    
    # Удаляем предыдущие сообщения
    prev_messages = data.get("prev_messages", [])
    chat_id = message_or_callback.chat.id if hasattr(message_or_callback, 'chat') else message_or_callback.message.chat.id
    for msg_id in prev_messages:
        try:
            await message_or_callback.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass
    
    # Создаем лайк
    await LikeRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_profile_id,
        is_like=True
    )
    
    # Помечаем анкету как просмотренную только после действия
    await MatchingService.mark_as_viewed(session, user.id, current_profile_id)
    
    # Проверяем на взаимный лайк
    has_mutual = await LikeRepository.check_mutual_like(
        session,
        user.id,
        current_profile_id
    )
    
    if has_mutual:
        # Создаем мэтч
        match_exists = await MatchRepository.check_match_exists(
            session,
            user.id,
            current_profile_id
        )
        
        if not match_exists:
            await MatchRepository.create(session, user.id, current_profile_id)
            # Делаем commit сразу после создания мэтча
            await session.commit()
            
            to_user = await UserRepository.get_by_id(session, current_profile_id)
            to_user = await UserRepository.get_with_university(session, to_user.id)
            
            # Отправляем уведомления о мэтче
            await NotificationService.notify_match(
                message_or_callback.bot,
                session,
                user,
                to_user
            )
        else:
            await session.commit()
    else:
        # Делаем commit перед отправкой уведомлений
        await session.commit()
        
        # Отправляем уведомление получателю о новом лайке
        to_user = await UserRepository.get_by_id(session, current_profile_id)
        if to_user:
            await NotificationService.notify_like(
                message_or_callback.bot,
                session,
                to_user
            )
    
    # Показываем следующую анкету
    msg_obj = message_or_callback if hasattr(message_or_callback, 'chat') else message_or_callback.message
    await show_next_profile(msg_obj, session, state)


@router.callback_query(F.data == "like", ViewingStates.viewing_profiles)
async def handle_like(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка лайка через callback (для обратной совместимости)."""
    await callback.answer()
    await handle_like_callback(callback, session, state)


@router.message(F.text == "👎", ViewingStates.viewing_profiles)
async def handle_dislike_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка дизлайка через reply кнопку."""
    await handle_dislike_callback(message, session, state)


async def handle_dislike_callback(
    message_or_callback,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Внутренняя функция обработки дизлайка."""
    user = await UserRepository.get_by_telegram_id(session, message_or_callback.from_user.id)
    data = await state.get_data()
    current_profile_id = data.get("current_profile_id")
    
    if not current_profile_id:
        await message_or_callback.answer("❌ Ошибка")
        return
    
    # Удаляем предыдущие сообщения
    prev_messages = data.get("prev_messages", [])
    chat_id = message_or_callback.chat.id if hasattr(message_or_callback, 'chat') else message_or_callback.message.chat.id
    for msg_id in prev_messages:
        try:
            await message_or_callback.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass
    
    # Создаем дизлайк
    await LikeRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_profile_id,
        is_like=False
    )
    
    # Помечаем анкету как просмотренную только после действия
    await MatchingService.mark_as_viewed(session, user.id, current_profile_id)
    
    await session.commit()
    
    # Показываем следующую анкету
    msg_obj = message_or_callback if hasattr(message_or_callback, 'chat') else message_or_callback.message
    await show_next_profile(msg_obj, session, state)


@router.callback_query(F.data == "dislike", ViewingStates.viewing_profiles)
async def handle_dislike(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка дизлайка через callback (для обратной совместимости)."""
    await callback.answer()
    await handle_dislike_callback(callback, session, state)


@router.message(F.text == "💌", ViewingStates.viewing_profiles)
async def handle_like_with_message_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка лайка с сообщением через reply кнопку."""
    await state.set_state(ViewingStates.writing_message)
    from app.keyboards.reply import cancel_kb
    # Отправляем сообщение БЕЗ меню, только с кнопкой Отмена
    await message.answer(
        TEXTS["write_message_prompt"],
        reply_markup=cancel_kb()
    )


@router.callback_query(F.data == "like_with_message", ViewingStates.viewing_profiles)
async def handle_like_with_message(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка лайка с сообщением через callback (для обратной совместимости)."""
    await callback.answer()
    
    await state.set_state(ViewingStates.writing_message)
    from app.keyboards.reply import cancel_kb
    # Отправляем сообщение БЕЗ меню, только с кнопкой Отмена
    await callback.message.answer(
        TEXTS["write_message_prompt"],
        reply_markup=cancel_kb()
    )


@router.message(ViewingStates.writing_message)
async def process_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка сообщения при лайке."""
    from app.utils.helpers import validate_message
    # Используем глобальный импорт UserRepository из начала файла
    # Чтобы избежать UnboundLocalError, убеждаемся, что используем глобальный импорт
    # UserRepository уже импортирован в начале файла (строка 7)
    
    # Если пользователь нажал "Отмена", возвращаемся к той же анкете
    if message.text == "Отмена" or message.text == "Отмена ❌":
        await state.set_state(ViewingStates.viewing_profiles)
        # Получаем ID текущей анкеты из состояния
        data = await state.get_data()
        current_profile_id = data.get("current_profile_id")
        
        if current_profile_id:
            # Получаем пользователя и анкету
            # Используем глобальный импорт UserRepository из начала файла
            user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
            user = await UserRepository.get_with_university(session, user.id)
            current_profile = await UserRepository.get_by_id(session, current_profile_id)
            current_profile = await UserRepository.get_with_university(session, current_profile.id)
            
            # Показываем ту же анкету
            # Определяем количество фото
            photos_count = sum([
                1 if current_profile.photo_1 else 0,
                1 if current_profile.photo_2 else 0,
                1 if current_profile.photo_3 else 0
            ])
            
            message_ids = []
            if photos_count == 1:
                # Одно фото - прикрепляем reply клавиатуру напрямую
                profile_msgs = await send_profile(
                    message.bot,
                    message.chat.id,
                    current_profile,
                    keyboard=viewing_profile_kb()
                )
                if profile_msgs:
                    message_ids.append(profile_msgs.message_id)
            else:
                # Медиагруппа - отправляем без клавиатуры, затем отдельное сообщение
                profile_msgs = await send_profile(
                    message.bot,
                    message.chat.id,
                    current_profile,
                    keyboard=None
                )
                if isinstance(profile_msgs, list):
                    message_ids.extend([msg.message_id for msg in profile_msgs])
                    # Отправляем reply клавиатуру отдельным сообщением
                    action_msg = await message.answer(
                        ".",  # Минимальный видимый текст (будет удален при следующем показе)
                        reply_markup=viewing_profile_kb()
                    )
                    if action_msg:
                        message_ids.append(action_msg.message_id)
            
            await state.update_data(prev_messages=message_ids)
        else:
            # Если нет сохраненной анкеты, показываем следующую
            await show_next_profile(message, session, state)
        return
    
    if not validate_message(message.text):
        await message.answer(TEXTS["invalid_message"])
        return
    
    # Используем глобальный импорт UserRepository
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    data = await state.get_data()
    current_profile_id = data.get("current_profile_id")
    
    if not current_profile_id:
        await message.answer("❌ Ошибка")
        return
    
    # Создаем лайк с сообщением
    await LikeRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_profile_id,
        is_like=True,
        message=message.text
    )
    
    # Помечаем анкету как просмотренную только после действия
    await MatchingService.mark_as_viewed(session, user.id, current_profile_id)
    
    # Проверяем на взаимный лайк
    has_mutual = await LikeRepository.check_mutual_like(
        session,
        user.id,
        current_profile_id
    )
    
    if has_mutual:
        # Создаем мэтч
        match_exists = await MatchRepository.check_match_exists(
            session,
            user.id,
            current_profile_id
        )
        
        if not match_exists:
            await MatchRepository.create(session, user.id, current_profile_id)
            # Делаем commit сразу после создания мэтча
            await session.commit()
            
            to_user = await UserRepository.get_by_id(session, current_profile_id)
            to_user = await UserRepository.get_with_university(session, to_user.id)
            
            # Отправляем уведомления о мэтче
            await NotificationService.notify_match(
                message.bot,
                session,
                user,
                to_user
            )
        else:
            await session.commit()
    else:
        # Делаем commit перед отправкой уведомлений
        await session.commit()
        
        # Отправляем уведомление получателю о новом лайке
        to_user = await UserRepository.get_by_id(session, current_profile_id)
        if to_user:
            await NotificationService.notify_like(
                message.bot,
                session,
                to_user
            )
    
    # Удаляем предыдущие сообщения
    data = await state.get_data()
    prev_messages = data.get("prev_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    await state.set_state(ViewingStates.viewing_profiles)
    await show_next_profile(message, session, state)


@router.message(F.text == "🏠", ViewingStates.viewing_profiles)
async def handle_go_sleep_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться в меню через reply кнопку."""
    # Удаляем предыдущие сообщения
    data = await state.get_data()
    prev_messages = data.get("prev_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    await state.clear()
    
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await send_main_menu_with_cleanup(
        message.bot,
        message.chat.id,
        state,
        user.show_in_search
    )


@router.callback_query(F.data == "go_sleep")
async def handle_go_sleep(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться в меню через callback (для обратной совместимости)."""
    await callback.answer()
    await state.clear()
    
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    from app.database.repositories.user_repo import UserRepository
    user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
    await send_main_menu_with_cleanup(
        callback.message.bot,
        callback.message.chat.id,
        state,
        user.show_in_search
    )


@router.callback_query(F.data == "continue_viewing")
async def handle_continue_viewing(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Продолжить просмотр анкет."""
    await callback.answer()
    await state.set_state(ViewingStates.viewing_profiles)
    await callback.message.delete()
    await show_next_profile(callback.message, session, state)


@router.callback_query(F.data == "go_menu")
async def handle_go_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться в меню."""
    await callback.answer()
    await state.clear()
    
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    from app.database.repositories.user_repo import UserRepository
    user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
    await send_main_menu_with_cleanup(
        callback.message.bot,
        callback.message.chat.id,
        state,
        user.show_in_search
    )

