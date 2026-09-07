import logging
import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton, ReplyKeyboardRemove

from handlers.user.start import BookingFSM
from keyboards.inline import build_phone_keyboard, build_review_keyboard
from utils.helpers import get_datetime_display

logger = logging.getLogger(__name__)
router = Router()


@router.message(BookingFSM.AWAITING_NAME)
async def handle_name(message: Message, state: FSMContext):
    logger.info(f"[NAME] User {message.from_user.id} entered name: {message.text[:30]}")
    if message.text and len(message.text.strip()) >= 2:
        await state.update_data(user_name=message.text.strip())
        await state.set_state(BookingFSM.AWAITING_PHONE)

        kb = build_phone_keyboard()
        await message.answer(
            "Спасибо! Теперь введите номер телефона:\n\n"
            "Вы можете поделиться номером одним нажатием или ввести вручную.",
            reply_markup=kb,
        )
    else:
        await message.answer(
            "Имя должно содержать минимум 2 символа. Пожалуйста, введите ваше имя:"
        )


@router.message(BookingFSM.AWAITING_PHONE, F.contact | (F.text == "📱 Поделиться номером"))
async def handle_phone_shared(message: Message, state: FSMContext):
    logger.info(f"[PHONE] User {message.from_user.id} shared contact")
    if message.contact:
        phone = "+" + str(message.contact.phone_number)
        logger.info(f"[PHONE] Contact received: {phone}")
        await state.update_data(user_phone=phone)
        await _proceed_to_additional(message, state)
    else:
        await message.answer("Номер телефона не получен. Попробуйте ещё раз.")


@router.message(BookingFSM.AWAITING_PHONE, F.text == "✏️ Ввести вручную")
async def handle_manual_phone_prompt(message: Message, state: FSMContext):
    logger.info(f"[PHONE] User {message.from_user.id} chose manual input")
    await message.answer(
        "Введите номер телефона (например: +79644203553):",
        reply_markup=ReplyKeyboardRemove(resize_keyboard=True),
    )


@router.message(BookingFSM.AWAITING_PHONE)
async def handle_phone_manual(message: Message, state: FSMContext):
    text = message.text or ""
    logger.info(f"[PHONE] User {message.from_user.id} entered phone: {text[:30]}")
    
    # Убрать все кроме цифр и+
    phone = re.sub(r"[^\d+]", "", text.strip())
    logger.info(f"[PHONE] Cleaned phone: {phone}")
    
    # Нормализация: если начинается с 8, заменить на +7
    if phone.startswith("8") and len(phone) == 11:
        phone = "+7" + phone[1:]
        logger.info(f"[PHONE] Converted 8 to +7: {phone}")
    
    # Если нет + в начале, добавить
    if not phone.startswith("+") and phone.startswith("7"):
        phone = "+" + phone
        logger.info(f"[PHONE] Added + prefix: {phone}")
    
    # Проверка длины (минимум 11 символов для +7XXXXXXXXXX)
    phone_digits = re.sub(r"[^\d]", "", phone)
    if len(phone_digits) >= 11 and (phone.startswith("+") or phone.startswith("7")):
        # Гарантируем формат +7XXXXXXXXXX
        if not phone.startswith("+"):
            phone = "+" + phone
        logger.info(f"[PHONE] Valid phone: {phone}")
        await state.update_data(user_phone=phone)
        # Скрываем клавиатуру после успешного ввода
        await message.answer(
            "✓ Номер принят!",
            reply_markup=ReplyKeyboardRemove(),
        )
        await _proceed_to_additional(message, state)
    else:
        logger.warning(f"[PHONE] Invalid phone format: {phone} (digits: {phone_digits}, len: {len(phone_digits)})")
        await message.answer(
            "Номер введён некорректно. Введите номер в формате +7XXXXXXXXXX\n"
            "Примеры: +79644203553 или 89644203553"
        )


@router.message(BookingFSM.AWAITING_NAME, F.text == "← Вернуться к выбору")
@router.message(BookingFSM.AWAITING_PHONE, F.text == "← Вернуться к выбору")
async def handle_back_from_contacts(message: Message, state: FSMContext):
    logger.info(f"[BACK] User {message.from_user.id} went back from contacts")
    from handlers.user.scheduling import get_available_dates
    from keyboards.inline import build_date_keyboard

    specialist_id = (await state.get_data()).get("specialist_id")
    dates = await get_available_dates(specialist_id)
    keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")
    await message.answer(
        "📅 Выберите дату консультации:",
        reply_markup=keyboard,
    )
    await state.set_state(BookingFSM.AWAITING_DATE)


async def _proceed_to_additional(message: Message, state: FSMContext):
    logger.info(f"[PHONE] Proceeding to additional question for user {message.from_user.id}")
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Пропустить"))
    skip_kb = builder.as_markup(resize_keyboard=True)
    await state.set_state(BookingFSM.AWAITING_ADDITIONAL)
    await message.answer(
        "📝 Необязательный вопрос:\n\n"
        "Есть ли что-то, что вы хотели бы сообщить специалисту "
        "перед консультацией?\n\n"
        "Вы можете написать или нажать «Пропустить».",
        reply_markup=skip_kb,
    )
