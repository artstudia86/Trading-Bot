#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Bybit Futures Trading Bot
--------------------------
Простой торговый бот для фьючерсного рынка Bybit (USDT Linear).
- Фильтрация монет по объёму, whitelist/blacklist
- Вход по рыночному ордеру
- Выставление Take Profit (лимитный ордер) и Stop Loss
- Telegram-уведомления о закрытии сделки
- Логирование в файл и консоль
"""

import os
import time
import logging
from datetime import datetime

import requests
from pybit.unified_trading import HTTP

# ─────────────────────────────────────────────
# НАСТРОЙКИ — редактируй здесь
# ─────────────────────────────────────────────

API_KEY    = "ВАШ_API_KEY"
API_SECRET = "ВАШ_API_SECRET"

SIDE            = "Buy"      # "Buy" = Long, "Sell" = Short
BET_USDT        = 10.0       # Размер ставки в USDT (без учёта плеча)
LEVERAGE        = 10         # Плечо
TAKE_PROFIT_PCT = 1.5        # Тейк профит в % от цены входа
STOP_LOSS_PCT   = 2.5        # Стоп лосс в % от цены входа

MIN_VOLUME_24H  = 1_000_000  # Минимальный суточный объём монеты в USDT (0 = без фильтра)
WHITELIST       = []         # Например: ["BTCUSDT", "ETHUSDT"] — пусто = все монеты
BLACKLIST       = ["BTCUSDT", "ETHUSDT"]  # Монеты которые пропускаем

TELEGRAM_TOKEN   = ""        # Токен Telegram-бота (оставь пустым чтобы не использовать)
TELEGRAM_CHAT_ID = ""        # Ваш Telegram ID

LOG_FILE        = "bot.log"  # Файл лога (пустая строка = только консоль)

# ─────────────────────────────────────────────
# Логирование
# ─────────────────────────────────────────────

handlers = [logging.StreamHandler()]
if LOG_FILE:
    os.makedirs(os.path.dirname(os.path.abspath(LOG_FILE)) or '.', exist_ok=True)
    handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s',
    datefmt='%d.%m.%Y %H:%M:%S',
    handlers=handlers,
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Telegram
# ─────────────────────────────────────────────

def telegram_send(message: str):
    """Отправляет сообщение в Telegram. Ничего не делает если токен не задан."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = (
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            f"?chat_id={TELEGRAM_CHAT_ID}&parse_mode=html&text={message}"
        )
        requests.get(url, timeout=10)
    except Exception as e:
        log.warning(f"Telegram error: {e}")


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────

def get_precision(step: str) -> int:
    """
    Определяет количество знаков после запятой по шагу (tickSize / qtyStep).
    Например: '0.001' → 3, '0.5' → 1, '1' → 0
    """
    if '.' in step:
        return len(step.rstrip('0').split('.')[1])
    return 0


def fmt(value: float, precision: int) -> str:
    """Форматирует число под нужную точность биржи."""
    return f"{value:.{precision}f}"


def get_account_type(session: HTTP) -> str:
    """Определяет тип аккаунта: CONTRACT (старый) или UNIFIED (новый)."""
    result = session.get_account_info()
    status = result['result']['unifiedMarginStatus']
    return 'CONTRACT' if status == 1 else 'UNIFIED'


def get_balance(session: HTTP, account_type: str) -> float:
    """Возвращает доступный баланс USDT."""
    result = session.get_wallet_balance(accountType=account_type, coin='USDT')
    return float(result['result']['list'][0]['coin'][0]['walletBalance'])


def get_all_tickers(session: HTTP) -> list:
    """Возвращает список всех тикеров linear-фьючерсов."""
    result = session.get_tickers(category='linear')
    if result['retMsg'] == 'OK':
        return result['result']['list']
    return []


