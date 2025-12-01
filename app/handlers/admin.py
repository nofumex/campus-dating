"""Обработчики админ-панели."""
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.config import Config
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.university_repo import UniversityRepository
from app.database.repositories.report_repo import ReportRepository
from app.database.models import User, University, Report, Match, Like, ViewedProfile
from app.keyboards.inline import (
    admin_menu_kb,
    admin_universities_kb,
    admin_report_kb,
    admin_fakes_menu_kb,
    admin_fakes_list_kb,
    admin_fake_detail_kb,
)
from app.utils.text_templates import TEXTS
from app.utils.helpers import send_profile
from app.states.states import AdminStates

router = Router()

# Кэш для жалоб
REPORTS_CACHE: List[Report] = []


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом."""
    return user_id == Config.ADMIN_ID


@router.message(F.text == "/admin")
async def admin_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начало работы с админ-панелью."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    await state.set_state(AdminStates.main_menu)
    
    # Подсчитываем необработанные жалобы
    pending_reports = await ReportRepository.get_pending(session)
    
    await message.answer(
        "👑 Админ-панель",
        reply_markup=admin_menu_kb(len(pending_reports))
    )


@router.callback_query(F.data == "admin_stats", AdminStates.main_menu)
async def show_stats(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать статистику."""
    await callback.answer()
    
    # Всего пользователей
    total_users = await session.scalar(select(func.count(User.id)))
    active_users = await session.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )
    inactive_users = await session.scalar(
        select(func.count(User.id)).where(User.is_active == False)
    )
    banned_users = await session.scalar(
        select(func.count(User.id)).where(User.is_banned == True)
    )
    
    # Университеты
    total_unis = await session.scalar(select(func.count(University.id)))
    
    # Мэтчи
    total_matches = await session.scalar(select(func.count(Match.id)))
    
    # Лайки сегодня
    from datetime import datetime, timedelta
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    likes_today = await session.scalar(
        select(func.count(Like.id)).where(Like.created_at >= today)
    )
    
    # Просмотры сегодня
    views_today = await session.scalar(
        select(func.count(ViewedProfile.id)).where(ViewedProfile.created_at >= today)
    )
    
    # Регистрации за неделю
    week_ago = datetime.utcnow() - timedelta(days=7)
    registrations_week = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= week_ago)
    )
    
    stats_text = f"""📊 Статистика бота:

👥 Всего пользователей: {total_users}
✅ Активных анкет: {active_users}
😴 Неактивных: {inactive_users}
🚫 Забаненных: {banned_users}

🎓 Университетов: {total_unis}

💕 Всего мэтчей: {total_matches}
❤️ Лайков сегодня: {likes_today}
👀 Просмотров сегодня: {views_today}

📈 Регистраций за неделю: {registrations_week}"""
    
    await callback.message.answer(stats_text)


@router.callback_query(F.data == "admin_universities", AdminStates.main_menu)
async def show_universities_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать меню управления университетами."""
    await callback.answer()
    await state.set_state(AdminStates.main_menu)
    await callback.message.answer(
        "🎓 Управление университетами",
        reply_markup=admin_universities_kb()
    )


@router.callback_query(F.data == "admin_add_uni")
async def start_add_university(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать добавление университета."""
    await callback.answer()
    await state.set_state(AdminStates.adding_university)
    await callback.message.answer(
        "Введи название университета.\n\nФормат: Полное название | Сокращение | Город\n\nПример: Московский государственный университет | МГУ | Москва"
    )


