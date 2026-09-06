from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config.settings import settings
from database.repositories import save_consent, has_consent, get_active_specialists
from keyboards.inline import build_welcome_keyboard, build_consent_keyboard, build_specialist_keyboard

router = Router()

# FSM States
from aiogram.fsm.state import State, StatesGroup


class BookingFSM(StatesGroup):
    AWAITING_CONSENT = State()
    AWAITING_SPECIALIST = State()
    AWAITING_DATE = State()
    AWAITING_TIME = State()
    AWAITING_NAME = State()
    AWAITING_PHONE = State()
    AWAITING_ADDITIONAL = State()
    AWAITING_REVIEW = State()


WELCOME_MESSAGE = (
    "👋 Добро пожаловать! Я бот для записи на психологическую консультацию.\n\n"
    "📌 Формат консультации:\n"
    "• Длительность: 60 минут\n"
    "• Онлайн в удобном для вас формате\n"
    "• Конфиденциальность гарантирована\n\n"
    "Для записи нажмите кнопку ниже:"
)

POLICY_TEXT = (
    "📄 Политика конфиденциальности\n\n"
    "Мы собираем и обрабатываем ваши персональные данные в следующих целях:\n\n"
    "1. Для записи на консультацию (имя, номер телефона, Telegram ID)\n"
    "2. Для отправки напоминаний о консультации\n"
    "3. Для улучшения качества услуг\n\n"
    "Ваши данные не будут переданы третьим лицам, за исключением случаев, "
    "предусмотренных законодательством РФ.\n\n"
    "Обработка данных осуществляется в соответствии с Федеральным законом "
    "№ 152-ФЗ «О персональных данных».\n\n"
    "Нажимая «Согласен(а)», вы подтверждаете своё согласие на обработку данных."
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=build_welcome_keyboard(),
    )


@router.callback_query(lambda c: c.data == "start_booking")
async def cb_start_booking(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingFSM.AWAITING_CONSENT)
    await callback.message.answer(
        "📋 Для записи необходимо ваше согласие на обработку персональных данных.\n\n"
        "Мы собираем минимальный набор данных: имя, номер телефона и информацию о вашей "
        "записи на консультацию.\n\n"
        "Все данные защищены и используются только для организации консультаций.",
        reply_markup=build_consent_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "show_policy")
async def cb_show_policy(callback: CallbackQuery):
    await callback.message.answer(
        POLICY_TEXT,
        reply_markup=build_consent_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "consent_given")
async def cb_consent_given(callback: CallbackQuery, state: FSMContext, db_session):
    from database.repositories import save_consent
    user_id = callback.from_user.id
    await save_consent(db_session, user_id)

    await state.set_state(BookingFSM.AWAITING_SPECIALIST)

    specialists = await get_active_specialists(db_session)
    if not specialists:
        await callback.message.answer(
            "Специалисты временно недоступны. Пожалуйста, свяжитесь с менеджером."
        )
        await state.clear()
        return

    keyboard = await build_specialist_keyboard(specialists)
    await callback.message.answer(
        "👨‍⚕️ Выберите специалиста:\n\n"
        "Если вы не уверены, кого выбрать — нажмите кнопку ниже, "
        "и мы поможем подобрать подходящего специалиста.",
        reply_markup=keyboard,
    )
    await callback.answer()
