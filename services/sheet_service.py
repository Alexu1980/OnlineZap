import logging
import os

import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetService:
    """Сервис для работы с Google Sheets."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        self._credentials_path = settings.google_sheets_credentials_path
        self._sheet_id = settings.google_sheet_id
        self._sheet_name = settings.google_sheet_name

    def _authorize(self):
        """Авторизация в Google Sheets через Service Account."""
        if not os.path.exists(self._credentials_path):
            logger.warning(
                "Файл credentials не найден: %s. Google Sheets будет отключён.",
                self._credentials_path,
            )
            return False

        try:
            # Загружаем credentials
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=SCOPES
            )
            
            # Подключаемся через client
            self._client = gspread.Client(credentials=creds, scope=SCOPES)
            self._client.authorize()
            
            # Открываем таблицу
            self._spreadsheet = self._client.open_by_key(self._sheet_id)
            self._worksheet = self._spreadsheet.worksheet(self._sheet_name)
            
            logger.info("Google Sheets авторизация успешна")
            return True
            
        except Exception as e:
            logger.error("Ошибка авторизации Google Sheets: %s", e, exc_info=True)
            return False

    def _ensure_initialized(self):
        """Инициализация при необходимости."""
        if self._worksheet is None:
            if not self._authorize():
                return False
            self._initialize_sheet()
        return True

    def _initialize_sheet(self):
        """Создание листа и заголовков если нужно."""
        headers = [
            "ID",
            "Дата создания",
            "Имя",
            "Телефон",
            "Username",
            "Telegram ID",
            "Специалист",
            "Дата консультации",
            "Время",
            "Статус",
            "Комментарий",
        ]
        try:
            existing = self._worksheet.get_all_values()
            if not existing:
                self._worksheet.update([headers], "A1")
                logger.info("Google Sheets инициализирован с заголовками")
        except Exception as e:
            logger.error("Ошибка инициализации листа: %s", e)

    async def append_booking(self, booking: dict) -> int:
        """Добавление записи в Google Sheets. Возвращает номер строки."""
        if not self._ensure_initialized():
            logger.warning("Google Sheets недоступен. Запись не сохранена в таблицу.")
            return -1

        try:
            row = [
                booking.get("id", ""),
                booking.get("created_at", ""),
                booking.get("user_name", ""),
                booking.get("user_phone", ""),
                booking.get("user_username", ""),
                booking.get("user_telegram_id", ""),
                booking.get("specialist_name", ""),
                booking.get("consultation_date", ""),
                booking.get("consultation_time", ""),
                booking.get("status", ""),
                booking.get("manager_comment", ""),
            ]
            result = self._worksheet.append_row(row)
            logger.info(f"Запись #{booking.get('id')} добавлена в Google Sheets")
            return result.get('rowCount', -1)
        except Exception as e:
            logger.error("Ошибка добавления в Google Sheets: %s", e, exc_info=True)
            return -1

    def update_booking_status(self, row_number: int, status: str) -> bool:
        """Обновление статуса записи в Google Sheets."""
        if not self._ensure_initialized():
            return False

        try:
            self._worksheet.update_cell(row_number, 10, status)
            return True
        except Exception as e:
            logger.error("Ошибка обновления статуса в Google Sheets: %s", e)
            return False

    def update_booking_comment(self, row_number: int, comment: str) -> bool:
        """Обновление комментария менеджера в Google Sheets."""
        if not self._ensure_initialized():
            return False

        try:
            self._worksheet.update_cell(row_number, 11, comment)
            return True
        except Exception as e:
            logger.error("Ошибка обновления комментария: %s", e)
            return False

    @classmethod
    def clear_instance(cls):
        """Очистка синглтона (для тестирования)."""
        if cls._instance:
            cls._instance._worksheet = None
            cls._instance._spreadsheet = None
            cls._instance._client = None
