# Project state

Последнее актуальное состояние проекта.

## Назначение

Telegram-бот `@eco2watermarkbot` принимает изображения, накладывает логотип/watermark и отправляет пользователю готовый JPEG-файл.

## Где лежит проект

### Локально на ноутбуке

```text
/Users/svatoslav/Documents/coding/watermark-bot
```

### GitHub

```text
https://github.com/angelbeast106-wq/watermark-bot
```

### На сервере

```text
server: 159.194.204.123
user: root
path: /root/watermark-bot
```

Подключение:

```bash
ssh root@159.194.204.123
```

## Как бот запущен на сервере

Бот работает как `systemd`-сервис:

```text
watermark-bot.service
```

Файл сервиса:

```text
/etc/systemd/system/watermark-bot.service
```

Содержимое сервиса:

```ini
[Unit]
Description=Watermark Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/root/watermark-bot
ExecStart=/root/watermark-bot/.venv/bin/python /root/watermark-bot/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Проверить статус:

```bash
systemctl status watermark-bot
```

Перезапустить:

```bash
systemctl restart watermark-bot
```

Посмотреть живые логи:

```bash
journalctl -u watermark-bot -f
```

Бот включен в автозапуск:

```bash
systemctl enable watermark-bot
```

## Runtime-настройки

Настройки на сервере лежат здесь:

```text
/root/watermark-bot/.env
```

Локально настройки лежат здесь:

```text
/Users/svatoslav/Documents/coding/watermark-bot/.env
```

Файл `.env` нельзя коммитить и публиковать, потому что в нем находится `BOT_TOKEN`.

Актуальные значения watermark:

```env
WATERMARK_PATH=assets/watermark.png
WATERMARK_ANCHOR=top_right
WATERMARK_WIDTH_PERCENT=23.4
WATERMARK_MARGIN_PERCENT=6
WATERMARK_TOP_MARGIN_PERCENT=0
WATERMARK_OPACITY=1
SHIFT_STEP_PX=24
```

Что это значит:

- логотип берется из `assets/watermark.png`;
- логотип ставится в верхний правый угол;
- логотип прижат к верхнему краю;
- размер логотипа - `23.4%` ширины изображения;
- правый отступ - `6%`, поэтому логотип немного сдвинут левее от края;
- дополнительная прозрачность отключена.

## Основные файлы

- `bot.py` - Telegram-бот, aiogram handlers, callback-кнопки, пользовательские сессии.
- `watermark_processor.py` - обработка изображений через Pillow.
- `assets/watermark.png` - логотип, который наносится на изображения.
- `.env.example` - безопасный пример настроек без реального токена.
- `requirements.txt` - Python-зависимости.
- `docs/ARCHITECTURE.md` - архитектура проекта.
- `docs/DEVELOPMENT.md` - локальная разработка.
- `docs/PROJECT_STATE.md` - актуальное состояние проекта и деплой.

## Как обновлять сервер после изменений

Локально:

```bash
cd /Users/svatoslav/Documents/coding/watermark-bot
git status
git add .
git commit -m "Describe changes"
git push
```

На сервере:

```bash
ssh root@159.194.204.123
cd /root/watermark-bot
git pull
systemctl restart watermark-bot
systemctl status watermark-bot
```

Если изменились зависимости:

```bash
cd /root/watermark-bot
.venv/bin/pip install -r requirements.txt
systemctl restart watermark-bot
```

## Как развернуть с нуля на новом сервере

```bash
ssh root@SERVER_IP
cd /root
git clone https://github.com/angelbeast106-wq/watermark-bot.git
cd /root/watermark-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

В `.env` нужно вставить реальный `BOT_TOKEN`.

После этого создать сервис:

```bash
nano /etc/systemd/system/watermark-bot.service
systemctl daemon-reload
systemctl enable watermark-bot
systemctl start watermark-bot
systemctl status watermark-bot
```

## Важные ограничения

- Один Telegram bot token может работать через polling только в одном месте одновременно.
- Если локально запустить `python bot.py`, а серверный сервис уже работает, будет `TelegramConflictError`.
- Перед локальным тестом лучше остановить серверный сервис:

```bash
systemctl stop watermark-bot
```

- После локального теста серверный сервис нужно снова запустить:

```bash
systemctl start watermark-bot
```

## Что не хранится в GitHub

- `.env` с токеном;
- `.venv`;
- `__pycache__`;
- `*.log`;
- `*.tar.gz`;
- `.DS_Store`.
