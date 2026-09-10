import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.settings import settings
from database.repositories import (
    save_consent, 
    get_active_specialists, 
    get_user_consent,
    revoke_consent,
)
from keyboards.inline import (
    build_welcome_keyboard, 
    build_consent_keyboard, 
    build_consent_confirmed_keyboard,
    build_consent_revoked_keyboard,
    build_specialist_keyboard,
)

logger = logging.getLogger(__name__)
router = Router()

# FSM States
from aiogram.fsm.state import State, StatesGroup


class BookingFSM(StatesGroup):
    AWAITING_CONSENT = State()
    CONSENT_GIVEN = State()  # Новое состояние после согласия
    AWAITING_SPECIALIST = State()
    AWAITING_DATE = State()
    AWAITING_TIME = State()
    AWAITING_NAME = State()
    AWAITING_PHONE = State()
    AWAITING_ADDITIONAL = State()
    AWAITING_REVIEW = State()


class ConsentFSM(StatesGroup):
    AWAITING_CONSENT_DECISION = State()  # Ожидание решения по согласию


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
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    # Получаем username бота
    bot_username = (await message.bot.get_me()).username
    bot_url = f"https://t.me/{bot_username}"
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📤 Поделиться ботом",
        url=f"https://t.me/share/url?url={bot_url}&text=Привет! Запишись на психологическую консультацию через этого бота:",
    )
    builder.button(
        text="🔗 Открыть бота",
        url=bot_url,
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


async def _show_specialist_selection(callback: CallbackQuery, state: FSMContext, db_session):
    """Показ выбора специалиста."""
    from database.repositories import get_active_specialists
    from keyboards.inline import build_specialist_keyboard
    from handlers.user.start import BookingFSM
    
    specialists = await get_active_specialists(db_session)
    if not specialists:
        logger.warning(f"[SPECIALIST] No specialists available for user {callback.from_user.id}")
        await callback.message.answer(
            "Специалисты временно недоступны. Пожалуйста, свяжитесь с менеджером."
        )
        await state.clear()
        return

    logger.info(f"[SPECIALIST] Showing {len(specialists)} specialists to user {callback.from_user.id}")
    keyboard = await build_specialist_keyboard(specialists)
    await callback.message.answer(
        "👨‍⚕️ Выберите специалиста:\n\n"
        "Если вы не уверены, кого выбрать — нажмите кнопку ниже, "
        "и мы поможем подобрать подходящего специалиста.",
        reply_markup=keyboard,
    )
    await state.set_state(BookingFSM.AWAITING_SPECIALIST)
    await callback.answer()


@router.callback_query(lambda c: c.data == "start_booking")
async def cb_start_booking(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[START_BOOKING] User {callback.from_user.id} clicked 'Записаться'")
    
    # Проверяем, давал ли пользователь уже согласие
    user_has_consent = await get_user_consent(db_session, callback.from_user.id)
    
    if user_has_consent:
        logger.info(f"[START_BOOKING] User {callback.from_user.id} already gave consent, showing specialist selection")
        # Показываем сообщение о том что согласие получено и кнопку записи
        await callback.message.answer(
            "📋 Ваше согласие на обработку персональных данных уже получено.\n\n"
            "Вы можете отозвать согласие нажав соответствующую кнопку.\n\n"
            "Для записи к специалисту нажмите кнопку ниже:",
            reply_markup=build_consent_keyboard(has_consent=True),
        )
    else:
        logger.info(f"[START_BOOKING] User {callback.from_user.id} needs to give consent")
        await state.set_state(ConsentFSM.AWAITING_CONSENT_DECISION)
        await callback.message.answer(
            "📋 Для записи необходимо ваше согласие на обработку персональных данных.\n\n"
            "Мы собираем минимальный набор данных: имя, номер телефона и информацию о вашей "
            "записи на консультацию.\n\n"
            "Все данные защищены и используются только для организации консультаций.",
            reply_markup=build_consent_keyboard(has_consent=False),
        )
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
    logger.info(f"[CONSENT] User {callback.from_user.id} clicked 'Согласен(а)'")
    user_id = callback.from_user.id
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    logger.info(f"[CONSENT] Current state: {current_state}")
    
    await save_consent(db_session, user_id)
    logger.info(f"[CONSENT] Consent saved for user {user_id}")

    # Редактируем текущее сообщение и показываем кнопку подтверждения
    try:
        await callback.message.edit_text(
            text="✅ Спасибо! Ваше согласие получено.\n\nТеперь вы можете записаться на консультацию.",
            reply_markup=build_consent_confirmed_keyboard(),
        )
        logger.info(f"[CONSENT] Message edited for user {user_id}")
    except Exception as e:
        logger.error(f"[CONSENT] Error editing message: {e}")
        await callback.answer()
        return
    
    # Сбрасываем состояние чтобы избежать повторных вызовов
    await state.clear()
    await callback.answer()
    logger.info(f"[CONSENT] State cleared for user {user_id}")


@router.callback_query(lambda c: c.data == "consent_confirmed")
async def cb_consent_confirmed(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[CONSENT_CONFIRMED] User {callback.from_user.id} clicked 'Согласие получено'")
    
    # Проверяем, есть ли согласие (на всякий случай)
    user_has_consent = await get_user_consent(db_session, callback.from_user.id)
    
    if not user_has_consent:
        logger.warning(f"[CONSENT_CONFIRMED] User {callback.from_user.id} has no consent")
        await callback.answer(
            "Необходимо дать согласие на обработку персональных данных. "
            "Без этого записаться не получится.",
            show_alert=True,
        )
        return
    
    # Согласие есть - показываем выбор специалиста, редактируя текущее сообщение
    try:
        specialists = await get_active_specialists(db_session)
        if not specialists:
            logger.warning(f"[CONSENT_CONFIRMED] No specialists available for user {callback.from_user.id}")
            await callback.message.edit_text(
                text="Специалисты временно недоступны. Пожалуйста, свяжитесь с менеджером.",
            )
            return
        
        keyboard = await build_specialist_keyboard(specialists)
        await callback.message.edit_text(
            text="👨‍⚕️ Выберите специалиста:\n\n"
            "Если вы не уверены, кого выбрать — нажмите кнопку ниже, "
            "и мы поможем подобрать подходящего специалиста.",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"[CONSENT_CONFIRMED] Error editing message: {e}")
        await callback.answer()
        return
    await callback.answer()
    await state.clear()


@router.callback_query(lambda c: c.data == "go_to_specialist")
async def cb_go_to_specialist(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[GO_TO_SPECIALIST] User {callback.from_user.id} clicked 'Выбор специалиста'")
    
    # Проверяем, есть ли согласие
    user_has_consent = await get_user_consent(db_session, callback.from_user.id)
    
    if not user_has_consent:
        logger.warning(f"[GO_TO_SPECIALIST] User {callback.from_user.id} has no consent")
        await callback.answer(
            "Необходимо дать согласие на обработку персональных данных. "
            "Без этого записаться не получится.",
            show_alert=True,
        )
        return
    
    # Согласие есть - показываем выбор специалиста
    try:
        specialists = await get_active_specialists(db_session)
        if not specialists:
            logger.warning(f"[GO_TO_SPECIALIST] No specialists available for user {callback.from_user.id}")
            await callback.message.edit_text(
                text="Специалисты временно недоступны. Пожалуйста, свяжитесь с менеджером.",
            )
            return
        
        keyboard = await build_specialist_keyboard(specialists)
        await callback.message.edit_text(
            text="👨‍⚕️ Выберите специалиста:\n\n"
            "Если вы не уверены, кого выбрать — нажмите кнопку ниже, "
            "и мы поможем подобрать подходящего специалиста.",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"[GO_TO_SPECIALIST] Error editing message: {e}")
        await callback.answer()
        return
    await callback.answer()
    await state.clear()


@router.callback_query(lambda c: c.data == "consent_revoked")
async def cb_consent_revoked(callback: CallbackQuery, state: FSMContext, db_session):
    logger.info(f"[CONSENT_REVOKED] User {callback.from_user.id} revoked consent")
    user_id = callback.from_user.id
    
    # Удаляем запись о согласии из БД
    from database.repositories import revoke_consent
    await revoke_consent(db_session, user_id)
    
    # Редактируем сообщение и возвращаем кнопку согласия (без перехода к специалисту)
    try:
        await callback.message.edit_text(
            text="⚠️ Ваше согласие на обработку персональных данных отозвано.\n\n"
            "Для продолжения записи, пожалуйста, дайте согласие заново.",
            reply_markup=build_consent_revoked_keyboard(),
        )
    except Exception as e:
        logger.error(f"[CONSENT_REVOKED] Error editing message: {e}")
        await callback.answer()
        return
    await callback.answer()
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
