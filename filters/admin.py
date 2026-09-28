from aiogram.types import User

from config.settings import settings


class AdminUserFilter:
    def __init__(self):
        self.admin_ids = settings.admin_ids

    async def __call__(self, user: User) -> bool:
        if user is None:
            return False
        return user.id in self.admin_ids
