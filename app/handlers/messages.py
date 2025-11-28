"""Обработчики сообщений."""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.keyboards.reply import main_menu_kb
from app.utils.text_templates import TEXTS

router = Router()


@router.message(F.text == "5. Выключить анкету 😴")
async def hide_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Выключить анкету."""
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    await UserRepository.update(session, user.id, {"show_in_search": False})
    await session.commit()
    
    await message.answer(
        TEXTS["profile_hidden"],
        reply_markup=main_menu_kb(False)
    )


@router.message(F.text == "5. Включить анкету 💫")
async def show_profile(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Включить анкету."""
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    if not user or not user.is_registered:
        await message.answer("❌ Сначала заверши регистрацию")
        return
    
    await UserRepository.update(session, user.id, {"show_in_search": True})
    await session.commit()
    
    await message.answer(
        TEXTS["profile_visible"],
        reply_markup=main_menu_kb(True)
    )

