from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from handlers.user.start import BookingFSM
from keyboards.inline import build_phone_keyboard, build_review_keyboard
from utils.helpers import get_datetime_display

router = Router()


@router.message(BookingFSM.AWAITING_NAME)
async def handle_name(message: Message, state: FSMContext):
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


@router.message(BookingFSM.AWAITING_PHONE, F.text == "📱 Поделиться номером")
async def handle_phone_shared(message: Message, state: FSMContext):
    if message.contact:
        phone = "+" + str(message.contact.phone_number)
        await state.update_data(user_phone=phone)
        await _proceed_to_additional(message, state)
    else:
        await message.answer("Номер телефона не получен. Попробуйте ещё раз.")


@router.message(BookingFSM.AWAITING_PHONE, F.text == "✏️ Ввести вручную")
async def handle_manual_phone_prompt(message: Message, state: FSMContext):
    await message.answer(
        "Введите ваш номер телефона в формате +7XXXXXXXXXX:",
    )


@router.message(BookingFSM.AWAITING_PHONE)
async def handle_phone_manual(message: Message, state: FSMContext):
    import re
    phone = re.sub(r"[^\d+]", "", message.text.strip())
    if len(phone) >= 10 and (phone.startswith("+") or phone.startswith("7")):
        await state.update_data(user_phone=phone)
        await _proceed_to_additional(message, state)
    else:
        await message.answer(
            "Номер введён некорректно. Введите номер в формате +7XXXXXXXXXX:"
        )


@router.message(BookingFSM.AWAITING_NAME, F.text == "← Вернуться к выбору")
@router.message(BookingFSM.AWAITING_PHONE, F.text == "← Вернуться к выбору")
async def handle_back_from_contacts(message: Message, state: FSMContext):
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
    skip_kb = ReplyKeyboardMarkup(
        keyboards=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True,
    )
    await state.set_state(BookingFSM.AWAITING_ADDITIONAL)
    await message.answer(
        "📝 Необязательный вопрос:\n\n"
        "Есть ли что-то, что вы хотели бы сообщить специалисту "
        "перед консультацией?\n\n"
        "Вы можете написать или нажать «Пропустить».",
        reply_markup=skip_kb,
    )
