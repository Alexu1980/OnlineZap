import logging
from aiogram import Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.repositories import get_active_specialists, get_bookings_by_user
from keyboards.inline import build_specialist_keyboard
from handlers.user.start import BookingFSM

logger = logging.getLogger(__name__)
router = Router()


async def _get_available_dates(specialist_id: int) -> list:
    """Возвращает список доступных дат."""
    from handlers.user.scheduling import get_available_dates
    return await get_available_dates(specialist_id)


@router.callback_query(lambda c: c.data.startswith("spec_") and c.data != "spec_help")
async def cb_select_specialist(callback: CallbackQuery, state: FSMContext, db_session):
    from database.repositories import get_specialist_by_id
    specialist_id = int(callback.data.split("_")[1])
    logger.info(f"[SPECIALIST] User {callback.from_user.id} selected specialist #{specialist_id}")

    specialist = await get_specialist_by_id(db_session, specialist_id)
    await state.update_data(
        specialist_id=specialist_id,
        specialist_name=specialist.name if specialist else "Неизвестно",
    )
    
    # Проверяем, есть ли у пользователя предыдущие записи
    user_bookings = await get_bookings_by_user(db_session, callback.from_user.id)
    
    if user_bookings:
        # Берём последнюю запись для получения имени и телефона
        last_booking = user_bookings[-1]
        await state.update_data(
            user_name=last_booking.user_name,
            user_phone=last_booking.user_phone,
        )
        
        # Показываем сообщение с предзаполненными данными
        kb = InlineKeyboardBuilder()
        kb.button(
            text="✏️ Изменить персональные данные",
            callback_data="edit_personal_data",
        )
        kb.button(
            text="✅ Использовать текущие данные",
            callback_data="use_saved_data",
        )
        kb.adjust(1, 1)
        
        await callback.message.answer(
            f"👨‍⚕️ Вы выбрали специалиста: {specialist.name}\n\n"
            f"👤 Имя: {last_booking.user_name}\n"
            f"📱 Телефон: {last_booking.user_phone}\n\n"
            f"Если данные изменились, нажмите кнопку ниже:",
            reply_markup=kb.as_markup(),
        )
    else:
        # Новый пользователь — показываем выбор даты
        dates = await _get_available_dates(specialist_id)
        if not dates:
            logger.warning(f"[SPECIALIST] No available dates for specialist {specialist_id}, user {callback.from_user.id}")
            await callback.message.answer(
                "К сожалению, в ближайшее время нет доступных дат. "
                "Пожалуйста, попробуйте позже или выберите другого специалиста."
            )
            await state.clear()
            return

        keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")
        await callback.message.answer(
            "📅 Выберите дату консультации:",
            reply_markup=keyboard,
        )
    
    await callback.answer()
    await state.set_state(BookingFSM.AWAITING_DATE)
    logger.info(f"[SPECIALIST] Saved state data for user {callback.from_user.id}")


@router.callback_query(lambda c: c.data == "spec_help")
async def cb_spec_help(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[SPECIALIST_HELP] User {callback.from_user.id} requested help choosing specialist")
    specialists = await get_active_specialists(db_session)
    if not specialists:
        await callback.message.answer("Специалисты временно недоступны.")
        await state.clear()
        return

    spec = specialists[0]
    await state.update_data(specialist_id=spec.id, specialist_name=spec.name)
    await state.set_state(BookingFSM.AWAITING_DATE)

    from handlers.user.scheduling import get_available_dates
    dates = await get_available_dates(spec.id)

    if not dates:
        await callback.message.answer("В ближайшее время нет доступных дат. Попробуйте позже.")
        await state.clear()
        return

    from keyboards.inline import build_date_keyboard
    keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")

    await callback.message.answer(
        f"🤝 Я рекомендую вам специалиста: {spec.name} — {spec.specialization}\n\n"
        "Теперь выберите дату консультации:",
        reply_markup=keyboard,
    )
    await callback.answer()
    logger.info(f"[SPECIALIST_HELP] Recommended {spec.name} to user {callback.from_user.id}")


@router.callback_query(lambda c: c.data == "back_to_specialist")
async def cb_back_to_specialist(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[BACK] User {callback.from_user.id} went back to specialist selection")
    specialists = await get_active_specialists(db_session)
    keyboard = await build_specialist_keyboard(specialists)
    await callback.message.answer(
        "👨‍⚕️ Выберите специалиста:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "edit_personal_data")
async def cb_edit_personal_data(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[EDIT_DATA] User {callback.from_user.id} requested to edit personal data")
    await state.set_state(BookingFSM.AWAITING_NAME)
    await callback.message.answer(
        "✏️ Введите ваше имя:",
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "use_saved_data")
async def cb_use_saved_data(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[USE_SAVED] User {callback.from_user.id} using saved personal data")
    data = await state.get_data()
    specialist_id = data.get("specialist_id")
    
    if not specialist_id:
        await callback.answer("Ошибка. Начните заново: /start")
        return
    
    dates = await _get_available_dates(specialist_id)
    if not dates:
        await callback.message.answer("На эту дату нет доступных слотов.")
        return
    
    keyboard = build_date_keyboard(dates, back_callback="back_to_specialist")
    await callback.message.edit_text(
        text="📅 Выберите дату консультации:",
        reply_markup=keyboard,
    )
    await callback.answer()
