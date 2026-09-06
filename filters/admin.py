from aiogram.types import User
from aiogram.filters import BaseFilter
from aiogram.dispatcher.flags import get_flag

from config.settings import settings


class AdminUserFilter(BaseFilter):
    def __init__(self):
        self.admin_ids = settings.admin_ids

    async def __call__(self, user: User) -> bool:
        if user is None:
            return False
        return user.id in self.admin_ids


class IsFromAdminFilter(BaseFilter):
    """Проверка что событие пришло от админа."""

    def __init__(self):
        self.admin_ids = settings.admin_ids

    async def __call__(self, event) -> bool:
        if hasattr(event, "from_user") and event.from_user:
            return event.from_user.id in self.admin_ids
        # Check for callback query
        if hasattr(event, "from_user"):
            return event.from_user.id in self.admin_ids
        return False
