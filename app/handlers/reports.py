"""Обработчики жалоб."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repo import UserRepository
from app.database.repositories.report_repo import ReportRepository
from app.keyboards.inline import report_reasons_kb, continue_viewing_kb
from app.keyboards.reply import skip_kb
from app.utils.text_templates import TEXTS
from app.states.states import ReportStates, ViewingStates

router = Router()


@router.callback_query(F.data == "report", ViewingStates.viewing_profiles)
async def start_report(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Начать процесс жалобы."""
    await callback.answer()
    
    # Сохраняем ID текущей анкеты
    data = await state.get_data()
    current_profile_id = data.get("current_profile_id")
    await state.update_data(report_profile_id=current_profile_id)
    
    await state.set_state(ReportStates.choosing_reason)
    await callback.message.answer(
        "Выбери причину жалобы:",
        reply_markup=report_reasons_kb()
    )


@router.callback_query(F.data.startswith("report_"), ReportStates.choosing_reason)
async def handle_report_reason(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка выбора причины жалобы."""
    reason_map = {
        "report_photo": "Фото не соответствует",
        "report_offensive": "Оскорбительный контент",
        "report_spam": "Продажа/реклама",
        "report_minor": "Несовершеннолетний",
        "report_other": "Другое",
    }
    
    if callback.data == "report_cancel":
        await callback.answer()
        await state.set_state(ViewingStates.viewing_profiles)
        await callback.message.delete()
        return
    
    reason = reason_map.get(callback.data, "Другое")
    
    await state.update_data(report_reason=reason)
    await state.set_state(ReportStates.writing_comment)
    
    await callback.message.delete()
    await callback.message.answer(
        "Хочешь добавить комментарий к жалобе?",
        reply_markup=skip_kb()
    )


@router.message(ReportStates.writing_comment)
async def process_report_comment(
    message: Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """Обработка комментария к жалобе."""
    # Если пользователь нажал цифру (вернулся в меню), выходим из процесса жалобы
    if message.text in ["1", "2", "3", "4"]:
        await state.clear()
        from app.utils.menu_helpers import send_main_menu_with_cleanup
        from app.database.repositories.user_repo import UserRepository
        user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
        await send_main_menu_with_cleanup(
            message.bot,
            message.chat.id,
            state,
            user.show_in_search
        )
        return
    
    if message.text and message.text.strip() == "Пропустить ⏭️":
        comment = None
    else:
        comment = message.text if message.text else None
    
    data = await state.get_data()
    reason = data.get("report_reason")
    current_profile_id = data.get("report_profile_id")
    
    if not current_profile_id:
        await message.answer("❌ Ошибка")
        return
    
    user = await UserRepository.get_by_telegram_id(session, message.from_user.id)
    
    await ReportRepository.create(
        session,
        from_user_id=user.id,
        to_user_id=current_profile_id,
        reason=reason,
        comment=comment
    )
    
    await session.commit()
    
    await state.set_state(ViewingStates.viewing_profiles)
    await message.answer(
        TEXTS["report_sent"] + "\n\nПоказать следующую анкету?",
        reply_markup=continue_viewing_kb()
    )

