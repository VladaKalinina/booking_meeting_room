# booking_meeting_room

Telegram-бот для бронирования переговорных комнат.

## Возможности

- регистрация сотрудников через Telegram;
- бронирование переговорных комнат с проверкой занятости;
- изменение и отмена своих бронирований;
- добавление участников встречи по email;
- принятие и отклонение приглашений;
- просмотр расписания комнат по датам;
- уведомления участникам при приглашении, изменении и отмене встречи;
- напоминания за 15 минут до начала встречи;
- админское управление комнатами, оборудованием и пользователями;
- админский список всех бронирований и аналитика.

## Роли

Сотрудник может регистрироваться, создавать и изменять свои бронирования, приглашать участников, отвечать на приглашения и смотреть расписание.

Администратор дополнительно управляет комнатами, оборудованием, пользователями, всеми бронированиями и аналитикой.

## Запуск бота

1. Активируйте виртуальное окружение:

```powershell
.\venv\Scripts\Activate.ps1
```

2. Установите зависимости:

```powershell
python -m pip install -r requirements.txt
```

3. Создайте файл `.env` по примеру `.env.example` и укажите настройки:

```env
TELEGRAM_BOT_TOKEN=your_token
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/booking_meeting_room
TELEGRAM_PROXY_URL=
```

4. Запустите бота:

```powershell
python main.py
```

Проверить подключение к Telegram Bot API:

```powershell
python scripts/check_bot.py
```

## Запуск в Docker

1. Установите Docker Desktop или Docker Engine.

2. Создайте `.env` по примеру `.env.example` и заполните:

```env
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_PROXY_URL=
POSTGRES_DB=booking_meeting_room
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strong_password
POSTGRES_PORT=5432
```

Для Docker строку `DATABASE_URL` можно оставить любой: `docker-compose.yml` сам передаёт боту адрес БД внутри сети контейнеров.

3. Соберите и запустите контейнеры:

```powershell
docker compose up -d --build
```

Контейнер `bot` дождётся PostgreSQL, применит миграции Alembic и запустит polling.

4. Посмотреть логи:

```powershell
docker compose logs -f bot
```

5. Остановить проект:

```powershell
docker compose down
```

Остановить и удалить данные PostgreSQL:

```powershell
docker compose down -v
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

Запустить все локальные проверки одной командой:

```powershell
python scripts/check_all.py
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

Проверить сервис создания бронирований:

```powershell
python scripts/check_booking.py
```

Проверить изменение бронирований:

```powershell
python scripts/check_booking_edit.py
```

Проверить список и отмену своих бронирований:

```powershell
python scripts/check_my_reservations.py
```

Проверить участников встречи и статусы приглашений:

```powershell
python scripts/check_participants.py
```

Проверить напоминания о встречах:

```powershell
python scripts/check_reminders.py
```

Проверить админский список и отмену бронирований:

```powershell
python scripts/check_admin_reservations.py
```

Проверить управление пользователями:

```powershell
python scripts/check_user_management.py
```

Назначить администратора:

```powershell
python scripts/set_admin.py <telegram_id_or_email> true
```

Проверить админскую аналитику:

```powershell
python scripts/check_analytics.py
```
