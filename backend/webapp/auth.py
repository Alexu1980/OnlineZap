"""Аутентификация через Telegram WebApp init data."""
import hashlib
import hmac
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, Header
from config.settings import settings


def parse_query_string(query_string: str) -> dict:
    """Парсинг query string из Telegram WebApp init data."""
    return dict(parse_qsl(query_string))


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Верификация Telegram WebApp init data.
    
    Возвращает dict с данными пользователя (user).
    """
    try:
        data = parse_query_string(init_data)
        check_hash = data.get('hash', '')
        del data['hash']
        
        # Проверка даты авторизации (не старше 24 часов)
        auth_date = int(data.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            raise HTTPException(status_code=401, detail="Data expired")
        
        # Проверка hash
        secret = hmac.new(
            b"WebAppData",
            settings.bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        data_check = "&".join(
            f"{k}={v}" for k, v in sorted(data.items())
        )
        calculated_hash = hmac.new(
            secret,
            data_check.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != check_hash:
            raise HTTPException(status_code=401, detail="Invalid hash")
        
        # Возвращаем данные пользователя
        user_data = data.get('user', {})
        if not user_data:
            raise HTTPException(status_code=401, detail="No user data")
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
