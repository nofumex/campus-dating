"""Inline клавиатуры."""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.models import University


def report_button_kb() -> InlineKeyboardMarkup:
    """Кнопка жалобы под сообщением анкеты."""
    keyboard = [
        [
            InlineKeyboardButton(text="⚠️Пожаловаться", callback_data="report"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def incoming_like_kb() -> InlineKeyboardMarkup:
    """Клавиатура для входящего лайка."""
    keyboard = [
        [
            InlineKeyboardButton(text="❤️", callback_data="mutual_like"),
            InlineKeyboardButton(text="👎", callback_data="reject_like"),
            InlineKeyboardButton(text="💤", callback_data="go_sleep"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def universities_kb(
    universities: List[University],
    page: int = 1,
    per_page: int = 5
) -> InlineKeyboardMarkup:
    """Клавиатура с университетами (с пагинацией)."""
    total_pages = (len(universities) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    buttons = []
    for uni in universities[start_idx:end_idx]:
        buttons.append([InlineKeyboardButton(
            text=uni.name,
            callback_data=f"uni_{uni.id}"
        )])
    
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"uni_page_{page-1}"
        ))
    if page < total_pages:
        nav.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=f"uni_page_{page+1}"
        ))
    
    if nav:
        buttons.append(nav)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def report_reasons_kb() -> InlineKeyboardMarkup:
    """Клавиатура с причинами жалобы."""
    keyboard = [
        [InlineKeyboardButton(text="Фото не соответствует", callback_data="report_photo")],
        [InlineKeyboardButton(text="Оскорбительный контент", callback_data="report_offensive")],
        [InlineKeyboardButton(text="Продажа/реклама", callback_data="report_spam")],
        [InlineKeyboardButton(text="Несовершеннолетний", callback_data="report_minor")],
        [InlineKeyboardButton(text="Другое", callback_data="report_other")],
        [InlineKeyboardButton(text="Отмена ❌", callback_data="report_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def edit_profile_kb() -> InlineKeyboardMarkup:
    """Клавиатура редактирования профиля - 2 столбца по 3 кнопки + кнопка Назад."""
    keyboard = [
        [
            InlineKeyboardButton(text="Имя", callback_data="edit_name"),
            InlineKeyboardButton(text="Возраст", callback_data="edit_age"),
            InlineKeyboardButton(text="О себе", callback_data="edit_bio")
        ],
        [
            InlineKeyboardButton(text="Кого ищу", callback_data="edit_looking_for"),
            InlineKeyboardButton(text="Фото", callback_data="edit_photo"),
            InlineKeyboardButton(text="Университет", callback_data="edit_university")
        ],
        [InlineKeyboardButton(text="Назад ◀️", callback_data="edit_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def match_kb(username: Optional[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для мэтча."""
    keyboard = []
    if username:
        keyboard.append([
            InlineKeyboardButton(
                text="Написать",
                url=f"https://t.me/{username.lstrip('@')}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="⬅️", callback_data="prev_match"),
        InlineKeyboardButton(text="➡️", callback_data="next_match")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def match_write_only_kb(username: str) -> InlineKeyboardMarkup:
    """Клавиатура только с кнопкой 'Написать' для нового мэтча."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Написать",
                url=f"https://t.me/{username.lstrip('@')}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def continue_viewing_kb() -> InlineKeyboardMarkup:
    """Клавиатура для продолжения просмотра."""
    keyboard = [
        [
            InlineKeyboardButton(text="Продолжить 👀", callback_data="continue_viewing"),
            InlineKeyboardButton(text="В меню 🏠", callback_data="go_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_menu_kb(pending_reports_count: int = 0) -> InlineKeyboardMarkup:
    """Главное меню админа."""
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🎓 Университеты", callback_data="admin_universities")],
        [InlineKeyboardButton(
            text=f"📋 Жалобы ({pending_reports_count} новых)",
            callback_data="admin_reports"
        )],
        [InlineKeyboardButton(text="🚫 Забанить пользователя", callback_data="admin_ban")],
        [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_universities_kb() -> InlineKeyboardMarkup:
    """Меню управления университетами."""
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить университет", callback_data="admin_add_uni")],
        [InlineKeyboardButton(text="📋 Список университетов", callback_data="admin_list_unis")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_report_kb(report_id: int, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для обработки жалобы."""
    keyboard = [
        [
            InlineKeyboardButton(text="🚫 Забанить", callback_data=f"admin_ban_{report_id}"),
            InlineKeyboardButton(text="⚠️ Предупредить", callback_data=f"admin_warn_{report_id}"),
        ],
        [
            InlineKeyboardButton(text="✅ Отклонить жалобу", callback_data=f"admin_reject_{report_id}"),
        ],
    ]
    
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton(
            text="◀️ Пред.",
            callback_data=f"admin_report_page_{current_page-1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="admin_report_info"
    ))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton(
            text="След. ▶️",
            callback_data=f"admin_report_page_{current_page+1}"
        ))
    
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

