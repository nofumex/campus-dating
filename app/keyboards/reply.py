"""Reply клавиатуры."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb(profile_active: bool = True) -> ReplyKeyboardMarkup:
    """Главное меню - только цифры."""
    keyboard = [
        [
            KeyboardButton(text="1"),
            KeyboardButton(text="2"),
            KeyboardButton(text="3"),
            KeyboardButton(text="4")
        ],
    ]
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def viewing_profile_kb() -> ReplyKeyboardMarkup:
    """Клавиатура при просмотре анкеты."""
    keyboard = [
        [
            KeyboardButton(text="❤️"),
            KeyboardButton(text="💌"),
            KeyboardButton(text="👎"),
            KeyboardButton(text="🏠")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def gender_kb() -> ReplyKeyboardMarkup:
    """Выбор пола."""
    keyboard = [
        [KeyboardButton(text="Я парень 👨")],
        [KeyboardButton(text="Я девушка 👩")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def looking_for_kb() -> ReplyKeyboardMarkup:
    """Кого ищем."""
    keyboard = [
        [KeyboardButton(text="Парней 👨")],
        [KeyboardButton(text="Девушек 👩")],
        [KeyboardButton(text="Без разницы 🤷")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def photo_done_kb() -> ReplyKeyboardMarkup:
    """Кнопка готово для фото."""
    keyboard = [[KeyboardButton(text="Готово ✅")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def skip_kb() -> ReplyKeyboardMarkup:
    """Кнопка пропустить."""
    keyboard = [[KeyboardButton(text="Пропустить ⏭️")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    """Кнопка отмена."""
    keyboard = [[KeyboardButton(text="Отмена")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def confirm_profile_kb() -> ReplyKeyboardMarkup:
    """Подтверждение анкеты."""
    keyboard = [
        [KeyboardButton(text="Да, всё супер! ✅")],
        [KeyboardButton(text="Заполнить заново 🔄")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def back_to_menu_kb() -> ReplyKeyboardMarkup:
    """Вернуться в меню - использует главное меню с цифрами."""
    return main_menu_kb()


def profile_menu_kb() -> ReplyKeyboardMarkup:
    """Меню профиля - только цифры."""
    keyboard = [
        [
            KeyboardButton(text="1"),
            KeyboardButton(text="2"),
            KeyboardButton(text="3")
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def view_profiles_kb() -> ReplyKeyboardMarkup:
    """Кнопка для просмотра анкет - использует главное меню с цифрами."""
    return main_menu_kb()


def edit_back_kb() -> ReplyKeyboardMarkup:
    """Кнопка назад для меню редактирования."""
    keyboard = [[KeyboardButton(text="Назад ◀️")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def yes_no_kb() -> ReplyKeyboardMarkup:
    """Клавиатура Да/Нет."""
    keyboard = [
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def likes_action_kb() -> ReplyKeyboardMarkup:
    """Клавиатура действий при просмотре лайков."""
    keyboard = [
        [
            KeyboardButton(text="❤️"),
            KeyboardButton(text="👎"),
            KeyboardButton(text="🏠")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def matches_navigation_kb(username: str = None) -> ReplyKeyboardMarkup:
    """Клавиатура навигации по мэтчам."""
    keyboard = []
    if username:
        keyboard.append([KeyboardButton(text="Написать")])
    keyboard.append([
        KeyboardButton(text="⬅️"),
        KeyboardButton(text="➡️")
    ])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def matches_view_profiles_kb() -> ReplyKeyboardMarkup:
    """Клавиатура при просмотре мэтчей – только кнопка 'Смотреть анкеты'."""
    keyboard = [
        [KeyboardButton(text="👁 Смотреть анкеты")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def super_favorite_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для особенной анкеты – одна кнопка 😍."""
    keyboard = [
        [KeyboardButton(text="😍")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

