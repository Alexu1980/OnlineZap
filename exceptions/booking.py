class BookingError(Exception):
    """Базовое исключение для ошибок бронирования."""
    pass


class SlotAlreadyReserved(BookingError):
    """Слот уже зарезервирован."""
    def __init__(self, message: str = "Этот слот уже зарезервирован. Пожалуйста, выберите другое время."):
        self.message = message
        super().__init__(self.message)


class SlotAlreadyBooked(BookingError):
    """Слот уже забронирован."""
    def __init__(self, message: str = "Это время уже занято. Пожалуйста, выберите другой слот."):
        self.message = message
        super().__init__(self.message)


class BookingNotFound(BookingError):
    """Запись не найдена."""
    def __init__(self, message: str = "Запись не найдена."):
        self.message = message
        super().__init__(self.message)


class BookingAlreadyCancelled(BookingError):
    """Запись уже отменена."""
    def __init__(self, message: str = "Эта запись уже отменена."):
        self.message = message
        super().__init__(self.message)


class BookingAlreadyCompleted(BookingError):
    """Консультация уже прошла."""
    def __init__(self, message: str = "Консультация уже прошла, перенос или отмена невозможны."):
        self.message = message
        super().__init__(self.message)
