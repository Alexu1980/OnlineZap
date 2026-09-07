import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config.settings import settings
from database.repositories import save_consent, get_active_specialists
from keyboards.inline import build_welcome_keyboard, build_consent_keyboard, build_specialist_keyboard

logger = logging.getLogger(__name__)
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
    "📱 Доступные команды:\n"
    "/start - главное меню\n"
    "/lk_user - мои записи\n"
    "/help - помощь\n"
    "/invite - пригласить друга\n\n"
    "Для записи нажмите кнопку ниже:"
)

HELP_MESSAGE = (
    "📖 <b>Помощь по использованию бота</b>\n\n"
    "<b>🔹 Основные команды:</b>\n\n"
    "/start — главное меню бота\n"
    "/lk_user — просмотр моих записей\n"
    "/help — эта справка\n"
    "/invite — пригласить друга\n\n"
    "<b>📋 Личный кабинет (/lk_user):</b>\n\n"
    "• Просмотр всех активных записей\n"
    "• История завершённых и отменённых записей\n"
    "• Перенос консультации — нажмите кнопку «🔄 Перенести»\n"
    "• Отмена консультации — нажмите кнопку «❌ Отменить»\n\n"
    "<b>📅 Запись на консультацию:</b>\n\n"
    "1. Нажмите «📝 Записаться»\n"
    "2. Согласитесь на обработку данных\n"
    "3. Выберите специалиста\n"
    "4. Выберите дату и время\n"
    "5. Введите имя и телефон\n"
    "6. Подтвердите запись\n\n"
    "<b>⚠️ Важно:</b>\n\n"
    "• Для переноса записи выберите её в личном кабинете\n"
    "• Отменить запись можно не позднее чем за 24 часа до консультации\n"
    "• Если вы не можете прийти — обязательно отмените запись\n\n"
    "Если у вас возникли вопросы, напишите в нашу техподдержку:\n"
    "👨‍💻 <a href=\"https://t.me/your_support_bot\">Написать в техподдержку</a>"
)

INVITE_MESSAGE = (
    "🎁 <b>Пригласите друга!</b>\n\n"
    "Поделитесь этим ботом с друзьями и получите скидку 10% на следующую консультацию.\n\n"
    "<b>Как это работает:</b>\n\n"
    "1. Нажмите кнопку ниже, чтобы поделиться ботом\n"
    "2. Ваш друг записывается на первую консультацию\n"
    "3. Вы получаете скидку 10% на следующую консультацию\n\n"
    "Чем больше друзей пригласите — тем больше скидка!\n\n"
    "Максимальная скидка: 30%"
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
    logger.info(f"[START] User {message.from_user.id} ({message.from_user.username}) executed /start")
    await state.clear()
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=build_welcome_keyboard(),
    )
    logger.info(f"[START] Welcome message sent to {message.from_user.id}")


@router.message(Command("lk_user"))
async def cmd_lk_user(message: Message):
    """Личный кабинет пользователя - просмотр записей."""
    logger.info(f"[LK_USER] User {message.from_user.id} executed /lk_user")
    
    from keyboards.inline import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📋 Открыть личные записи",
        callback_data="personal_cabinet",
    )
    builder.button(
        text="← Назад",
        callback_data="start_menu",
    )
    builder.adjust(1, 1)
    
    await message.answer(
        "📋 <b>Личный кабинет</b>\n\n"
        "Здесь вы можете просмотреть все свои записи:\n\n"
        "• Активные записи — upcoming консультации\n"
        "• История — завершённые и отменённые записи\n"
        "• Управление — перенос и отмена записей\n\n"
        "Нажмите на кнопку ниже, чтобы открыть список записей:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    logger.info(f"[LK_USER] LK menu sent to user {message.from_user.id}")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь по использованию бота."""
    logger.info(f"[HELP] User {message.from_user.id} executed /help")
    
    await message.answer(
        HELP_MESSAGE,
        parse_mode="HTML",
    )
    logger.info(f"[HELP] Help message sent to user {message.from_user.id}")


@router.message(Command("invite"))
async def cmd_invite(message: Message):
    """Пригласить друга."""
    logger.info(f"[INVITE] User {message.from_user.id} executed /invite")
    
    from keyboards.inline import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📤 Поделиться ботом",
        url=f"https://t.me/share/url?url=https://t.me/{(await message.bot.get_me()).username}&text={INVITE_MESSAGE.replace(chr(10), ' ')}",
    )
    builder.button(
        text="📋 Скопировать ссылку",
        url=f"https://t.me/{(await message.bot.get_me()).username}",
    )
    builder.button(
        text="← Назад",
        callback_data="start_menu",
    )
    builder.adjust(1, 1, 1)
    
    await message.answer(
        INVITE_MESSAGE,
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    logger.info(f"[INVITE] Invite message sent to user {message.from_user.id}")


@router.callback_query(lambda c: c.data == "start_booking")
async def cb_start_booking(callback: CallbackQuery, state: FSMContext):
    logger.info(f"[START_BOOKING] User {callback.from_user.id} clicked 'Записаться'")
    await state.set_state(BookingFSM.AWAITING_CONSENT)
    await callback.message.answer(
        "📋 Для записи необходимо ваше согласие на обработку персональных данных.\n\n"
        "Мы собираем минимальный набор данных: имя, номер телефона и информацию о вашей "
        "записи на консультацию.\n\n"
        "Все данные защищены и используются только для организации консультаций.",
        reply_markup=build_consent_keyboard(),
    )
    await callback.answer()
    logger.info(f"[START_BOOKING] Consent screen shown to {callback.from_user.id}")


@router.callback_query(lambda c: c.data == "show_policy")
async def cb_show_policy(callback: CallbackQuery):
    logger.info(f"[SHOW_POLICY] User {callback.from_user.id} requested privacy policy")
    await callback.message.answer(
        POLICY_TEXT,
        reply_markup=build_consent_keyboard(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "consent_given")
async def cb_consent_given(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[CONSENT] User {callback.from_user.id} gave consent")
    user_id = callback.from_user.id
    await save_consent(db_session, user_id)

    await state.set_state(BookingFSM.AWAITING_SPECIALIST)

    specialists = await get_active_specialists(db_session)
    if not specialists:
        logger.warning(f"[CONSENT] No specialists available for user {user_id}")
        await callback.message.answer(
            "Специалисты временно недоступны. Пожалуйста, свяжитесь с менеджером."
        )
        await state.clear()
        return

    logger.info(f"[CONSENT] Showing {len(specialists)} specialists to user {user_id}")
    keyboard = await build_specialist_keyboard(specialists)
    await callback.message.answer(
        "👨‍⚕️ Выберите специалиста:\n\n"
        "Если вы не уверены, кого выбрать — нажмите кнопку ниже, "
        "и мы поможем подобрать подходящего специалиста.",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "start_menu")
async def cb_start_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    logger.info(f"[START_MENU] User {callback.from_user.id} returned to start menu")
    await callback.message.answer(
        WELCOME_MESSAGE,
        reply_markup=build_welcome_keyboard(),
    )
    await callback.answer()
