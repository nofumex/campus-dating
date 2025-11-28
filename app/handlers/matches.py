"""Обработчики взаимных симпатий."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.repositories.match_repo import MatchRepository
from app.keyboards.inline import match_kb
from app.keyboards.reply import main_menu_kb
from app.utils.text_templates import TEXTS
from app.utils.helpers import send_profile
from app.states.states import MatchesStates

router = Router()


@router.message(F.text == "4")
async def show_matches(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать взаимные симпатии."""
    # Проверяем, что пользователь не в других состояниях
    current_state = await state.get_state()
    from app.states.states import ProfileMenuStates, ViewingStates, LikesStates
    if current_state in [ProfileMenuStates.in_profile_menu, ViewingStates.viewing_profiles, 
                         ViewingStates.writing_message, LikesStates.confirming_view, 
                         LikesStates.viewing_likes]:
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    await UserRepository.update_last_active(session, user.id)
    await session.commit()
    
    # Удаляем предыдущие сообщения из других состояний
    data = await state.get_data()
    prev_messages = data.get("prev_messages", []) + data.get("prev_match_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    matches = await MatchRepository.get_user_matches(session, user.id)
    
    if not matches:
        # Отправляем сообщение об отсутствии мэтчей
        await message.answer(TEXTS["no_matches"])
        # Отправляем главное меню отдельным сообщением с удалением предыдущих
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    # Сохраняем мэтчи в состоянии (исключаем свою анкету)
    match_partners = []
    for match in matches:
        # Получаем партнера напрямую из мэтча
        if match.user1_id == user.id:
            partner_id = match.user2_id
        else:
            partner_id = match.user1_id
        
        # Проверяем, что партнер не сам пользователь
        if partner_id != user.id:
            # Загружаем партнера с университетом
            partner = await UserRepository.get_by_id(session, partner_id)
            if partner:
                partner = await UserRepository.get_with_university(session, partner.id)
                match_partners.append(partner.id)
    
    # Проверяем, есть ли мэтчи после фильтрации
    if not match_partners:
        await message.answer(TEXTS["no_matches"])
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    await state.update_data(matches=match_partners, current_match_index=0, prev_match_messages=[])
    await state.set_state(MatchesStates.viewing_matches)
    
    # Показываем первый мэтч
    await show_current_match(message, session, state)


async def show_current_match(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать текущий мэтч."""
    data = await state.get_data()
    match_ids = data.get("matches", [])
    current_index = data.get("current_match_index", 0)
    
    # Удаляем предыдущие сообщения, если они есть
    prev_messages = data.get("prev_match_messages", [])
    for msg_id in prev_messages:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    if not match_ids or current_index >= len(match_ids):
        # Мэтчи закончились
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
    
    # Получаем текущего партнера
    partner = await UserRepository.get_by_id(session, match_ids[current_index])
    partner = await UserRepository.get_with_university(session, partner.id)
    
    # Показываем анкету с счетчиком
    current_num = current_index + 1
    total = len(match_ids)
    counter_text = f"\n\n{current_num}/{total}"
    
    # Отправляем анкету с счетчиком в caption и кнопками
    profile_msgs = await send_profile(
        message.bot,
        message.chat.id,
        partner,
        keyboard=match_kb(partner.username if partner.username else None),
        caption_prefix="",
        caption_suffix=counter_text
    )
    
    message_ids = []
    if isinstance(profile_msgs, list):
        message_ids.extend([msg.message_id for msg in profile_msgs])
    elif profile_msgs:
        message_ids.append(profile_msgs.message_id)
    
    # Сохраняем ID сообщений для последующего удаления
    await state.update_data(prev_match_messages=message_ids)


@router.callback_query(F.data == "prev_match", MatchesStates.viewing_matches)
async def handle_prev_match(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Перейти к предыдущему мэтчу."""
    await callback.answer()
    
    data = await state.get_data()
    current_index = data.get("current_match_index", 0)
    
    if current_index > 0:
        await state.update_data(current_match_index=current_index - 1)
        await show_current_match(callback.message, session, state)
    else:
        await callback.answer("Это первый мэтч", show_alert=True)


@router.callback_query(F.data == "next_match", MatchesStates.viewing_matches)
async def handle_next_match(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Перейти к следующему мэтчу."""
    await callback.answer()
    
    data = await state.get_data()
    match_ids = data.get("matches", [])
    current_index = data.get("current_match_index", 0)
    
    if current_index < len(match_ids) - 1:
        await state.update_data(current_match_index=current_index + 1)
        await show_current_match(callback.message, session, state)
    else:
        await callback.answer("Это последний мэтч", show_alert=True)