def get_instrument_info(session: HTTP, symbol: str) -> dict:
    """Возвращает параметры инструмента (точность цены, объёма, мин. кол-во)."""
    result = session.get_instruments_info(category='linear', symbol=symbol)
    if result['retMsg'] == 'OK':
        return result['result']['list'][0]
    return {}


def get_position(session: HTTP, symbol: str) -> dict:
    """Возвращает текущую открытую позицию по символу."""
    result = session.get_positions(category='linear', symbol=symbol)
    if result['retMsg'] == 'OK':
        return result['result']['list'][0]
    return {}


def set_leverage(session: HTTP, symbol: str, leverage: int):
    """Устанавливает плечо для символа."""
    try:
        session.set_leverage(
            category='linear',
            symbol=symbol,
            buyLeverage=str(leverage),
            sellLeverage=str(leverage),
        )
        log.info(f"{symbol} | Плечо установлено: {leverage}x")
    except Exception as e:
        # Ошибка "already set" — не критично, продолжаем
        log.debug(f"set_leverage: {e}")


def place_order(
    session: HTTP,
    symbol: str,
    side: str,
    order_type: str,
    qty: str,
    price: str = None,
    reduce_only: bool = False,
) -> str:
    """
    Выставляет ордер на бирже.

    Args:
        symbol:      торговая пара, например 'SOLUSDT'
        side:        'Buy' или 'Sell'
        order_type:  'Market' или 'Limit'
        qty:         объём строкой с нужной точностью
        price:       цена для Limit-ордера
        reduce_only: True = ордер только закрывает позицию (TP/SL)

    Returns:
        orderId при успехе, '' при ошибке
    """
    kwargs = {
        'category':    'linear',
        'symbol':      symbol,
        'side':        side,
        'orderType':   order_type,
        'qty':         qty,
        'positionIdx': 0,  # One-Way Mode
    }
    if price:
        kwargs['price'] = price
    if reduce_only:
        kwargs['reduceOnly'] = True

    result = session.place_order(**kwargs)

    if result['retMsg'] == 'OK':
        order_id = result['result']['orderId']
        log.info(
            f"{symbol} | Ордер {side} {order_type} "
            f"qty={qty} price={price or 'market'} → orderId={order_id}"
        )
        return order_id

    log.error(f"{symbol} | place_order ошибка: {result['retMsg']}")
    return ''


def cancel_all_orders(session: HTTP, symbol: str):
    """Отменяет все открытые ордера по символу."""
    try:
        session.cancel_all_orders(category='linear', symbol=symbol)
        log.info(f"{symbol} | Все ордера отменены")
    except Exception as e:
        log.error(f"cancel_all_orders: {e}")


# ─────────────────────────────────────────────
# Фильтрация монет
# ─────────────────────────────────────────────

def find_symbol(tickers: list) -> str:
    """
    Ищет подходящую монету по фильтрам:
      - USDT-пара
      - Объём за 24ч >= MIN_VOLUME_24H
      - Не в BLACKLIST
      - Если задан WHITELIST — только из него

    Returns:
        Символ монеты или '' если ничего не найдено
    """
    for ticker in tickers:
        symbol = ticker.get('symbol', '')

        # Только USDT linear-фьючерсы
        if not symbol.endswith('USDT'):
            continue

        # Whitelist: если задан — берём только из него
        if WHITELIST and symbol not in WHITELIST:
            continue

        # Blacklist: пропускаем запрещённые монеты
        if BLACKLIST and symbol in BLACKLIST:
            continue

        # Фильтр по суточному объёму
        try:
            volume = float(ticker.get('turnover24h', 0))
            if MIN_VOLUME_24H > 0 and volume < MIN_VOLUME_24H:
                continue
        except (ValueError, TypeError):
            continue

        return symbol

    return ''


# ─────────────────────────────────────────────
# Основная логика
# ─────────────────────────────────────────────

