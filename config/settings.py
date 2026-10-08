import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path), encoding="utf-8")


class Settings(BaseSettings):
    bot_token: str
    admin_ids_csv: str
    google_sheets_credentials_path: str = "credentials.json"
    google_sheet_id: str
    google_sheet_name: str = "Bookings"
    slot_duration_minutes: int = 60
    reservation_timeout_seconds: int = 300
    reminder_24h_enabled: bool = True
    reminder_2h_enabled: bool = True
    database_url: str = "postgresql+asyncpg://onlinezap:change_me@localhost:5432/onlinezap"
    admin_chat_id_csv: str
    miniapp_url: str = "http://localhost:3000/app"

    class Config:
        env_file_encoding = "utf-8"

    @property
    def admin_ids(self) -> List[int]:
        return [int(x.strip()) for x in self.admin_ids_csv.split(",") if x.strip()]

    @property
    def admin_chat_id(self) -> int:
        ids = [int(x.strip()) for x in self.admin_chat_id_csv.split(",") if x.strip()]
        return ids[0] if ids else 0


settings = Settings()
