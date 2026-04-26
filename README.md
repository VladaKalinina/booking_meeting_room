# booking_meeting_room

Telegram-бот для бронирования переговорных комнат.

## Запуск бота

1. Активируйте виртуальное окружение:

```powershell
.\venv\Scripts\Activate.ps1
```

2. Установите зависимости:

```powershell
python -m pip install -r requirements.txt
```

3. Создайте файл `.env` по примеру `.env.example` и укажите токен бота:

```env
TELEGRAM_BOT_TOKEN=your_token
```

4. Запустите бота:

```powershell
python main.py
```

## База данных

Применить миграции:

```powershell
python -m alembic upgrade head
```

Проверить подключение и созданные таблицы:

```powershell
python scripts/check_db.py
```

Проверить сервис регистрации пользователя:

```powershell
python scripts/check_user_service.py
```

Проверить полноценную регистрацию профиля:

```powershell
python scripts/check_registration.py
```

Проверить сервис управления комнатами:

```powershell
python scripts/check_rooms.py
```

Проверить сервис управления оборудованием:

```powershell
python scripts/check_equipment.py
```

Проверить сервис расписания:

```powershell
python scripts/check_schedule.py
```

Назначить администратора:

```powershell
python scripts/set_admin.py <telegram_id_or_email> true
```
