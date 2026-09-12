"""Тестовый скрипт для проверки базы данных и команды /admin_view."""
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent))

from database.engine import AsyncSessionLocal
from database.repositories import get_all_bookings


async def test_database():
    """Проверяет базу данных и выводит все записи."""
    print("=" * 60)
    print("ТЕСТ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    try:
        async with AsyncSessionLocal() as db:
            bookings = await get_all_bookings(db)
        
        print(f"\n✅ Найдено {len(bookings)} записей в базе данных\n")
        
        if not bookings:
            print("⚠️ База данных пуста. Это нормально, если записей ещё нет.")
        else:
            for b in bookings:
                print(f"🔹 Запись #{b.id}")
                print(f"   Статус: {b.status}")
                print(f"   Имя: {b.user_name}")
                print(f"   Телефон: {b.user_phone}")
                print(f"   Telegram: @{b.user_username or 'не указан'}")
                print(f"   Специалист: {b.specialist_name}")
                print(f"   Дата: {b.consultation_date} {b.consultation_time}")
                if b.additional_info:
                    print(f"   Комментарий: {b.additional_info}")
                if b.manager_comment:
                    print(f"   Комментарий менеджера: {b.manager_comment}")
                print()
        
        print("=" * 60)
        print("ТЕСТ ЗАВЕРШЁН")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка при подключении к базе данных: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_database())
