import gspread
from google.oauth2.service_account import Credentials
import sys

print(f"Версия gspread: {gspread.__version__}")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

try:
    creds = Credentials.from_service_account_file(
        'credentials.json',
        scopes=SCOPES
    )
    print("✓ Credentials загружены успешно")
    
    # Пробуем новый метод (gspread 6.x+)
    print("\nПопытка 1: gspread.authorize() (gspread 6.x+)")
    try:
        client = gspread.authorize(creds)
        print("✓ Успешно использован gspread.authorize()")
        use_new_method = True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        use_new_method = False
    
    # Если не получилось, пробуем старый метод (gspread 5.x)
    if not use_new_method:
        print("\nПопытка 2: gspread.Client() (gspread 5.x)")
        try:
            client = gspread.Client(credentials=creds, scope=SCOPES)
            client.authorize()
            print("✓ Успешно использован gspread.Client()")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            print("\n⚠️ Не удалось авторизоваться ни одним методом!")
            sys.exit(1)
    
    # Открываем таблицу
    SHEET_ID = '11WfXPmyuQ1wlhyPNwm_A9ds1UfEgyjQYDcA1gnAMUJ0'
    print(f"\n📂 Открытие таблицы ID: {SHEET_ID[:20]}...")
    
    try:
        sheet = client.open_by_key(SHEET_ID)
        print(f"✓ Таблица открыта: {sheet.title}")
        
        # Получаем лист
        worksheet = sheet.worksheet('Bookings')
        print(f"✓ Лист 'Bookings' найден")
        print(f"✓ Строк в таблице: {worksheet.row_count}")
        
        # Получаем все значения
        if worksheet.row_count > 1:
            values = worksheet.get_all_values()
            print(f"\n📊 Первые записи:")
            for i, row in enumerate(values[:5]):
                print(f"  {i+1}. {row}")
        else:
            print("\n📊 Таблица пуста (только заголовки)")
            
        print("\n✅ ТЕСТ ПРОЙДЕН! Google Sheets работает!")
        
    except Exception as e:
        print(f"✗ Ошибка открытия таблицы: {e}")
        sys.exit(1)
        
except FileNotFoundError:
    print("✗ Файл credentials.json не найден!")
    print("Убедитесь, что файл лежит в текущей директории")
    sys.exit(1)
except Exception as e:
    print(f"✗ Неожиданная ошибка: {e}")


    import traceback
    traceback.print_exc()
    sys.exit(1)
