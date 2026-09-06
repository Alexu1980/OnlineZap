from datetime import datetime

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from database.repositories import get_active_specialists


# ==================== Welcome ====================

def build_welcome_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Записаться на консультацию", callback_data="start_booking"))
    builder.adjust(1)
    return builder.inline_keyboard


# ==================== Consent ====================

def build_consent_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Согласен(а)", callback_data="consent_given"),
    )
    builder.row(
        InlineKeyboardButton(text="📄 Политика конфиденциальности", callback_data="show_policy"),
    )
    builder.adjust(1, 1)
    return builder.inline_keyboard


# ==================== Specialist ====================

async def build_specialist_keyboard(specialists: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for spec in specialists:
        builder.button(
            text=f"👨‍⚕️ {spec.name}",
            callback_data=f"spec_{spec.id}",
        )
    builder.button(
        text="🤔 Не знаю, помогите выбрать",
        callback_data="spec_help",
    )
    builder.adjust(1)
    return builder.inline_keyboard


# ==================== Date ====================

def build_date_keyboard(dates: list[str], back_callback: str = "back") -> InlineKeyboardMarkup:
    """
    dates — список дат в формате YYYY-MM-DD
    """
    builder = InlineKeyboardBuilder()
    for date_str in dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            display = dt.strftime("%d.%m")
        except ValueError:
            display = date_str
        builder.button(
            text=display,
            callback_data=f"date_{date_str}",
        )
    if back_callback:
        builder.row(InlineKeyboardButton(text="← Назад", callback_data=back_callback))
    builder.adjust(3, 3)
    return builder.inline_keyboard


# ==================== Time ====================

def build_time_keyboard(slots: list[dict], back_callback: str = "back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(
            text=slot["time"],
            callback_data=f"time_{slot['slot_key']}",
        )
    if back_callback:
        builder.row(InlineKeyboardButton(text="← Назад", callback_data=back_callback))
    builder.adjust(4, 4)
    return builder.inline_keyboard


# ==================== Contacts ====================

def build_phone_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📱 Поделиться номером", request_contact=True),
    )
    builder.row(
        KeyboardButton(text="✏️ Ввести вручную"),
    )
    builder.adjust(1)
    return builder.keyboard


def build_manual_phone_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="← Вернуться к выбору"),
    )
    builder.adjust(1)
    return builder.keyboard


# ==================== Review ====================

def build_review_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm_booking")
    builder.button(text="✏️ Изменить данные", callback_data="edit_booking")
    builder.adjust(1, 1)
    return builder.inline_keyboard


# ==================== Booking Actions ====================

def build_booking_action_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Перенести",
        callback_data=f"reschedule_{booking_id}",
    )
    builder.button(
        text="❌ Отменить",
        callback_data=f"cancel_{booking_id}",
    )
    builder.adjust(1, 1)
    return builder.inline_keyboard


# ==================== Confirm Cancel ====================

def build_confirm_cancel_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, отменить", callback_data=f"confirm_cancel_{booking_id}")
    builder.button(text="Отмена", callback_data=f"cancel_action_{booking_id}")
    builder.adjust(1, 1)
    return builder.inline_keyboard


# ==================== Reschedule ====================

def build_reschedule_back_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="← Назад к записям", callback_data=f"my_bookings_{booking_id}")
    return builder.inline_keyboard
