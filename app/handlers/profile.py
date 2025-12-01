"""Обработчики профиля."""
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.services.matching_service import MatchingService
from app.keyboards.reply import (
    profile_menu_kb, main_menu_kb, gender_kb, looking_for_kb,
    photo_done_kb, skip_kb
)
from app.keyboards.inline import edit_profile_kb
from app.utils.text_templates import TEXTS
from app.utils.helpers import send_profile, validate_name, validate_age, validate_bio
from app.states.states import EditProfileStates, ProfileMenuStates, ViewingStates

router = Router()


@router.message(F.text == "1", ProfileMenuStates.in_profile_menu)
async def start_viewing_from_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать просмотр анкет из меню профиля."""
    # Отправляем сообщение с remove keyboard ДО начала просмотра
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
    
    await state.clear()
    await state.set_state(ViewingStates.viewing_profiles)
    # Клавиатура будет установлена в show_next_profile
    from app.handlers.viewing import show_next_profile
    await show_next_profile(message, session, state)


@router.message(F.text == "2", ProfileMenuStates.in_profile_menu)
async def start_edit(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать редактирование профиля."""
    # Отправляем сообщение с remove keyboard ДО основного сообщения
    import asyncio
    remove_msg = await message.answer(
        "✏️",  # Эмодзи карандаша
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
    
    await state.set_state(EditProfileStates.choosing_what_to_edit)
    # Отправляем сообщение с inline кнопками
    await message.answer(
        "Что хочешь изменить?",
        reply_markup=edit_profile_kb()
    )


@router.message(F.text == "2")
async def show_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать профиль пользователя."""
    # Проверяем, что мы не в меню профиля (там "2" означает "Редактировать")
    current_state = await state.get_state()
    if current_state == ProfileMenuStates.in_profile_menu:
        # Это обрабатывается в обработчике выше
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    user = await UserRepository.get_with_university(session, user.id)
    await UserRepository.update_last_active(session, user.id)
    await session.commit()
    
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.callback_query(F.data == "edit_name", EditProfileStates.choosing_what_to_edit)
async def edit_name(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование имени."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_name)
    await callback.message.answer("Введи новое имя:", reply_markup=ReplyKeyboardRemove())


@router.message(EditProfileStates.editing_name)
async def process_edit_name(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка нового имени."""
    if not validate_name(message.text):
        await message.answer(TEXTS["invalid_name"])
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await UserRepository.update(session, user.id, {"name": message.text})
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    # Отправляем сообщение об обновлении
    await message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.callback_query(F.data == "edit_age", EditProfileStates.choosing_what_to_edit)
async def edit_age(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование возраста."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_age)
    await callback.message.answer("Введи новый возраст:", reply_markup=ReplyKeyboardRemove())


@router.message(EditProfileStates.editing_age)
async def process_edit_age(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка нового возраста."""
    age = validate_age(message.text)
    
    if age is None:
        await message.answer(TEXTS["invalid_age"])
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await UserRepository.update(session, user.id, {"age": age})
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    # Отправляем сообщение об обновлении
    await message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.callback_query(F.data == "edit_bio", EditProfileStates.choosing_what_to_edit)
async def edit_bio(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование описания."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_bio)
    await callback.message.answer("Введи новое описание:", reply_markup=skip_kb())


@router.message(EditProfileStates.editing_bio)
async def process_edit_bio(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка нового описания."""
    if message.text and message.text.strip() == "Пропустить ⏭️":
        bio = ""
    else:
        bio = message.text.strip() if message.text else ""
        
        if not validate_bio(bio):
            await message.answer(TEXTS["invalid_bio"])
            return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await UserRepository.update(session, user.id, {"bio": bio})
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    # Отправляем сообщение об обновлении
    await message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.callback_query(F.data == "edit_looking_for", EditProfileStates.choosing_what_to_edit)
async def edit_looking_for(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование кого ищем."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_looking_for)
    await callback.message.answer(TEXTS["ask_looking_for"], reply_markup=looking_for_kb())


@router.callback_query(F.data == "edit_photo", EditProfileStates.choosing_what_to_edit)
async def edit_photo(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование фото."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_photo)
    await state.update_data(photos=[])
    # Не показываем кнопку "Готово ✅" до тех пор, пока не будет добавлено хотя бы одно фото
    from aiogram.types import ReplyKeyboardRemove
    await callback.message.answer(
        "Отправь новые фото (от 1 до 3).\nТекущие фото будут заменены.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.callback_query(F.data == "edit_university", EditProfileStates.choosing_what_to_edit)
async def edit_university(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Редактирование университета."""
    await callback.answer()
    await state.set_state(EditProfileStates.editing_university)
    await callback.message.answer(
        "⚠️ Если сменишь университет, тебе будут показываться анкеты только из нового вуза.\n\nВыбери новый университет:"
    )
    
    from app.database.repositories.university_repo import UniversityRepository
    from app.keyboards.inline import universities_kb
    
    universities = await UniversityRepository.get_all_active(session)
    if not universities:
        await callback.message.answer("❌ Пока нет доступных университетов")
        return
    
    await callback.message.answer(
        "🎓 Выбери свой университет из списка:",
        reply_markup=universities_kb(universities, page=1)
    )


@router.callback_query(F.data == "edit_back", EditProfileStates.choosing_what_to_edit)
async def edit_back_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться к профилю из меню редактирования через callback (для обратной совместимости)."""
    await callback.answer()
    await state.set_state(ProfileMenuStates.in_profile_menu)
    await callback.message.delete()
    
    # Получаем пользователя и показываем профиль с меню
    user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    
    # Отправляем профиль
    await send_profile(
        callback.message.bot,
        callback.message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню профиля
    await callback.message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.message(F.text == "Назад ◀️", EditProfileStates.choosing_what_to_edit)
async def edit_back_message(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Вернуться к профилю из меню редактирования через reply кнопку."""
    await state.set_state(ProfileMenuStates.in_profile_menu)
    
    # Получаем пользователя и показываем профиль с меню
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    
    # Отправляем профиль
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню профиля
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.message(EditProfileStates.editing_looking_for)
async def process_edit_looking_for(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка нового значения кого ищем."""
    text = message.text.strip()
    
    if "парн" in text.lower() or "👨" in text:
        looking_for = "male"
    elif "девуш" in text.lower() or "👩" in text:
        looking_for = "female"
    elif "разниц" in text.lower() or "🤷" in text:
        looking_for = "any"
    else:
        await message.answer("❌ Пожалуйста, выбери вариант из предложенных")
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await UserRepository.update(session, user.id, {"looking_for": looking_for})
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    # Отправляем сообщение об обновлении
    await message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )




@router.message(EditProfileStates.editing_photo, F.photo)
async def process_edit_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка загрузки нового фото."""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    # Разрешаем только ОДНО фото в анкете
    if len(photos) >= 1:
        await message.answer("❌ Можно загрузить только одно фото для анкеты")
        return
    
    photo_id = message.photo[-1].file_id
    photos.append(photo_id)
    
    await state.update_data(photos=photos)
    await message.answer("Фото сохранено ✅")
    
    # Показываем кнопку "Готово ✅" после добавления первого (и единственного) фото
    # Отправляем кнопку отдельным сообщением (Telegram требует текст)
    await message.answer("⬇️", reply_markup=photo_done_kb())


@router.message(EditProfileStates.editing_photo, F.text == "Готово ✅")
async def process_edit_photo_done(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Завершение изменения фото."""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if not photos:
        await message.answer("❌ Пожалуйста, загрузи хотя бы одно фото")
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    update_data = {
        "photo_1": photos[0],
        "photo_2": None,
        "photo_3": None,
    }
    
    await UserRepository.update(session, user.id, update_data)
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    # Отправляем сообщение об обновлении
    await message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        message.bot,
        message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.message(F.text == "3", ProfileMenuStates.in_profile_menu)
async def reset_views(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Сбросить просмотренные анкеты."""
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    await MatchingService.reset_views(session, user.id)
    await session.commit()
    
    # Очищаем состояние и возвращаемся в главное меню
    await state.clear()
    
    # Отправляем сообщение о сбросе
    await message.answer(TEXTS["views_reset"])
    # Отправляем главное меню отдельным сообщением с удалением предыдущих
    from app.utils.menu_helpers import send_main_menu_with_cleanup
    await send_main_menu_with_cleanup(
        message.bot,
        message.chat.id,
        state,
        user.show_in_search
    )


@router.callback_query(F.data.startswith("uni_") & ~F.data.startswith("uni_page_"), EditProfileStates.editing_university)
async def handle_university_change(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка изменения университета."""
    university_id = int(callback.data.split("_")[1])
    
    from app.database.repositories.university_repo import UniversityRepository
    university = await UniversityRepository.get_by_id(session, university_id)
    if not university:
        await callback.answer("❌ Университет не найден", show_alert=True)
        return
    
    user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
    await UserRepository.update(session, user.id, {"university_id": university_id})
    await session.commit()
    
    await state.set_state(ProfileMenuStates.in_profile_menu)
    await callback.message.delete()
    # Отправляем сообщение об обновлении
    await callback.message.answer(TEXTS["profile_updated"])
    # Отправляем обновленный профиль
    user = await UserRepository.get_by_telegram_id(session, callback.from_user.id)
    user = await UserRepository.get_with_university(session, user.id)
    await send_profile(
        callback.message.bot,
        callback.message.chat.id,
        user,
        keyboard=None
    )
    # Отправляем меню
    await callback.message.answer(
        "Твоя анкета 👆\n\n" + TEXTS["profile_menu"],
        reply_markup=profile_menu_kb()
    )


@router.callback_query(F.data.startswith("uni_page_"), EditProfileStates.editing_university)
async def handle_university_page_change(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка пагинации университетов при редактировании."""
    page = int(callback.data.split("_")[-1])
    
    from app.database.repositories.university_repo import UniversityRepository
    from app.keyboards.inline import universities_kb
    
    universities = await UniversityRepository.get_all_active(session)
    await callback.message.edit_reply_markup(
        reply_markup=universities_kb(universities, page=page)
    )
    await callback.answer()



