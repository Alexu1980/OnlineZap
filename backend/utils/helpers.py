import re


def format_phone(raw: str) -> str:
    """Нормализация номера телефона: оставляем только цифры и +."""
    return "+" + re.sub(r"[^\d+]", "", raw)


def parse_phone(phone: str) -> str:
    """Парсинг номера телефона из строки."""
    return re.sub(r"[^\d+]", "", phone)


def get_date_display(date_str: str) -> str:
    """Форматирование даты для отображения пользователю."""
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return f"{dt.strftime('%d.%m.%Y')} ({days[dt.weekday()]})"
    except (ValueError, TypeError):
        return date_str


def get_datetime_display(date_str: str, time_str: str) -> str:
    """Форматирование даты и времени для отображения."""
    try:
        from datetime import datetime
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        days = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        months = [
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря"
        ]
        return f"{dt.day} {months[dt.month - 1]} {dt.year}, {dt.strftime('%A')}, {time_str}"
    except (ValueError, TypeError):
        return f"{date_str}, {time_str}"


def get_future_dates(days_count: int = 30) -> list[str]:
    """Возвращает список дат на следующие days_count дней."""
    from datetime import datetime, timedelta
    dates = []
    today = datetime.now()
    for i in range(1, days_count + 1):
        d = today + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def format_booking_status(status: str) -> str:
    """Форматирование статуса записи для отображения."""
    status_map = {
        "Подтверждена": "✅ Подтверждена",
        "Отменена": "❌ Отменена",
        "Завершена": "✔️ Завершена",
        "Ожидает": "⏳ Ожидает",
    }
    return status_map.get(status, f"📌 {status}")