@router.message(AdminStates.adding_university)
async def process_add_university(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка добавления университета."""
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("❌ Неверный формат. Используй: Название | Сокращение | Город")
        return
    
    name = parts[0].strip()
    short_name = parts[1].strip()
    city = parts[2].strip()
    
    university = await UniversityRepository.create(
        session,
        name=name,
        short_name=short_name,
        city=city
    )
    
    await session.commit()
    
    await state.set_state(AdminStates.main_menu)
    await message.answer(f"✅ Университет '{name}' добавлен!")


@router.callback_query(F.data == "admin_reports")
async def show_reports(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать жалобы."""
    await callback.answer()
    
    global REPORTS_CACHE
    REPORTS_CACHE = await ReportRepository.get_pending(session)
    
    if not REPORTS_CACHE:
        await callback.message.answer("✅ Нет необработанных жалоб")
        return
    
    await state.update_data(current_report_index=0)
    await show_current_report(callback, session, state)


@router.callback_query(F.data == "admin_fakes", AdminStates.main_menu)
async def show_fakes_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать меню управления фейковыми анкетами."""
    await callback.answer()
    await callback.message.answer(
        "🎭 Управление фейковыми анкетами",
        reply_markup=admin_fakes_menu_kb()
    )


@router.callback_query(F.data == "admin_fake_add")
async def start_add_fake(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать добавление фейковой анкеты."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.adding_fake)
    await callback.message.answer(
        "Отправь сообщение с фото и подписью в формате:\n\n"
        "Имя, Число, Аббревиатура\n\n"
        "Например: Маша, 19, МГУ"
    )


async def _create_fake_from_message(
    message: Message,
    session: AsyncSession
) -> bool:
    """
    Вспомогательная функция: создать фейковую анкету из сообщения админа.
    Формат текста: 'Имя, Число, Аббревиатура'. Обязательно должно быть фото.
    """
    from sqlalchemy import and_, desc

    if not message.photo:
        await message.answer("❌ Нужно отправить фото анкеты.")
        return False
    
    text = (message.caption or message.text or "").strip()
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 3:
        await message.answer("❌ Неверный формат. Используй: Имя, Число, Аббревиатура")
        return False
    
    name, age_str, uni_short = parts
    try:
        age = int(age_str)
    except ValueError:
        await message.answer("❌ Возраст должен быть числом")
        return False
    
    # Ищем университет по аббревиатуре (short_name)
    uni_stmt = select(University).where(University.short_name == uni_short)
    uni_result = await session.execute(uni_stmt)
    university = uni_result.scalar_one_or_none()
    if not university:
        await message.answer("❌ Университет с такой аббревиатурой не найден")
        return False
    
    photo_id = message.photo[-1].file_id
    
    # Придумываем уникальный telegram_id для фейка: используем отрицательные ID
    max_fake_stmt = (
        select(func.min(User.telegram_id))
        .where(User.is_fake == True)
    )
    min_fake_tid = await session.scalar(max_fake_stmt)
    if min_fake_tid is None or min_fake_tid >= 0:
        new_tid = -1
    else:
        new_tid = min_fake_tid - 1
    
    user_data = {
        "telegram_id": new_tid,
        "username": None,
        "name": name,
        "age": age,
        "gender": "male",  # для фейков можно поставить значения по умолчанию
        "looking_for": "any",
        "bio": "",
        "university_id": university.id,
        "photo_1": photo_id,
        "photo_2": None,
        "photo_3": None,
        "is_registered": True,
        "show_in_search": True,
        "is_active": True,
        "is_fake": True,
    }
    
    await UserRepository.create(session, user_data)
    await session.commit()
    
    await message.answer("✅ Фейковая анкета создана")
    return True


@router.message(AdminStates.adding_fake)
async def process_add_fake(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка сообщения для создания фейковой анкеты."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    ok = await _create_fake_from_message(message, session)
    if ok:
        await state.set_state(AdminStates.main_menu)


@router.message(F.photo)
async def auto_create_fake_from_photo(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """
    Авто-создание фейка: если админ в любом месте шлёт фото с подписью
    'Имя, Число, Аббревиатура', создаём фейковую анкету.
    """
    if not is_admin(message.from_user.id):
        return
    
    text = (message.caption or message.text or "").strip()
    if "," not in text:
        return
    
    # Не ломаем другие состояния явно, просто пробуем создать фейк.
    await _create_fake_from_message(message, session)


@router.callback_query(F.data == "admin_fake_list")
async def list_fakes(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать список всех фейковых анкет."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer()
    
    stmt = (
        select(User)
        .options(selectinload(User.university))
        .where(User.is_fake == True, User.is_active == True)
        .order_by(User.created_at.desc())
    )
    result = await session.execute(stmt)
    fakes = list(result.scalars().all())
    
    if not fakes:
        await callback.message.answer("Пока нет фейковых анкет.")
        return
    
    await callback.message.answer(
        "Все фейковые анкеты:",
        reply_markup=admin_fakes_list_kb(fakes)
    )


@router.callback_query(F.data.startswith("admin_fake_"))
async def handle_fake_item(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка нажатия на конкретную фейковую анкету или её команды."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    data = callback.data
    
    if data == "admin_fake_nop":
        await callback.answer()
        return
    
    if data.startswith("admin_fake_delete_"):
        fake_id = int(data.split("_")[-1])
        fake = await UserRepository.get_by_id(session, fake_id)
        if not fake or not fake.is_fake:
            await callback.answer("❌ Фейк не найден", show_alert=True)
            return
        
        await UserRepository.update(
            session,
            fake.id,
            {"is_active": False, "show_in_search": False}
        )
        await session.commit()
        await callback.answer()
        await callback.message.answer("✅ Фейковая анкета удалена из поиска")
        return
    
    # admin_fake_{id} — показать анкету и статистику
    fake_id = int(data.split("_")[-1])
    fake = await UserRepository.get_by_id(session, fake_id)
    if not fake or not fake.is_fake:
        await callback.answer("❌ Фейк не найден", show_alert=True)
        return
    
    await callback.answer()
    
    fake = await UserRepository.get_with_university(session, fake.id)
    
    # Показываем анкету
    await send_profile(
        callback.bot,
        callback.message.chat.id,
        fake,
        keyboard=None
    )
    
    # Считаем лайки/дизлайки
    likes_count = await session.scalar(
        select(func.count(Like.id)).where(
            Like.to_user_id == fake.id,
            Like.is_like == True
        )
    ) or 0
    dislikes_count = await session.scalar(
        select(func.count(Like.id)).where(
            Like.to_user_id == fake.id,
            Like.is_like == False
        )
    ) or 0
    
    await callback.message.answer(
        f"Статистика по фейку {fake.name}, {fake.age}:",
        reply_markup=admin_fake_detail_kb(fake.id, likes_count, dislikes_count)
    )


@router.callback_query(F.data == "admin_super_favorite", AdminStates.main_menu)
async def start_set_super_favorite(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать установку особенного пользователя с 😍."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.setting_super_favorite)
    await callback.message.answer(
        "Введи username пользователя (можно с @), для которого будет режим 😍:"
    )


@router.message(AdminStates.setting_super_favorite)
async def process_set_super_favorite(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Установка пользователя с особым режимом просмотра (😍)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещён")
        return
    
    username = (message.text or "").strip()
    if not username:
        await message.answer("❌ Введи username")
        return
    
    user = await UserRepository.get_by_username(session, username)
    if not user:
        await message.answer("❌ Пользователь с таким username не найден")
        return
    
    # Сбрасываем флаг у всех и ставим у выбранного
    await UserRepository.set_all_super_favorite_false(session)
    await UserRepository.set_super_favorite(session, user.id, True)
    await session.commit()
    
    await state.set_state(AdminStates.main_menu)
    await message.answer(
        f"✅ Пользователь @{user.username or user.telegram_id} теперь в особом режиме 😍"
    )


async def show_current_report(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Показать текущую жалобу."""
    data = await state.get_data()
    report_index = data.get("current_report_index", 0)
    
    if report_index >= len(REPORTS_CACHE):
        await callback.message.answer("✅ Все жалобы обработаны")
        return
    
    report = REPORTS_CACHE[report_index]
    
    # Загружаем пользователей
    from_user = await UserRepository.get_with_university(session, report.from_user_id)
    to_user = await UserRepository.get_with_university(session, report.to_user_id)
    
    # Показываем анкету, на которую пожаловались
    await send_profile(
        callback.bot,
        callback.message.chat.id,
        to_user,
        keyboard=None
    )
    
    report_text = f"""📋 Жалоба (показаны новые)

Жалоба от: @{from_user.username or 'без username'} (ID: {from_user.telegram_id})
Причина: {report.reason}
Комментарий: {report.comment or 'нет'}
Дата: {report.created_at.strftime('%d.%m.%Y %H:%M')}"""
    
    await callback.message.answer(
        report_text,
        reply_markup=admin_report_kb(
            report.id,
            report_index + 1,
            len(REPORTS_CACHE)
        )
    )


@router.callback_query(F.data.startswith("admin_ban_"))
async def handle_ban_user(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Забанить пользователя."""
    await callback.answer()
    
    report_id = int(callback.data.split("_")[-1])
    report = await ReportRepository.get_by_id(session, report_id)
    
    if not report:
        await callback.message.answer("❌ Жалоба не найдена")
        return
    
    # Баним пользователя
    await UserRepository.update(session, report.to_user_id, {"is_banned": True})
    
    # Обновляем статус жалобы
    await ReportRepository.update_status(
        session,
        report_id,
        "reviewed",
        "Пользователь забанен"
    )
    
    await session.commit()
    
    # Отправляем уведомление
    from app.services.notification_service import NotificationService
    banned_user = await UserRepository.get_by_id(session, report.to_user_id)
    await NotificationService.notify_ban(callback.bot, banned_user)
    
    await callback.message.answer("✅ Пользователь забанен")
    
    # Обновляем кэш и показываем следующую жалобу
    global REPORTS_CACHE
    REPORTS_CACHE = [r for r in REPORTS_CACHE if r.id != report_id]
    
    data = await state.get_data()
    await state.update_data(current_report_index=0)
    await show_current_report(callback, session, state)


@router.callback_query(F.data.startswith("admin_reject_"))
async def handle_reject_report(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Отклонить жалобу."""
    await callback.answer()
    
    report_id = int(callback.data.split("_")[-1])
    
    await ReportRepository.update_status(
        session,
        report_id,
        "rejected",
        "Жалоба отклонена"
    )
    
    await session.commit()
    
    await callback.message.answer("✅ Жалоба отклонена")
    
    # Обновляем кэш
    global REPORTS_CACHE
    REPORTS_CACHE = [r for r in REPORTS_CACHE if r.id != report_id]
    
    data = await state.get_data()
    await state.update_data(current_report_index=0)
    await show_current_report(callback, session, state)

