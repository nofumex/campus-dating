"""Обработчики регистрации."""
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.repositories.university_repo import UniversityRepository
from app.keyboards.inline import choose_university_kb
from app.keyboards.reply import (
    gender_kb, looking_for_kb, photo_done_kb, skip_kb, confirm_profile_kb
)
from app.utils.text_templates import TEXTS
from app.utils.helpers import validate_name, validate_age, validate_bio
from app.states.states import RegistrationStates
from app.utils.helpers import send_profile

router = Router()

# Храним выбранные университеты для пагинации
UNIVERSITIES_CACHE: List = []


@router.message(RegistrationStates.waiting_for_university & ~F.via_bot)
async def show_universities(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать список университетов."""
    # Игнорируем сообщения через inline-режим (они обрабатываются отдельным обработчиком)
    if message.via_bot:
        return
    
    global UNIVERSITIES_CACHE
    
    if not UNIVERSITIES_CACHE:
        UNIVERSITIES_CACHE = await UniversityRepository.get_all_active(session)
    
    if not UNIVERSITIES_CACHE:
        await message.answer(
            "❌ Пока нет доступных университетов. Обратитесь к администратору."
        )
        return
    
    await message.answer(
        TEXTS["choose_university"],
        reply_markup=choose_university_kb()
    )




@router.inline_query()
async def handle_inline_query(
    inline_query: InlineQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка inline-запросов для выбора университета."""
    query = inline_query.query.strip()
    query_lower = query.lower()
    
    # Обрабатываем ТОЛЬКО запросы, которые точно начинаются с "uni" (не пустые)
    if not query_lower.startswith("uni"):
        return
    
    # Получаем все активные университеты
    universities = await UniversityRepository.get_all_active(session)
    
    if not universities:
        await inline_query.answer(
            results=[],
            cache_time=1
        )
        return
    
    # Фильтруем университеты по запросу (если есть текст после "uni")
    query_text = query_lower.replace("uni", "").strip()
    if query_text:
        universities = [
            uni for uni in universities
            if query_text in uni.name.lower() or query_text in uni.short_name.lower() or query_text in uni.city.lower()
        ]
    
    # Создаем результаты для inline-запроса
    # title = аббревиатура, description = полное название - город
    results = []
    for uni in universities[:50]:  # Telegram ограничивает до 50 результатов
        results.append(
            InlineQueryResultArticle(
                id=f"uni_{uni.id}",
                title=uni.short_name,  # Аббревиатура в title
                description=f"{uni.name} - {uni.city}",  # Полное название и город в description
                input_message_content=InputTextMessageContent(
                    message_text=f"#{uni.short_name}"  # Отправляем только аббревиатуру
                )
            )
        )
    
    await inline_query.answer(
        results=results,
        cache_time=300
    )


@router.message(F.text.startswith("#") & F.via_bot)
async def handle_university_selection_via_bot(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка выбора университета через inline-режим (сообщение в формате #АББРЕВИАТУРА)."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Проверяем, что сообщение пришло через нашего бота
    if not message.via_bot:
        return
    
    # Проверяем формат сообщения (должно быть #АББРЕВИАТУРА)
    if not message.text or len(message.text) < 2 or not message.text[1:].strip():
        return
    
    # Проверяем текущее состояние ПЕРЕД удалением сообщения
    current_state = await state.get_state()
    logger.info(f"Registration handler: состояние = {current_state}, ожидаемое = {RegistrationStates.waiting_for_university}")
    
    # Обрабатываем только если состояние waiting_for_university
    if current_state != RegistrationStates.waiting_for_university:
        logger.info("Состояние не waiting_for_university, пропускаем")
        return
    
    logger.info(f"Обрабатываем выбор университета при регистрации: {message.text}")
    
    # Удаляем сообщение с выбором университета СРАЗУ
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Извлекаем аббревиатуру из текста сообщения (убираем #)
    short_name = message.text[1:].strip()
    logger.info(f"Ищем университет с аббревиатурой: {short_name}")
    
    # Ищем университет по аббревиатуре
    universities = await UniversityRepository.get_all_active(session)
    university = None
    for uni in universities:
        if uni.short_name == short_name:
            university = uni
            logger.info(f"Найден университет: {university.name}")
            break
    
    if not university:
        logger.warning(f"Университет с аббревиатурой {short_name} не найден")
        await message.answer("❌ Университет не найден")
        return
    
    # Сохраняем выбранный университет
    await state.update_data(university_id=university.id)
    await state.set_state(RegistrationStates.waiting_for_name)
    logger.info(f"Университет сохранен, переходим к запросу имени")
    
    # Отправляем сообщение с запросом имени
    await message.answer(TEXTS["ask_name"])


@router.message(RegistrationStates.waiting_for_name)
async def process_name(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка ввода имени."""
    name = message.text.strip()
    
    if not validate_name(name):
        await message.answer(TEXTS["invalid_name"])
        return
    
    await state.update_data(name=name)
    await state.set_state(RegistrationStates.waiting_for_age)
    await message.answer(TEXTS["ask_age"])


@router.message(RegistrationStates.waiting_for_age)
async def process_age(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка ввода возраста."""
    age = validate_age(message.text)
    
    if age is None:
        await message.answer(TEXTS["invalid_age"])
        return
    
    await state.update_data(age=age)
    await state.set_state(RegistrationStates.waiting_for_gender)
    await message.answer(TEXTS["ask_gender"], reply_markup=gender_kb())


@router.message(RegistrationStates.waiting_for_gender)
async def process_gender(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка выбора пола."""
    text = message.text.strip()
    
    if "парень" in text.lower() or "👨" in text:
        gender = "male"
    elif "девушка" in text.lower() or "👩" in text:
        gender = "female"
    else:
        await message.answer("❌ Пожалуйста, выбери пол из предложенных вариантов")
        return
    
    await state.update_data(gender=gender)
    await state.set_state(RegistrationStates.waiting_for_looking_for)
    await message.answer(TEXTS["ask_looking_for"], reply_markup=looking_for_kb())


@router.message(RegistrationStates.waiting_for_looking_for)
async def process_looking_for(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка выбора кого ищем."""
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
    
    await state.update_data(looking_for=looking_for)
    await state.set_state(RegistrationStates.waiting_for_photo)
    # Не показываем кнопку "Готово ✅" до тех пор, пока не будет добавлено хотя бы одно фото
    from aiogram.types import ReplyKeyboardRemove
    await message.answer(TEXTS["ask_photo"], reply_markup=ReplyKeyboardRemove())


@router.message(RegistrationStates.waiting_for_photo, F.photo)
async def process_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка загрузки фото."""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    # Разрешаем только ОДНО фото
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


@router.message(RegistrationStates.waiting_for_photo, F.text == "Готово ✅")
async def process_photo_done(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка завершения загрузки фото."""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if not photos:
        await message.answer("❌ Пожалуйста, загрузи хотя бы одно фото")
        return
    
    await state.set_state(RegistrationStates.waiting_for_bio)
    await message.answer(TEXTS["ask_bio"], reply_markup=skip_kb())


@router.message(RegistrationStates.waiting_for_bio)
async def process_bio(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка ввода описания."""
    if message.text and message.text.strip() == "Пропустить ⏭️":
        bio = ""
    else:
        bio = message.text.strip() if message.text else ""
        
        if not validate_bio(bio):
            await message.answer(TEXTS["invalid_bio"])
            return
    
    await state.update_data(bio=bio)
    await state.set_state(RegistrationStates.confirm_profile)
    
    # Показываем анкету для подтверждения
    data = await state.get_data()
    photos = data.get("photos", [])
    
    # Создаем временного пользователя для отображения
    from app.database.models import User, University
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    
    university = await UniversityRepository.get_by_id(session, data["university_id"])
    
    # Отправляем фото с подписью (только одно, даже если в состоянии почему-то больше)
    caption = f"{data['name']}, {data['age']}, {university.short_name} 🎓\n\n{data['bio']}"
    
    await message.answer_photo(
        photo=photos[0],
        caption=caption
    )
    
    await message.answer(
        "Всё верно?",
        reply_markup=confirm_profile_kb()
    )


@router.message(RegistrationStates.confirm_profile, F.text == "Да, всё супер! ✅")
async def confirm_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Подтверждение и сохранение анкеты."""
    data = await state.get_data()
    photos = data.get("photos", [])
    
    if not photos:
        await message.answer("❌ Ошибка: фото не найдены")
        return
    
    # Получаем или создаем пользователя
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    user_data = {
        "telegram_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data["name"],
        "age": data["age"],
        "gender": data["gender"],
        "looking_for": data["looking_for"],
        "bio": data["bio"],
        "university_id": data["university_id"],
        "photo_1": photos[0],
        "photo_2": None,
        "photo_3": None,
        "is_registered": True,
        "show_in_search": True,
    }
    
    if user:
        await UserRepository.update(session, user.id, user_data)
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    else:
        user = await UserRepository.create(session, user_data)
    
    await session.commit()
    
    await state.clear()
    
    from app.keyboards.reply import main_menu_kb
    # Сначала отправляем текст без меню
    await message.answer(TEXTS["profile_confirmed"])
    # Затем отдельным сообщением отправляем главное меню с клавиатурой
    await message.answer(
        TEXTS["main_menu"],
        reply_markup=main_menu_kb(user.show_in_search)
    )


@router.message(RegistrationStates.confirm_profile, F.text == "Заполнить заново 🔄")
async def restart_registration(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Перезапуск регистрации."""
    await state.clear()
    await state.set_state(RegistrationStates.waiting_for_university)
    await show_universities(message, session, state)