def run():
    log.info("=" * 50)
    log.info("Bybit Bot — старт")
    log.info(f"Сторона: {SIDE} | Ставка: {BET_USDT} USDT | Плечо: {LEVERAGE}x")
    log.info(f"TP: {TAKE_PROFIT_PCT}% | SL: {STOP_LOSS_PCT}%")
    log.info("=" * 50)

    # ── Подключение к Bybit ──
    session = HTTP(
        testnet=False,
        api_key=API_KEY,
        api_secret=API_SECRET,
    )
    log.info("HTTP-сессия создана")

    # ── Тип аккаунта и баланс ──
    account_type = get_account_type(session)
    log.info(f"Тип аккаунта: {account_type}")

    balance = get_balance(session, account_type)
    log.info(f"Баланс: {balance:.4f} USDT")

    if balance <= 0:
        log.error("Нет средств на аккаунте. Пополните баланс.")
        return

    if BET_USDT < 5.2:
        log.error(
            f"Размер ставки {BET_USDT} USDT меньше минимума (5 USDT). "
            "Увеличьте BET_USDT."
        )
        return

    # ── Поиск монеты ──
    tickers = get_all_tickers(session)
    if not tickers:
        log.error("Не удалось получить список тикеров.")
        return

    symbol = find_symbol(tickers)
    if not symbol:
        log.error(
            "Нет монет, прошедших фильтры. "
            "Проверьте WHITELIST / BLACKLIST / MIN_VOLUME_24H."
        )
        return

    log.info(f"Выбрана монета: {symbol}")

    # ── Параметры инструмента ──
    instr = get_instrument_info(session, symbol)
    if not instr:
        log.error(f"Не удалось получить параметры инструмента {symbol}.")
        return

    qty_step  = instr['lotSizeFilter']['qtyStep']
    tick_size = instr['priceFilter']['tickSize']
    min_qty   = float(instr['lotSizeFilter']['minOrderQty'])
    max_lev   = float(instr['leverageFilter']['maxLeverage'])

    qty_prec   = get_precision(qty_step)
    price_prec = get_precision(tick_size)
    leverage   = min(LEVERAGE, int(max_lev))

    log.info(
        f"{symbol} | qtyStep={qty_step} tickSize={tick_size} "
        f"maxLev={max_lev}"
    )

    # ── Установка плеча ──
    set_leverage(session, symbol, leverage)

    # ── Текущая цена ──
    ticker_data = next((t for t in tickers if t['symbol'] == symbol), {})
    current_price = float(ticker_data.get('lastPrice', 0))

    if current_price <= 0:
        log.error(f"Не удалось получить цену {symbol}.")
        return

    log.info(f"{symbol} | Текущая цена: {current_price}")

    # ── Расчёт объёма ──
    # Объём = (ставка USDT * плечо) / цена монеты
    qty_float = (BET_USDT * leverage) / current_price
    qty_float = max(qty_float, min_qty)
    qty = fmt(qty_float, qty_prec)

    log.info(
        f"{symbol} | Объём: {qty} | "
        f"Ставка с плечом: {BET_USDT * leverage:.2f} USDT"
    )

    # ── Вход в позицию (Market) ──
    order_id = place_order(
        session=session,
        symbol=symbol,
        side=SIDE,
        order_type='Market',
        qty=qty,
    )

    if not order_id:
        log.error("Не удалось открыть позицию. Выход.")
        return

    # Ждём подтверждения открытия на бирже
    time.sleep(1.5)

    # ── Фактическая цена входа из позиции ──
    position = get_position(session, symbol)
    entry_price = float(position.get('avgPrice', current_price))
    actual_qty  = float(position.get('size', qty_float))

    if actual_qty == 0:
        log.error(
            f"{symbol} | Позиция не открылась (size=0). "
            "Проверьте баланс и минимальный объём."
        )
        return

    log.info(
        f"{symbol} | Позиция открыта | "
        f"Цена входа: {entry_price} | Объём: {actual_qty}"
    )

    # ── Расчёт цен TP и SL ──
    if SIDE == 'Buy':
        # Long: TP выше входа, SL ниже
        price_tp = entry_price * (1 + TAKE_PROFIT_PCT / 100)
        price_sl = entry_price * (1 - STOP_LOSS_PCT   / 100)
        close_side = 'Sell'
    else:
        # Short: TP ниже входа, SL выше
        price_tp = entry_price * (1 - TAKE_PROFIT_PCT / 100)
        price_sl = entry_price * (1 + STOP_LOSS_PCT   / 100)
        close_side = 'Buy'

    price_tp_str   = fmt(price_tp,   price_prec)
    price_sl_str   = fmt(price_sl,   price_prec)
    actual_qty_str = fmt(actual_qty, qty_prec)

    log.info(f"{symbol} | TP: {price_tp_str} | SL: {price_sl_str}")

    # ── Take Profit — лимитный ордер ──
    tp_order_id = place_order(
        session=session,
        symbol=symbol,
        side=close_side,
        order_type='Limit',
        qty=actual_qty_str,
        price=price_tp_str,
        reduce_only=True,
    )

    # ── Stop Loss — через set_trading_stop (встроенный механизм биржи) ──
    # Надёжнее отдельного ордера: не слетает при перезапуске бота
    try:
        result = session.set_trading_stop(
            category='linear',
            symbol=symbol,
            stopLoss=price_sl_str,
            positionIdx=0,
        )
        if result['retMsg'] == 'OK':
            log.info(
                f"{symbol} | Stop Loss установлен: {price_sl_str}"
            )
        else:
            log.warning(
                f"{symbol} | set_trading_stop ответ: {result['retMsg']}"
            )
    except Exception as e:
        log.error(f"{symbol} | Ошибка set_trading_stop: {e}")

    # ── Мониторинг позиции (опрос каждые 5 сек) ──
    log.info(f"{symbol} | Мониторинг позиции запущен...")

    while True:
        time.sleep(5)

        try:
            position   = get_position(session, symbol)
            pos_size   = float(position.get('size', 0))
            pnl        = float(position.get('unrealisedPnl', 0))
            mark_price = float(position.get('markPrice', entry_price))
        except Exception as e:
            log.error(f"{symbol} | Ошибка опроса позиции: {e}")
            continue

        if pos_size == 0:
            # Позиция закрыта — TP или SL сработал
            log.info(f"{symbol} | Позиция закрыта.")
            break

        log.info(
            f"{symbol} | Открыта | "
            f"Цена: {mark_price:.{price_prec}f} | "
            f"PNL: {pnl:+.4f} USDT"
        )

    # ── Финальный баланс и итог ──
    try:
        final_balance = get_balance(session, account_type)
    except Exception:
        final_balance = 0.0

    profit_usdt = final_balance - balance
    profit_pct  = (profit_usdt / balance * 100) if balance > 0 else 0.0

    log.info(
        f"{symbol} | Сделка завершена | "
        f"PNL: {profit_usdt:+.4f} USDT ({profit_pct:+.2f}%) | "
        f"Баланс: {final_balance:.4f} USDT"
    )

    # ── Telegram-уведомление ──
    msg = (
        f"<b>Сделка закрыта</b>\n"
        f"Монета: <b>{symbol}</b>\n"
        f"Направление: {SIDE}\n"
        f"Вход: {entry_price} | Объём: {actual_qty}\n"
        f"TP: {price_tp_str} | SL: {price_sl_str}\n"
        f"<b>PNL: {profit_usdt:+.4f} USDT ({profit_pct:+.2f}%)</b>\n"
        f"Баланс: {final_balance:.4f} USDT"
    )
    telegram_send(msg)

    # ── Отменяем оставшиеся ордера ──
    # (если SL сработал — TP-ордер висит, его нужно снять)
    cancel_all_orders(session, symbol)

    log.info("Бот завершил работу.")


# ─────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run()
