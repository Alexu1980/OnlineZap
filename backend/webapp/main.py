"""FastAPI приложение для Telegram MiniApp."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from webapp.routes import availability, slots, bookings, specialists, user_data, user_bookings, reschedule

logger = logging.getLogger("webapp")


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"HTTP {request.method} {request.url.path} - Client: {request.client.host}")
        logger.info(f"HTTP Query params: {request.query_params}")
        try:
            response = await call_next(request)
            logger.info(f"HTTP {request.method} {request.url.path} - Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"HTTP {request.method} {request.url.path} - ERROR: {e}", exc_info=True)
            raise


app = FastAPI(title="OnlineZap API", version="1.0.0")
app.add_middleware(RequestLoggerMiddleware)

# Health check - ПЕРВЫЙ маршрут!
@app.get("/api/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok"}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация маршрутов - ПРАВИЛЬНЫЙ ПОРЯДОК!
# Сначала конкретные маршруты, потом с path params
app.include_router(availability.router, prefix="/api", tags=["availability"])
app.include_router(slots.router, prefix="/api", tags=["slots"])
app.include_router(bookings.router, prefix="/api", tags=["bookings"])
app.include_router(specialists.router, prefix="/api", tags=["specialists"])
app.include_router(user_data.router, prefix="/api", tags=["user_data"])
app.include_router(user_bookings.router, prefix="/api", tags=["user_bookings"])
app.include_router(reschedule.router, prefix="/api", tags=["reschedule"])

# Статические файлы для MiniApp
STATIC_DIR = Path(__file__).parent.parent / "static" / "app"
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR)), name="app")
