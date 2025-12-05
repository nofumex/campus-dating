"""Вспомогательные функции для работы с меню."""
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from app.keyboards.reply import main_menu_kb
from app.utils.text_templates import TEXTS


async def send_main_menu_with_cleanup(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    show_in_search: bool = True
) -> None:
    """Отправить главное меню с удалением предыдущих меню."""
    # Получаем ID предыдущих меню из состояния
    data = await state.get_data()
    prev_menu_ids = data.get("prev_menu_ids", [])
    
    # Удаляем предыдущие меню
    for msg_id in prev_menu_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass
    
    # Отправляем новое меню
    menu_msg = await bot.send_message(
        chat_id=chat_id,
        text=TEXTS["main_menu"],
        reply_markup=main_menu_kb(show_in_search)
    )
    
    # Сохраняем ID нового меню
    await state.update_data(prev_menu_ids=[menu_msg.message_id])





