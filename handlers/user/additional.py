import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.user.start import BookingFSM
from keyboards.inline import build_review_keyboard
from utils.helpers import get_datetime_display

logger = logging.getLogger(__name__)
router = Router()


@router.message(BookingFSM.AWAITING_ADDITIONAL)
async def handle_additional(message: Message, state: FSMContext):
    logger.info(f"[ADDITIONAL] User {message.from_user.id} response: {message.text[:50] if message.text else 'skip'}")
    
    if message.text and len(message.text.strip()) > 0:
        await state.update_data(additional_info=message.text.strip())
        logger.info(f"[ADDITIONAL] Additional info saved: {message.text[:50]}")
    else:
        await state.update_data(additional_info=None)
    await _show_review(message, state)


async def _show_review(message: Message, state: FSMContext):
    data = await state.get_data()
    specialist_name = data.get("specialist_name", "Не выбран")
    date_str = data.get("selected_date", "")
    time_str = data.get("selected_time", "")
    name = data.get("user_name", "")
    phone = data.get("user_phone", "")
    additional = data.get("additional_info")

    logger.info(f"[REVIEW] Showing review for user {message.from_user.id}: {specialist_name} on {date_str} {time_str}")

    review_text = (
        "📋 Проверьте данные записи:\n\n"
        f"👨‍⚕️ Специалист: {specialist_name}\n"
        f"📅 Дата: {get_datetime_display(date_str, time_str)}\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {phone}"
    )
    if additional:
        review_text += f"\n\n💬 Сообщение специалисту: {additional}"

    review_text += "\n\nНажмите «Подтвердить» для завершения записи."

    await message.answer(review_text, reply_markup=build_review_keyboard())
    await state.set_state(BookingFSM.AWAITING_REVIEW)


@router.message(BookingFSM.AWAITING_ADDITIONAL, F.text == "← Вернуться к выбору")
async def handle_back_from_additional(message: Message, state: FSMContext):
    logger.info(f"[BACK] User {message.from_user.id} went back from additional question")
    from handlers.user.contacts import _proceed_to_additional
    from keyboards.inline import build_phone_keyboard
    kb = build_phone_keyboard()
    await message.answer(
        "Введите номер телефона:",
        reply_markup=kb,
    )
