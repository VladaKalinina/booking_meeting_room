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
