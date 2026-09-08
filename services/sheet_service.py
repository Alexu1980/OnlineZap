import logging
import os
import time
from functools import wraps

import gspread
from gspread.exceptions import APIError
from google.oauth2.service_account import Credentials

from config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Retry configuration for Google API
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Декоратор для повторения попыток при ошибке Google API."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (gspread.exceptions.APIError, Exception) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Попытка {attempt + 1} failed for {func.__name__}: {e}. Retry in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
                        raise
        return wrapper
    return decorator


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
        # Проверяем несколько возможных путей
        possible_paths = [self._credentials_path]
        
        # Если путь относительный, добавляем абсолютные варианты
        if not os.path.isabs(self._credentials_path):
            possible_paths.extend([
                "/app/" + self._credentials_path,
                "/app/app/" + self._credentials_path,
                os.path.join(os.getcwd(), self._credentials_path),
            ])
        
        # Находим первый существующий файл
        credentials_file = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials_file = path
                break
        
        if not credentials_file:
            logger.warning(
                "Файл credentials не найден. Проверены пути: %s",
                possible_paths,
            )
            return False
        
        logger.info("Используется файл credentials: %s", credentials_file)

        try:
            logger.info("Загрузка credentials из: %s", credentials_file)
            
            # Загружаем credentials
            creds = Credentials.from_service_account_file(
                credentials_file, scopes=SCOPES
            )
            logger.info("Credentials загружены успешно")
            
            # Подключаемся через client
            self._client = gspread.Client(credentials=creds, scope=SCOPES)
            self._client.authorize()
            logger.info("Клиент gspread авторизован")
            
            # Открываем таблицу по ID
            logger.info(f"Попытка открыть таблицу ID: {self._sheet_id}")
            self._spreadsheet = self._client.open_by_key(self._sheet_id)
            logger.info(f"Таблица открыта: {self._spreadsheet.title}")
            
            # Получаем список всех листов
            worksheets = self._spreadsheet.worksheets()
            logger.info(f"Доступные листы: {[w.title for w in worksheets]}")
            
            # Открываем нужный лист
            self._worksheet = self._spreadsheet.worksheet(self._sheet_name)
            logger.info(f"Лист '{self._sheet_name}' открыт успешно")
            
            return True
            
        except gspread.exceptions.WorksheetNotFound as e:
            logger.error(f"Лист '{self._sheet_name}' не найден в таблице! Доступные листы: {e}")
            return False
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

    @retry_on_failure
    async def append_booking(self, booking: dict) -> int:
        """Добавление записи в Google Sheets. Возвращает номер строки."""
        if not self._ensure_initialized():
            logger.warning("Google Sheets недоступен. Запись не сохранена в таблицу.")
            return -1

        try:
            # Формируем строку для записи
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
            
            logger.info(f"Добавление в Google Sheets: {row}")
            
            # append_row возвращает dict с информацией
            result = self._worksheet.append_row(row)
            
            logger.info(
                f"Запись #{booking.get('id')} успешно добавлена в Google Sheets. "
                f"Ряд: {result.get('updates', {}).get('updatedRow', 'N/A')}"
            )
            return result.get('updates', {}).get('updatedRow', -1)
            
        except Exception as e:
            logger.error(
                f"Ошибка добавления в Google Sheets: {e}. "
                f"Данные: {booking.get('id')} - {booking.get('user_name')}"
            )
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
