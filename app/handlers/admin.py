"""Обработчики админ-панели."""
from typing import List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import Config
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.university_repo import UniversityRepository
from app.database.repositories.report_repo import ReportRepository
from app.database.models import User, University, Report, Match, Like, ViewedProfile
from app.keyboards.inline import (
    admin_menu_kb, admin_universities_kb, admin_report_kb
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

