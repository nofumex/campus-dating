"""Обработчик команды /start."""
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.keyboards.reply import main_menu_kb
from app.utils.text_templates import TEXTS
from app.states.states import RegistrationStates

router = Router()


@router.message(F.text == "Создать анкету 💫")
async def start_registration(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать регистрацию."""
    # Удаляем клавиатуру после нажатия
    await message.answer(
        "Начинаем создание анкеты...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.set_state(RegistrationStates.waiting_for_university)
    
    from app.handlers.registration import show_universities
    await show_universities(message, session, state)


@router.message(F.text == "/start")
async def cmd_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработчик команды /start."""
    await state.clear()
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user:
        # Новый пользователь - показываем кнопку только один раз
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Создать анкету 💫")]],
            resize_keyboard=True
        )
        await message.answer(
            TEXTS["welcome"],
            reply_markup=kb
        )
    elif not user.is_registered:
        # Пользователь существует, но не зарегистрирован - без кнопки
        await state.set_state(RegistrationStates.waiting_for_university)
        
        from app.handlers.registration import show_universities
        await show_universities(message, session, state)
    else:
        # Пользователь зарегистрирован - при старте "размораживаем" анкету
        update_data = {}
        if not user.is_active:
            update_data["is_active"] = True
        if not user.show_in_search:
            update_data["show_in_search"] = True
        
        if update_data:
            await UserRepository.update(session, user.id, update_data)
            # Обновляем объект пользователя локально, чтобы отразить изменения в меню
            for key, value in update_data.items():
                setattr(user, key, value)
        
        await UserRepository.update_last_active(session, user.id)
        await session.commit()
        
        await message.answer(
            TEXTS["main_menu"],
            reply_markup=main_menu_kb(user.show_in_search)
        )


@router.message(F.text == "/freeze")
async def cmd_freeze(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Команда /freeze — временно скрывает анкету из поиска."""
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала создай и заполни анкету")
        return
    
    # Замораживаем анкету: выключаем активность и видимость в поиске
    await UserRepository.update(
        session,
        user.id,
        {
            "is_active": False,
            "show_in_search": False,
        }
    )
    await session.commit()
    
    await state.clear()
    
    await message.answer(
        "🧊 Твоя анкета заморожена.\n"
        "Она больше не показывается другим пользователям.\n\n"
        "Чтобы снова всё включить — просто отправь /start.",
        reply_markup=main_menu_kb(False)
    )

