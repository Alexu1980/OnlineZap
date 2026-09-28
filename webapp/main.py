"""FastAPI приложение для Telegram MiniApp."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from webapp.routes import specialists, availability, slots, bookings

app = FastAPI(title="OnlineZap API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене ограничить до домена MiniApp
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация маршрутов API
app.include_router(specialists.router, prefix="/api", tags=["specialists"])
app.include_router(availability.router, prefix="/api", tags=["availability"])
app.include_router(slots.router, prefix="/api", tags=["slots"])
app.include_router(bookings.router, prefix="/api", tags=["bookings"])

# Статические файлы для MiniApp (после сборки)
STATIC_DIR = Path(__file__).parent.parent / "static" / "app"
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR)), name="app")


@app.get("/api/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}
