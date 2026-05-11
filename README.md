# 🤖 Bybit Futures Trading Bot

Простой торговый бот для фьючерсного рынка **Bybit (USDT Linear)** на Python.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Bybit](https://img.shields.io/badge/Exchange-Bybit-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ⚡ Что делает

- Подключается к Bybit через официальный API
- Фильтрует монеты по суточному объёму, whitelist и blacklist
- Открывает позицию **рыночным ордером** (Long или Short)
- Выставляет **Take Profit** лимитным ордером
- Выставляет **Stop Loss** через встроенный механизм биржи (`set_trading_stop`)
- Мониторит позицию и фиксирует результат при закрытии
- Отправляет **Telegram-уведомление** об итогах сделки
- Пишет лог в консоль и файл

---

## 📋 Требования
Python 3.10+
pybit
requests


Установка зависимостей:

```bash
pip install pybit requests
```

---

## 🚀 Быстрый старт

1. Клонируй репозиторий:

```bash
git clone https://github.com/artstudia86/Trading-Bot.git
cd Trading-Bot
```

2. Открой `bot.py` и заполни настройки вверху файла:

```python
API_KEY    = "ВАШ_API_KEY"
API_SECRET = "ВАШ_API_SECRET"

SIDE            = "Buy"   # "Buy" = Long, "Sell" = Short
BET_USDT        = 10.0    # Ставка в USDT
LEVERAGE        = 10      # Плечо
TAKE_PROFIT_PCT = 1.5     # Тейк профит в %
STOP_LOSS_PCT   = 2.5     # Стоп лосс в %
```

3. Запусти бота:

```bash
python bot.py
```

---

## ⚙️ Все настройки

| Параметр | Описание | Пример |
|---|---|---|
| `API_KEY` | Публичный API-ключ Bybit | `"abc123..."` |
| `API_SECRET` | Секретный API-ключ Bybit | `"xyz789..."` |
| `SIDE` | Направление: Long или Short | `"Buy"` / `"Sell"` |
| `BET_USDT` | Размер ставки в USDT (без плеча) | `10.0` |
| `LEVERAGE` | Плечо (не превышает максимум биржи) | `10` |
| `TAKE_PROFIT_PCT` | Расстояние до TP в % от цены входа | `1.5` |
| `STOP_LOSS_PCT` | Расстояние до SL в % от цены входа | `2.5` |
| `MIN_VOLUME_24H` | Мин. суточный объём монеты в USDT | `1_000_000` |
| `WHITELIST` | Список разрешённых монет (пусто = все) | `["SOLUSDT"]` |
| `BLACKLIST` | Список запрещённых монет | `["BTCUSDT"]` |
| `TELEGRAM_TOKEN` | Токен Telegram-бота | `"123:ABC..."` |
| `TELEGRAM_CHAT_ID` | Ваш Telegram ID | `"4863165453"` |
| `LOG_FILE` | Путь к файлу лога (пусто = только консоль) | `"bot.log"` |

> **Важно:** `WHITELIST` и `BLACKLIST` нельзя использовать одновременно — заполняй только один из них.

---

## 🔑 Как создать API-ключ на Bybit

1. Войди в аккаунт на [bybit.com](https://www.bybit.com)
2. Перейди: **Аккаунт → API → Создать новый ключ**
3. Выбери тип: **System-generated**
4. Права: ✅ **Чтение** + ✅ **Торговля фьючерсами**
5. IP-доступ: **Без ограничений** (или укажи свой IP)
6. Скопируй `API Key` и `API Secret` — секрет показывается **только один раз**

---

## 📲 Настройка Telegram-уведомлений

1. Открой [@BotFather](https://t.me/BotFather) → `/newbot` → получи токен
2. Открой [@userinfobot](https://t.me/userinfobot) → `/start` → получи свой ID
3. Вставь оба значения в настройки `bot.py`

Пример уведомления:
🤖 Сделка закрыта
Монета: SOLUSDT
Направление: Buy
Вход: 142.35 | Объём: 0.702
TP: 144.49 | SL: 138.79
PNL: +0.1420 USDT (+1.42%)
Баланс: 100.1420 USDT


---

## 📁 Структура проекта
bybit-bot/
├── bot.py # Основной файл бота
├── bot.log # Лог (создаётся автоматически)
└── README.md

---

## 🔄 Логика работы
Старт
│ ├─► Проверка API + баланса
│ ├─► Получение тикеров всех монет
│ ├─► Фильтрация по объёму / whitelist / blacklist
│ ├─► Установка плеча
│ ├─► Открытие позиции (Market Order)
│ ├─► Выставление Take Profit (Limit Order)
│ ├─► Выставление Stop Loss (set_trading_stop)
│ ├─► Мониторинг каждые 5 сек
│ └─► Позиция закрыта → Telegram → Лог → Стоп

---

## ⚠️ Дисклеймер

Бот предназначен для **образовательных целей**. Торговля криптовалютными фьючерсами с плечом несёт **высокий риск потери средств**. Используй на свой страх и риск. Автор не несёт ответственности за убытки.

---

## 👤 Автор

**artstudia86** — [github.com/artstudia86](https://github.com/artstudia86)

---

## 📜 Лицензия

[MIT](LICENSE)
