import os
import sqlite3
import subprocess
import threading
from io import BytesIO
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from flask import Flask, jsonify, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
import requests
import re
import jdatetime
import holidays
import time
from flask import Response
import json
from flask_cors import CORS
from flask import render_template


app = Flask(__name__)
CORS(app)

# =========================================================
# TRADE VALUE SNAPSHOT
# =========================================================

# ساعت ایران UTC+3:30
IRAN_TIMEZONE = timezone(
    timedelta(
        hours=3,
        minutes=30
    )
)

# مسیر فایل ذخیره ارزش معاملات
TRADE_VALUE_SNAPSHOT_FILE = os.path.join(
    app.root_path,
    "data",
    "trade_value_snapshot.json"
)

# جلوگیری از نوشتن همزمان چند request روی فایل
trade_value_snapshot_lock = threading.Lock()

# مسیر فایل Snapshot سفارشات پایان بازار
ORDER_BOOK_SNAPSHOT_FILE = os.path.join(
    app.root_path,
    "data",
    "order_book_snapshot.json"
)

# فهرست ثابت نمادهای تب سهام؛ بقیه اطلاعات از TSETMC دریافت می‌شود.
STOCK_SYMBOLS_FILE = os.path.join(
    app.root_path,
    "data",
    "stock_symbols.json"
)

STOCK_DATABASE_FILE = os.path.join(
    app.root_path,
    "data",
    "stocks.db"
)

stock_database_lock = threading.Lock()
stock_database_ready = False
stock_refresh_lock = threading.Lock()
stock_refresh_state = {
    "running": False,
    "started_at": None,
    "last_attempt_at": 0.0,
    "error": None
}

all_stock_refresh_lock = threading.Lock()
all_stock_refresh_state = {
    "running": False,
    "started_at": None,
    "phases": [],
    "manual": False,
    "error": None,
}

stock_price_history_lock = threading.Lock()
stock_price_history_state = {
    "running": False,
    "started_at": None,
    "total": 0,
    "completed": 0,
    "stored_points": 0,
    "errors": 0,
    "error": None,
}

stock_strategy_history_lock = threading.Lock()
stock_strategy_history_state = {
    "running": False,
    "started_at": None,
    "total": 0,
    "completed": 0,
    "stored_points": 0,
    "errors": 0,
    "error": None,
}

watch_market_cache_lock = threading.Lock()
watch_market_cache = {
    "data": None,
    "fetched_at": 0,
}

watch_market_overview_cache_lock = threading.Lock()
watch_market_overview_cache = {
    "data": None,
    "fetched_at": 0,
}

RAHAVARD_LIVE_QUOTES_FILE = os.path.join(
    app.root_path,
    "data",
    "rahavard_live_quotes.json",
)
RAHAVARD_LIVE_COLLECTOR_FILE = os.path.join(
    app.root_path,
    "rahavard_live.js",
)
rahavard_live_quotes_lock = threading.Lock()
rahavard_live_quotes_state = {
    "data": {},
    "process": None,
}

RAHAVARD_HEADERS = {
    "Accept": "application/json",
    "Application-Name": "rahavard",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": "com.rahavard365.v2.front",
    "platform": "web",
}

WATCH_MARKET_ASSETS = (
    {
        "key": "dollar",
        "asset_id": 2,
        "name": "دلار آمریکا",
        "unit": "تومان",
        "divisor": 10,
        "live_required": True,
        "tone": "currency",
        "source_url": "https://rahavard365.com/asset/2/دلار-آمریکا",
    },
    {
        "key": "nimai_dollar",
        "asset_id": 43157,
        "name": "دلار نیمایی",
        "unit": "تومان",
        "divisor": 10,
        "tone": "currency",
        "source_url": (
            "https://rahavard365.com/asset/43157/"
            "دلار-آمریکا-حواله-بازار-توافقی-نیمایی"
        ),
    },
    {
        "key": "gold_18",
        "asset_id": 1560,
        "name": "طلای ۱۸ عیار",
        "unit": "تومان/گرم",
        "divisor": 10,
        "tone": "gold",
        "source_url": "https://rahavard365.com/asset/1560/طلای-۱۸-عیار",
    },
    {
        "key": "gold_ounce",
        "asset_id": 2016,
        "name": "اونس جهانی طلا",
        "unit": "دلار",
        "divisor": 1,
        "tone": "gold",
        "source_url": "https://rahavard365.com/asset/2016/انس-طلا",
    },
    {
        "key": "silver_ounce",
        "asset_id": 2017,
        "name": "اونس جهانی نقره",
        "unit": "دلار",
        "divisor": 1,
        "tone": "silver",
        "source_url": "https://rahavard365.com/asset/2017/انس-نقره",
    },
    {
        "key": "silver_certificate",
        "asset_id": 35945,
        "name": "گواهی شمش نقره",
        "unit": "تومان",
        "divisor": 10,
        "tone": "silver",
        "source_url": "https://rahavard365.com/asset/35945",
    },
    {
        "key": "copper_certificate",
        "asset_id": 44055,
        "name": "گواهی سپرده مس کاتد",
        "unit": "تومان/کیلوگرم",
        "divisor": 10,
        "tone": "copper",
        "source_url": "https://rahavard365.com/asset/44055",
    },
)

WATCH_IME_COMMODITIES = (
    {
        "key": "steel_rebar",
        "tag_id": 1511,
        "code": "SteelRebar",
        "name": "میلگرد",
        "tone": "steel",
        "source_url": "https://bourseeye.com/commodities/1511/میلگرد",
    },
    {
        "key": "zinc_ingot",
        "tag_id": 1512,
        "code": "ZincIngot",
        "name": "شمش روی",
        "tone": "zinc",
        "source_url": "https://bourseeye.com/commodities/1512/شمش-روی",
    },
    {
        "key": "iron_ore_pellet",
        "tag_id": 1510,
        "code": "IronOrePlt",
        "name": "گندله سنگ آهن",
        "tone": "iron",
        "source_url": "https://bourseeye.com/commodities/1510/گندله-سنگ-آهن",
    },
)

POUNDS_PER_METRIC_TON = 2204.6226218488

WATCH_MARKET_OVERVIEW_TTL_SECONDS = 110
RAHAVARD_LIVE_QUOTE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

STOCK_CACHE_TTL_SECONDS = max(
    30,
    int(os.environ.get("STOCK_DATA_CACHE_SECONDS", "300"))
)

TSETMC_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 StockMarketWatch/1.0"
}

STOCK_STANDARD_SNAPSHOT_MINUTE = 12 * 60 + 30
STOCK_EXTENDED_SNAPSHOT_MINUTE = 18 * 60
# The strategy UI accepts technical periods up to 250. MACD may need the
# slow period plus the signal lookback (250 + 250 - 1), so retain 500 closing
# prices to cover every supported RSI/EMA/MACD configuration and reduce
# recursive-indicator seed drift versus charting services.
STOCK_PRICE_HISTORY_TARGET_DAYS = 500
STOCK_STRATEGY_HISTORY_TARGET_DAYS = 60
STOCK_PRICE_HISTORY_WORKERS = 10
STOCK_STRATEGY_HISTORY_WORKERS = 5
STOCK_EXTENDED_SESSION_SYMBOLS = {
    "عیار",
    "طلا",
    "کهربا",
    "مثقال",
    "نقرابی",
    "نقران",
}

# The complete-market tab now contains equity instruments only.  Funds are
# intentionally excluded even if they are exchange traded.
ALL_STOCK_EXTENDED_CATEGORIES = {
    "1A",
    "2A",
    "H1",
    "H2",
    "Q1",
    "QS",
}
ALL_STOCK_EQUITY_INSTRUMENT_PREFIXES = (
    "IRO1",
    "IRO3",
    "IRO5",
    "IRO7",
    "IRR1",
    "IRR3",
    "IRR5",
    "IRR7",
)

# TSETMC does not currently publish a usable free-float value for these
# instruments. These user-supplied percentages are authoritative and are
# reapplied after every online refresh.
STOCK_FLOATING_SHARE_OVERRIDES = {
    "فزر": 38,
    "وشهر": 12,
    "مارون": 28.8,
    "آریا": 4.3,
    "سامان": 5.7,
    "ومپنا": 10,
    "نیشکر": 0.95,
    "فجهان": 13,
    "شرانل": 11,
    "ارفع": 10,
    "هرمز": 11,
    "فغدیر": 6,
    "شگویا": 23,
    "شاوان": 28,
    "اهرم": None,
    "توان": None,
    "موج": None,
    "جوانه کوچک": None,
    "دزاگرس": 32,
    "دارا یکم": None,
    "پالایش": None,
    "شتاب": None,
    "جهش": None,
    "فنقره": 25,
    "قچار": 35,
    "زاگرس": 10,
    "ددانا": 9,
    "حگهر": 12,
    "حسینا": 16,
    "غصینو": 22,
    "غمینو": 31,
    "دماوند": 13,
    "بمپنا": 13,
    "بپاس": 23,
    "کزغال": 18,
}

STOCK_DETAIL_FIELDS = (
    "ins_code",
    "market_date",
    "company",
    "industry",
    "market_value",
    "last_price",
    "yesterday_price",
    "last_price_change_percent",
    "closing_price",
    "closing_price_change_percent",
    "price_power",
    "price_power_status",
    "daily_high_price",
    "daily_low_price",
    "daily_upper_price",
    "daily_lower_price",
    "trade_value",
    "trade_to_float_percent",
    "real_money_flow",
    "money_flow_quality",
    "real_buy_per_capita",
    "real_sell_per_capita",
    "real_buy_power",
    "trade_volume",
    "share_count",
    "floating_share_percent",
    "real_buy_volume",
    "real_buy_count",
    "legal_buy_volume",
    "legal_buy_count",
    "real_sell_volume",
    "real_sell_count",
    "legal_sell_volume",
    "legal_sell_count",
    "monthly_average_volume",
    "order_book_value",
    "order_book_volume",
    "order_book_count",
    "order_book_buy_value",
    "order_book_buy_volume",
    "order_book_buy_count",
    "order_book_sell_value",
    "order_book_sell_volume",
    "order_book_sell_count",
)

STOCK_HISTORY_METRICS = {
    "price_power": "قدرت قیمت",
    "trade_value": "ارزش معاملات",
    "trade_to_float_percent": "نسبت معامله به شناوری",
    "real_money_flow": "ورود پول حقیقی",
    "money_flow_quality": "کیفیت ورود پول",
    "real_buy_per_capita": "سرانه خرید حقیقی",
    "real_sell_per_capita": "سرانه فروش حقیقی",
    "real_buy_power": "قدرت خرید حقیقی",
}

STOCK_DATABASE_EXTRA_COLUMNS = {
    "ins_code": "TEXT",
    "market_date": "TEXT",
    "last_price": "INTEGER",
    "yesterday_price": "INTEGER",
    "last_price_change_percent": "REAL",
    "closing_price": "INTEGER",
    "closing_price_change_percent": "REAL",
    "price_power": "INTEGER",
    "price_power_status": "TEXT",
    "daily_high_price": "INTEGER",
    "daily_low_price": "INTEGER",
    "daily_upper_price": "INTEGER",
    "daily_lower_price": "INTEGER",
    "trade_value": "INTEGER",
    "trade_to_float_percent": "REAL",
    "real_money_flow": "INTEGER",
    "money_flow_quality": "REAL",
    "real_buy_per_capita": "INTEGER",
    "real_sell_per_capita": "INTEGER",
    "real_buy_power": "REAL",
    "trade_volume": "INTEGER",
    "share_count": "INTEGER",
    "floating_share_percent": "REAL",
    "real_buy_volume": "INTEGER",
    "real_buy_count": "INTEGER",
    "legal_buy_volume": "INTEGER",
    "legal_buy_count": "INTEGER",
    "real_sell_volume": "INTEGER",
    "real_sell_count": "INTEGER",
    "legal_sell_volume": "INTEGER",
    "legal_sell_count": "INTEGER",
    "monthly_average_volume": "INTEGER",
    "order_book_value": "INTEGER",
    "order_book_volume": "INTEGER",
    "order_book_count": "INTEGER",
    "order_book_buy_value": "INTEGER",
    "order_book_buy_volume": "INTEGER",
    "order_book_buy_count": "INTEGER",
    "order_book_sell_value": "INTEGER",
    "order_book_sell_volume": "INTEGER",
    "order_book_sell_count": "INTEGER",
}

# جلوگیری از خواندن/نوشتن همزمان فایل سفارشات
order_book_snapshot_lock = threading.Lock()


def load_stock_symbols():
    """Load the small, ordered symbol allow-list kept by the application."""
    with open(STOCK_SYMBOLS_FILE, "r", encoding="utf-8") as file:
        values = json.load(file)

    if not isinstance(values, list):
        raise ValueError("ساختار فایل نمادهای سهام معتبر نیست.")

    symbols = []
    seen = set()
    for value in values:
        symbol = str(value or "").strip()
        normalized = normalize_symbol(symbol)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        symbols.append(symbol)

    if not symbols:
        raise ValueError("فهرست نمادهای سهام خالی است.")

    return symbols


def stock_number(value):
    """Convert numeric TSETMC fields without treating zero as missing."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def stock_integer(value):
    """Return an integer for count/volume fields while preserving missing values."""
    number = stock_number(value)
    return int(round(number)) if number is not None else None


def clean_stock_text(value):
    text = str(value or "").strip().translate(
        str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
    )
    return re.sub(r"\s+", " ", text)


def is_all_stock_equity_instrument(
    symbol,
    instrument_id=None,
    company=None,
    category=None,
    session_type=None,
):
    """Keep ordinary equity rows; reject funds and numbered side instruments."""
    clean_symbol = clean_stock_text(symbol)
    if not clean_symbol or re.search(r"[0-9۰-۹]+$", clean_symbol):
        return False

    clean_company = clean_stock_text(company)
    if "صندوق" in clean_company or "گواهی سپرده" in clean_company:
        return False
    if clean_stock_text(category).upper() in ALL_STOCK_EXTENDED_CATEGORIES:
        return False

    clean_instrument_id = str(instrument_id or "").strip().upper()
    if clean_instrument_id:
        return clean_instrument_id.startswith(
            ALL_STOCK_EQUITY_INSTRUMENT_PREFIXES
        )

    return str(session_type or "standard") != "extended"


@contextmanager
def stock_database_connection():
    connection = sqlite3.connect(STOCK_DATABASE_FILE, timeout=15)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_stock_database():
    global stock_database_ready

    if stock_database_ready:
        return

    with stock_database_lock:
        if stock_database_ready:
            return

        os.makedirs(os.path.dirname(STOCK_DATABASE_FILE), exist_ok=True)
        symbols = load_stock_symbols()

        with stock_database_connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stocks (
                    symbol TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    company TEXT,
                    industry TEXT,
                    market_value INTEGER,
                    ins_code TEXT,
                    market_date TEXT,
                    last_price INTEGER,
                    last_price_change_percent REAL,
                    closing_price INTEGER,
                    closing_price_change_percent REAL,
                    price_power INTEGER,
                    price_power_status TEXT,
                    daily_high_price INTEGER,
                    daily_low_price INTEGER,
                    daily_upper_price INTEGER,
                    daily_lower_price INTEGER,
                    trade_value INTEGER,
                    trade_to_float_percent REAL,
                    real_money_flow INTEGER,
                    money_flow_quality REAL,
                    real_buy_per_capita INTEGER,
                    real_sell_per_capita INTEGER,
                    real_buy_power REAL,
                    trade_volume INTEGER,
                    share_count INTEGER,
                    floating_share_percent REAL,
                    real_buy_volume INTEGER,
                    real_buy_count INTEGER,
                    legal_buy_volume INTEGER,
                    legal_buy_count INTEGER,
                    real_sell_volume INTEGER,
                    real_sell_count INTEGER,
                    legal_sell_volume INTEGER,
                    legal_sell_count INTEGER,
                    monthly_average_volume INTEGER,
                    order_book_value INTEGER,
                    order_book_volume INTEGER,
                    order_book_count INTEGER,
                    order_book_buy_value INTEGER,
                    order_book_buy_volume INTEGER,
                    order_book_buy_count INTEGER,
                    order_book_sell_value INTEGER,
                    order_book_sell_volume INTEGER,
                    order_book_sell_count INTEGER,
                    updated_at TEXT
                )
                """
            )
            existing_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(stocks)")
            }
            for column_name, column_type in STOCK_DATABASE_EXTRA_COLUMNS.items():
                if column_name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE stocks ADD COLUMN {column_name} {column_type}"
                    )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_watchlist (
                    symbol TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    data_json TEXT,
                    added_at TEXT NOT NULL,
                    updated_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_daily_snapshots (
                    trade_date TEXT NOT NULL,
                    trade_date_jalali TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (trade_date, symbol)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stock_daily_snapshots_symbol_date
                ON stock_daily_snapshots (symbol, trade_date DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS all_stocks (
                    symbol TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    category TEXT,
                    session_type TEXT NOT NULL,
                    trade_date TEXT,
                    captured_at TEXT NOT NULL,
                    data_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS all_stock_daily_snapshots (
                    trade_date TEXT NOT NULL,
                    trade_date_jalali TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    category TEXT,
                    session_type TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (trade_date, symbol)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_all_stock_daily_symbol_date
                ON all_stock_daily_snapshots (symbol, trade_date DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS all_stock_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history (
                    symbol TEXT NOT NULL,
                    ins_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    trade_date_jalali TEXT NOT NULL,
                    raw_closing_price REAL NOT NULL,
                    adjusted_closing_price REAL NOT NULL,
                    raw_last_price REAL,
                    daily_high_price REAL,
                    daily_low_price REAL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    PRIMARY KEY (symbol, trade_date)
                )
                """
            )
            price_history_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(stock_price_history)"
                )
            }
            for column_name in ("daily_high_price", "daily_low_price"):
                if column_name not in price_history_columns:
                    connection.execute(
                        "ALTER TABLE stock_price_history "
                        f"ADD COLUMN {column_name} REAL"
                    )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stock_price_history_symbol_date
                ON stock_price_history (symbol, trade_date DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_price_history_sync (
                    symbol TEXT PRIMARY KEY,
                    ins_code TEXT NOT NULL,
                    requested_days INTEGER NOT NULL,
                    stored_count INTEGER NOT NULL,
                    latest_trade_date TEXT,
                    synced_at TEXT NOT NULL,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_strategy_history (
                    symbol TEXT NOT NULL,
                    ins_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    trade_date_jalali TEXT NOT NULL,
                    trade_value REAL,
                    trade_volume REAL,
                    trade_count REAL,
                    price_power INTEGER,
                    trade_to_float_percent REAL,
                    trade_to_float_is_estimated INTEGER NOT NULL DEFAULT 0,
                    real_money_flow REAL,
                    money_flow_quality REAL,
                    real_buy_per_capita REAL,
                    real_sell_per_capita REAL,
                    real_buy_power REAL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    PRIMARY KEY (symbol, trade_date)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stock_strategy_history_symbol_date
                ON stock_strategy_history (symbol, trade_date DESC)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_strategy_history_sync (
                    symbol TEXT PRIMARY KEY,
                    ins_code TEXT NOT NULL,
                    requested_days INTEGER NOT NULL,
                    stored_count INTEGER NOT NULL,
                    latest_trade_date TEXT,
                    synced_at TEXT NOT NULL,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_daily_snapshots (
                    trade_date TEXT PRIMARY KEY,
                    trade_date_jalali TEXT,
                    source_market_date TEXT,
                    captured_at TEXT NOT NULL,
                    free_dollar_price REAL,
                    total_market_trade_value REAL,
                    money_flows_json TEXT NOT NULL,
                    industry_flows_json TEXT NOT NULL
                )
                """
            )
            market_snapshot_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(market_daily_snapshots)"
                )
            }
            if "source_market_date" not in market_snapshot_columns:
                connection.execute(
                    "ALTER TABLE market_daily_snapshots "
                    "ADD COLUMN source_market_date TEXT"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    note_text TEXT NOT NULL,
                    importance INTEGER NOT NULL CHECK (importance BETWEEN 1 AND 5),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stock_notes_symbol_updated
                ON stock_notes (symbol, updated_at DESC)
                """
            )

            existing_count = connection.execute(
                "SELECT COUNT(*) FROM stocks"
            ).fetchone()[0]

            if existing_count == 0:
                for position, symbol in enumerate(symbols):
                    connection.execute(
                        """
                        INSERT INTO stocks (symbol, position)
                        VALUES (?, ?)
                        """,
                        (symbol, position)
                    )
            else:
                for position, symbol in enumerate(symbols):
                    connection.execute(
                        """
                        INSERT INTO stocks (symbol, position)
                        VALUES (?, ?)
                        ON CONFLICT(symbol) DO UPDATE SET position = excluded.position
                        """,
                        (symbol, position)
                    )

            placeholders = ",".join("?" for _ in symbols)
            connection.execute(
                f"DELETE FROM stocks WHERE symbol NOT IN ({placeholders})",
                symbols
            )
            connection.executemany(
                """
                UPDATE stocks
                SET floating_share_percent = ?
                WHERE symbol = ?
                """,
                (
                    (percentage, symbol)
                    for symbol, percentage
                    in STOCK_FLOATING_SHARE_OVERRIDES.items()
                ),
            )

        stock_database_ready = True


def read_stock_database():
    initialize_stock_database()
    with stock_database_connection() as connection:
        rows = []
        for database_row in connection.execute(
            f"""
            SELECT symbol, {", ".join(STOCK_DETAIL_FIELDS)}
            FROM stocks
            ORDER BY position
            """
        ).fetchall():
            row = {
                "symbol": database_row["symbol"],
                **{
                    field: database_row[field]
                    for field in STOCK_DETAIL_FIELDS
                },
            }
            apply_stock_floating_share_override(row)
            row.update(calculate_stock_indicators(row))
            rows.append(row)
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM stock_metadata"
            ).fetchall()
        }
    return rows, metadata


def read_all_stock_database():
    """Read the last finalized row for every share and exchange-traded fund."""
    initialize_stock_database()
    with stock_database_connection() as connection:
        records = connection.execute(
            """
            SELECT
                symbol,
                position,
                category,
                session_type,
                trade_date,
                captured_at,
                data_json
            FROM all_stocks
            ORDER BY position, symbol COLLATE NOCASE
            """
        ).fetchall()
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM all_stock_metadata"
            ).fetchall()
        }

    rows = []
    for record in records:
        try:
            row = json.loads(record["data_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            row = {}
        if not isinstance(row, dict):
            row = {}
        row.update({
            "symbol": record["symbol"],
            "category": record["category"],
            "session_type": record["session_type"],
            "snapshot_date": record["trade_date"],
            "captured_at": record["captured_at"],
        })
        if not is_all_stock_equity_instrument(
            row.get("symbol"),
            row.get("instrument_id"),
            row.get("company"),
            row.get("category"),
            row.get("session_type"),
        ):
            continue
        apply_stock_floating_share_override(row)
        row.update(calculate_stock_indicators(row))
        rows.append(row)
    return rows, metadata


def all_stock_due_phases(current_time, metadata=None):
    """Return daily close phases that have reached their cutoff and are unsaved."""
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    metadata = metadata or {}
    trade_date = current_time.date().isoformat()
    current_minute = current_time.hour * 60 + current_time.minute
    phases = []
    if (
        current_minute >= STOCK_STANDARD_SNAPSHOT_MINUTE
        and metadata.get("standard_completed_date") != trade_date
    ):
        phases.append("standard")
    return phases


def save_all_stock_phase(rows, phase, captured_at=None):
    """Atomically publish and archive one complete-market close phase."""
    if phase not in {"standard", "extended"}:
        raise ValueError("بازه معاملاتی تمام سهام معتبر نیست.")
    prepared_rows = [
        dict(row)
        for row in rows
        if isinstance(row, dict)
        and row.get("symbol")
        and row.get("session_type") == phase
        and is_all_stock_equity_instrument(
            row.get("symbol"),
            row.get("instrument_id"),
            row.get("company"),
            row.get("category"),
            row.get("session_type"),
        )
    ]
    if not prepared_rows:
        raise RuntimeError("داده‌ای برای ثبت روزانه تمام سهام دریافت نشد.")

    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    completed_date = current_time.date().isoformat()
    captured_at_iso = current_time.isoformat()
    snapshot_count = 0
    has_current_market_data = any(
        normalize_stock_market_date(row.get("market_date")) == completed_date
        for row in prepared_rows
    )
    published_rows = prepared_rows if has_current_market_data else []

    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        if published_rows:
            connection.execute(
                "DELETE FROM all_stocks WHERE session_type = ?",
                (phase,),
            )
        for fallback_position, row in enumerate(published_rows):
            apply_stock_floating_share_override(row)
            row.update(calculate_stock_indicators(row))
            symbol = clean_stock_text(row.get("symbol"))
            category = clean_stock_text(row.get("category"))
            market_date = normalize_stock_market_date(row.get("market_date"))
            position = stock_integer(row.get("position"))
            if position is None:
                position = fallback_position
            payload = json.dumps(
                row,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            connection.execute(
                """
                INSERT INTO all_stocks (
                    symbol,
                    position,
                    category,
                    session_type,
                    trade_date,
                    captured_at,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    position,
                    category,
                    phase,
                    market_date,
                    captured_at_iso,
                    payload,
                ),
            )

            # Do not create a duplicate daily row on holidays or when TSETMC is
            # still reporting a previous market day.
            if market_date != completed_date:
                continue
            market_day = datetime.strptime(market_date, "%Y-%m-%d").date()
            jalali_date = jdatetime.date.fromgregorian(
                date=market_day
            ).strftime("%Y-%m-%d")
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO all_stock_daily_snapshots (
                    trade_date,
                    trade_date_jalali,
                    symbol,
                    category,
                    session_type,
                    captured_at,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    market_date,
                    jalali_date,
                    symbol,
                    category,
                    phase,
                    captured_at_iso,
                    payload,
                ),
            )
            snapshot_count += max(cursor.rowcount, 0)

        metadata = {
            f"{phase}_completed_date": completed_date,
            f"{phase}_checked_at": captured_at_iso,
        }
        if published_rows:
            metadata.update({
                f"{phase}_updated_at": captured_at_iso,
                f"{phase}_count": str(len(published_rows)),
                "last_successful_update": captured_at_iso,
            })
        connection.executemany(
            """
            INSERT INTO all_stock_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            metadata.items(),
        )

    daily_price_rows = [
        row
        for row in published_rows
        if normalize_stock_market_date(row.get("market_date")) == completed_date
    ]
    save_daily_stock_price_points(daily_price_rows, current_time)
    save_daily_stock_strategy_points(daily_price_rows, current_time)

    return {
        "phase": phase,
        "completed_date": completed_date,
        "row_count": len(published_rows),
        "snapshot_count": snapshot_count,
    }


def publish_all_stock_current_phase(rows, phase, captured_at=None):
    """Publish fresh complete-market rows without changing the daily archive."""
    if phase not in {"standard", "extended"}:
        raise ValueError("بازه معاملاتی تمام سهام معتبر نیست.")
    prepared_rows = [
        dict(row)
        for row in rows
        if isinstance(row, dict)
        and row.get("symbol")
        and row.get("session_type") == phase
        and is_all_stock_equity_instrument(
            row.get("symbol"),
            row.get("instrument_id"),
            row.get("company"),
            row.get("category"),
            row.get("session_type"),
        )
    ]
    if not prepared_rows:
        raise RuntimeError("داده‌ای برای به‌روزرسانی تمام سهام دریافت نشد.")

    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    current_date = current_time.date().isoformat()
    captured_at_iso = current_time.isoformat()
    has_current_market_data = any(
        normalize_stock_market_date(row.get("market_date")) == current_date
        for row in prepared_rows
    )
    if not has_current_market_data:
        return {
            "phase": phase,
            "row_count": 0,
            "published": False,
        }

    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM all_stocks WHERE session_type = ?",
            (phase,),
        )
        for fallback_position, row in enumerate(prepared_rows):
            apply_stock_floating_share_override(row)
            row.update(calculate_stock_indicators(row))
            symbol = clean_stock_text(row.get("symbol"))
            position = stock_integer(row.get("position"))
            if position is None:
                position = fallback_position
            connection.execute(
                """
                INSERT INTO all_stocks (
                    symbol,
                    position,
                    category,
                    session_type,
                    trade_date,
                    captured_at,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    position,
                    clean_stock_text(row.get("category")),
                    phase,
                    normalize_stock_market_date(row.get("market_date")),
                    captured_at_iso,
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ),
            )
        connection.executemany(
            """
            INSERT INTO all_stock_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            {
                f"{phase}_manual_updated_at": captured_at_iso,
                f"{phase}_count": str(len(prepared_rows)),
                "last_manual_update": captured_at_iso,
                "last_successful_update": captured_at_iso,
            }.items(),
        )

    return {
        "phase": phase,
        "row_count": len(prepared_rows),
        "published": True,
    }


def read_all_stock_daily_snapshots(trade_date=None, symbol=None):
    """Read the complete-market daily archive, newest market day by default."""
    initialize_stock_database()
    requested_symbol = normalize_symbol(symbol) if symbol else None
    with stock_database_connection() as connection:
        selected_date = trade_date
        if not selected_date:
            record = connection.execute(
                "SELECT MAX(trade_date) AS trade_date "
                "FROM all_stock_daily_snapshots"
            ).fetchone()
            selected_date = record["trade_date"] if record else None
        if not selected_date:
            return [], None
        records = connection.execute(
            """
            SELECT
                trade_date,
                trade_date_jalali,
                symbol,
                category,
                session_type,
                captured_at,
                data_json
            FROM all_stock_daily_snapshots
            WHERE trade_date = ?
            ORDER BY symbol COLLATE NOCASE
            """,
            (selected_date,),
        ).fetchall()

    snapshots = []
    for record in records:
        if requested_symbol and normalize_symbol(record["symbol"]) != requested_symbol:
            continue
        try:
            data = json.loads(record["data_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            data = {}
        snapshots.append({
            "trade_date": record["trade_date"],
            "trade_date_jalali": record["trade_date_jalali"],
            "symbol": record["symbol"],
            "category": record["category"],
            "session_type": record["session_type"],
            "captured_at": record["captured_at"],
            "data": data if isinstance(data, dict) else {},
        })
    return snapshots, selected_date


def read_stock_watchlist():
    initialize_stock_database()
    with stock_database_connection() as connection:
        records = connection.execute(
            """
            SELECT symbol, data_json, added_at, updated_at
            FROM stock_watchlist
            ORDER BY position
            """
        ).fetchall()

    rows = []
    for record in records:
        try:
            row = json.loads(record["data_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            row = {}
        if not isinstance(row, dict):
            row = {}
        row["symbol"] = record["symbol"]
        apply_stock_floating_share_override(row)
        row.update(calculate_stock_indicators(row))
        rows.append(row)

    return rows


def normalize_stock_note_input(symbol, note_text, importance):
    normalized_symbol = normalize_symbol(symbol)
    if not normalized_symbol:
        raise ValueError("نام نماد الزامی است.")

    normalized_text = str(note_text or "").strip()
    if not normalized_text:
        raise ValueError("متن یادداشت را وارد کنید.")
    if len(normalized_text) > 4000:
        raise ValueError("متن یادداشت نباید بیشتر از ۴۰۰۰ نویسه باشد.")

    if isinstance(importance, bool):
        raise ValueError("درجه اهمیت باید عددی بین ۱ تا ۵ باشد.")
    try:
        normalized_importance = int(importance)
    except (TypeError, ValueError):
        raise ValueError("درجه اهمیت باید عددی بین ۱ تا ۵ باشد.") from None
    if normalized_importance not in range(1, 6):
        raise ValueError("درجه اهمیت باید عددی بین ۱ تا ۵ باشد.")

    return normalized_symbol, normalized_text, normalized_importance


def serialize_stock_note(database_row):
    return {
        "id": database_row["id"],
        "symbol": database_row["symbol"],
        "text": database_row["note_text"],
        "importance": database_row["importance"],
        "created_at": database_row["created_at"],
        "updated_at": database_row["updated_at"],
    }


def read_stock_notes(symbol=None):
    initialize_stock_database()
    normalized_symbol = normalize_symbol(symbol) if symbol else None
    with stock_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, symbol, note_text, importance, created_at, updated_at
            FROM stock_notes
            ORDER BY symbol COLLATE NOCASE, importance DESC, updated_at DESC, id DESC
            """
        ).fetchall()

    if normalized_symbol:
        rows = [
            row
            for row in rows
            if normalize_symbol(row["symbol"]) == normalized_symbol
        ]
    return [serialize_stock_note(row) for row in rows]


def create_stock_note(symbol, note_text, importance):
    symbol, note_text, importance = normalize_stock_note_input(
        symbol,
        note_text,
        importance,
    )
    now = datetime.now(IRAN_TIMEZONE).isoformat()
    initialize_stock_database()
    with stock_database_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO stock_notes (
                symbol, note_text, importance, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (symbol, note_text, importance, now, now),
        )
        row = connection.execute(
            """
            SELECT id, symbol, note_text, importance, created_at, updated_at
            FROM stock_notes
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return serialize_stock_note(row)


def update_stock_note(note_id, note_text, importance):
    try:
        normalized_note_id = int(note_id)
    except (TypeError, ValueError):
        raise ValueError("شناسه یادداشت نامعتبر است.") from None

    initialize_stock_database()
    with stock_database_connection() as connection:
        existing = connection.execute(
            "SELECT symbol FROM stock_notes WHERE id = ?",
            (normalized_note_id,),
        ).fetchone()
        if existing is None:
            return None

        _, note_text, importance = normalize_stock_note_input(
            existing["symbol"],
            note_text,
            importance,
        )
        connection.execute(
            """
            UPDATE stock_notes
            SET note_text = ?, importance = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                note_text,
                importance,
                datetime.now(IRAN_TIMEZONE).isoformat(),
                normalized_note_id,
            ),
        )
        row = connection.execute(
            """
            SELECT id, symbol, note_text, importance, created_at, updated_at
            FROM stock_notes
            WHERE id = ?
            """,
            (normalized_note_id,),
        ).fetchone()
    return serialize_stock_note(row)


def delete_stock_note(note_id):
    try:
        normalized_note_id = int(note_id)
    except (TypeError, ValueError):
        return False

    initialize_stock_database()
    with stock_database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM stock_notes WHERE id = ?",
            (normalized_note_id,),
        )
    return cursor.rowcount > 0


def save_stock_watchlist_row(row):
    symbol = str(row.get("symbol") or "").strip()
    if not symbol:
        raise ValueError("نماد معتبر نیست.")

    apply_stock_floating_share_override(row)
    now = datetime.now(IRAN_TIMEZONE).isoformat()
    payload = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    initialize_stock_database()
    with stock_database_connection() as connection:
        existing = connection.execute(
            "SELECT position, added_at FROM stock_watchlist WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        if existing:
            position = existing["position"]
            added_at = existing["added_at"]
        else:
            position = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 FROM stock_watchlist"
            ).fetchone()[0]
            added_at = now

        connection.execute(
            """
            INSERT INTO stock_watchlist (
                symbol, position, data_json, added_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                data_json = excluded.data_json,
                updated_at = excluded.updated_at
            """,
            (symbol, position, payload, added_at, now),
        )

    return row


def delete_stock_watchlist_symbol(symbol):
    target = normalize_symbol(symbol)
    initialize_stock_database()
    with stock_database_connection() as connection:
        records = connection.execute(
            "SELECT symbol FROM stock_watchlist ORDER BY position"
        ).fetchall()
        stored_symbol = next(
            (
                record["symbol"]
                for record in records
                if normalize_symbol(record["symbol"]) == target
            ),
            None,
        )
        if not stored_symbol:
            return False

        connection.execute(
            "DELETE FROM stock_watchlist WHERE symbol = ?",
            (stored_symbol,),
        )
        remaining = connection.execute(
            "SELECT symbol FROM stock_watchlist ORDER BY position"
        ).fetchall()
        connection.executemany(
            "UPDATE stock_watchlist SET position = ? WHERE symbol = ?",
            ((position, record["symbol"]) for position, record in enumerate(remaining)),
        )
    return True


def replace_stock_database(rows, updated_at, resolved_count):
    """Atomically replace the catalogue so readers keep seeing old data until commit."""
    initialize_stock_database()
    symbols = load_stock_symbols()
    by_symbol = {
        normalize_symbol(row.get("symbol")): row
        for row in rows
        if isinstance(row, dict) and row.get("symbol")
    }

    with stock_database_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM stocks")
        insert_columns = (
            "symbol",
            "position",
            *STOCK_DETAIL_FIELDS,
            "updated_at",
        )
        insert_sql = (
            f"INSERT INTO stocks ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join('?' for _ in insert_columns)})"
        )
        for position, symbol in enumerate(symbols):
            row = {
                **by_symbol.get(normalize_symbol(symbol), {}),
                "symbol": symbol,
            }
            apply_stock_floating_share_override(row)
            connection.execute(
                insert_sql,
                (
                    symbol,
                    position,
                    *(row.get(field) for field in STOCK_DETAIL_FIELDS),
                    updated_at,
                ),
            )

        metadata = {
            "last_successful_update": updated_at,
            "last_successful_update_epoch": str(time.time()),
            "resolved_count": str(resolved_count)
        }
        connection.executemany(
            """
            INSERT INTO stock_metadata (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            metadata.items()
        )


def normalize_stock_market_date(value):
    """Convert TSETMC's YYYYMMDD market date to an ISO date."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) != 8:
        return None

    try:
        return datetime.strptime(digits, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def parse_tsetmc_price_history(payload, limit=STOCK_PRICE_HISTORY_TARGET_DAYS):
    """Normalize and adjust TSETMC daily closes to the newest price scale."""
    raw_rows = payload.get("closingPriceDaily") if isinstance(payload, dict) else []
    parsed_rows = []
    for item in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(item, dict):
            continue
        trade_date = normalize_stock_market_date(item.get("dEven"))
        closing_price = stock_number(item.get("pClosing"))
        if not trade_date or closing_price is None or closing_price <= 0:
            continue
        parsed_rows.append({
            "trade_date": trade_date,
            "raw_closing_price": closing_price,
            "raw_last_price": stock_number(item.get("pDrCotVal")),
            "daily_high_price": stock_number(item.get("priceMax")),
            "daily_low_price": stock_number(item.get("priceMin")),
            "yesterday_price": stock_number(item.get("priceYesterday")),
            "trade_value": stock_number(item.get("qTotCap")),
            "trade_volume": stock_number(item.get("qTotTran5J")),
            "trade_count": stock_number(item.get("zTotTran")),
        })

    parsed_rows.sort(key=lambda item: item["trade_date"], reverse=True)
    parsed_rows = parsed_rows[:max(1, int(limit or STOCK_PRICE_HISTORY_TARGET_DAYS))]
    cumulative_adjustment = 1.0
    adjusted_rows = []
    for index, item in enumerate(parsed_rows):
        adjusted_rows.append({
            **item,
            "adjusted_closing_price": round(
                item["raw_closing_price"] * cumulative_adjustment,
                6,
            ),
        })
        if index + 1 >= len(parsed_rows):
            continue
        older_closing = parsed_rows[index + 1]["raw_closing_price"]
        yesterday_price = item.get("yesterday_price")
        if (
            yesterday_price is not None
            and yesterday_price > 0
            and older_closing > 0
        ):
            cumulative_adjustment *= yesterday_price / older_closing
    return adjusted_rows


def fetch_stock_price_history(
    symbol,
    ins_code,
    limit=STOCK_PRICE_HISTORY_TARGET_DAYS,
):
    """Fetch the latest daily closing-price history for one TSETMC instrument."""
    safe_limit = max(1, min(int(limit or STOCK_PRICE_HISTORY_TARGET_DAYS), 500))
    payload = fetch_tsetmc_json(
        "https://cdn.tsetmc.com/api/ClosingPrice/"
        f"GetClosingPriceDailyList/{ins_code}/{safe_limit}",
        attempts=3,
    )
    return parse_tsetmc_price_history(payload, safe_limit)


def store_stock_price_history(
    symbol,
    ins_code,
    points,
    requested_days=STOCK_PRICE_HISTORY_TARGET_DAYS,
    captured_at=None,
):
    """Upsert one symbol's adjusted history and record backfill coverage."""
    clean_symbol = clean_stock_text(symbol)
    clean_ins_code = str(ins_code or "").strip()
    if not clean_symbol or not clean_ins_code:
        raise ValueError("نماد یا شناسه TSETMC برای تاریخچه قیمت معتبر نیست.")
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    captured_at_iso = current_time.isoformat()
    prepared_points = []
    for point in points or []:
        trade_date = str(point.get("trade_date") or "")
        adjusted_price = stock_number(point.get("adjusted_closing_price"))
        raw_price = stock_number(point.get("raw_closing_price"))
        if not trade_date or adjusted_price is None or raw_price is None:
            continue
        market_day = datetime.strptime(trade_date, "%Y-%m-%d").date()
        prepared_points.append((
            clean_symbol,
            clean_ins_code,
            trade_date,
            jdatetime.date.fromgregorian(date=market_day).strftime("%Y-%m-%d"),
            raw_price,
            adjusted_price,
            stock_number(point.get("raw_last_price")),
            stock_number(point.get("daily_high_price")),
            stock_number(point.get("daily_low_price")),
            captured_at_iso,
            "tsetmc_history",
        ))

    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.executemany(
            """
            INSERT INTO stock_price_history (
                symbol,
                ins_code,
                trade_date,
                trade_date_jalali,
                raw_closing_price,
                adjusted_closing_price,
                raw_last_price,
                daily_high_price,
                daily_low_price,
                captured_at,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                ins_code = excluded.ins_code,
                trade_date_jalali = excluded.trade_date_jalali,
                raw_closing_price = excluded.raw_closing_price,
                adjusted_closing_price = excluded.adjusted_closing_price,
                raw_last_price = excluded.raw_last_price,
                daily_high_price = excluded.daily_high_price,
                daily_low_price = excluded.daily_low_price,
                captured_at = excluded.captured_at,
                source = excluded.source
            """,
            prepared_points,
        )
        latest_trade_date = max(
            (point[2] for point in prepared_points),
            default=None,
        )
        connection.execute(
            """
            INSERT INTO stock_price_history_sync (
                symbol,
                ins_code,
                requested_days,
                stored_count,
                latest_trade_date,
                synced_at,
                error
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(symbol) DO UPDATE SET
                ins_code = excluded.ins_code,
                requested_days = excluded.requested_days,
                stored_count = excluded.stored_count,
                latest_trade_date = excluded.latest_trade_date,
                synced_at = excluded.synced_at,
                error = NULL
            """,
            (
                clean_symbol,
                clean_ins_code,
                int(requested_days),
                len(prepared_points),
                latest_trade_date,
                captured_at_iso,
            ),
        )
    return len(prepared_points)


def mark_stock_price_history_error(symbol, ins_code, error, captured_at=None):
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO stock_price_history_sync (
                symbol, ins_code, requested_days, stored_count,
                latest_trade_date, synced_at, error
            )
            VALUES (?, ?, 0, 0, NULL, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                ins_code = excluded.ins_code,
                synced_at = excluded.synced_at,
                error = excluded.error
            """,
            (
                clean_stock_text(symbol),
                str(ins_code or "").strip(),
                current_time.astimezone(IRAN_TIMEZONE).isoformat(),
                str(error),
            ),
        )


def pending_stock_price_history_rows(
    rows,
    target_days=STOCK_PRICE_HISTORY_TARGET_DAYS,
):
    """Return instruments whose one-time adjusted-price backfill is incomplete."""
    initialize_stock_database()
    with stock_database_connection() as connection:
        sync_rows = {
            normalize_symbol(record["symbol"]): record
            for record in connection.execute(
                """
                SELECT symbol, ins_code, requested_days, stored_count,
                       synced_at, error
                FROM stock_price_history_sync
                """
            ).fetchall()
        }
        range_coverage = {
            normalize_symbol(record["symbol"]): (
                int(record["total_count"] or 0),
                int(record["range_count"] or 0),
            )
            for record in connection.execute(
                """
                SELECT
                    symbol,
                    COUNT(*) AS total_count,
                    SUM(
                        CASE
                            WHEN daily_high_price IS NOT NULL
                             AND daily_low_price IS NOT NULL
                            THEN 1 ELSE 0
                        END
                    ) AS range_count
                FROM (
                    SELECT
                        symbol,
                        daily_high_price,
                        daily_low_price,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol
                            ORDER BY trade_date DESC
                        ) AS row_number
                    FROM stock_price_history
                    WHERE source = 'tsetmc_history'
                )
                WHERE row_number <= ?
                GROUP BY symbol
                """,
                (int(target_days),),
            ).fetchall()
        }
    pending = []
    seen = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = clean_stock_text(row.get("symbol"))
        ins_code = str(row.get("ins_code") or "").strip()
        normalized_symbol = normalize_symbol(symbol)
        if not symbol or not ins_code or normalized_symbol in seen:
            continue
        seen.add(normalized_symbol)
        sync = sync_rows.get(normalized_symbol)
        needs_refresh = (
            sync is None
            or str(sync["ins_code"] or "") != ins_code
        )
        if sync is not None and not needs_refresh:
            if sync["error"]:
                try:
                    last_attempt = datetime.fromisoformat(sync["synced_at"])
                    if last_attempt.tzinfo is None:
                        last_attempt = last_attempt.replace(tzinfo=IRAN_TIMEZONE)
                    needs_refresh = (
                        datetime.now(IRAN_TIMEZONE) - last_attempt
                        >= timedelta(hours=6)
                    )
                except (TypeError, ValueError):
                    needs_refresh = True
            else:
                needs_refresh = (
                    int(sync["requested_days"] or 0) < int(target_days)
                )
                total_count, range_count = range_coverage.get(
                    normalized_symbol,
                    (0, 0),
                )
                if total_count > 0 and range_count < total_count:
                    needs_refresh = True
        if needs_refresh:
            pending.append({"symbol": symbol, "ins_code": ins_code})
    return pending


def refresh_stock_price_history(instruments):
    """Backfill adjusted closes concurrently while serializing SQLite writes."""
    errors = []
    stored_points = 0
    try:
        with ThreadPoolExecutor(
            max_workers=min(STOCK_PRICE_HISTORY_WORKERS, len(instruments))
        ) as executor:
            futures = {
                executor.submit(
                    fetch_stock_price_history,
                    instrument["symbol"],
                    instrument["ins_code"],
                    STOCK_PRICE_HISTORY_TARGET_DAYS,
                ): instrument
                for instrument in instruments
            }
            for future in as_completed(futures):
                instrument = futures[future]
                try:
                    points = future.result()
                    stored_points += store_stock_price_history(
                        instrument["symbol"],
                        instrument["ins_code"],
                        points,
                    )
                except Exception as error:
                    errors.append(f"{instrument['symbol']}: {error}")
                    try:
                        mark_stock_price_history_error(
                            instrument["symbol"],
                            instrument["ins_code"],
                            error,
                        )
                    except sqlite3.Error:
                        pass
                finally:
                    with stock_price_history_lock:
                        stock_price_history_state["completed"] += 1
                        stock_price_history_state["stored_points"] = stored_points
                        stock_price_history_state["errors"] = len(errors)
    except Exception as error:
        errors.append(str(error))
    finally:
        with stock_price_history_lock:
            stock_price_history_state["running"] = False
            stock_price_history_state["stored_points"] = stored_points
            stock_price_history_state["errors"] = len(errors)
            stock_price_history_state["error"] = (
                f"تاریخچه قیمت {len(errors)} نماد کامل نشد."
                if errors else None
            )


def start_stock_price_history_backfill(rows):
    """Start the missing 500-session backfill without delaying page responses."""
    pending = pending_stock_price_history_rows(rows)
    if not pending:
        with stock_price_history_lock:
            if not stock_price_history_state["running"]:
                stock_price_history_state.update({
                    "total": len(rows or []),
                    "completed": len(rows or []),
                    "errors": 0,
                    "error": None,
                })
        return False
    with stock_price_history_lock:
        if stock_price_history_state["running"]:
            return False
        stock_price_history_state.update({
            "running": True,
            "started_at": datetime.now(IRAN_TIMEZONE).isoformat(),
            "total": len(pending),
            "completed": 0,
            "stored_points": 0,
            "errors": 0,
            "error": None,
        })
    threading.Thread(
        target=refresh_stock_price_history,
        args=(pending,),
        name="stock-price-history-backfill",
        daemon=True,
    ).start()
    return True


def save_daily_stock_price_points(rows, captured_at=None):
    """Append one daily close and rebase prior prices after corporate actions."""
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    captured_at_iso = current_time.isoformat()
    prepared_rows = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = clean_stock_text(row.get("symbol"))
        ins_code = str(row.get("ins_code") or "").strip()
        trade_date = normalize_stock_market_date(row.get("market_date"))
        closing_price = stock_number(row.get("closing_price"))
        if not symbol or not ins_code or not trade_date or not closing_price:
            continue
        prepared_rows.append((symbol, ins_code, trade_date, closing_price, row))
    if not prepared_rows:
        return 0

    inserted_count = 0
    initialize_stock_database()
    with stock_database_connection() as connection:
        for symbol, ins_code, trade_date, closing_price, row in prepared_rows:
            exists = connection.execute(
                """
                SELECT 1 FROM stock_price_history
                WHERE symbol = ? AND trade_date = ?
                """,
                (symbol, trade_date),
            ).fetchone()
            if exists:
                connection.execute(
                    """
                    UPDATE stock_price_history
                    SET ins_code = ?,
                        raw_closing_price = ?,
                        adjusted_closing_price = ?,
                        raw_last_price = COALESCE(?, raw_last_price),
                        daily_high_price = COALESCE(?, daily_high_price),
                        daily_low_price = COALESCE(?, daily_low_price),
                        captured_at = ?
                    WHERE symbol = ? AND trade_date = ?
                    """,
                    (
                        ins_code,
                        closing_price,
                        closing_price,
                        stock_number(row.get("last_price")),
                        stock_number(row.get("daily_high_price")),
                        stock_number(row.get("daily_low_price")),
                        captured_at_iso,
                        symbol,
                        trade_date,
                    ),
                )
                continue
            previous = connection.execute(
                """
                SELECT trade_date, raw_closing_price
                FROM stock_price_history
                WHERE symbol = ? AND trade_date < ?
                ORDER BY trade_date DESC
                LIMIT 1
                """,
                (symbol, trade_date),
            ).fetchone()
            yesterday_price = stock_number(row.get("yesterday_price"))
            if previous and yesterday_price and previous["raw_closing_price"]:
                adjustment = yesterday_price / previous["raw_closing_price"]
                if abs(adjustment - 1) > 0.000001:
                    connection.execute(
                        """
                        UPDATE stock_price_history
                        SET adjusted_closing_price = adjusted_closing_price * ?
                        WHERE symbol = ? AND trade_date < ?
                        """,
                        (adjustment, symbol, trade_date),
                    )
            market_day = datetime.strptime(trade_date, "%Y-%m-%d").date()
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO stock_price_history (
                    symbol, ins_code, trade_date, trade_date_jalali,
                    raw_closing_price, adjusted_closing_price,
                    raw_last_price, daily_high_price, daily_low_price,
                    captured_at, source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    ins_code,
                    trade_date,
                    jdatetime.date.fromgregorian(date=market_day).strftime("%Y-%m-%d"),
                    closing_price,
                    closing_price,
                    stock_number(row.get("last_price")),
                    stock_number(row.get("daily_high_price")),
                    stock_number(row.get("daily_low_price")),
                    captured_at_iso,
                    "daily_close",
                ),
            )
            inserted_count += max(cursor.rowcount, 0)
    return inserted_count


def read_stock_price_history(symbols=None):
    """Read adjusted closes newest-first, optionally limited to selected symbols."""
    requested_values = (
        sorted({clean_stock_text(symbol) for symbol in symbols if clean_stock_text(symbol)})
        if symbols is not None
        else None
    )
    requested_symbols = (
        {normalize_symbol(symbol) for symbol in requested_values}
        if requested_values is not None
        else None
    )
    initialize_stock_database()
    with stock_database_connection() as connection:
        if requested_values is None:
            records = connection.execute(
                """
                SELECT symbol, trade_date, raw_closing_price,
                       adjusted_closing_price, raw_last_price,
                       daily_high_price, daily_low_price
                FROM stock_price_history
                ORDER BY trade_date DESC
                """
            ).fetchall()
        else:
            records = []
            for offset in range(0, len(requested_values), 500):
                batch = requested_values[offset:offset + 500]
                placeholders = ",".join("?" for _ in batch)
                records.extend(connection.execute(
                    f"""
                    SELECT symbol, trade_date, raw_closing_price,
                           adjusted_closing_price, raw_last_price,
                           daily_high_price, daily_low_price
                    FROM stock_price_history
                    WHERE symbol IN ({placeholders})
                    ORDER BY trade_date DESC
                    """,
                    batch,
                ).fetchall())
    history = {}
    for record in records:
        normalized_symbol = normalize_symbol(record["symbol"])
        if requested_symbols is not None and normalized_symbol not in requested_symbols:
            continue
        history.setdefault(normalized_symbol, []).append({
            "trade_date": record["trade_date"],
            "closing_price": record["adjusted_closing_price"],
            "raw_closing_price": record["raw_closing_price"],
            "last_price": record["raw_last_price"],
            "daily_high_price": record["daily_high_price"],
            "daily_low_price": record["daily_low_price"],
        })
    return history


def parse_tsetmc_client_type_history(
    payload,
    limit=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
):
    """Normalize the newest historical real/legal trading rows by market date."""
    raw_rows = payload.get("clientType") if isinstance(payload, dict) else []
    parsed = []
    for item in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(item, dict):
            continue
        trade_date = normalize_stock_market_date(item.get("recDate"))
        if not trade_date:
            continue
        parsed.append({
            "trade_date": trade_date,
            "real_buy_value": stock_number(item.get("buy_I_Value")),
            "real_sell_value": stock_number(item.get("sell_I_Value")),
            "real_buy_count": stock_number(
                item.get("buy_I_Count")
                if item.get("buy_I_Count") is not None
                else item.get("buy_CountI")
            ),
            "real_sell_count": stock_number(
                item.get("sell_I_Count")
                if item.get("sell_I_Count") is not None
                else item.get("sell_CountI")
            ),
            "real_buy_volume": stock_number(item.get("buy_I_Volume")),
            "real_sell_volume": stock_number(item.get("sell_I_Volume")),
            "legal_buy_volume": stock_number(item.get("buy_N_Volume")),
            "legal_sell_volume": stock_number(item.get("sell_N_Volume")),
        })
    parsed.sort(key=lambda item: item["trade_date"], reverse=True)
    return parsed[:max(1, int(limit or STOCK_STRATEGY_HISTORY_TARGET_DAYS))]


def fetch_stock_client_type_history(
    ins_code,
    limit=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
):
    try:
        response = requests.get(
            f"https://old.tsetmc.com/tsev2/data/ClientType.aspx?i={ins_code}",
            headers=TSETMC_HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        rows = []
        for raw_row in response.text.strip().split(";"):
            fields = raw_row.split(",")
            if len(fields) < 13:
                continue
            trade_date = normalize_stock_market_date(fields[0])
            if not trade_date:
                continue
            rows.append({
                "trade_date": trade_date,
                "real_buy_count": stock_number(fields[1]),
                "real_sell_count": stock_number(fields[3]),
                "real_buy_volume": stock_number(fields[5]),
                "legal_buy_volume": stock_number(fields[6]),
                "real_sell_volume": stock_number(fields[7]),
                "legal_sell_volume": stock_number(fields[8]),
                "real_buy_value": stock_number(fields[9]),
                "real_sell_value": stock_number(fields[11]),
            })
            if len(rows) >= max(1, int(limit)):
                break
        if rows:
            return rows
    except requests.RequestException:
        pass

    payload = fetch_tsetmc_json(
        f"https://cdn.tsetmc.com/api/ClientType/GetClientTypeHistory/{ins_code}",
        attempts=3,
    )
    return parse_tsetmc_client_type_history(payload, limit)


def build_stock_strategy_history_points(
    price_points,
    client_points,
    share_count=None,
    floating_share_percent=None,
    limit=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
):
    """Combine price/value and client-type history into current strategy metrics."""
    client_by_date = {
        point["trade_date"]: point
        for point in client_points or []
        if point.get("trade_date")
    }
    shares = stock_number(share_count)
    floating_percent = stock_number(floating_share_percent)
    floating_share_count = (
        shares * floating_percent / 100
        if shares and shares > 0 and floating_percent and floating_percent > 0
        else None
    )
    results = []
    for price_point in (price_points or [])[:max(1, int(limit))]:
        trade_date = price_point.get("trade_date")
        if not trade_date:
            continue
        closing_price = stock_number(price_point.get("raw_closing_price"))
        last_price = stock_number(price_point.get("raw_last_price"))
        trade_value = stock_number(price_point.get("trade_value"))
        trade_volume = stock_number(price_point.get("trade_volume"))
        price_power = None
        if last_price is not None and closing_price is not None:
            price_power = (
                1 if last_price > closing_price
                else (-1 if last_price < closing_price else 0)
            )
        trade_to_float_percent = (
            round(trade_volume / floating_share_count * 100, 4)
            if trade_volume is not None and floating_share_count
            else None
        )

        client = client_by_date.get(trade_date, {})
        real_buy_value = stock_number(client.get("real_buy_value"))
        real_sell_value = stock_number(client.get("real_sell_value"))
        real_buy_count = stock_number(client.get("real_buy_count"))
        real_sell_count = stock_number(client.get("real_sell_count"))
        real_money_flow = (
            real_buy_value - real_sell_value
            if real_buy_value is not None and real_sell_value is not None
            else None
        )
        real_buy_per_capita = (
            real_buy_value / real_buy_count
            if real_buy_value is not None and real_buy_count and real_buy_count > 0
            else None
        )
        real_sell_per_capita = (
            real_sell_value / real_sell_count
            if real_sell_value is not None and real_sell_count and real_sell_count > 0
            else None
        )
        real_buy_power = (
            real_buy_per_capita / real_sell_per_capita
            if real_buy_per_capita is not None
            and real_sell_per_capita is not None
            and real_sell_per_capita > 0
            else None
        )
        money_flow_quality = (
            round(real_money_flow / trade_value * 100, 4)
            if real_money_flow is not None and trade_value and trade_value > 0
            else None
        )
        results.append({
            "trade_date": trade_date,
            "trade_value": trade_value,
            "trade_volume": trade_volume,
            "trade_count": stock_number(price_point.get("trade_count")),
            "price_power": price_power,
            "trade_to_float_percent": trade_to_float_percent,
            "trade_to_float_is_estimated": trade_to_float_percent is not None,
            "real_money_flow": real_money_flow,
            "money_flow_quality": money_flow_quality,
            "real_buy_per_capita": real_buy_per_capita,
            "real_sell_per_capita": real_sell_per_capita,
            "real_buy_power": real_buy_power,
        })
    return results


def fetch_stock_strategy_history_points(
    instrument,
    limit=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
):
    price_points = fetch_stock_price_history(
        instrument.get("symbol"),
        instrument.get("ins_code"),
        limit,
    )
    client_points = fetch_stock_client_type_history(
        instrument.get("ins_code"),
        limit,
    )
    return build_stock_strategy_history_points(
        price_points,
        client_points,
        share_count=instrument.get("share_count"),
        floating_share_percent=instrument.get("floating_share_percent"),
        limit=limit,
    )


def store_stock_strategy_history(
    symbol,
    ins_code,
    points,
    requested_days=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
    captured_at=None,
):
    clean_symbol = clean_stock_text(symbol)
    clean_ins_code = str(ins_code or "").strip()
    if not clean_symbol or not clean_ins_code:
        raise ValueError("نماد یا شناسه TSETMC برای تاریخچه استراتژی معتبر نیست.")
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    captured_at_iso = current_time.isoformat()
    prepared_points = []
    for point in points or []:
        trade_date = str(point.get("trade_date") or "")
        if not trade_date:
            continue
        market_day = datetime.strptime(trade_date, "%Y-%m-%d").date()
        prepared_points.append((
            clean_symbol,
            clean_ins_code,
            trade_date,
            jdatetime.date.fromgregorian(date=market_day).strftime("%Y-%m-%d"),
            stock_number(point.get("trade_value")),
            stock_number(point.get("trade_volume")),
            stock_number(point.get("trade_count")),
            stock_integer(point.get("price_power")),
            stock_number(point.get("trade_to_float_percent")),
            1 if point.get("trade_to_float_is_estimated") else 0,
            stock_number(point.get("real_money_flow")),
            stock_number(point.get("money_flow_quality")),
            stock_number(point.get("real_buy_per_capita")),
            stock_number(point.get("real_sell_per_capita")),
            stock_number(point.get("real_buy_power")),
            captured_at_iso,
            "tsetmc_60_day_backfill",
        ))

    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.executemany(
            """
            INSERT INTO stock_strategy_history (
                symbol, ins_code, trade_date, trade_date_jalali,
                trade_value, trade_volume, trade_count, price_power,
                trade_to_float_percent, trade_to_float_is_estimated,
                real_money_flow, money_flow_quality,
                real_buy_per_capita, real_sell_per_capita, real_buy_power,
                captured_at, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                ins_code = excluded.ins_code,
                trade_date_jalali = excluded.trade_date_jalali,
                trade_value = excluded.trade_value,
                trade_volume = excluded.trade_volume,
                trade_count = excluded.trade_count,
                price_power = excluded.price_power,
                trade_to_float_percent = excluded.trade_to_float_percent,
                trade_to_float_is_estimated = excluded.trade_to_float_is_estimated,
                real_money_flow = excluded.real_money_flow,
                money_flow_quality = excluded.money_flow_quality,
                real_buy_per_capita = excluded.real_buy_per_capita,
                real_sell_per_capita = excluded.real_sell_per_capita,
                real_buy_power = excluded.real_buy_power,
                captured_at = excluded.captured_at,
                source = excluded.source
            WHERE stock_strategy_history.source != 'daily_close'
            """,
            prepared_points,
        )
        latest_trade_date = max(
            (point[2] for point in prepared_points),
            default=None,
        )
        connection.execute(
            """
            INSERT INTO stock_strategy_history_sync (
                symbol, ins_code, requested_days, stored_count,
                latest_trade_date, synced_at, error
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(symbol) DO UPDATE SET
                ins_code = excluded.ins_code,
                requested_days = excluded.requested_days,
                stored_count = excluded.stored_count,
                latest_trade_date = excluded.latest_trade_date,
                synced_at = excluded.synced_at,
                error = NULL
            """,
            (
                clean_symbol,
                clean_ins_code,
                int(requested_days),
                len(prepared_points),
                latest_trade_date,
                captured_at_iso,
            ),
        )
    return len(prepared_points)


def mark_stock_strategy_history_error(symbol, ins_code, error, captured_at=None):
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO stock_strategy_history_sync (
                symbol, ins_code, requested_days, stored_count,
                latest_trade_date, synced_at, error
            )
            VALUES (?, ?, 0, 0, NULL, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                ins_code = excluded.ins_code,
                synced_at = excluded.synced_at,
                error = excluded.error
            """,
            (
                clean_stock_text(symbol),
                str(ins_code or "").strip(),
                current_time.astimezone(IRAN_TIMEZONE).isoformat(),
                str(error),
            ),
        )


def pending_stock_strategy_history_rows(
    rows,
    target_days=STOCK_STRATEGY_HISTORY_TARGET_DAYS,
):
    initialize_stock_database()
    with stock_database_connection() as connection:
        sync_rows = {
            normalize_symbol(record["symbol"]): record
            for record in connection.execute(
                """
                SELECT symbol, ins_code, requested_days, synced_at, error
                FROM stock_strategy_history_sync
                """
            ).fetchall()
        }
    pending = []
    seen = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = clean_stock_text(row.get("symbol"))
        ins_code = str(row.get("ins_code") or "").strip()
        normalized_symbol = normalize_symbol(symbol)
        if not symbol or not ins_code or normalized_symbol in seen:
            continue
        seen.add(normalized_symbol)
        sync = sync_rows.get(normalized_symbol)
        needs_refresh = (
            sync is None
            or str(sync["ins_code"] or "") != ins_code
        )
        if sync is not None and not needs_refresh:
            if sync["error"]:
                try:
                    last_attempt = datetime.fromisoformat(sync["synced_at"])
                    if last_attempt.tzinfo is None:
                        last_attempt = last_attempt.replace(tzinfo=IRAN_TIMEZONE)
                    needs_refresh = (
                        datetime.now(IRAN_TIMEZONE) - last_attempt
                        >= timedelta(hours=6)
                    )
                except (TypeError, ValueError):
                    needs_refresh = True
            else:
                needs_refresh = int(sync["requested_days"] or 0) < int(target_days)
        if needs_refresh:
            pending.append({
                "symbol": symbol,
                "ins_code": ins_code,
                "share_count": row.get("share_count"),
                "floating_share_percent": row.get("floating_share_percent"),
            })
    return pending


def refresh_stock_strategy_history(instruments):
    errors = []
    stored_points = 0
    try:
        with ThreadPoolExecutor(
            max_workers=min(STOCK_STRATEGY_HISTORY_WORKERS, len(instruments))
        ) as executor:
            futures = {
                executor.submit(
                    fetch_stock_strategy_history_points,
                    instrument,
                    STOCK_STRATEGY_HISTORY_TARGET_DAYS,
                ): instrument
                for instrument in instruments
            }
            for future in as_completed(futures):
                instrument = futures[future]
                try:
                    stored_points += store_stock_strategy_history(
                        instrument["symbol"],
                        instrument["ins_code"],
                        future.result(),
                    )
                except Exception as error:
                    errors.append(f"{instrument['symbol']}: {error}")
                    try:
                        mark_stock_strategy_history_error(
                            instrument["symbol"],
                            instrument["ins_code"],
                            error,
                        )
                    except sqlite3.Error:
                        pass
                finally:
                    with stock_strategy_history_lock:
                        stock_strategy_history_state["completed"] += 1
                        stock_strategy_history_state["stored_points"] = stored_points
                        stock_strategy_history_state["errors"] = len(errors)
    except Exception as error:
        errors.append(str(error))
    finally:
        with stock_strategy_history_lock:
            stock_strategy_history_state["running"] = False
            stock_strategy_history_state["stored_points"] = stored_points
            stock_strategy_history_state["errors"] = len(errors)
            stock_strategy_history_state["error"] = (
                f"تاریخچه استراتژی {len(errors)} نماد کامل نشد."
                if errors else None
            )


def start_stock_strategy_history_backfill(rows):
    pending = pending_stock_strategy_history_rows(rows)
    if not pending:
        with stock_strategy_history_lock:
            if not stock_strategy_history_state["running"]:
                stock_strategy_history_state.update({
                    "total": len(rows or []),
                    "completed": len(rows or []),
                    "errors": 0,
                    "error": None,
                })
        return False
    with stock_strategy_history_lock:
        if stock_strategy_history_state["running"]:
            return False
        stock_strategy_history_state.update({
            "running": True,
            "started_at": datetime.now(IRAN_TIMEZONE).isoformat(),
            "total": len(pending),
            "completed": 0,
            "stored_points": 0,
            "errors": 0,
            "error": None,
        })
    threading.Thread(
        target=refresh_stock_strategy_history,
        args=(pending,),
        name="stock-strategy-history-backfill",
        daemon=True,
    ).start()
    return True


def save_daily_stock_strategy_points(rows, captured_at=None):
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    captured_at_iso = current_time.isoformat()
    prepared = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = clean_stock_text(row.get("symbol"))
        ins_code = str(row.get("ins_code") or "").strip()
        trade_date = normalize_stock_market_date(row.get("market_date"))
        if not symbol or not ins_code or not trade_date:
            continue
        market_day = datetime.strptime(trade_date, "%Y-%m-%d").date()
        prepared.append((
            symbol,
            ins_code,
            trade_date,
            jdatetime.date.fromgregorian(date=market_day).strftime("%Y-%m-%d"),
            stock_number(row.get("trade_value")),
            stock_number(row.get("trade_volume")),
            None,
            stock_integer(row.get("price_power")),
            stock_number(row.get("trade_to_float_percent")),
            0,
            stock_number(row.get("real_money_flow")),
            stock_number(row.get("money_flow_quality")),
            stock_number(row.get("real_buy_per_capita")),
            stock_number(row.get("real_sell_per_capita")),
            stock_number(row.get("real_buy_power")),
            captured_at_iso,
            "daily_close",
        ))
    if not prepared:
        return 0
    initialize_stock_database()
    with stock_database_connection() as connection:
        before_changes = connection.total_changes
        connection.executemany(
            """
            INSERT INTO stock_strategy_history (
                symbol, ins_code, trade_date, trade_date_jalali,
                trade_value, trade_volume, trade_count, price_power,
                trade_to_float_percent, trade_to_float_is_estimated,
                real_money_flow, money_flow_quality,
                real_buy_per_capita, real_sell_per_capita, real_buy_power,
                captured_at, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, trade_date) DO UPDATE SET
                ins_code = excluded.ins_code,
                trade_date_jalali = excluded.trade_date_jalali,
                trade_value = COALESCE(excluded.trade_value, stock_strategy_history.trade_value),
                trade_volume = COALESCE(excluded.trade_volume, stock_strategy_history.trade_volume),
                trade_count = COALESCE(excluded.trade_count, stock_strategy_history.trade_count),
                price_power = COALESCE(excluded.price_power, stock_strategy_history.price_power),
                trade_to_float_percent = COALESCE(
                    excluded.trade_to_float_percent,
                    stock_strategy_history.trade_to_float_percent
                ),
                trade_to_float_is_estimated = CASE
                    WHEN excluded.trade_to_float_percent IS NOT NULL THEN 0
                    ELSE stock_strategy_history.trade_to_float_is_estimated
                END,
                real_money_flow = COALESCE(
                    excluded.real_money_flow,
                    stock_strategy_history.real_money_flow
                ),
                money_flow_quality = COALESCE(
                    excluded.money_flow_quality,
                    stock_strategy_history.money_flow_quality
                ),
                real_buy_per_capita = COALESCE(
                    excluded.real_buy_per_capita,
                    stock_strategy_history.real_buy_per_capita
                ),
                real_sell_per_capita = COALESCE(
                    excluded.real_sell_per_capita,
                    stock_strategy_history.real_sell_per_capita
                ),
                real_buy_power = COALESCE(
                    excluded.real_buy_power,
                    stock_strategy_history.real_buy_power
                ),
                captured_at = excluded.captured_at,
                source = 'daily_close'
            WHERE stock_strategy_history.source != 'daily_close'
            """,
            prepared,
        )
        return connection.total_changes - before_changes


def read_stock_strategy_metric_history(symbols=None):
    requested_values = (
        sorted({clean_stock_text(symbol) for symbol in symbols if clean_stock_text(symbol)})
        if symbols is not None
        else None
    )
    requested_symbols = (
        {normalize_symbol(symbol) for symbol in requested_values}
        if requested_values is not None
        else None
    )
    initialize_stock_database()
    with stock_database_connection() as connection:
        if requested_values is None:
            records = connection.execute(
                "SELECT * FROM stock_strategy_history ORDER BY trade_date DESC"
            ).fetchall()
        else:
            records = []
            for offset in range(0, len(requested_values), 500):
                batch = requested_values[offset:offset + 500]
                placeholders = ",".join("?" for _ in batch)
                records.extend(connection.execute(
                    f"""
                    SELECT * FROM stock_strategy_history
                    WHERE symbol IN ({placeholders})
                    ORDER BY trade_date DESC
                    """,
                    batch,
                ).fetchall())
    history = {}
    metric_fields = (
        "trade_value",
        "trade_volume",
        "price_power",
        "trade_to_float_percent",
        "real_money_flow",
        "money_flow_quality",
        "real_buy_per_capita",
        "real_sell_per_capita",
        "real_buy_power",
    )
    for record in records:
        normalized_symbol = normalize_symbol(record["symbol"])
        if requested_symbols is not None and normalized_symbol not in requested_symbols:
            continue
        history.setdefault(normalized_symbol, []).append({
            "trade_date": record["trade_date"],
            **{field: record[field] for field in metric_fields},
            "trade_to_float_is_estimated": bool(
                record["trade_to_float_is_estimated"]
            ),
        })
    return history


def save_daily_stock_snapshots(rows, captured_at=None):
    """Keep the first eligible close snapshot per symbol and Tehran day."""
    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)

    current_minute = current_time.hour * 60 + current_time.minute
    trade_date = current_time.date().isoformat()
    trade_date_jalali = jdatetime.date.fromgregorian(
        date=current_time.date()
    ).strftime("%Y-%m-%d")
    captured_at_iso = current_time.isoformat()
    extended_symbols = {
        normalize_symbol(symbol)
        for symbol in STOCK_EXTENDED_SESSION_SYMBOLS
    }
    inserted_count = 0
    eligible_rows = []

    initialize_stock_database()
    with stock_database_connection() as connection:
        for row in rows:
            if not isinstance(row, dict) or not row.get("symbol"):
                continue
            if row.get("market_date") != trade_date:
                continue

            normalized_symbol = normalize_symbol(row["symbol"])
            is_extended = normalized_symbol in extended_symbols
            threshold = (
                STOCK_EXTENDED_SNAPSHOT_MINUTE
                if is_extended
                else STOCK_STANDARD_SNAPSHOT_MINUTE
            )
            if current_minute < threshold:
                continue

            eligible_rows.append(row)

            session_type = "extended" if is_extended else "standard"
            snapshot_payload = json.dumps(
                row,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO stock_daily_snapshots (
                    trade_date,
                    trade_date_jalali,
                    symbol,
                    session_type,
                    captured_at,
                    data_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_date,
                    trade_date_jalali,
                    row["symbol"],
                    session_type,
                    captured_at_iso,
                    snapshot_payload,
                ),
            )
            inserted_count += max(cursor.rowcount, 0)

    save_daily_stock_price_points(eligible_rows, current_time)
    save_daily_stock_strategy_points(eligible_rows, current_time)

    return {
        "trade_date": trade_date,
        "trade_date_jalali": trade_date_jalali,
        "inserted_count": inserted_count,
    }


def read_daily_stock_snapshots(trade_date=None, symbol=None):
    """Read archived rows, defaulting to the latest available trading day."""
    initialize_stock_database()
    normalized_symbol = normalize_symbol(symbol) if symbol else None

    with stock_database_connection() as connection:
        selected_date = trade_date
        if not selected_date:
            selected_date_row = connection.execute(
                "SELECT MAX(trade_date) AS trade_date FROM stock_daily_snapshots"
            ).fetchone()
            selected_date = (
                selected_date_row["trade_date"]
                if selected_date_row
                else None
            )

        if not selected_date:
            return [], None

        query = """
            SELECT
                trade_date,
                trade_date_jalali,
                symbol,
                session_type,
                captured_at,
                data_json
            FROM stock_daily_snapshots
            WHERE trade_date = ?
        """
        query += " ORDER BY symbol COLLATE NOCASE"

        database_rows = connection.execute(query, [selected_date]).fetchall()

    if normalized_symbol:
        database_rows = [
            row
            for row in database_rows
            if normalize_symbol(row["symbol"]) == normalized_symbol
        ]

    snapshots = []
    for database_row in database_rows:
        try:
            data = json.loads(database_row["data_json"])
        except (TypeError, json.JSONDecodeError):
            data = {}
        snapshots.append(
            {
                "trade_date": database_row["trade_date"],
                "trade_date_jalali": database_row["trade_date_jalali"],
                "symbol": database_row["symbol"],
                "session_type": database_row["session_type"],
                "captured_at": database_row["captured_at"],
                "data": data,
            }
        )

    return snapshots, selected_date


def read_latest_daily_stock_snapshots(symbols=None, source="featured"):
    """Return the newest archived row available for each requested symbol."""
    initialize_stock_database()
    source = "all" if source == "all" else "featured"
    snapshot_table = (
        "all_stock_daily_snapshots"
        if source == "all"
        else "stock_daily_snapshots"
    )
    requested_symbols = (
        {
            normalize_symbol(symbol)
            for symbol in symbols
            if normalize_symbol(symbol)
        }
        if symbols is not None
        else None
    )

    with stock_database_connection() as connection:
        database_rows = connection.execute(
            f"""
            SELECT
                trade_date,
                trade_date_jalali,
                symbol,
                session_type,
                captured_at,
                data_json
            FROM {snapshot_table}
            ORDER BY trade_date DESC, captured_at DESC
            """
        ).fetchall()

    snapshots = []
    seen_symbols = set()
    for database_row in database_rows:
        normalized_symbol = normalize_symbol(database_row["symbol"])
        if requested_symbols is not None and normalized_symbol not in requested_symbols:
            continue
        if normalized_symbol in seen_symbols:
            continue

        try:
            data = json.loads(database_row["data_json"])
        except (TypeError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}

        snapshots.append(
            {
                "trade_date": database_row["trade_date"],
                "trade_date_jalali": database_row["trade_date_jalali"],
                "symbol": database_row["symbol"],
                "session_type": database_row["session_type"],
                "captured_at": database_row["captured_at"],
                "data": data,
            }
        )
        seen_symbols.add(normalized_symbol)
        if requested_symbols is not None and seen_symbols >= requested_symbols:
            break

    return snapshots


def read_stock_metric_history(symbol, metric, limit=365):
    """Read one saved daily metric for a stock in chronological order."""
    if metric not in STOCK_HISTORY_METRICS:
        raise ValueError("شاخص انتخاب‌شده برای نمودار معتبر نیست.")

    requested_symbol = clean_stock_text(symbol)
    if not requested_symbol:
        raise ValueError("نماد برای نمایش نمودار مشخص نشده است.")

    safe_limit = max(1, min(int(limit or 365), 3650))
    initialize_stock_database()
    with stock_database_connection() as connection:
        database_rows = connection.execute(
            """
            SELECT
                trade_date,
                trade_date_jalali,
                symbol,
                captured_at,
                data_json,
                source_priority
            FROM (
                SELECT
                    trade_date,
                    trade_date_jalali,
                    symbol,
                    captured_at,
                    data_json,
                    0 AS source_priority
                FROM stock_daily_snapshots
                WHERE symbol = ?
                UNION ALL
                SELECT
                    trade_date,
                    trade_date_jalali,
                    symbol,
                    captured_at,
                    data_json,
                    1 AS source_priority
                FROM all_stock_daily_snapshots
                WHERE symbol = ?
            )
            ORDER BY trade_date DESC, captured_at DESC, source_priority ASC
            LIMIT ?
            """,
            (requested_symbol, requested_symbol, safe_limit * 2),
        ).fetchall()
        price_rows = connection.execute(
            """
            SELECT trade_date, raw_closing_price, raw_last_price,
                   daily_high_price, daily_low_price
            FROM stock_price_history
            WHERE symbol = ?
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (requested_symbol, safe_limit * 2),
        ).fetchall()

    price_by_date = {
        row["trade_date"]: row
        for row in price_rows
    }

    points = []
    seen_dates = set()
    for database_row in reversed(database_rows):
        if database_row["trade_date"] in seen_dates:
            continue
        try:
            data = json.loads(database_row["data_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue

        value = stock_number(data.get(metric))
        if value is None:
            continue
        point = {
            "date": database_row["trade_date"],
            "date_jalali": database_row["trade_date_jalali"],
            "value": value,
        }
        if metric == "price_power":
            status_data = dict(data)
            price_row = price_by_date.get(database_row["trade_date"])
            if price_row is not None:
                for target_field, source_field in (
                    ("last_price", "raw_last_price"),
                    ("closing_price", "raw_closing_price"),
                    ("daily_high_price", "daily_high_price"),
                    ("daily_low_price", "daily_low_price"),
                ):
                    if price_row[source_field] is not None:
                        status_data[target_field] = price_row[source_field]
            point["status"] = stock_price_power_status(status_data)
        points.append(point)
        seen_dates.add(database_row["trade_date"])

    return points[-safe_limit:]


def apply_latest_stock_snapshots(current_rows, source="featured"):
    """Replace current rows with each symbol's latest daily snapshot when present."""
    source_rows = [
        dict(row)
        for row in current_rows
        if isinstance(row, dict) and row.get("symbol")
    ]
    requested_symbols = [row["symbol"] for row in source_rows]
    snapshots = (
        read_latest_daily_stock_snapshots(requested_symbols, source="all")
        if source == "all"
        else read_latest_daily_stock_snapshots(requested_symbols)
    )
    snapshots_by_symbol = {
        normalize_symbol(snapshot["symbol"]): snapshot
        for snapshot in snapshots
    }
    rows = []
    used_snapshots = []

    for current_row in source_rows:
        snapshot = snapshots_by_symbol.get(
            normalize_symbol(current_row["symbol"])
        )
        if snapshot is None:
            rows.append(current_row)
            continue

        row = dict(snapshot["data"])
        row["symbol"] = current_row["symbol"]
        if not row.get("market_date"):
            row["market_date"] = snapshot["trade_date"]
        for identity_field in ("company", "industry", "ins_code"):
            if not row.get(identity_field) and current_row.get(identity_field):
                row[identity_field] = current_row[identity_field]
        apply_stock_floating_share_override(row)
        row.update(calculate_stock_indicators(row))
        rows.append(row)
        used_snapshots.append(snapshot)

    dates = sorted(
        {snapshot["trade_date"] for snapshot in used_snapshots}
    )
    jalali_by_date = {
        snapshot["trade_date"]: snapshot["trade_date_jalali"]
        for snapshot in used_snapshots
    }
    latest_date = dates[-1] if dates else None
    return rows, {
        "data_source": "daily_snapshot",
        "saved_count": len(used_snapshots),
        "missing_snapshot_count": len(source_rows) - len(used_snapshots),
        "snapshot_date": latest_date,
        "snapshot_date_jalali": (
            jalali_by_date.get(latest_date) if latest_date else None
        ),
        "snapshot_dates": dates,
        "snapshot_dates_jalali": [jalali_by_date[date] for date in dates],
        "mixed_snapshot_dates": len(dates) > 1,
    }


def save_market_daily_snapshot(payload, captured_at=None):
    """Upsert the latest cross-market metrics for each Tehran calendar day."""
    if not isinstance(payload, dict):
        return None

    current_time = captured_at or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)

    overview = payload.get("overview")
    if not isinstance(overview, dict):
        overview = {}
    prices = [
        item for item in overview.get("prices", [])
        if isinstance(item, dict)
    ]
    money_flows = [
        item for item in overview.get("flows", [])
        if isinstance(item, dict)
    ]
    industry_flows = [
        item for item in overview.get("industry_flows", [])
        if isinstance(item, dict)
    ]
    free_dollar = next(
        (
            watch_market_number(item.get("price"))
            for item in prices
            if item.get("key") == "dollar"
        ),
        None,
    )
    total_market_trade_value = watch_market_number(
        payload.get("total_market_trade_value")
    )
    trade_date = current_time.date().isoformat()
    trade_date_jalali = jdatetime.date.fromgregorian(
        date=current_time.date()
    ).strftime("%Y-%m-%d")
    source_market_date = str(payload.get("market_date") or "").strip() or None
    flows_json = json.dumps(
        money_flows,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    industry_flows_json = json.dumps(
        industry_flows,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    initialize_stock_database()
    with stock_database_connection() as connection:
        connection.execute(
            """
            INSERT INTO market_daily_snapshots (
                trade_date,
                trade_date_jalali,
                source_market_date,
                captured_at,
                free_dollar_price,
                total_market_trade_value,
                money_flows_json,
                industry_flows_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(trade_date) DO UPDATE SET
                trade_date_jalali = excluded.trade_date_jalali,
                source_market_date = COALESCE(
                    excluded.source_market_date,
                    market_daily_snapshots.source_market_date
                ),
                captured_at = excluded.captured_at,
                free_dollar_price = COALESCE(
                    excluded.free_dollar_price,
                    market_daily_snapshots.free_dollar_price
                ),
                total_market_trade_value = COALESCE(
                    excluded.total_market_trade_value,
                    market_daily_snapshots.total_market_trade_value
                ),
                money_flows_json = CASE
                    WHEN excluded.money_flows_json <> '[]'
                    THEN excluded.money_flows_json
                    ELSE market_daily_snapshots.money_flows_json
                END,
                industry_flows_json = CASE
                    WHEN excluded.industry_flows_json <> '[]'
                    THEN excluded.industry_flows_json
                    ELSE market_daily_snapshots.industry_flows_json
                END
            """,
            (
                trade_date,
                trade_date_jalali,
                source_market_date,
                current_time.isoformat(),
                free_dollar,
                total_market_trade_value,
                flows_json,
                industry_flows_json,
            ),
        )

    return {
        "trade_date": trade_date,
        "trade_date_jalali": trade_date_jalali,
        "source_market_date": source_market_date,
    }


def read_market_daily_snapshots(limit=30):
    """Read the newest saved cross-market daily snapshots."""
    initialize_stock_database()
    safe_limit = max(1, min(int(limit or 30), 3650))
    with stock_database_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                trade_date,
                trade_date_jalali,
                source_market_date,
                captured_at,
                free_dollar_price,
                total_market_trade_value,
                money_flows_json,
                industry_flows_json
            FROM market_daily_snapshots
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    snapshots = []
    for row in rows:
        try:
            flows = json.loads(row["money_flows_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            flows = []
        try:
            industry_flows = json.loads(row["industry_flows_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            industry_flows = []
        snapshots.append({
            "trade_date": row["trade_date"],
            "trade_date_jalali": row["trade_date_jalali"],
            "source_market_date": row["source_market_date"],
            "captured_at": row["captured_at"],
            "free_dollar_price": row["free_dollar_price"],
            "total_market_trade_value": row["total_market_trade_value"],
            "money_flows": flows,
            "industry_flows": industry_flows,
        })
    return snapshots


STOCK_STRATEGY_METRICS = (
    "trade_value",
    "trade_to_float_percent",
    "real_buy_power",
    "real_money_flow",
    "money_flow_quality",
)

STOCK_STRATEGY_TECHNICAL_METRICS = (
    "rsi",
    "ema",
    "macd",
)


def normalize_stock_strategy_integer(value, default, minimum=0, maximum=250):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def normalize_stock_strategy_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def normalize_stock_strategy_rules(payload):
    source = payload if isinstance(payload, dict) else {}
    normalized = {}
    for metric in STOCK_STRATEGY_METRICS:
        rule = source.get(metric) if isinstance(source.get(metric), dict) else {}
        operator = str(rule.get("operator") or "gte").strip().lower()
        if operator not in {"gte", "lte", "eq"}:
            operator = "gte"
        try:
            days = int(rule.get("days") or 0)
        except (TypeError, ValueError):
            days = 0
        try:
            consecutive_days = int(rule.get("consecutive_days") or 0)
        except (TypeError, ValueError):
            consecutive_days = 0
        try:
            fixed_value = float(rule.get("fixed") or 0)
        except (TypeError, ValueError):
            fixed_value = 0
        normalized[metric] = {
            "enabled": bool(rule.get("enabled")),
            "operator": operator,
            "days": max(0, min(days, 250)),
            "fixed": (
                fixed_value
                if metric == "money_flow_quality"
                else (fixed_value if fixed_value > 0 else 0)
            ),
            "consecutive_days": (
                max(0, min(consecutive_days, 250))
                if metric == "real_money_flow"
                else 0
            ),
        }

    rsi_source = (
        source.get("rsi")
        if isinstance(source.get("rsi"), dict)
        else {}
    )
    rsi_operator = str(rsi_source.get("operator") or "gte").strip().lower()
    if rsi_operator not in {"gte", "lte", "eq", "between"}:
        rsi_operator = "gte"
    rsi_fixed = max(
        0,
        min(
            normalize_stock_strategy_number(
                rsi_source.get("fixed"),
                50,
            ),
            100,
        ),
    )
    rsi_maximum = max(
        0,
        min(
            normalize_stock_strategy_number(
                rsi_source.get("maximum"),
                70,
            ),
            100,
        ),
    )
    if rsi_operator == "between" and rsi_maximum < rsi_fixed:
        rsi_fixed, rsi_maximum = rsi_maximum, rsi_fixed
    normalized["rsi"] = {
        "enabled": bool(rsi_source.get("enabled")),
        "operator": rsi_operator,
        "period": normalize_stock_strategy_integer(
            rsi_source.get("period"),
            14,
            minimum=2,
        ),
        "fixed": rsi_fixed,
        "maximum": rsi_maximum,
        "days": 0,
        "consecutive_days": 0,
    }

    ema_source = (
        source.get("ema")
        if isinstance(source.get("ema"), dict)
        else {}
    )
    ema_operator = str(ema_source.get("operator") or "gte").strip().lower()
    if ema_operator not in {"gte", "lte", "eq"}:
        ema_operator = "gte"
    ema_mode = str(ema_source.get("mode") or "price").strip().lower()
    if ema_mode not in {"price", "crossover"}:
        ema_mode = "price"
    ema_period = normalize_stock_strategy_integer(
        ema_source.get("period"),
        20,
        minimum=2,
        maximum=249,
    )
    ema_long_period = normalize_stock_strategy_integer(
        ema_source.get("long_period"),
        50,
        minimum=3,
    )
    ema_long_period = max(ema_period + 1, ema_long_period)
    normalized["ema"] = {
        "enabled": bool(ema_source.get("enabled")),
        "operator": ema_operator,
        "mode": ema_mode,
        "period": ema_period,
        "long_period": ema_long_period,
        "days": 0,
        "fixed": 0,
        "consecutive_days": 0,
    }

    macd_source = (
        source.get("macd")
        if isinstance(source.get("macd"), dict)
        else {}
    )
    macd_operator = str(
        macd_source.get("operator") or "gte"
    ).strip().lower()
    if macd_operator not in {"gte", "lte", "eq"}:
        macd_operator = "gte"
    fast_period = normalize_stock_strategy_integer(
        macd_source.get("fast_period"),
        12,
        minimum=2,
        maximum=249,
    )
    slow_period = normalize_stock_strategy_integer(
        macd_source.get("slow_period"),
        26,
        minimum=3,
    )
    slow_period = max(fast_period + 1, slow_period)
    compare_to = str(
        macd_source.get("compare_to") or "signal"
    ).strip().lower()
    if compare_to not in {"signal", "zero"}:
        compare_to = "signal"
    normalized["macd"] = {
        "enabled": bool(macd_source.get("enabled")),
        "operator": macd_operator,
        "compare_to": compare_to,
        "fast_period": fast_period,
        "slow_period": slow_period,
        "signal_period": normalize_stock_strategy_integer(
            macd_source.get("signal_period"),
            9,
            minimum=2,
        ),
        "days": 0,
        "fixed": 0,
        "consecutive_days": 0,
    }

    industry_growth_source = (
        source.get("industry_growth")
        if isinstance(source.get("industry_growth"), dict)
        else {}
    )
    normalized["industry_growth"] = {
        "enabled": bool(industry_growth_source.get("enabled")),
        "days": normalize_stock_strategy_integer(
            industry_growth_source.get("days"),
            30,
            minimum=1,
        ),
        "operator": "lt_industry_average",
        "fixed": 0,
        "consecutive_days": 0,
    }

    symbol_industry_source = (
        source.get("symbol_industry_compare")
        if isinstance(source.get("symbol_industry_compare"), dict)
        else {}
    )
    normalized["symbol_industry_compare"] = {
        "enabled": bool(symbol_industry_source.get("enabled")),
        "symbol": normalize_symbol(symbol_industry_source.get("symbol")),
        "days": normalize_stock_strategy_integer(
            symbol_industry_source.get("days"),
            10,
            minimum=1,
        ),
        "include_industry": symbol_industry_source.get(
            "include_industry",
            True,
        ) is not False,
        "operator": "compare_with_industry",
        "fixed": 0,
        "consecutive_days": 0,
    }

    return normalized


def stock_strategy_rule_is_active(metric, rule):
    if not rule.get("enabled"):
        return False
    if metric == "real_money_flow":
        return rule.get("consecutive_days", 0) > 0 or rule.get("days", 0) > 0
    return True


def compare_stock_strategy_value(current_value, reference_value, operator):
    current_number = stock_number(current_value)
    reference_number = stock_number(reference_value)
    if current_number is None or reference_number is None:
        return False
    if operator == "lte":
        return current_number <= reference_number
    if operator == "eq":
        tolerance = max(1e-9, abs(reference_number) * 1e-9)
        return abs(current_number - reference_number) <= tolerance
    return current_number >= reference_number


def stock_order_book_presence(row):
    """Return buy/sell presence for a known order book, or None if missing."""
    if not isinstance(row, dict):
        return None
    buy_values = [
        stock_number(row.get("order_book_buy_value")),
        stock_number(row.get("order_book_buy_volume")),
        stock_number(row.get("order_book_buy_count")),
    ]
    sell_values = [
        stock_number(row.get("order_book_sell_value")),
        stock_number(row.get("order_book_sell_volume")),
        stock_number(row.get("order_book_sell_count")),
    ]
    if all(value is None for value in buy_values + sell_values):
        return None
    has_buy_orders = any(value is not None and value > 0 for value in buy_values)
    has_sell_orders = any(value is not None and value > 0 for value in sell_values)
    return has_buy_orders, has_sell_orders


def stock_strategy_buy_queue_state(row):
    """Return whether the row is one of the two buy-queue states."""
    status = stock_price_power_status(row)
    if status is None:
        return None
    return status in {"buy_queue", "buy_queue_neutral"}


def stock_price_power_status(row):
    """Classify price position into the seven requested market states."""
    if not isinstance(row, dict):
        return None

    last_price = stock_number(row.get("last_price"))
    closing_price = stock_number(row.get("closing_price"))
    upper_price = stock_number(row.get("daily_high_price"))
    if upper_price is None or upper_price <= 0:
        upper_price = stock_number(row.get("daily_upper_price"))
    lower_price = stock_number(row.get("daily_low_price"))
    if lower_price is None or lower_price <= 0:
        lower_price = stock_number(row.get("daily_lower_price"))

    if last_price is not None and closing_price is not None:
        if upper_price is not None and last_price == upper_price:
            return (
                "buy_queue_neutral"
                if closing_price == upper_price
                else "buy_queue"
            )
        if lower_price is not None and last_price == lower_price:
            return (
                "sell_queue_neutral"
                if closing_price == lower_price
                else "sell_queue"
            )

    # Compatibility for snapshots saved before daily price limits were stored.
    # Current rows have both limits and never need this order-book fallback.
    if upper_price is None or lower_price is None:
        presence = stock_order_book_presence(row)
        if presence is not None:
            has_buy_orders, has_sell_orders = presence
            if has_buy_orders and not has_sell_orders:
                return (
                    "buy_queue_neutral"
                    if last_price is not None and last_price == closing_price
                    else "buy_queue"
                )
            if has_sell_orders and not has_buy_orders:
                return (
                    "sell_queue_neutral"
                    if last_price is not None and last_price == closing_price
                    else "sell_queue"
                )

    if last_price is not None and closing_price is not None:
        if last_price > closing_price:
            return "positive"
        if last_price < closing_price:
            return "negative"
        return "neutral"

    price_power = stock_number(row.get("price_power"))
    if price_power is None:
        return None
    if price_power > 0:
        return "positive"
    if price_power < 0:
        return "negative"
    return "neutral"


def calculate_stock_ema_series(values, period):
    """Return an EMA series seeded with the first full-period SMA."""
    numeric_values = [stock_number(value) for value in values]
    if period < 2 or len(numeric_values) < period:
        return [None] * len(numeric_values)
    if any(value is None for value in numeric_values):
        return [None] * len(numeric_values)

    result = [None] * len(numeric_values)
    seed = sum(numeric_values[:period]) / period
    result[period - 1] = seed
    multiplier = 2 / (period + 1)
    previous = seed
    for index in range(period, len(numeric_values)):
        previous = (
            (numeric_values[index] - previous) * multiplier
            + previous
        )
        result[index] = previous
    return result


def calculate_stock_ema(values, period):
    series = calculate_stock_ema_series(values, period)
    return series[-1] if series else None


def calculate_stock_ema_crossover(values, fast_period, slow_period):
    """Return 1 for an upward cross, -1 for downward, 0 for no cross."""
    if slow_period <= fast_period:
        return None
    fast_series = calculate_stock_ema_series(values, fast_period)
    slow_series = calculate_stock_ema_series(values, slow_period)
    comparable = [
        (fast_value, slow_value)
        for fast_value, slow_value in zip(fast_series, slow_series)
        if fast_value is not None and slow_value is not None
    ]
    if len(comparable) < 2:
        return None

    previous_fast, previous_slow = comparable[-2]
    current_fast, current_slow = comparable[-1]
    if previous_fast <= previous_slow and current_fast > current_slow:
        return 1
    if previous_fast >= previous_slow and current_fast < current_slow:
        return -1
    return 0


def calculate_stock_rsi(values, period):
    """Calculate Wilder's RSI from daily closing prices."""
    numeric_values = [stock_number(value) for value in values]
    if (
        period < 2
        or len(numeric_values) < period + 1
        or any(value is None for value in numeric_values)
    ):
        return None

    changes = [
        numeric_values[index] - numeric_values[index - 1]
        for index in range(1, len(numeric_values))
    ]
    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for index in range(period, len(changes)):
        average_gain = (
            average_gain * (period - 1) + gains[index]
        ) / period
        average_loss = (
            average_loss * (period - 1) + losses[index]
        ) / period

    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def calculate_stock_macd(values, fast_period, slow_period, signal_period):
    """Calculate the current MACD, signal, and histogram values."""
    if slow_period <= fast_period:
        return {"macd": None, "signal": None, "histogram": None}
    fast_series = calculate_stock_ema_series(values, fast_period)
    slow_series = calculate_stock_ema_series(values, slow_period)
    macd_values = [
        fast_value - slow_value
        for fast_value, slow_value in zip(fast_series, slow_series)
        if fast_value is not None and slow_value is not None
    ]
    if not macd_values:
        return {"macd": None, "signal": None, "histogram": None}

    current_macd = macd_values[-1]
    current_signal = calculate_stock_ema(macd_values, signal_period)
    return {
        "macd": current_macd,
        "signal": current_signal,
        "histogram": (
            current_macd - current_signal
            if current_signal is not None
            else None
        ),
    }


def stock_strategy_closing_prices(row, symbol_history):
    """Build an ascending, de-duplicated daily closing-price series."""
    current_market_date = str(row.get("market_date") or "")
    prices_by_date = {}
    undated_prices = []
    for snapshot in reversed(symbol_history or []):
        closing_price = stock_number(snapshot.get("closing_price"))
        if closing_price is None or closing_price <= 0:
            continue
        trade_date = str(snapshot.get("trade_date") or "")
        if current_market_date and trade_date == current_market_date:
            continue
        if trade_date:
            prices_by_date[trade_date] = closing_price
        else:
            undated_prices.append(closing_price)

    prices = [prices_by_date[key] for key in sorted(prices_by_date)]
    prices.extend(undated_prices)
    current_closing_price = stock_number(row.get("closing_price"))
    if current_closing_price is not None and current_closing_price > 0:
        prices.append(current_closing_price)
    return prices


def calculate_stock_period_growth(closing_prices, requested_days):
    """Calculate closing-price growth against N prior trading observations."""
    numeric_prices = []
    for value in closing_prices or []:
        numeric_value = stock_number(value)
        if numeric_value is not None and numeric_value > 0:
            numeric_prices.append(numeric_value)
    available_days = len(numeric_prices) - 1
    if available_days < 1:
        return None
    days_used = min(max(1, int(requested_days)), available_days)
    starting_price = numeric_prices[-(days_used + 1)]
    ending_price = numeric_prices[-1]
    return {
        "growth_percent": ((ending_price / starting_price) - 1) * 100,
        "days_used": days_used,
    }


def build_stock_industry_growth_comparisons(rows, history, requested_days):
    """Compare every stock's closing-price growth with its industry average."""
    requested_days = max(1, int(requested_days))
    price_series = {}
    industry_members = {}
    coverage = {
        "requested_days": requested_days,
        "minimum_days_used": None,
        "maximum_days_used": None,
        "partial_symbol_count": 0,
        "valid_symbol_count": 0,
        "industry_count": 0,
    }

    for row in rows or []:
        if not isinstance(row, dict) or not row.get("symbol"):
            continue
        symbol_key = normalize_symbol(row["symbol"])
        industry_label = clean_stock_text(row.get("industry"))
        industry_key = normalize_symbol(industry_label)
        symbol_history = history.get(symbol_key, [])
        closing_prices = stock_strategy_closing_prices(row, symbol_history)
        price_series[symbol_key] = closing_prices
        current_closing_price = stock_number(row.get("closing_price"))
        if current_closing_price is None or current_closing_price <= 0:
            continue
        growth = calculate_stock_period_growth(closing_prices, requested_days)
        if not industry_key or growth is None:
            continue

        member = {
            "symbol": row.get("symbol"),
            "symbol_key": symbol_key,
            "industry": industry_label,
            "industry_key": industry_key,
            "industry_growth_percent": growth["growth_percent"],
            "industry_growth_days_used": growth["days_used"],
        }
        industry_members.setdefault(industry_key, []).append(member)
        coverage["valid_symbol_count"] += 1
        if growth["days_used"] < requested_days:
            coverage["partial_symbol_count"] += 1
            coverage["minimum_days_used"] = (
                growth["days_used"]
                if coverage["minimum_days_used"] is None
                else min(coverage["minimum_days_used"], growth["days_used"])
            )
            coverage["maximum_days_used"] = (
                growth["days_used"]
                if coverage["maximum_days_used"] is None
                else max(coverage["maximum_days_used"], growth["days_used"])
            )

    comparisons = {}
    coverage["industry_count"] = len(industry_members)
    for members in industry_members.values():
        industry_average = sum(
            member["industry_growth_percent"] for member in members
        ) / len(members)
        for member in members:
            comparisons[member["symbol_key"]] = {
                **member,
                "industry_average_growth_percent": industry_average,
                "below_industry_average_percent": (
                    industry_average - member["industry_growth_percent"]
                ),
                "industry_growth_member_count": len(members),
            }

    return comparisons, coverage, price_series


def read_stock_strategy_history(source="featured", symbols=None):
    source = "all" if source == "all" else "featured"
    requested_symbols = (
        {normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)}
        if symbols is not None
        else None
    )
    snapshot_table = (
        "all_stock_daily_snapshots"
        if source == "all"
        else "stock_daily_snapshots"
    )
    initialize_stock_database()
    with stock_database_connection() as connection:
        records = connection.execute(
            f"""
            SELECT trade_date, symbol, data_json
            FROM {snapshot_table}
            ORDER BY trade_date DESC, captured_at DESC
            """
        ).fetchall()

    history = {}
    for record in records:
        normalized_symbol = normalize_symbol(record["symbol"])
        if (
            requested_symbols is not None
            and normalized_symbol not in requested_symbols
        ):
            continue
        try:
            data = json.loads(record["data_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        data["trade_date"] = record["trade_date"]
        history.setdefault(normalized_symbol, []).append(data)

    metric_history = read_stock_strategy_metric_history(symbols=symbols)
    for normalized_symbol, metric_points in metric_history.items():
        symbol_history = history.setdefault(normalized_symbol, [])
        by_date = {
            str(item.get("trade_date") or ""): item
            for item in symbol_history
            if item.get("trade_date")
        }
        for point in metric_points:
            trade_date = point["trade_date"]
            existing = by_date.get(trade_date)
            if existing is not None:
                existing.update(point)
                continue
            metric_row = dict(point)
            symbol_history.append(metric_row)
            by_date[trade_date] = metric_row

    adjusted_history = read_stock_price_history(symbols=symbols)
    for normalized_symbol, price_points in adjusted_history.items():
        symbol_history = history.setdefault(normalized_symbol, [])
        by_date = {
            str(item.get("trade_date") or ""): item
            for item in symbol_history
            if item.get("trade_date")
        }
        for point in price_points:
            trade_date = point["trade_date"]
            existing = by_date.get(trade_date)
            if existing is not None:
                existing["closing_price"] = point["closing_price"]
                existing["raw_closing_price"] = point["raw_closing_price"]
                continue
            price_row = dict(point)
            symbol_history.append(price_row)
            by_date[trade_date] = price_row
        symbol_history.sort(
            key=lambda item: str(item.get("trade_date") or ""),
            reverse=True,
        )
    return history


def stock_strategy_technical_required_points(metric, rule):
    if metric == "rsi":
        return rule["period"] + 1
    if metric == "ema":
        if rule.get("mode") == "crossover":
            return rule["long_period"] + 1
        return rule["period"]
    if metric == "macd":
        if rule.get("compare_to") == "zero":
            return rule["slow_period"]
        return rule["slow_period"] + rule["signal_period"] - 1
    return 0


def evaluate_stock_strategy(rows, history, rules):
    normalized_rules = normalize_stock_strategy_rules(rules)
    active_metrics = [
        metric
        for metric, rule in normalized_rules.items()
        if stock_strategy_rule_is_active(metric, rule)
    ]
    results = []
    partial_history_count = 0
    missing_history_count = 0
    excluded_zero_or_missing_count = 0
    history_coverage = {
        metric: {
            "requested_days": rule["days"],
            "minimum_days_used": None,
            "maximum_days_used": None,
            "partial_symbol_count": 0,
        }
        for metric, rule in normalized_rules.items()
        if stock_strategy_rule_is_active(metric, rule) and rule["days"] > 0
    }
    technical_coverage = {
        metric: {
            "required_points": stock_strategy_technical_required_points(
                metric,
                normalized_rules[metric],
            ),
            "minimum_points_used": None,
            "maximum_points_used": None,
            "insufficient_symbol_count": 0,
        }
        for metric in STOCK_STRATEGY_TECHNICAL_METRICS
        if stock_strategy_rule_is_active(metric, normalized_rules[metric])
    }

    industry_growth_rule = normalized_rules["industry_growth"]
    industry_growth_active = stock_strategy_rule_is_active(
        "industry_growth",
        industry_growth_rule,
    )
    industry_growth_comparisons = {}
    closing_price_series = {}
    if industry_growth_active:
        (
            industry_growth_comparisons,
            industry_growth_coverage,
            closing_price_series,
        ) = build_stock_industry_growth_comparisons(
            rows,
            history,
            industry_growth_rule["days"],
        )
        history_coverage["industry_growth"] = industry_growth_coverage

    symbol_industry_rule = normalized_rules["symbol_industry_compare"]
    symbol_industry_active = stock_strategy_rule_is_active(
        "symbol_industry_compare",
        symbol_industry_rule,
    )
    symbol_industry_comparisons = {}
    symbol_industry_target = None
    if symbol_industry_active:
        (
            symbol_industry_comparisons,
            symbol_industry_coverage,
            symbol_industry_price_series,
        ) = build_stock_industry_growth_comparisons(
            rows,
            history,
            symbol_industry_rule["days"],
        )
        history_coverage[
            "symbol_industry_compare"
        ] = symbol_industry_coverage
        symbol_industry_target = symbol_industry_comparisons.get(
            symbol_industry_rule["symbol"]
        )
        if not closing_price_series:
            closing_price_series = symbol_industry_price_series

    for row in rows:
        if not isinstance(row, dict) or not row.get("symbol"):
            continue
        normalized_symbol = normalize_symbol(row["symbol"])
        symbol_history = history.get(normalized_symbol, [])
        current_market_date = str(row.get("market_date") or "")
        result = {
            "symbol": row.get("symbol"),
            "company": row.get("company"),
            "industry": row.get("industry"),
            "market_value": row.get("market_value"),
            "ins_code": row.get("ins_code"),
            "price_power": row.get("price_power"),
            "price_power_status": (
                row.get("price_power_status")
                or stock_price_power_status(row)
            ),
            "last_price": row.get("last_price"),
            "closing_price": row.get("closing_price"),
            "daily_high_price": row.get("daily_high_price"),
            "daily_low_price": row.get("daily_low_price"),
            "daily_upper_price": row.get("daily_upper_price"),
            "daily_lower_price": row.get("daily_lower_price"),
            "order_book_buy_value": row.get("order_book_buy_value"),
            "order_book_buy_volume": row.get("order_book_buy_volume"),
            "order_book_buy_count": row.get("order_book_buy_count"),
            "order_book_sell_value": row.get("order_book_sell_value"),
            "order_book_sell_volume": row.get("order_book_sell_volume"),
            "order_book_sell_count": row.get("order_book_sell_count"),
        }
        passed = True
        row_has_partial_history = False
        row_has_missing_history = False
        row_has_zero_or_missing_value = False

        closing_prices = closing_price_series.get(normalized_symbol)
        if closing_prices is None:
            closing_prices = stock_strategy_closing_prices(row, symbol_history)
        rsi_rule = normalized_rules["rsi"]
        ema_rule = normalized_rules["ema"]
        macd_rule = normalized_rules["macd"]
        rsi_value = calculate_stock_rsi(
            closing_prices,
            rsi_rule["period"],
        )
        ema_value = calculate_stock_ema(
            closing_prices,
            ema_rule["period"],
        )
        ema_slow_value = calculate_stock_ema(
            closing_prices,
            ema_rule["long_period"],
        )
        ema_cross_direction = calculate_stock_ema_crossover(
            closing_prices,
            ema_rule["period"],
            ema_rule["long_period"],
        )
        macd_values = calculate_stock_macd(
            closing_prices,
            macd_rule["fast_period"],
            macd_rule["slow_period"],
            macd_rule["signal_period"],
        )
        current_closing_price = stock_number(row.get("closing_price"))
        result.update({
            "closing_price": current_closing_price,
            "technical_history_count": len(closing_prices),
            "rsi": rsi_value,
            "rsi_period": rsi_rule["period"],
            "ema": ema_value,
            "ema_period": ema_rule["period"],
            "ema_slow": ema_slow_value,
            "ema_long_period": ema_rule["long_period"],
            "ema_cross_direction": ema_cross_direction,
            "macd": macd_values["macd"],
            "macd_signal": macd_values["signal"],
            "macd_histogram": macd_values["histogram"],
            "macd_fast_period": macd_rule["fast_period"],
            "macd_slow_period": macd_rule["slow_period"],
            "macd_signal_period": macd_rule["signal_period"],
            "industry_growth_percent": None,
            "industry_average_growth_percent": None,
            "below_industry_average_percent": None,
            "industry_growth_days_used": 0,
            "industry_growth_member_count": 0,
            "symbol_industry_return_percent": None,
            "symbol_industry_average_return_percent": None,
            "symbol_industry_days_used": 0,
            "symbol_industry_member_count": 0,
        })

        if industry_growth_active:
            industry_growth = industry_growth_comparisons.get(normalized_symbol)
            if industry_growth is None:
                passed = False
                row_has_missing_history = True
            else:
                result.update({
                    key: industry_growth[key]
                    for key in (
                        "industry_growth_percent",
                        "industry_average_growth_percent",
                        "below_industry_average_percent",
                        "industry_growth_days_used",
                        "industry_growth_member_count",
                    )
                })
                if (
                    industry_growth["industry_growth_days_used"]
                    < industry_growth_rule["days"]
                ):
                    row_has_partial_history = True
                if industry_growth["below_industry_average_percent"] <= 0:
                    passed = False

        if symbol_industry_active:
            comparison = symbol_industry_comparisons.get(normalized_symbol)
            selected_industry_key = (
                symbol_industry_target.get("industry_key")
                if symbol_industry_target
                else None
            )
            is_selected_symbol = (
                normalized_symbol == symbol_industry_rule["symbol"]
            )
            is_selected_industry = bool(
                symbol_industry_rule["include_industry"]
                and comparison
                and selected_industry_key
                and comparison.get("industry_key") == selected_industry_key
            )
            if (
                symbol_industry_target is None
                or not (is_selected_symbol or is_selected_industry)
            ):
                passed = False
            elif comparison is None:
                passed = False
                row_has_missing_history = True
            else:
                result.update({
                    "symbol_industry_return_percent": comparison[
                        "industry_growth_percent"
                    ],
                    "symbol_industry_average_return_percent": comparison[
                        "industry_average_growth_percent"
                    ],
                    "symbol_industry_days_used": comparison[
                        "industry_growth_days_used"
                    ],
                    "symbol_industry_member_count": comparison[
                        "industry_growth_member_count"
                    ],
                })
                if (
                    comparison["industry_growth_days_used"]
                    < symbol_industry_rule["days"]
                ):
                    row_has_partial_history = True

        for metric in STOCK_STRATEGY_METRICS:
            rule = normalized_rules[metric]
            current_value = stock_number(row.get(metric))
            result[metric] = current_value
            result[f"{metric}_average"] = None
            result[f"{metric}_history_count"] = 0
            if metric == "real_money_flow":
                result["real_money_flow_positive_streak"] = 0
            if not stock_strategy_rule_is_active(metric, rule):
                continue

            accepts_negative = metric == "money_flow_quality"
            if (
                current_value is None
                or current_value == 0
                or (not accepts_negative and current_value < 0)
            ):
                passed = False
                row_has_zero_or_missing_value = True
                continue

            if metric == "real_money_flow":
                requested_streak = rule["consecutive_days"]
                if requested_streak > 0:
                    positive_streak = 1 if current_value > 0 else 0
                    available_days = 1
                    if positive_streak:
                        for snapshot in symbol_history:
                            if (
                                current_market_date
                                and snapshot.get("trade_date") == current_market_date
                            ):
                                continue
                            available_days += 1
                            value = stock_number(snapshot.get(metric))
                            if value is None or value <= 0:
                                break
                            positive_streak += 1
                            if positive_streak >= requested_streak:
                                break
                    result["real_money_flow_positive_streak"] = positive_streak
                    if positive_streak < requested_streak:
                        passed = False
                        if available_days < requested_streak:
                            row_has_missing_history = True

            should_compare_fixed = (
                metric == "money_flow_quality"
                or (
                    metric not in {"trade_value", "real_money_flow"}
                    and rule["fixed"] > 0
                )
            )
            if should_compare_fixed:
                if not compare_stock_strategy_value(
                    current_value,
                    rule["fixed"],
                    rule["operator"],
                ):
                    passed = False

            if rule["days"] > 0:
                historical_values = []
                for snapshot in symbol_history:
                    if (
                        current_market_date
                        and snapshot.get("trade_date") == current_market_date
                    ):
                        continue
                    value = stock_number(snapshot.get(metric))
                    if value is None or value == 0:
                        continue
                    if metric != "real_money_flow" and value < 0:
                        continue
                    historical_values.append(value)
                    if len(historical_values) >= rule["days"]:
                        break

                result[f"{metric}_history_count"] = len(historical_values)
                if not historical_values:
                    passed = False
                    row_has_missing_history = True
                else:
                    average = sum(historical_values) / len(historical_values)
                    result[f"{metric}_average"] = average
                    coverage = history_coverage[metric]
                    used_days = len(historical_values)
                    if used_days < rule["days"]:
                        row_has_partial_history = True
                        coverage["partial_symbol_count"] += 1
                        coverage["minimum_days_used"] = (
                            used_days
                            if coverage["minimum_days_used"] is None
                            else min(coverage["minimum_days_used"], used_days)
                        )
                        coverage["maximum_days_used"] = (
                            used_days
                            if coverage["maximum_days_used"] is None
                            else max(coverage["maximum_days_used"], used_days)
                        )
                    average_passed = (
                        current_value > average
                        if metric == "real_money_flow"
                        else compare_stock_strategy_value(
                            current_value,
                            average,
                            rule["operator"],
                        )
                    )
                    if not average_passed:
                        passed = False

        for metric in STOCK_STRATEGY_TECHNICAL_METRICS:
            rule = normalized_rules[metric]
            if not stock_strategy_rule_is_active(metric, rule):
                continue

            coverage = technical_coverage[metric]
            points_used = len(closing_prices)
            if metric == "rsi":
                current_value = rsi_value
                reference_value = rule["fixed"]
            elif metric == "ema":
                if rule.get("mode") == "crossover":
                    current_value = ema_cross_direction
                    reference_value = (
                        -1 if rule["operator"] == "lte"
                        else (0 if rule["operator"] == "eq" else 1)
                    )
                else:
                    current_value = current_closing_price
                    reference_value = ema_value
            else:
                current_value = macd_values["macd"]
                reference_value = (
                    0
                    if rule.get("compare_to") == "zero"
                    else macd_values["signal"]
                )

            if current_value is None or reference_value is None:
                passed = False
                row_has_missing_history = True
                coverage["insufficient_symbol_count"] += 1
                coverage["minimum_points_used"] = (
                    points_used
                    if coverage["minimum_points_used"] is None
                    else min(coverage["minimum_points_used"], points_used)
                )
                coverage["maximum_points_used"] = (
                    points_used
                    if coverage["maximum_points_used"] is None
                    else max(coverage["maximum_points_used"], points_used)
                )
                continue
            if metric == "rsi" and rule["operator"] == "between":
                if not rule["fixed"] <= current_value <= rule["maximum"]:
                    passed = False
                continue
            if metric == "ema" and rule.get("mode") == "crossover":
                if current_value != reference_value:
                    passed = False
                continue
            if not compare_stock_strategy_value(
                current_value,
                reference_value,
                rule["operator"],
            ):
                passed = False

        if row_has_partial_history:
            partial_history_count += 1
        if row_has_missing_history:
            missing_history_count += 1
        if row_has_zero_or_missing_value:
            excluded_zero_or_missing_count += 1
        if passed:
            results.append(result)

    return {
        "count": len(results),
        "evaluated_count": len(rows),
        "active_filter_count": len(active_metrics),
        "partial_history_count": partial_history_count,
        "missing_history_count": missing_history_count,
        "insufficient_history_count": missing_history_count,
        "excluded_zero_or_missing_count": excluded_zero_or_missing_count,
        "history_coverage": history_coverage,
        "technical_coverage": technical_coverage,
        "symbol_industry_target_found": (
            symbol_industry_target is not None
            if symbol_industry_active
            else None
        ),
        "symbol_industry_target_symbol": (
            symbol_industry_target.get("symbol")
            if symbol_industry_target
            else symbol_industry_rule.get("symbol") or None
        ),
        "symbol_industry_target_industry": (
            symbol_industry_target.get("industry")
            if symbol_industry_target
            else None
        ),
        "rules": normalized_rules,
        "stocks": results,
    }


def get_stock_strategy(payload, use_saved_data=False, source="featured"):
    source = "all" if source == "all" else "featured"
    rows, metadata = (
        read_all_stock_database()
        if source == "all"
        else read_stock_database()
    )
    snapshot_metadata = {}
    if use_saved_data:
        rows, snapshot_metadata = (
            apply_latest_stock_snapshots(rows, source="all")
            if source == "all"
            else apply_latest_stock_snapshots(rows)
        )
    result = evaluate_stock_strategy(
        rows,
        read_stock_strategy_history(
            source=source,
            symbols=[row.get("symbol") for row in rows if row.get("symbol")],
        ),
        payload,
    )
    result["source"] = source
    result["source_updated_at"] = metadata.get("last_successful_update")
    result.update(snapshot_metadata)
    return result


def stock_strategy_export_settings(rules):
    """Return active strategy inputs as readable spreadsheet rows."""
    operator_labels = {
        "gte": "بزرگ‌تر یا مساوی",
        "lte": "کوچک‌تر یا مساوی",
        "eq": "مساوی",
        "between": "بین دو مقدار",
    }
    settings = []

    def add(strategy, field, value):
        settings.append((strategy, field, value))

    for metric, strategy_name in (
        ("trade_value", "ارزش معاملات"),
        ("trade_to_float_percent", "نسبت معامله به شناوری"),
        ("real_buy_power", "قدرت خرید حقیقی"),
        ("real_money_flow", "ورود پول حقیقی"),
        ("money_flow_quality", "کیفیت ورود پول"),
        ("symbol_industry_compare", "مقایسه نماد با صنعت"),
        ("industry_growth", "میانگین رشد صنعت"),
        ("rsi", "RSI"),
        ("ema", "EMA"),
        ("macd", "MACD"),
    ):
        rule = rules.get(metric) or {}
        if not stock_strategy_rule_is_active(metric, rule):
            continue

        if metric == "trade_value":
            add(strategy_name, "نوع مقایسه", operator_labels[rule["operator"]])
            add(strategy_name, "میانگین چند روزه", rule["days"])
        elif metric in {"trade_to_float_percent", "real_buy_power"}:
            add(strategy_name, "نوع مقایسه", operator_labels[rule["operator"]])
            add(
                strategy_name,
                "عدد ثابت (درصد)"
                if metric == "trade_to_float_percent"
                else "عدد ثابت (برابر)",
                rule["fixed"],
            )
            add(strategy_name, "میانگین چند روزه", rule["days"])
        elif metric == "real_money_flow":
            add(
                strategy_name,
                "حداقل روزهای مثبت پیاپی",
                rule["consecutive_days"],
            )
            add(
                strategy_name,
                "بزرگ‌تر از میانگین چندروزه",
                rule["days"],
            )
        elif metric == "money_flow_quality":
            add(strategy_name, "نوع مقایسه", operator_labels[rule["operator"]])
            add(strategy_name, "درصد کیفیت ورود پول", rule["fixed"])
        elif metric == "symbol_industry_compare":
            add(strategy_name, "نماد مبنا", rule.get("symbol") or "—")
            add(strategy_name, "بازه بازدهی (روز)", rule["days"])
            add(
                strategy_name,
                "نمایش هم‌صنعتی‌ها",
                "بله" if rule.get("include_industry") else "خیر",
            )
        elif metric == "industry_growth":
            add(
                strategy_name,
                "بازه رشد قیمت پایانی (روز)",
                rule["days"],
            )
        elif metric == "rsi":
            add(strategy_name, "نوع مقایسه", operator_labels[rule["operator"]])
            add(strategy_name, "حد پایین", rule["fixed"])
            add(strategy_name, "حد بالا", rule["maximum"])
            add(strategy_name, "دوره", rule["period"])
        elif metric == "ema":
            add(
                strategy_name,
                "حالت بررسی",
                "تقاطع EMA کوتاه و بلند"
                if rule.get("mode") == "crossover"
                else "قیمت پایانی نسبت به EMA",
            )
            add(strategy_name, "جهت مقایسه", operator_labels[rule["operator"]])
            add(strategy_name, "دوره EMA کوتاه", rule["period"])
            add(strategy_name, "دوره EMA بلند", rule["long_period"])
        elif metric == "macd":
            add(
                strategy_name,
                "مقایسه با",
                "خط صفر" if rule.get("compare_to") == "zero" else "خط Signal",
            )
            add(strategy_name, "نوع مقایسه", operator_labels[rule["operator"]])
            add(strategy_name, "دوره سریع", rule["fast_period"])
            add(strategy_name, "دوره کند", rule["slow_period"])
            add(strategy_name, "دوره Signal", rule["signal_period"])

    return settings


def stock_strategy_export_columns(rules):
    """Build result columns only for strategies enabled in the export."""
    columns = [
        {"key": "symbol", "label": "نماد", "format": "@"},
        {"key": "company", "label": "نام شرکت", "format": "@"},
        {"key": "industry", "label": "صنعت", "format": "@"},
    ]
    added_keys = {column["key"] for column in columns}

    def add(key, label, number_format="0.00", scale=1, value_map=None):
        if key in added_keys:
            return
        columns.append({
            "key": key,
            "label": label,
            "format": number_format,
            "scale": scale,
            "value_map": value_map,
        })
        added_keys.add(key)

    rule = rules.get("trade_value") or {}
    if stock_strategy_rule_is_active("trade_value", rule):
        add(
            "trade_value",
            "ارزش معاملات (میلیارد تومان)",
            "#,##0.00",
            10_000_000_000,
        )
        if rule.get("days", 0) > 0:
            add(
                "trade_value_average",
                "میانگین ارزش معاملات (میلیارد تومان)",
                "#,##0.00",
                10_000_000_000,
            )

    rule = rules.get("trade_to_float_percent") or {}
    if stock_strategy_rule_is_active("trade_to_float_percent", rule):
        add("trade_to_float_percent", "نسبت معامله به شناوری (درصد)")
        if rule.get("days", 0) > 0:
            add(
                "trade_to_float_percent_average",
                "میانگین نسبت معامله به شناوری (درصد)",
            )

    rule = rules.get("real_buy_power") or {}
    if stock_strategy_rule_is_active("real_buy_power", rule):
        add("real_buy_power", "قدرت خرید حقیقی (برابر)")
        if rule.get("days", 0) > 0:
            add("real_buy_power_average", "میانگین قدرت خرید حقیقی (برابر)")

    rule = rules.get("real_money_flow") or {}
    if stock_strategy_rule_is_active("real_money_flow", rule):
        add(
            "real_money_flow",
            "ورود پول حقیقی (میلیارد تومان)",
            "#,##0.00",
            10_000_000_000,
        )
        if rule.get("consecutive_days", 0) > 0:
            add(
                "real_money_flow_positive_streak",
                "ورود پول مثبت پیاپی (روز)",
                "#,##0",
            )
        if rule.get("days", 0) > 0:
            add(
                "real_money_flow_average",
                "میانگین ورود پول (میلیارد تومان)",
                "#,##0.00",
                10_000_000_000,
            )

    rule = rules.get("money_flow_quality") or {}
    if stock_strategy_rule_is_active("money_flow_quality", rule):
        add("money_flow_quality", "کیفیت ورود پول (درصد)")

    rule = rules.get("industry_growth") or {}
    if stock_strategy_rule_is_active("industry_growth", rule):
        add("industry_growth_percent", "بازدهی نماد (درصد)")
        add(
            "industry_average_growth_percent",
            "میانگین بازدهی صنعت (درصد)",
        )
        add(
            "below_industry_average_percent",
            "فاصله از میانگین صنعت (درصد)",
        )
        add("industry_growth_days_used", "روزهای محاسبه", "#,##0")

    rule = rules.get("symbol_industry_compare") or {}
    if stock_strategy_rule_is_active("symbol_industry_compare", rule):
        add("symbol_industry_return_percent", "بازدهی نماد (درصد)")
        add(
            "symbol_industry_average_return_percent",
            "میانگین بازدهی صنعت (درصد)",
        )
        add("symbol_industry_days_used", "روزهای محاسبه", "#,##0")

    rule = rules.get("rsi") or {}
    if stock_strategy_rule_is_active("rsi", rule):
        add("rsi", f"RSI {rule['period']}")

    rule = rules.get("ema") or {}
    if stock_strategy_rule_is_active("ema", rule):
        add("closing_price", "قیمت پایانی (ریال)", "#,##0")
        add("ema", f"EMA {rule['period']} (ریال)", "#,##0.00")
        if rule.get("mode") == "crossover":
            add(
                "ema_slow",
                f"EMA {rule['long_period']} (ریال)",
                "#,##0.00",
            )
            add(
                "ema_cross_direction",
                "جهت تقاطع EMA",
                "@",
                value_map={
                    -1: "شکست رو به پایین",
                    0: "بدون تقاطع",
                    1: "شکست رو به بالا",
                },
            )

    rule = rules.get("macd") or {}
    if stock_strategy_rule_is_active("macd", rule):
        add("macd", "MACD")
        add("macd_signal", "Signal")
        add("macd_histogram", "Histogram")

    return columns


def build_stock_strategy_excel(result, use_saved_data=False):
    """Create a two-sheet XLSX for active strategy inputs and results."""
    rules = result.get("rules") or {}
    settings = stock_strategy_export_settings(rules)
    if not settings:
        raise ValueError("حداقل یک استراتژی معتبر را فعال کنید.")

    columns = stock_strategy_export_columns(rules)
    stocks = result.get("stocks") or []
    workbook = Workbook()
    settings_sheet = workbook.active
    settings_sheet.title = "تنظیمات فعال"
    results_sheet = workbook.create_sheet("نتایج")
    workbook.properties.title = "خروجی استراتژی سهام"
    workbook.properties.creator = "دیدبان بازار سهام"

    dark_fill = PatternFill("solid", fgColor="0B3558")
    accent_fill = PatternFill("solid", fgColor="DDF5FF")
    white_font = Font(name="Arial", color="FFFFFF", bold=True)
    title_font = Font(name="Arial", color="0B3558", bold=True, size=15)
    body_font = Font(name="Arial", color="172033", size=10)
    thin_border = Border(
        bottom=Side(style="thin", color="B8D8E8"),
    )
    generated_at = datetime.now(IRAN_TIMEZONE)
    jalali_date = jdatetime.date.fromgregorian(
        date=generated_at.date()
    ).strftime("%Y/%m/%d")
    generated_label = f"{jalali_date} - {generated_at.strftime('%H:%M')}"
    source_label = (
        "تمام سهام‌ها"
        if result.get("source") == "all"
        else "سهام برتر"
    )
    data_label = (
        "آخرین داده ذخیره‌شده"
        if use_saved_data
        else "آخرین داده موجود"
    )

    for worksheet in (settings_sheet, results_sheet):
        worksheet.sheet_view.rightToLeft = True
        worksheet.sheet_view.showGridLines = False
        worksheet.freeze_panes = "A1"

    settings_sheet["A1"] = "تنظیمات فعال استراتژی"
    settings_sheet["A1"].font = title_font
    settings_sheet["A2"] = "دامنه اجرا"
    settings_sheet["B2"] = source_label
    settings_sheet["A3"] = "مبنای داده"
    settings_sheet["B3"] = data_label
    settings_sheet["A4"] = "زمان تولید"
    settings_sheet["B4"] = generated_label
    settings_sheet["A5"] = "تعداد نمادهای نتیجه"
    settings_sheet["B5"] = len(stocks)
    settings_header_row = 7
    settings_sheet.append([])
    settings_sheet.append(["استراتژی", "ورودی", "مقدار"])
    for strategy, field, value in settings:
        settings_sheet.append([strategy, field, value])
    settings_end_row = settings_header_row + len(settings)
    settings_table = Table(
        displayName="ActiveStrategySettings",
        ref=f"A{settings_header_row}:C{settings_end_row}",
    )
    settings_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    settings_sheet.add_table(settings_table)
    settings_sheet.freeze_panes = f"A{settings_header_row + 1}"

    results_sheet["A1"] = "نمادهای عبورکرده از استراتژی‌های فعال"
    results_sheet["A1"].font = title_font
    results_sheet["A2"] = "دامنه و مبنای داده"
    results_sheet["B2"] = f"{source_label} - {data_label}"
    results_sheet["A3"] = "تعداد نتیجه"
    results_sheet["B3"] = len(stocks)
    results_header_row = 5
    for column_index, column in enumerate(columns, start=1):
        results_sheet.cell(results_header_row, column_index, column["label"])

    for row_index, stock in enumerate(stocks, start=results_header_row + 1):
        for column_index, column in enumerate(columns, start=1):
            value = stock.get(column["key"])
            value_map = column.get("value_map")
            if value_map is not None:
                value = value_map.get(value, value_map.get(stock_number(value), "—"))
            elif value is not None and column.get("scale", 1) != 1:
                numeric_value = stock_number(value)
                value = (
                    numeric_value / column["scale"]
                    if numeric_value is not None
                    else None
                )
            cell = results_sheet.cell(row_index, column_index, value)
            cell.number_format = column.get("format", "General")

    if stocks:
        results_end_row = results_header_row + len(stocks)
        results_table = Table(
            displayName="StrategyResults",
            ref=(
                f"A{results_header_row}:"
                f"{results_sheet.cell(results_header_row, len(columns)).column_letter}"
                f"{results_end_row}"
            ),
        )
        results_table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        results_sheet.add_table(results_table)

    for worksheet in (settings_sheet, results_sheet):
        for row in worksheet.iter_rows():
            for cell in row:
                if cell.row != 1:
                    cell.font = body_font
                cell.alignment = Alignment(
                    horizontal="right",
                    vertical="center",
                )
        worksheet.row_dimensions[1].height = 27

    for row in range(2, 6):
        settings_sheet.cell(row, 1).font = Font(
            name="Arial", color="36546B", bold=True, size=10
        )
        settings_sheet.cell(row, 1).fill = accent_fill
        settings_sheet.cell(row, 2).fill = accent_fill
    for cell in settings_sheet[settings_header_row]:
        cell.fill = dark_fill
        cell.font = white_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    for cell in results_sheet[results_header_row]:
        cell.fill = dark_fill
        cell.font = white_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
    for row in range(2, 4):
        results_sheet.cell(row, 1).font = Font(
            name="Arial", color="36546B", bold=True, size=10
        )
        results_sheet.cell(row, 1).fill = accent_fill
        results_sheet.cell(row, 2).fill = accent_fill

    settings_sheet.column_dimensions["A"].width = 25
    settings_sheet.column_dimensions["B"].width = 34
    settings_sheet.column_dimensions["C"].width = 24
    settings_sheet.auto_filter.ref = (
        f"A{settings_header_row}:C{settings_end_row}"
    )
    for column_index, column in enumerate(columns, start=1):
        letter = results_sheet.cell(results_header_row, column_index).column_letter
        results_sheet.column_dimensions[letter].width = min(
            36,
            max(13, len(column["label"]) * 1.15),
        )
    results_sheet.freeze_panes = "D6"
    results_sheet.auto_filter.ref = (
        f"A{results_header_row}:"
        f"{results_sheet.cell(results_header_row, len(columns)).column_letter}"
        f"{results_header_row + max(len(stocks), 1)}"
    )

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_stock_buy_queue_summary(
    rows,
    history,
    limit=10,
    use_previous_day=False,
    reference_date=None,
):
    requested_limit = normalize_stock_strategy_integer(
        limit,
        10,
        minimum=1,
        maximum=100,
    )
    reference_date = str(
        reference_date or datetime.now(IRAN_TIMEZONE).date().isoformat()
    )
    results = []
    target_dates = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("symbol"):
            continue

        normalized_symbol = normalize_symbol(row["symbol"])
        dated_candidates = []
        seen_candidate_dates = set()
        symbol_history = history.get(normalized_symbol, [])
        candidate_rows = (
            [*symbol_history, row]
            if use_previous_day
            else [row, *symbol_history]
        )
        for candidate in candidate_rows:
            if not isinstance(candidate, dict):
                continue
            candidate_date = str(
                candidate.get("trade_date")
                or candidate.get("market_date")
                or ""
            )
            if not candidate_date or candidate_date in seen_candidate_dates:
                continue
            seen_candidate_dates.add(candidate_date)
            dated_candidates.append((candidate_date, candidate))
        dated_candidates.sort(key=lambda item: item[0], reverse=True)

        target_date = str(row.get("market_date") or row.get("trade_date") or "")
        target_row = row
        if use_previous_day:
            previous_candidate = next(
                (
                    candidate
                    for candidate in dated_candidates
                    if candidate[0] < reference_date
                ),
                None,
            )
            if previous_candidate is None:
                continue
            target_date, target_row = previous_candidate

        if stock_strategy_buy_queue_state(target_row) is not True:
            continue

        buy_queue_value = stock_number(
            target_row.get("order_book_buy_value")
        )
        if buy_queue_value is None or buy_queue_value <= 0:
            continue

        historical_rows = [
            candidate
            for candidate_date, candidate in dated_candidates
            if candidate_date < target_date
        ]

        trade_value = stock_number(target_row.get("trade_value"))
        consecutive_queue_days = 1
        for snapshot in historical_rows:
            if stock_strategy_buy_queue_state(snapshot) is not True:
                break
            consecutive_queue_days += 1

        traded_value_percent = (
            round(
                trade_value / (trade_value + buy_queue_value) * 100,
                4,
            )
            if trade_value is not None
            and trade_value >= 0
            and trade_value + buy_queue_value > 0
            else None
        )
        results.append({
            "symbol": row.get("symbol"),
            "ins_code": row.get("ins_code"),
            "market_date": target_date or None,
            "buy_queue_value": buy_queue_value,
            "trade_value": trade_value,
            "traded_value_percent": traded_value_percent,
            "consecutive_queue_days": consecutive_queue_days,
        })
        if target_date:
            target_dates.add(target_date)

    results.sort(
        key=lambda item: (
            item["buy_queue_value"],
            item["trade_value"] is not None,
            item["trade_value"] or 0,
        ),
        reverse=True,
    )
    return {
        "requested_count": requested_limit,
        "matched_count": len(results),
        "count": min(len(results), requested_limit),
        "stocks": results[:requested_limit],
        "data_mode": "previous_day" if use_previous_day else "latest",
        "data_dates": sorted(target_dates, reverse=True),
    }


def get_stock_buy_queue_summary(
    limit=10,
    source="all",
    use_previous_day=False,
):
    source = "featured" if source == "featured" else "all"
    rows, metadata = (
        read_stock_database()
        if source == "featured"
        else read_all_stock_database()
    )
    result = build_stock_buy_queue_summary(
        rows,
        read_stock_strategy_history(
            source=source,
            symbols=[row.get("symbol") for row in rows if row.get("symbol")],
        ),
        limit=limit,
        use_previous_day=use_previous_day,
    )
    result.update({
        "source": source,
        "source_updated_at": metadata.get("last_successful_update"),
        "evaluated_count": len(rows),
    })
    return result


def watch_market_number(value):
    """Convert an upstream numeric field without accepting booleans."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def watch_market_timestamp(value):
    """Return a comparable Unix timestamp for an upstream market time."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1_000
        return timestamp

    text = str(value).strip()
    if not text:
        return None
    try:
        numeric_timestamp = float(text)
    except ValueError:
        numeric_timestamp = None
    if numeric_timestamp is not None:
        if numeric_timestamp > 10_000_000_000:
            numeric_timestamp /= 1_000
        return numeric_timestamp

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IRAN_TIMEZONE)
    return parsed.timestamp()


def get_rahavard_live_quotes(wait_seconds=4):
    """Return fresh last-trade quotes broadcast by Rahavard's live channel."""
    now = int(time.time())
    required_currency_ids = {2, 43157}
    with rahavard_live_quotes_lock:
        process = rahavard_live_quotes_state.get("process")
        if process is None or process.poll() is not None:
            try:
                rahavard_live_quotes_state["process"] = subprocess.Popen(
                    ["node", RAHAVARD_LIVE_COLLECTOR_FILE],
                    cwd=app.root_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except OSError:
                rahavard_live_quotes_state["process"] = None

        deadline = time.time() + max(0, wait_seconds)
        while True:
            try:
                with open(
                    RAHAVARD_LIVE_QUOTES_FILE,
                    "r",
                    encoding="utf-8",
                ) as file:
                    payload = json.load(file)
                fresh_quotes = {
                    int(asset_id): quote
                    for asset_id, quote in payload.items()
                    if (
                        isinstance(quote, dict)
                        and now - int(quote.get("fetched_at", 0))
                        < RAHAVARD_LIVE_QUOTE_MAX_AGE_SECONDS
                    )
                }
                # A valid file is authoritative even when all entries have
                # expired. This prevents stale in-memory quotes from living
                # forever after the live collector stops receiving updates.
                rahavard_live_quotes_state["data"] = fresh_quotes
                if required_currency_ids.issubset(fresh_quotes):
                    break
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                fresh_quotes = {}

            if time.time() >= deadline:
                break
            time.sleep(0.15)

        return {
            int(asset_id): quote
            for asset_id, quote in (
                rahavard_live_quotes_state.get("data") or {}
            ).items()
            if (
                isinstance(quote, dict)
                and now - int(quote.get("fetched_at", 0))
                < RAHAVARD_LIVE_QUOTE_MAX_AGE_SECONDS
            )
        }


def normalize_rahavard_live_quote(quote, config):
    raw_price = watch_market_number(quote.get("price"))
    if raw_price is None or raw_price <= 0:
        raise ValueError("قیمت زنده معتبر از ره‌آورد دریافت نشد.")
    divisor = float(config.get("divisor") or 1)
    raw_change = watch_market_number(quote.get("price_change"))
    raw_percent = watch_market_number(quote.get("change_percent"))
    if raw_percent is not None and abs(raw_percent) <= 1:
        raw_percent *= 100
    return {
        "key": config["key"],
        "name": config["name"],
        "price": raw_price / divisor,
        "unit": config["unit"],
        "change": raw_change / divisor if raw_change is not None else None,
        "change_percent": raw_percent,
        "market_time": quote.get("market_time"),
        "tone": config.get("tone", "currency"),
        "source": "rahavard365-live",
        "source_url": config["source_url"],
    }


def parse_rahavard_quote(asset_data, config):
    """Normalize one Rahavard asset response for the Markets summary cards."""
    trades = asset_data.get("trades") or []
    preferred_payloads = (
        list(trades)
        + [asset_data.get("last_trade"), asset_data.get("header_last_trade")]
        if config.get("prefer_daily_trade")
        else [asset_data.get("last_trade"), asset_data.get("header_last_trade")]
        + list(trades)
    )

    payload = None
    raw_price = None
    uses_real_price = False
    for candidate in preferred_payloads:
        if not isinstance(candidate, dict):
            continue
        candidate_real_price = watch_market_number(
            candidate.get("real_close_price")
        )
        candidate_close_price = watch_market_number(candidate.get("close_price"))
        if candidate_real_price is not None and candidate_real_price > 0:
            payload = candidate
            raw_price = candidate_real_price
            uses_real_price = True
            break
        if candidate_close_price is not None and candidate_close_price > 0:
            payload = candidate
            raw_price = candidate_close_price
            break

    if payload is None or raw_price is None:
        raise ValueError("قیمت معتبر از ره‌آورد دریافت نشد.")

    change_field = (
        "real_close_price_change"
        if uses_real_price
        else "close_price_change"
    )
    percent_field = (
        "real_close_price_change_percent"
        if uses_real_price
        else "close_price_change_percent"
    )
    divisor = float(config.get("divisor") or 1)
    raw_change = watch_market_number(payload.get(change_field))
    raw_percent = watch_market_number(payload.get(percent_field))

    return {
        "key": config["key"],
        "name": config["name"],
        "price": raw_price / divisor,
        "unit": config["unit"],
        "change": raw_change / divisor if raw_change is not None else None,
        "change_percent": (
            raw_percent * 100
            if raw_percent is not None
            else None
        ),
        "market_time": (
            payload.get("end_date_time")
            or payload.get("end_time")
            or payload.get("date_time")
        ),
        "tone": config.get("tone", "currency"),
        "source": "rahavard365",
        "source_url": config["source_url"],
    }


def fetch_rahavard_watch_asset(config, live_quotes=None):
    live_quote = (live_quotes or {}).get(config["asset_id"])
    normalized_live_quote = None
    if live_quote:
        try:
            normalized_live_quote = normalize_rahavard_live_quote(
                live_quote,
                config,
            )
        except (ValueError, TypeError):
            pass
    if config.get("live_required"):
        if normalized_live_quote:
            return normalized_live_quote
        raise ValueError("قیمت زنده آخرین معامله هنوز دریافت نشده است.")

    response = requests.get(
        f"https://rahavard365.com/api/v2/asset/{config['asset_id']}",
        headers=RAHAVARD_HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    asset_data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(asset_data, dict):
        raise ValueError("پاسخ دارایی ره‌آورد معتبر نیست.")
    api_quote = parse_rahavard_quote(asset_data, config)
    if normalized_live_quote:
        live_time = watch_market_timestamp(
            normalized_live_quote.get("market_time")
        )
        api_time = watch_market_timestamp(api_quote.get("market_time"))
        if live_time is not None and (
            api_time is None or live_time > api_time
        ):
            return normalized_live_quote
    return api_quote


def fetch_global_copper_quote():
    response = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/HG=F",
        params={"range": "1d", "interval": "5m"},
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    meta = result["meta"]
    price = watch_market_number(meta.get("regularMarketPrice"))
    if price is None or price <= 0:
        raise ValueError("قیمت معتبر مس جهانی دریافت نشد.")

    change = watch_market_number(meta.get("regularMarketChange"))
    change_percent = watch_market_number(meta.get("regularMarketChangePercent"))
    previous_close = watch_market_number(meta.get("chartPreviousClose"))
    if change is None and previous_close is not None:
        change = price - previous_close
    if (
        change_percent is None
        and previous_close is not None
        and previous_close > 0
    ):
        change_percent = (price / previous_close - 1) * 100

    price_per_metric_ton = price * POUNDS_PER_METRIC_TON
    change_per_metric_ton = (
        change * POUNDS_PER_METRIC_TON
        if change is not None
        else None
    )

    return {
        "key": "global_copper",
        "name": "مس جهانی",
        "price": round(price_per_metric_ton, 2),
        "unit": "دلار/تن",
        "change": (
            round(change_per_metric_ton, 2)
            if change_per_metric_ton is not None
            else None
        ),
        "change_percent": change_percent,
        "market_time": meta.get("regularMarketTime"),
        "tone": "copper",
        "source": "yahoo-finance",
        "source_url": "https://finance.yahoo.com/quote/HG=F/",
    }


def parse_bourseeye_commodity_quote(page_html, config):
    """Parse one public IME certificate quote embedded in BourseEye HTML."""
    if not isinstance(page_html, str) or not page_html:
        raise ValueError("صفحه قیمت‌های بورس کالا معتبر نیست.")

    code = str(config.get("code") or "").strip()
    patterns = (
        (rf'\\"code\\"\s*:\s*\\"{re.escape(code)}\\"', True),
        (rf'"code"\s*:\s*"{re.escape(code)}"', False),
    )
    marker_index = -1
    escaped = False
    for pattern, is_escaped in patterns:
        match = re.search(pattern, page_html)
        if match:
            marker_index = match.start()
            escaped = is_escaped
            break
    if marker_index < 0:
        raise ValueError(f"قیمت {config.get('name') or code} پیدا نشد.")

    object_start = page_html.rfind("{", 0, marker_index)
    object_end = page_html.find("}", marker_index)
    if object_start < 0 or object_end < 0:
        raise ValueError("ساختار داده بورس کالا معتبر نیست.")

    serialized = page_html[object_start:object_end + 1]
    if escaped:
        serialized = serialized.replace(r'\"', '"')
    try:
        row = json.loads(serialized)
    except json.JSONDecodeError as error:
        raise ValueError("داده قیمت بورس کالا قابل خواندن نیست.") from error

    unit_price_rials = watch_market_number(
        row.get("unit_price_rials") or row.get("price_rials")
    )
    if unit_price_rials is None or unit_price_rials <= 0:
        raise ValueError("آخرین قیمت معتبر بورس کالا دریافت نشد.")

    return {
        "key": config["key"],
        "name": config["name"],
        "price": unit_price_rials / 10,
        "unit": "تومان/کیلوگرم",
        "change": None,
        "change_percent": watch_market_number(
            row.get("price_change_percent")
        ),
        "market_time": row.get("price_date"),
        "tone": config.get("tone", "market"),
        "source": "bourseeye-ime",
        "source_url": config["source_url"],
    }


def fetch_bourseeye_commodity_quotes():
    """Fetch the selected IME certificate prices with one public request."""
    response = requests.get(
        "https://bourseeye.com/commodities",
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache",
            "User-Agent": TSETMC_HEADERS["User-Agent"],
        },
        timeout=20,
    )
    response.raise_for_status()
    quotes = {}
    for config in WATCH_IME_COMMODITIES:
        try:
            quote = parse_bourseeye_commodity_quote(response.text, config)
        except (KeyError, TypeError, ValueError):
            continue
        quotes[quote["key"]] = quote
    if not quotes:
        raise ValueError("هیچ قیمت معتبری از بورس کالا دریافت نشد.")
    return quotes


def fetch_rahavard_fund_ids(kind):
    response = requests.get(
        f"https://rahavard365.com/api/v2/{kind}/funds",
        headers=RAHAVARD_HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("فهرست صندوق‌های کالایی معتبر نیست.")
    return {
        int(row["asset_id"])
        for row in rows
        if isinstance(row, dict) and row.get("asset_id")
    }


def fetch_rahavard_fund_money(asset_id):
    response = requests.get(
        (
            "https://rahavard365.com/api/v2/market-data/assets/"
            f"{asset_id}/last-trade"
        ),
        headers=RAHAVARD_HEADERS,
        timeout=15,
    )
    if response.status_code == 404:
        return {"money": 0.0, "market_date": None}
    response.raise_for_status()
    payload = response.json()
    row = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(row, dict):
        raise ValueError("داده جریان پول صندوق معتبر نیست.")

    person_buy_value = watch_market_number(row.get("person_buy_value")) or 0
    person_sell_value = watch_market_number(row.get("person_sell_value")) or 0
    market_time = row.get("end_time") or row.get("end_date_time") or ""
    return {
        "money": (
            person_buy_value - person_sell_value
        ) / 10 / 1_000_000_000,
        "market_date": str(market_time)[:10] or None,
    }


def fetch_commodity_fund_money_totals():
    groups = {
        kind: fetch_rahavard_fund_ids(kind)
        for kind in ("gold", "silver")
    }
    rows = {"gold": [], "silver": []}
    errors = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(fetch_rahavard_fund_money, asset_id): kind
            for kind, asset_ids in groups.items()
            for asset_id in asset_ids
        }
        for future in as_completed(futures):
            kind = futures[future]
            try:
                rows[kind].append(future.result())
            except (requests.RequestException, ValueError, TypeError):
                errors.append(f"{kind}-fund")

    totals = {}
    for kind, items in rows.items():
        latest_date = max(
            (
                item["market_date"]
                for item in items
                if item.get("market_date")
            ),
            default=None,
        )
        current_items = [
            item
            for item in items
            if item.get("market_date") == latest_date
        ]
        totals[kind] = {
            "value": sum(item["money"] for item in current_items),
            "count": len(current_items),
            "market_date": latest_date,
        }
    return totals, errors


def watch_market_flow_item(key, name, value, count=None, market_date=None):
    return {
        "key": key,
        "name": name,
        "value": value,
        "unit": "میلیارد تومان",
        "count": count,
        "market_date": market_date,
    }


def get_watch_market_overview(force=False):
    """Fetch the cross-market prices and commodity-fund money flows."""
    now = int(time.time())
    with watch_market_overview_cache_lock:
        cached_data = watch_market_overview_cache["data"]
        cached_at = watch_market_overview_cache["fetched_at"]
        if (
            not force
            and cached_data
            and now - cached_at < WATCH_MARKET_OVERVIEW_TTL_SECONDS
        ):
            return dict(cached_data)

    previous_prices = {
        item.get("key"): item
        for item in (cached_data or {}).get("prices", [])
        if item.get("key")
    }
    previous_flows = {
        item.get("key"): item
        for item in (cached_data or {}).get("flows", [])
        if item.get("key")
    }
    prices = dict(previous_prices)
    flows = dict(previous_flows)
    errors = []

    try:
        live_quotes = get_rahavard_live_quotes()
    except Exception:
        live_quotes = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        asset_futures = {
            executor.submit(
                fetch_rahavard_watch_asset,
                config,
                live_quotes,
            ): config["key"]
            for config in WATCH_MARKET_ASSETS
        }
        copper_future = executor.submit(fetch_global_copper_quote)
        ime_commodities_future = executor.submit(
            fetch_bourseeye_commodity_quotes
        )
        fund_money_future = executor.submit(fetch_commodity_fund_money_totals)

        for future in as_completed(asset_futures):
            key = asset_futures[future]
            try:
                prices[key] = future.result()
            except (requests.RequestException, ValueError, TypeError, KeyError):
                errors.append(key)

        try:
            copper = copper_future.result()
            prices[copper["key"]] = copper
        except (requests.RequestException, ValueError, TypeError, KeyError):
            errors.append("global_copper")

        try:
            ime_quotes = ime_commodities_future.result()
            prices.update(ime_quotes)
            errors.extend(
                config["key"]
                for config in WATCH_IME_COMMODITIES
                if config["key"] not in ime_quotes
            )
        except (requests.RequestException, ValueError, TypeError, KeyError):
            errors.append("ime-commodities")

        try:
            fund_totals, fund_errors = fund_money_future.result()
            errors.extend(fund_errors)
            for kind, name in (
                ("gold", "خالص پول صندوق‌های طلا"),
                ("silver", "خالص پول صندوق‌های نقره"),
            ):
                total = fund_totals.get(kind, {})
                flows[f"{kind}_funds"] = watch_market_flow_item(
                    f"{kind}_funds",
                    name,
                    total.get("value"),
                    count=total.get("count"),
                    market_date=total.get("market_date"),
                )
        except (requests.RequestException, ValueError, TypeError, KeyError):
            errors.append("fund-money")

    price_order = [config["key"] for config in WATCH_MARKET_ASSETS]
    price_order.insert(5, "global_copper")
    price_order.extend(config["key"] for config in WATCH_IME_COMMODITIES)
    flow_order = ("gold_funds", "silver_funds")
    result = {
        "prices": [prices[key] for key in price_order if key in prices],
        "flows": [flows[key] for key in flow_order if key in flows],
        "fetched_at": now if prices or flows else (cached_data or {}).get("fetched_at"),
        "errors": sorted(set(errors)),
    }
    if result["prices"] or result["flows"]:
        with watch_market_overview_cache_lock:
            watch_market_overview_cache.update(data=result, fetched_at=now)
    return result


def latest_watch_market_value(values):
    for value in reversed(values or []):
        number = watch_market_number(value)
        if number is not None:
            return number
    return None


def fetch_tradersarena_json(path):
    """Fetch one public TradersArena market-chart payload."""
    response = requests.get(
        f"https://tradersarena.ir{path}",
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Cache-Control": "no-cache",
            "Referer": "https://tradersarena.ir/",
            "User-Agent": TSETMC_HEADERS["User-Agent"],
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("پاسخ نمودارهای دیدبان معتبر نیست.")
    return payload


def fetch_tradersarena_industry_money_flows():
    """Return current real-money flow for all public industry rows."""
    response = requests.get(
        "https://tradersarena.ir/data/industries-csv",
        headers={
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Cache-Control": "no-cache",
            "Referer": "https://tradersarena.ir/",
            "User-Agent": TSETMC_HEADERS["User-Agent"],
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=15,
    )
    response.raise_for_status()
    try:
        rows = json.loads(response.content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("پاسخ جریان پول صنایع معتبر نیست.") from error
    if not isinstance(rows, list):
        raise ValueError("فهرست جریان پول صنایع معتبر نیست.")

    money_scale = 10_000_000_000
    excluded_industry_keys = {"gold-funds", "silver-funds"}
    industry_flows = []
    for row in rows:
        if not isinstance(row, list) or len(row) <= 15:
            continue
        key = str(row[0] or "").strip()
        if key in excluded_industry_keys:
            continue
        name = str(row[1] or "").strip()
        value = watch_market_number(row[15])
        if not name or value is None:
            continue
        industry_flows.append({
            "key": key,
            "name": name,
            "value": value / money_scale,
            "unit": "میلیارد تومان",
        })

    return sorted(
        industry_flows,
        key=lambda item: item["value"],
        reverse=True,
    )


def split_dedicated_industry_money_flows(industry_flows):
    """Move groups with dedicated cards out of the industry panel."""
    dedicated_keys = {
        "fixed-income-funds": "fixed_income",
    }
    visible_rows = []
    dedicated_rows = {}
    for item in industry_flows or []:
        if not isinstance(item, dict):
            continue
        dedicated_key = dedicated_keys.get(item.get("key"))
        if dedicated_key:
            dedicated_rows[dedicated_key] = item
        else:
            visible_rows.append(item)
    return visible_rows, dedicated_rows


def extract_tradersarena_stock_trade_value(summary):
    """Return share and rights trading value, excluding every fund category."""
    money_scale = 10_000_000_000
    stock_row = summary.get("st", []) if isinstance(summary, dict) else []
    if not isinstance(stock_row, list) or len(stock_row) <= 1:
        return None
    value = watch_market_number(stock_row[1])
    return value / money_scale if value is not None else None


def get_watch_market(force=False):
    """Return the Markets-tab overview and six live Tehran-market charts."""
    now = int(time.time())
    with watch_market_cache_lock:
        cached_data = watch_market_cache["data"]
        cached_at = watch_market_cache["fetched_at"]
        if not force and cached_data and now - cached_at < 45:
            return dict(cached_data)

    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            summary_future = executor.submit(
                fetch_tradersarena_json,
                "/data/market0",
            )
            totals_future = executor.submit(
                fetch_tradersarena_json,
                "/data/market/chart/totals0",
            )
            overview_future = executor.submit(
                get_watch_market_overview,
                force,
            )
            industry_flows_future = executor.submit(
                fetch_tradersarena_industry_money_flows
            )
            overview = overview_future.result()
            summary = summary_future.result()
            totals = totals_future.result()
            try:
                industry_flows = industry_flows_future.result()
            except (requests.RequestException, ValueError, TypeError):
                industry_flows = list(
                    ((cached_data or {}).get("overview") or {}).get(
                        "industry_flows",
                        [],
                    )
                )
                overview.setdefault("errors", []).append("industry-money-flow")

        industry_flows, dedicated_industry_flows = (
            split_dedicated_industry_money_flows(industry_flows)
        )
        fixed_income_flow = watch_market_number(
            dedicated_industry_flows.get("fixed_income", {}).get("value")
        )
        if fixed_income_flow is None:
            fixed_income_flow = next(
                (
                    watch_market_number(item.get("value"))
                    for item in (
                        ((cached_data or {}).get("overview") or {}).get(
                            "flows",
                            [],
                        )
                    )
                    if item.get("key") == "fixed_income"
                ),
                None,
            )

        timestamps = [int(value) for value in totals.get("time", [])]

        def numeric_series(key, scale=1):
            values = totals.get(key, [])
            size = min(len(timestamps), len(values))
            return [
                float(value) / scale if value is not None else None
                for value in values[:size]
            ]

        positive_values = numeric_series("plus")
        negative_values = numeric_series("minus")
        excitement = []
        for positive, negative in zip(positive_values, negative_values):
            if positive is None or negative is None:
                excitement.append(None)
                continue
            total = positive + negative
            excitement.append(
                round((positive - negative) / total * 100, 2)
                if total
                else 0
            )

        # TradersArena monetary values are in rials. 10^10 rials equals
        # one billion tomans, which is the unit shown in the charts.
        money_scale = 10_000_000_000
        total_market_trade_value = extract_tradersarena_stock_trade_value(
            summary
        )
        price_range = [
            float(value)
            for value in summary.get("s", [])
            if value is not None
        ]
        range_labels = [
            "کمتر از ‎−۵٪",
            "‎−۵ تا ‎−۴٪",
            "‎−۴ تا ‎−۳٪",
            "‎−۳ تا ‎−۲٪",
            "‎−۲ تا ‎−۱٪",
            "‎−۱ تا ۰٪",
            "۰ تا ‎+۱٪",
            "‎+۱ تا ‎+۲٪",
            "‎+۲ تا ‎+۳٪",
            "‎+۳ تا ‎+۴٪",
            "‎+۴ تا ‎+۵٪",
            "بیشتر از ‎+۵٪",
        ]
        order_snapshot = [
            float(value) / money_scale
            for value in summary.get("o", [])
            if value is not None
        ]
        result = {
            "source": "tradersarena.ir",
            "source_url": "https://tradersarena.ir/",
            "fetched_at": now,
            "market_date": summary.get("j"),
            "times": timestamps,
            "charts": {
                "order_flow": {
                    "buy": numeric_series("bo", money_scale),
                    "sell": numeric_series("so", money_scale),
                    "unit": "میلیارد تومان",
                },
                "price_range": {
                    "labels": range_labels[:len(price_range)],
                    "values": price_range,
                    "unit": "نماد",
                },
                "money_flow": {
                    "values": numeric_series("stockTransfer", money_scale),
                    "unit": "میلیارد تومان",
                },
                "fixed_income_money_flow": {
                    "values": numeric_series(
                        "fixedIncomesTransfer",
                        money_scale,
                    ),
                    "unit": "میلیارد تومان",
                },
                "breadth": {
                    "positive": positive_values,
                    "negative": negative_values,
                    "unit": "نماد",
                },
                "order_snapshot": {
                    "labels": [
                        "فروش ۵ ردیف اول",
                        "خرید ۵ ردیف اول",
                        "صف فروش",
                        "صف خرید",
                    ][:len(order_snapshot)],
                    "values": order_snapshot,
                    "unit": "میلیارد تومان",
                },
                "excitement": {
                    "values": excitement,
                    "unit": "درصد",
                    "formula": (
                        "(تعداد نمادهای مثبت − تعداد نمادهای منفی) "
                        "÷ مجموع نمادها × ۱۰۰"
                    ),
                },
            },
            "errors": [],
        }
        overview = dict(overview)
        overview_prices = [
            item
            for item in overview.get("prices", [])
            if item.get("key") != "market_trade_value"
        ]
        if total_market_trade_value is not None:
            overview_prices.append({
                "key": "market_trade_value",
                "name": "ارزش معاملات کل روز بورس",
                "price": total_market_trade_value,
                "unit": "میلیارد تومان",
                "change": None,
                "change_percent": None,
                "tone": "market",
                "source": "tradersarena.ir",
                "source_url": "https://tradersarena.ir/",
            })
        overview["prices"] = overview_prices
        overview_flows = [
            item
            for item in overview.get("flows", [])
            if item.get("key") not in {"stock_market", "fixed_income"}
        ]
        overview_flows.append(
            watch_market_flow_item(
                "stock_market",
                "خالص پول بازار سهام",
                latest_watch_market_value(
                    result["charts"]["money_flow"]["values"]
                ),
                market_date=result.get("market_date"),
            )
        )
        overview_flows.append(
            watch_market_flow_item(
                "fixed_income",
                "خالص پول صندوق‌های درآمد ثابت",
                fixed_income_flow,
                market_date=result.get("market_date"),
            )
        )
        overview["flows"] = overview_flows
        overview["industry_flows"] = industry_flows
        result["overview"] = overview
        result["total_market_trade_value"] = total_market_trade_value
        try:
            save_market_daily_snapshot(result)
        except Exception as error:
            print("Market daily snapshot save error:", error)
        with watch_market_cache_lock:
            watch_market_cache.update(data=result, fetched_at=now)
        return result
    except (requests.RequestException, ValueError, TypeError) as error:
        print("Watch market refresh error:", error)
        with watch_market_cache_lock:
            cached_data = watch_market_cache["data"]
        if cached_data:
            result = dict(cached_data)
            result["errors"] = ["watch-market-refresh"]
            return result
        try:
            overview = get_watch_market_overview(force=force)
        except Exception:
            overview = {
                "prices": [],
                "flows": [],
                "fetched_at": None,
                "errors": ["market-overview-unavailable"],
            }
        return {
            "source": "tradersarena.ir",
            "source_url": "https://tradersarena.ir/",
            "fetched_at": None,
            "market_date": None,
            "times": [],
            "charts": {},
            "overview": overview,
            "errors": ["watch-market-unavailable"],
        }


def parse_all_stock_market_watch(response_text):
    """Parse ordinary equity instruments from MarketWatchPlus."""
    instruments = []
    seen_codes = set()
    for market_row in str(response_text or "").strip().split(";"):
        fields = market_row.split(",")
        if len(fields) < 26:
            continue
        ins_code = str(fields[0] or "").strip()
        instrument_id = str(fields[1] or "").strip().upper()
        symbol = clean_stock_text(fields[2])
        company = clean_stock_text(fields[3])
        category = clean_stock_text(fields[25]).upper()
        if (
            not re.fullmatch(r"\d{10,}", ins_code)
            or ins_code in seen_codes
            or not symbol
            or not is_all_stock_equity_instrument(
                symbol,
                instrument_id,
                company,
                category,
                "standard",
            )
        ):
            continue

        closing_price = stock_number(fields[6])
        last_price = stock_number(fields[7])
        yesterday_price = stock_number(fields[13])
        price = closing_price if closing_price and closing_price > 0 else last_price
        session_type = (
            "extended"
            if category in ALL_STOCK_EXTENDED_CATEGORIES
            else "standard"
        )
        seen_codes.add(ins_code)
        instruments.append({
            "position": len(instruments),
            "symbol": symbol,
            "company": company,
            "ins_code": ins_code,
            "instrument_id": instrument_id,
            "category": category,
            "session_type": session_type,
            "price": price if price and price > 0 else None,
            "closing_price": (
                stock_integer(closing_price)
                if closing_price and closing_price > 0
                else None
            ),
            "last_price": (
                stock_integer(last_price)
                if last_price and last_price > 0
                else None
            ),
            "yesterday_price": (
                stock_integer(yesterday_price)
                if yesterday_price and yesterday_price > 0
                else None
            ),
            "trade_volume": stock_integer(fields[9]),
            "trade_value": stock_integer(fields[10]),
            "share_count": stock_integer(fields[21]),
        })
    return instruments


def fetch_all_stock_market_watch():
    """Fetch the complete share/fund universe with its current market values."""
    response = requests.get(
        "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx",
        headers=TSETMC_HEADERS,
        timeout=20
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return parse_all_stock_market_watch(response.text)


def fetch_stock_market_map():
    """Fetch current price, volume, and value in one Market Watch request."""
    instruments = fetch_all_stock_market_watch()

    return {
        normalize_symbol(item["symbol"]): {
            key: item.get(key)
            for key in (
                "ins_code",
                "price",
                "closing_price",
                "last_price",
                "yesterday_price",
                "trade_volume",
                "trade_value",
            )
        }
        for item in instruments
    }


def fetch_closing_data(ins_code):
    data = fetch_tsetmc_json(
        f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    )
    info = data.get("closingPriceInfo") or {}
    closing_price = stock_number(info.get("pClosing"))
    last_price = stock_number(info.get("pDrCotVal"))
    yesterday_price = stock_number(info.get("priceYesterday"))
    price = (
        closing_price
        if closing_price and closing_price > 0
        else last_price
    )
    if not price or price <= 0:
        price = yesterday_price if yesterday_price and yesterday_price > 0 else None
    return {
        "market_date": normalize_stock_market_date(info.get("dEven")),
        "price": price,
        "closing_price": (
            stock_integer(closing_price)
            if closing_price and closing_price > 0
            else None
        ),
        "daily_high_price": stock_integer(info.get("priceMax")),
        "daily_low_price": stock_integer(info.get("priceMin")),
        "last_price": (
            stock_integer(last_price)
            if last_price and last_price > 0
            else None
        ),
        "yesterday_price": (
            stock_integer(yesterday_price)
            if yesterday_price and yesterday_price > 0
            else None
        ),
        "trade_volume": stock_integer(info.get("qTotTran5J")),
        "trade_value": stock_integer(info.get("qTotCap")),
    }


def calculate_stock_change_percent(price, yesterday_price):
    price_value = stock_number(price)
    yesterday_value = stock_number(yesterday_price)
    if (
        price_value is None
        or yesterday_value is None
        or yesterday_value <= 0
    ):
        return None
    return round(((price_value - yesterday_value) / yesterday_value) * 100, 2)


def apply_stock_floating_share_override(row):
    """Apply the configured manual free-float percentage to a stock row."""
    if not isinstance(row, dict):
        return row
    symbol = str(row.get("symbol") or "").strip()
    if symbol in STOCK_FLOATING_SHARE_OVERRIDES:
        row["floating_share_percent"] = STOCK_FLOATING_SHARE_OVERRIDES[symbol]
    return row


def calculate_stock_indicators(row):
    """Calculate turnover, real-money flow, per-capita values, and buy power."""
    last_price = stock_number(row.get("last_price"))
    closing_price = stock_number(row.get("closing_price"))
    trade_value = stock_number(row.get("trade_value"))
    trade_volume = stock_number(row.get("trade_volume"))
    share_count = stock_number(row.get("share_count"))
    floating_percent = stock_number(row.get("floating_share_percent"))
    real_buy_volume = stock_number(row.get("real_buy_volume"))
    legal_buy_volume = stock_number(row.get("legal_buy_volume"))
    real_sell_volume = stock_number(row.get("real_sell_volume"))
    legal_sell_volume = stock_number(row.get("legal_sell_volume"))
    real_buy_count = stock_number(row.get("real_buy_count"))
    real_sell_count = stock_number(row.get("real_sell_count"))

    price_power = None
    if (
        last_price is not None
        and last_price > 0
        and closing_price is not None
        and closing_price > 0
    ):
        price_power = (
            1 if last_price > closing_price
            else (-1 if last_price < closing_price else 0)
        )

    trade_to_float_percent = None
    floating_share_count = (
        share_count * floating_percent / 100
        if share_count is not None
        and share_count > 0
        and floating_percent is not None
        and floating_percent > 0
        else None
    )
    if (
        trade_volume is not None
        and trade_volume >= 0
        and floating_share_count
        and floating_share_count > 0
    ):
        trade_to_float_percent = round(
            trade_volume / floating_share_count * 100,
            4,
        )

    def real_side_share(real_volume, legal_volume):
        if real_volume is None or real_volume < 0:
            return None
        side_total = (
            trade_volume
            if trade_volume is not None and trade_volume > 0
            else (
                real_volume + legal_volume
                if legal_volume is not None and legal_volume >= 0
                else None
            )
        )
        if side_total is None or side_total <= 0:
            return None
        return real_volume / side_total

    real_buy_share = real_side_share(real_buy_volume, legal_buy_volume)
    real_sell_share = real_side_share(real_sell_volume, legal_sell_volume)
    real_buy_value = (
        trade_value * real_buy_share
        if trade_value is not None and real_buy_share is not None
        else None
    )
    real_sell_value = (
        trade_value * real_sell_share
        if trade_value is not None and real_sell_share is not None
        else None
    )
    real_money_flow = (
        int(round(real_buy_value - real_sell_value))
        if real_buy_value is not None and real_sell_value is not None
        else None
    )
    money_flow_quality = (
        round(real_money_flow / trade_value * 100, 4)
        if real_money_flow is not None
        and trade_value is not None
        and trade_value > 0
        else None
    )
    real_buy_per_capita = (
        int(round(real_buy_value / real_buy_count))
        if real_buy_value is not None
        and real_buy_count is not None
        and real_buy_count > 0
        else None
    )
    real_sell_per_capita = (
        int(round(real_sell_value / real_sell_count))
        if real_sell_value is not None
        and real_sell_count is not None
        and real_sell_count > 0
        else None
    )
    real_buy_power = (
        round(real_buy_per_capita / real_sell_per_capita, 4)
        if real_buy_per_capita is not None
        and real_sell_per_capita is not None
        and real_sell_per_capita > 0
        else None
    )

    price_power_status = stock_price_power_status({
        **row,
        "price_power": price_power,
    })

    return {
        "price_power": price_power,
        "price_power_status": price_power_status,
        "trade_to_float_percent": trade_to_float_percent,
        "real_money_flow": real_money_flow,
        "money_flow_quality": money_flow_quality,
        "real_buy_per_capita": real_buy_per_capita,
        "real_sell_per_capita": real_sell_per_capita,
        "real_buy_power": real_buy_power,
    }


def fetch_stock_client_type(ins_code):
    data = fetch_tsetmc_json(
        f"https://cdn.tsetmc.com/api/ClientType/GetClientType/{ins_code}/1/0"
    )
    client_type = data.get("clientType") or {}
    return {
        "real_buy_volume": stock_integer(client_type.get("buy_I_Volume")),
        "real_buy_count": stock_integer(client_type.get("buy_CountI")),
        "legal_buy_volume": stock_integer(client_type.get("buy_N_Volume")),
        "legal_buy_count": stock_integer(client_type.get("buy_CountN")),
        "real_sell_volume": stock_integer(client_type.get("sell_I_Volume")),
        "real_sell_count": stock_integer(client_type.get("sell_CountI")),
        "legal_sell_volume": stock_integer(client_type.get("sell_N_Volume")),
        "legal_sell_count": stock_integer(client_type.get("sell_CountN")),
    }


def fetch_stock_order_book_totals(ins_code):
    """Sum value, volume, and order count across the first five price levels."""
    data = fetch_tsetmc_json(
        f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}"
    )
    best_limits = data.get("bestLimits") or []
    if not isinstance(best_limits, list):
        best_limits = []

    buy_value = 0
    buy_volume = 0
    buy_count = 0
    sell_value = 0
    sell_volume = 0
    sell_count = 0

    for row in best_limits[:5]:
        if not isinstance(row, dict):
            continue

        row_buy_price = stock_number(row.get("pMeDem")) or 0
        row_sell_price = stock_number(row.get("pMeOf")) or 0
        row_buy_volume = stock_integer(row.get("qTitMeDem")) or 0
        row_sell_volume = stock_integer(row.get("qTitMeOf")) or 0
        row_buy_count = stock_integer(row.get("zOrdMeDem")) or 0
        row_sell_count = stock_integer(row.get("zOrdMeOf")) or 0

        buy_value += row_buy_price * row_buy_volume
        buy_volume += row_buy_volume
        buy_count += row_buy_count
        sell_value += row_sell_price * row_sell_volume
        sell_volume += row_sell_volume
        sell_count += row_sell_count

    return {
        "order_book_value": int(round(buy_value + sell_value)),
        "order_book_volume": int(buy_volume + sell_volume),
        "order_book_count": int(buy_count + sell_count),
        "order_book_buy_value": int(round(buy_value)),
        "order_book_buy_volume": int(buy_volume),
        "order_book_buy_count": int(buy_count),
        "order_book_sell_value": int(round(sell_value)),
        "order_book_sell_volume": int(sell_volume),
        "order_book_sell_count": int(sell_count),
    }


def fetch_tsetmc_json(url, attempts=3):
    """Read a TSETMC JSON endpoint with short retries for transient CDN errors."""
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                headers=TSETMC_HEADERS,
                timeout=15
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("پاسخ JSON معتبر نیست.")
            return payload
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.4 * (attempt + 1))

    raise last_error


def find_stock_instrument(symbol):
    data = fetch_tsetmc_json(
        f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{symbol}",
    )
    candidates = data.get("instrumentSearch") or []
    target = normalize_symbol(symbol)

    exact_candidates = [
        candidate
        for candidate in candidates
        if normalize_symbol(candidate.get("lVal18AFC")) == target
        and str(candidate.get("flow")) != "3"
    ]
    exact_candidates.sort(
        key=lambda item: (
            str(item.get("flow")) not in {"1", "2"},
            str(item.get("lastDate")) not in {"0", "1"}
        )
    )

    fallback = None
    for candidate in exact_candidates[:6]:
        ins_code = str(candidate.get("insCode") or "").strip()
        if not ins_code:
            continue
        info = fetch_tsetmc_json(
            f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{ins_code}"
        )
        info = info.get("instrumentInfo") or {}
        if normalize_symbol(info.get("lVal18AFC")) != target:
            continue
        if fallback is None:
            fallback = info
        if str(info.get("lastDate")) == "0":
            return info

    return fallback


def fetch_stock_row(symbol, market_map, fallback_row=None):
    """Fetch one row without discarding fresh prices when an optional feed fails."""
    fallback_row = fallback_row if isinstance(fallback_row, dict) else {}
    target_symbol = normalize_symbol(symbol)
    fallback_ins_code = str(fallback_row.get("ins_code") or "").strip()
    warnings = []
    info = {}
    instrument_error = None

    # Existing catalogue symbols already have a verified TSETMC identifier.
    # Using it directly is both faster and less vulnerable to search throttling.
    if fallback_ins_code:
        try:
            payload = fetch_tsetmc_json(
                "https://cdn.tsetmc.com/api/Instrument/"
                f"GetInstrumentInfo/{fallback_ins_code}"
            )
            candidate = payload.get("instrumentInfo") or {}
            if normalize_symbol(candidate.get("lVal18AFC")) == target_symbol:
                info = candidate
        except (requests.RequestException, ValueError, TypeError) as error:
            instrument_error = error

    if not info:
        try:
            info = find_stock_instrument(symbol) or {}
        except (requests.RequestException, ValueError, TypeError) as error:
            warnings.append(f"instrument-search: {error}")

    if not info:
        warnings.append(
            "instrument-info: "
            + (
                str(instrument_error)
                if instrument_error is not None
                else "اطلاعات ایستای نماد در دسترس نبود."
            )
        )

    ins_code = str(info.get("insCode") or fallback_ins_code).strip()
    if not ins_code:
        raise ValueError(f"نماد {symbol} در TSETMC پیدا نشد.")

    sector = info.get("sector") or {}
    static_threshold = info.get("staticThreshold") or {}
    issued_units = stock_number(info.get("etfIssuedUnit"))
    listed_shares = stock_number(info.get("zTitad"))
    fallback_shares = stock_number(fallback_row.get("share_count"))
    units = next(
        (
            value
            for value in (issued_units, listed_shares, fallback_shares)
            if value is not None and value > 0
        ),
        None,
    )
    market_data = dict(market_map.get(normalize_symbol(symbol)) or {})

    # ClosingPrice is the authoritative final quote. Prefer every valid field
    # from it, while retaining the bulk market-watch value if this request fails.
    closing_market_date = None
    try:
        closing_data = fetch_closing_data(ins_code)
        closing_market_date = closing_data.get("market_date")
        for field in (
            "price",
            "closing_price",
            "last_price",
            "yesterday_price",
            "daily_high_price",
            "daily_low_price",
            "trade_volume",
            "trade_value",
        ):
            value = closing_data.get(field)
            if value is not None:
                market_data[field] = value
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"closing-price: {error}")

    price = market_data.get("price")
    closing_price = market_data.get("closing_price")
    last_price = market_data.get("last_price")
    yesterday_price = market_data.get("yesterday_price")

    client_type = {
        "real_buy_volume": None,
        "real_buy_count": None,
        "legal_buy_volume": None,
        "legal_buy_count": None,
        "real_sell_volume": None,
        "real_sell_count": None,
        "legal_sell_volume": None,
        "legal_sell_count": None,
    }
    try:
        client_type.update(fetch_stock_client_type(ins_code))
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"client-type: {error}")

    order_book_totals = {
        "order_book_value": None,
        "order_book_volume": None,
        "order_book_count": None,
        "order_book_buy_value": None,
        "order_book_buy_volume": None,
        "order_book_buy_count": None,
        "order_book_sell_value": None,
        "order_book_sell_volume": None,
        "order_book_sell_count": None,
    }
    try:
        order_book_totals.update(fetch_stock_order_book_totals(ins_code))
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"best-limits: {error}")

    market_value = None
    if units and units > 0 and price and price > 0:
        market_value = int(round(units * price))

    row = {
        "symbol": symbol,
        "ins_code": ins_code,
        "market_date": (
            closing_market_date
            or normalize_stock_market_date(info.get("dEven"))
            or fallback_row.get("market_date")
        ),
        "company": (
            clean_stock_text(info.get("lVal30"))
            or fallback_row.get("company")
        ),
        "industry": (
            clean_stock_text(sector.get("lSecVal"))
            or fallback_row.get("industry")
        ),
        "market_value": market_value or fallback_row.get("market_value"),
        "last_price": last_price,
        "yesterday_price": yesterday_price,
        "last_price_change_percent": calculate_stock_change_percent(
            last_price,
            yesterday_price,
        ),
        "closing_price": closing_price,
        "closing_price_change_percent": calculate_stock_change_percent(
            closing_price,
            yesterday_price,
        ),
        "daily_high_price": stock_integer(
            market_data.get("daily_high_price")
        ),
        "daily_low_price": stock_integer(
            market_data.get("daily_low_price")
        ),
        "daily_upper_price": stock_integer(
            static_threshold.get("psGelStaMax")
            if static_threshold.get("psGelStaMax") is not None
            else fallback_row.get("daily_upper_price")
        ),
        "daily_lower_price": stock_integer(
            static_threshold.get("psGelStaMin")
            if static_threshold.get("psGelStaMin") is not None
            else fallback_row.get("daily_lower_price")
        ),
        "trade_value": market_data.get("trade_value"),
        "trade_volume": market_data.get("trade_volume"),
        "share_count": stock_integer(units),
        "floating_share_percent": stock_number(
            info.get("kAjCapValCpsIdx")
            if info.get("kAjCapValCpsIdx") is not None
            else fallback_row.get("floating_share_percent")
        ),
        **client_type,
        "monthly_average_volume": stock_integer(
            info.get("qTotTran5JAvg")
            if info.get("qTotTran5JAvg") is not None
            else fallback_row.get("monthly_average_volume")
        ),
        **order_book_totals,
    }
    apply_stock_floating_share_override(row)
    row.update(calculate_stock_indicators(row))
    if warnings:
        row["_fetch_warning"] = f"{symbol}: " + "; ".join(warnings)
    return row


def fetch_all_stock_row(instrument):
    """Resolve one complete-market row without a symbol-search round trip."""
    symbol = clean_stock_text(instrument.get("symbol"))
    ins_code = str(instrument.get("ins_code") or "").strip()
    if not symbol or not ins_code:
        raise ValueError("شناسه نماد کامل نیست.")

    warnings = []
    try:
        info_payload = fetch_tsetmc_json(
            f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{ins_code}",
            attempts=3,
        )
        info = info_payload.get("instrumentInfo") or {}
    except (requests.RequestException, ValueError, TypeError) as error:
        info = {}
        warnings.append(f"{symbol}: instrument-info: {error}")

    sector = info.get("sector") or {}
    static_threshold = info.get("staticThreshold") or {}
    issued_units = stock_number(info.get("etfIssuedUnit"))
    listed_shares = stock_number(info.get("zTitad"))
    market_watch_shares = stock_number(instrument.get("share_count"))
    units = next(
        (
            value
            for value in (issued_units, listed_shares, market_watch_shares)
            if value is not None and value > 0
        ),
        None,
    )

    client_type = {
        "real_buy_volume": None,
        "real_buy_count": None,
        "legal_buy_volume": None,
        "legal_buy_count": None,
        "real_sell_volume": None,
        "real_sell_count": None,
        "legal_sell_volume": None,
        "legal_sell_count": None,
    }
    try:
        client_type.update(fetch_stock_client_type(ins_code))
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"{symbol}: client-type: {error}")

    order_book_totals = {
        "order_book_value": None,
        "order_book_volume": None,
        "order_book_count": None,
        "order_book_buy_value": None,
        "order_book_buy_volume": None,
        "order_book_buy_count": None,
        "order_book_sell_value": None,
        "order_book_sell_volume": None,
        "order_book_sell_count": None,
    }
    try:
        order_book_totals.update(fetch_stock_order_book_totals(ins_code))
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"{symbol}: best-limits: {error}")

    closing_data = {}
    try:
        closing_data = fetch_closing_data(ins_code)
    except (requests.RequestException, ValueError, TypeError) as error:
        warnings.append(f"{symbol}: closing-price: {error}")

    def current_value(field):
        value = closing_data.get(field)
        return value if value is not None else instrument.get(field)

    price = stock_number(current_value("price"))
    closing_price = stock_integer(current_value("closing_price"))
    last_price = stock_integer(current_value("last_price"))
    yesterday_price = stock_integer(current_value("yesterday_price"))
    market_value = (
        int(round(units * price))
        if units is not None and units > 0 and price is not None and price > 0
        else None
    )
    row = {
        "position": stock_integer(instrument.get("position")),
        "symbol": symbol,
        "category": clean_stock_text(instrument.get("category")).upper(),
        "session_type": instrument.get("session_type") or "standard",
        "ins_code": ins_code,
        "market_date": (
            closing_data.get("market_date")
            or normalize_stock_market_date(info.get("dEven"))
            or normalize_stock_market_date(instrument.get("market_date"))
        ),
        "company": (
            clean_stock_text(info.get("lVal30"))
            or clean_stock_text(instrument.get("company"))
        ),
        "industry": clean_stock_text(sector.get("lSecVal")),
        "market_value": market_value,
        "last_price": last_price,
        "yesterday_price": yesterday_price,
        "last_price_change_percent": calculate_stock_change_percent(
            last_price,
            yesterday_price,
        ),
        "closing_price": closing_price,
        "closing_price_change_percent": calculate_stock_change_percent(
            closing_price,
            yesterday_price,
        ),
        "daily_high_price": stock_integer(
            current_value("daily_high_price")
        ),
        "daily_low_price": stock_integer(
            current_value("daily_low_price")
        ),
        "daily_upper_price": stock_integer(
            static_threshold.get("psGelStaMax")
        ),
        "daily_lower_price": stock_integer(
            static_threshold.get("psGelStaMin")
        ),
        "trade_value": stock_integer(current_value("trade_value")),
        "trade_volume": stock_integer(current_value("trade_volume")),
        "share_count": stock_integer(units),
        "floating_share_percent": stock_number(info.get("kAjCapValCpsIdx")),
        **client_type,
        "monthly_average_volume": stock_integer(info.get("qTotTran5JAvg")),
        **order_book_totals,
    }
    apply_stock_floating_share_override(row)
    row.update(calculate_stock_indicators(row))
    return row, warnings


def fetch_all_stock_phase(phase):
    """Fetch one close phase for the complete-market tab."""
    if phase not in {"standard", "extended"}:
        raise ValueError("بازه معاملاتی تمام سهام معتبر نیست.")
    instruments = [
        instrument
        for instrument in fetch_all_stock_market_watch()
        if instrument.get("session_type") == phase
    ]
    if not instruments:
        raise RuntimeError("فهرست کامل نمادهای بازار از TSETMC دریافت نشد.")

    rows_by_symbol = {}
    warnings_by_symbol = {}
    retry_instruments = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(fetch_all_stock_row, instrument): instrument
            for instrument in instruments
        }
        for future in as_completed(futures):
            instrument = futures[future]
            try:
                row, row_warnings = future.result()
                key = normalize_symbol(row.get("symbol"))
                rows_by_symbol[key] = row
                warnings_by_symbol[key] = row_warnings
                if row_warnings:
                    retry_instruments.append(instrument)
            except (requests.RequestException, ValueError, TypeError) as error:
                key = normalize_symbol(instrument.get("symbol"))
                warnings_by_symbol[key] = [
                    f"{instrument.get('symbol')}: {error}"
                ]
                retry_instruments.append(instrument)

    # Retry only partial rows with lower concurrency. This prevents a single
    # throttled instrument-info request from leaving a row incomplete all day.
    if retry_instruments:
        with ThreadPoolExecutor(max_workers=3) as executor:
            retry_futures = {
                executor.submit(fetch_all_stock_row, instrument): instrument
                for instrument in retry_instruments
            }
            for future in as_completed(retry_futures):
                instrument = retry_futures[future]
                key = normalize_symbol(instrument.get("symbol"))
                try:
                    row, row_warnings = future.result()
                    rows_by_symbol[key] = row
                    warnings_by_symbol[key] = row_warnings
                except (requests.RequestException, ValueError, TypeError) as error:
                    warnings_by_symbol[key] = [
                        f"{instrument.get('symbol')}: {error}"
                    ]

    rows = list(rows_by_symbol.values())
    errors = [
        warning
        for row_warnings in warnings_by_symbol.values()
        for warning in row_warnings
    ]
    rows.sort(key=lambda row: stock_integer(row.get("position")) or 0)
    return rows, errors


def merge_all_stock_rows(fresh_rows, fallback_rows):
    """Preserve the previous finalized field when a close request is partial."""
    fallback_by_symbol = {
        normalize_symbol(row.get("symbol")): row
        for row in fallback_rows
        if isinstance(row, dict) and row.get("symbol")
    }
    merged = []
    for fresh_row in fresh_rows:
        row = dict(fresh_row)
        fallback = fallback_by_symbol.get(normalize_symbol(row.get("symbol")), {})
        for field in STOCK_DETAIL_FIELDS:
            if row.get(field) in (None, "") and fallback.get(field) not in (None, ""):
                row[field] = fallback.get(field)
        apply_stock_floating_share_override(row)
        row.update(calculate_stock_indicators(row))
        merged.append(row)
    return merged


def merge_stock_rows(symbols, fresh_rows, fallback_rows):
    fresh_by_symbol = {
        normalize_symbol(row.get("symbol")): row
        for row in fresh_rows
        if isinstance(row, dict)
    }
    fallback_by_symbol = {
        normalize_symbol(row.get("symbol")): row
        for row in fallback_rows
        if isinstance(row, dict)
    }

    merged = []
    for symbol in symbols:
        key = normalize_symbol(symbol)
        fresh = fresh_by_symbol.get(key, {})
        fallback = fallback_by_symbol.get(key, {})
        row = {"symbol": symbol}
        for field in STOCK_DETAIL_FIELDS:
            value = fresh.get(field)
            if value in (None, ""):
                value = fallback.get(field)
            row[field] = value if value not in (None, "") else None
        apply_stock_floating_share_override(row)
        row.update(calculate_stock_indicators(row))
        merged.append(row)
    return merged


def fetch_live_stock_catalog(symbols, fallback_rows=None):
    fallback_by_symbol = {
        normalize_symbol(row.get("symbol")): row
        for row in (fallback_rows or [])
        if isinstance(row, dict) and row.get("symbol")
    }
    try:
        market_map = fetch_stock_market_map()
    except requests.RequestException as error:
        print("Stock Market Watch price error:", error)
        market_map = {}

    rows = []
    failed_symbols = []
    errors = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                fetch_stock_row,
                symbol,
                market_map,
                fallback_by_symbol.get(normalize_symbol(symbol)),
            ): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                row = future.result()
                warning = row.pop("_fetch_warning", None)
                if warning:
                    errors.append(warning)
                rows.append(row)
            except (requests.RequestException, ValueError, TypeError) as error:
                failed_symbols.append(symbol)

    # A quieter second pass avoids losing rows during brief CDN throttling.
    if failed_symbols:
        with ThreadPoolExecutor(max_workers=3) as executor:
            retry_futures = {
                executor.submit(
                    fetch_stock_row,
                    symbol,
                    market_map,
                    fallback_by_symbol.get(normalize_symbol(symbol)),
                ): symbol
                for symbol in failed_symbols
            }
            for future in as_completed(retry_futures):
                symbol = retry_futures[future]
                try:
                    row = future.result()
                    warning = row.pop("_fetch_warning", None)
                    if warning:
                        errors.append(warning)
                    rows.append(row)
                except (requests.RequestException, ValueError, TypeError) as error:
                    errors.append(f"{symbol}: {error}")

    return rows, errors


def refresh_stock_watchlist():
    """Refresh watchlist rows while preserving the last usable value per field."""
    current_rows = read_stock_watchlist()
    symbols = [row["symbol"] for row in current_rows]
    if not symbols:
        return [], []

    fresh_rows, errors = fetch_live_stock_catalog(symbols, current_rows)
    merged_rows = merge_stock_rows(symbols, fresh_rows, current_rows)
    for row in merged_rows:
        save_stock_watchlist_row(row)
    save_daily_stock_snapshots(merged_rows, datetime.now(IRAN_TIMEZONE))
    return merged_rows, errors


def add_stock_watchlist_symbol(symbol):
    """Resolve a symbol, then store it in the persistent SQLite watchlist."""
    requested_symbol = normalize_symbol(symbol)
    if not requested_symbol:
        raise ValueError("نام نماد را وارد کنید.")

    current_rows = read_stock_watchlist()
    if any(
        normalize_symbol(row.get("symbol")) == requested_symbol
        for row in current_rows
    ):
        raise ValueError("این نماد از قبل در دیده‌بان وجود دارد.")

    database_rows, _ = read_stock_database()
    stored_row = next(
        (
            row for row in database_rows
            if normalize_symbol(row.get("symbol")) == requested_symbol
        ),
        None,
    )

    # Known catalogue symbols can be shown immediately from SQLite. Unknown
    # symbols are resolved online once, then all later page loads use SQLite.
    if stored_row and stored_row.get("ins_code"):
        resolved_row = {**stored_row, "symbol": stored_row["symbol"]}
    else:
        try:
            market_map = fetch_stock_market_map()
        except requests.RequestException:
            market_map = {}
        resolved_row = fetch_stock_row(requested_symbol, market_map)

    resolved_row.update(calculate_stock_indicators(resolved_row))
    return save_stock_watchlist_row(resolved_row)


def refresh_stock_database():
    error_message = None
    try:
        symbols = load_stock_symbols()
        database_rows, _ = read_stock_database()
        fresh_rows, errors = fetch_live_stock_catalog(symbols, database_rows)
        if not fresh_rows:
            raise RuntimeError("دریافت آنلاین اطلاعات سهام از TSETMC ناموفق بود.")

        merged_rows = merge_stock_rows(symbols, fresh_rows, database_rows)
        captured_at = datetime.now(IRAN_TIMEZONE)
        updated_at = captured_at.isoformat()
        replace_stock_database(merged_rows, updated_at, len(fresh_rows))
        # Archive the exact rows that were committed and will be shown in the
        # stock table.  Using the pre-commit merge objects here could leave the
        # chart history one response behind the visible table when concurrent
        # TSETMC feeds finish at slightly different times.
        committed_rows, _ = read_stock_database()
        save_daily_stock_snapshots(committed_rows, captured_at)

        if errors:
            error_message = (
                f"اطلاعات {len(errors)} نماد از آخرین داده دیتابیس حفظ شد."
            )
    except Exception as error:
        error_message = str(error)
        print("Stock database refresh error:", error)
    finally:
        with stock_refresh_lock:
            stock_refresh_state["running"] = False
            stock_refresh_state["error"] = error_message


def start_stock_database_refresh(force=False):
    """Start a single background refresh without delaying the HTTP response."""
    with stock_refresh_lock:
        now_timestamp = time.time()
        if stock_refresh_state["running"]:
            return False
        if (
            not force
            and now_timestamp - stock_refresh_state["last_attempt_at"] < 30
        ):
            return False

        stock_refresh_state["running"] = True
        stock_refresh_state["started_at"] = datetime.now(
            IRAN_TIMEZONE
        ).isoformat()
        stock_refresh_state["last_attempt_at"] = now_timestamp
        stock_refresh_state["error"] = None

    threading.Thread(
        target=refresh_stock_database,
        name="stock-database-refresh",
        daemon=True
    ).start()
    return True


def get_stock_catalog(force_refresh=False, use_saved_data=False):
    """Return SQLite rows immediately and refresh stale online data in background."""
    rows, metadata = read_stock_database()
    if use_saved_data:
        rows, snapshot_metadata = apply_latest_stock_snapshots(rows)
        complete_count = sum(
            1
            for row in rows
            if row.get("company")
            and row.get("industry")
            and stock_number(row.get("market_value")) not in (None, 0)
        )
        payload = {
            "count": len(rows),
            "resolved_count": int(
                metadata.get("resolved_count", complete_count)
            ),
            "source_updated_at": metadata.get("last_successful_update"),
            "stale": False,
            "refreshing": False,
            "refresh_started_at": None,
            "stocks": rows,
            **snapshot_metadata,
        }
        if snapshot_metadata["missing_snapshot_count"]:
            payload["warning"] = (
                f"برای {snapshot_metadata['missing_snapshot_count']} نماد "
                "داده روزانه ذخیره نشده و آخرین مقدار دیتابیس نمایش داده شد."
            )
        return payload

    try:
        last_update_epoch = float(
            metadata.get("last_successful_update_epoch", "0") or 0
        )
    except (TypeError, ValueError):
        last_update_epoch = 0

    refresh_due = (
        not last_update_epoch
        or time.time() - last_update_epoch >= STOCK_CACHE_TTL_SECONDS
    )
    if force_refresh or refresh_due:
        start_stock_database_refresh(force=force_refresh)

    with stock_refresh_lock:
        refresh_status = dict(stock_refresh_state)

    complete_count = sum(
        1
        for row in rows
        if row.get("company")
        and row.get("industry")
        and stock_number(row.get("market_value")) not in (None, 0)
    )

    payload = {
        "count": len(rows),
        "resolved_count": int(metadata.get("resolved_count", complete_count)),
        "source_updated_at": metadata.get("last_successful_update"),
        "data_source": "database",
        "stale": refresh_due,
        "refreshing": refresh_status["running"],
        "refresh_started_at": refresh_status["started_at"],
        "stocks": rows
    }
    if refresh_status["error"]:
        payload["warning"] = refresh_status["error"]
    return payload


def refresh_all_stock_database(phases, manual=False):
    """Refresh complete-market phases, archiving only scheduled close runs."""
    error_messages = []
    completed_phases = []
    try:
        for phase in phases:
            current_rows, _ = read_all_stock_database()
            rows, errors = fetch_all_stock_phase(phase)
            rows = merge_all_stock_rows(rows, current_rows)
            if manual:
                publish_all_stock_current_phase(
                    rows,
                    phase,
                    datetime.now(IRAN_TIMEZONE),
                )
            else:
                save_all_stock_phase(
                    rows,
                    phase,
                    datetime.now(IRAN_TIMEZONE),
                )
            completed_phases.append(phase)
            if errors:
                error_messages.append(
                    f"بخشی از جزئیات {len(errors)} درخواست TSETMC در "
                    f"بازه {'۱۸:۰۰' if phase == 'extended' else '۱۲:۳۰'} "
                    "در دسترس نبود."
                )
    except Exception as error:
        error_messages.append(str(error))
        print("All-stock database refresh error:", error)
    finally:
        with all_stock_refresh_lock:
            all_stock_refresh_state["running"] = False
            all_stock_refresh_state["phases"] = completed_phases
            all_stock_refresh_state["manual"] = False
            all_stock_refresh_state["error"] = " ".join(error_messages) or None


def start_all_stock_database_refresh(current_time=None, manual=False):
    """Start a manual live refresh or only the due daily close phases."""
    current_time = current_time or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)
    _, metadata = read_all_stock_database()
    phases = ["standard"] if manual else all_stock_due_phases(current_time, metadata)
    if not phases:
        return False

    with all_stock_refresh_lock:
        if all_stock_refresh_state["running"]:
            return False
        all_stock_refresh_state.update({
            "running": True,
            "started_at": current_time.isoformat(),
            "phases": list(phases),
            "manual": bool(manual),
            "error": None,
        })

    threading.Thread(
        target=refresh_all_stock_database,
        args=(phases, manual),
        name=(
            "all-stock-manual-refresh"
            if manual
            else "all-stock-daily-refresh"
        ),
        daemon=True,
    ).start()
    return True


def get_all_stock_catalog(
    check_refresh=True,
    current_time=None,
    force_refresh=False,
):
    """Serve complete-market rows and optionally trigger a live refresh."""
    current_time = current_time or datetime.now(IRAN_TIMEZONE)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IRAN_TIMEZONE)
    else:
        current_time = current_time.astimezone(IRAN_TIMEZONE)

    rows, metadata = read_all_stock_database()
    if rows:
        start_stock_price_history_backfill(rows)
        start_stock_strategy_history_backfill(rows)
    due_phases = all_stock_due_phases(current_time, metadata)
    if force_refresh:
        start_all_stock_database_refresh(current_time, manual=True)
    elif check_refresh and due_phases:
        start_all_stock_database_refresh(current_time)

    with all_stock_refresh_lock:
        refresh_status = dict(all_stock_refresh_state)
    with stock_price_history_lock:
        price_history_status = dict(stock_price_history_state)
    with stock_strategy_history_lock:
        strategy_history_status = dict(stock_strategy_history_state)
    payload = {
        "count": len(rows),
        "stocks": rows,
        "data_source": "daily_database",
        "source_updated_at": metadata.get("last_successful_update"),
        "standard_completed_date": metadata.get("standard_completed_date"),
        "extended_completed_date": metadata.get("extended_completed_date"),
        "standard_count": int(metadata.get("standard_count", "0") or 0),
        "extended_count": int(metadata.get("extended_count", "0") or 0),
        "due_phases": due_phases,
        "refreshing": refresh_status["running"],
        "refresh_started_at": refresh_status["started_at"],
        "refresh_phases": refresh_status["phases"],
        "manual_refresh": refresh_status.get("manual", False),
        "price_history": price_history_status,
        "strategy_history": strategy_history_status,
        "server_time": current_time.isoformat(),
    }
    if refresh_status["error"]:
        payload["warning"] = refresh_status["error"]
    return payload


def normalize_symbol(value):
    """یکسان‌سازی نویسه‌های عربی و فارسی برای مقایسه نام نمادها."""
    if value is None:
        return ""

    normalized = str(value).strip().translate(
        str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
    )
    return re.sub(r"[\s\u200c\u200f\ufeff]+", "", normalized)


# ✅ مپ نماد اختیار → نماد پایه
mapping = {
    "طوتعاون":"وتعاون","طهمن":"خبهمن","طهرم":"اهرم","طنارنج":"نارنج","طموج":"موج",
    "طملي":"فملی","طملت":"وبملت","طمخا":"اخابر","طكاريس":"کاریس","طفلا":"فولاد",
    "طفصبا":"فصبا","طفزر":"فزر","طفرابورس":"فرابورس","ططعام":"طعام","طصاد":"وبصادر",
    "طشنا":"شپنا","طستر":"خگستر","طسپا":"خساپا","طسامان":"سامان","طرويين":"رویین",
    "طران":"خودران","طذوب":"ذوب","طخود":"خودرو","طخاور":"خاور","طجهش":"جهش",
    "طجار":"وتجارت","طتيام":"تیام","طتوان":"توان","طتاص":"تاصیکو","طتاب":"شتاب",
    "طپناه":"پناه","طپتروآبان":"پتروآبان","طپادا":"پادا","طبيد":"بیدار",
    "طبساما":"بساما","طامين شهر":"امین شهر","طاطلس":"اطلس","طاساس":"آساس",
    "ضوتعاون":"وتعاون","ضهمن":"خبهمن","ضهرم":"اهرم","ضنارنج":"نارنج","ضموج":"موج",
    "ضملي":"فملی","ضملت":"وبملت","ضمخا":"اخابر","ضكاريس":"کاریس","ضفلا":"فولاد",
    "ضفصبا":"فصبا","ضفزر":"فزر","ضفرابورس":"فرابورس","ضطعام":"طعام","ضصاد":"وبصادر",
    "ضشنا":"شپنا","ضستر":"خگستر","ضستا":"شستا","طستا":"شستا","ضسپا":"خساپا","ضسامان":"سامان",
    "ضرويين":"رویین","ضران":"خودران","ضذوب":"ذوب","ضخود":"خودرو","ضخاور":"خاور",
    "ضجهش":"جهش","ضجار":"وتجارت","ضتيام":"تیام","ضتوان":"توان","ضتاص":"تاصیکو",
    "ضتاب":"شتاب","ضپناه":"پناه","ضپتروآبان":"پتروآبان","ضپادا":"پادا",
    "ضبيد":"بیدار","ضبساما":"بساما","ضامين شهر":"امین شهر","ضاطلس":"اطلس",
    "ضاساس":"آساس",
    "ضجوا":"جوانه کوچک","طجوا":"جوانه کوچک",
    "ضراز":"هم تراز","طراز":"هم تراز"
}

mapping = {
    normalize_symbol(option_symbol): normalize_symbol(base_symbol)
    for option_symbol, base_symbol in mapping.items()
}


def is_option_description(description, option_type=None):
    text = normalize_symbol(description)
    if option_type == "call":
        return text.startswith("اختیارخ")
    if option_type == "put":
        return text.startswith("اختیارف")
    return text.startswith("اختیارخ") or text.startswith("اختیارف")


def extract_option_base_label(description):
    """Extract the underlying label from a TSETMC option description."""
    text = str(description or "").strip().translate(
        str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
    )
    match = re.search(
        r"^اختیار[خف]\s+(.+?)-[\d,.]+-(?:\d{2,4}/\d{2}/\d{2}|\d{6,8})",
        text,
    )
    return match.group(1).strip() if match else ""


def option_symbol_root(symbol):
    return normalize_symbol(re.sub(r"\d+$", "", str(symbol or "")))


def build_dynamic_option_mapping(rows):
    """Merge the legacy map with underlyings discovered from live descriptions."""
    discovered = dict(mapping)
    market_symbols = {}

    for row in rows:
        fields = row.split(",")
        if len(fields) < 4:
            continue
        symbol = normalize_symbol(fields[2])
        if symbol and not is_option_description(fields[3]):
            market_symbols[symbol] = symbol

    comparable_symbols = {
        re.sub(r"[^\w\u0600-\u06ff]", "", symbol): symbol
        for symbol in market_symbols
    }

    for row in rows:
        fields = row.split(",")
        if len(fields) < 4 or not is_option_description(fields[3]):
            continue

        root = option_symbol_root(fields[2])
        if not root or root in discovered:
            continue

        label = extract_option_base_label(fields[3])
        normalized_label = normalize_symbol(label)
        comparable_label = re.sub(
            r"[^\w\u0600-\u06ff]", "", normalized_label
        )

        base_symbol = market_symbols.get(normalized_label)
        if not base_symbol:
            base_symbol = comparable_symbols.get(comparable_label)

        if not base_symbol and len(comparable_label) >= 3:
            candidates = [
                symbol
                for comparable, symbol in comparable_symbols.items()
                if comparable.startswith(comparable_label)
                or comparable_label.startswith(comparable)
            ]
            if len(candidates) == 1:
                base_symbol = candidates[0]

        if base_symbol:
            discovered[root] = base_symbol

    return discovered

def get_best_limits(ins_code):
    """
    دریافت BestLimits نماد.

    خروجی:
    1. قیمت خرید ردیف اول
    2. حجم خرید ردیف اول
    3. قیمت فروش ردیف اول
    4. حجم فروش ردیف اول
    5. پنج ردیف اول Order Book
    """

    url = f"http://cdn.tsetmc.com/api/BestLimits/{ins_code}"

    try:
        res = requests.get(
            url,
            timeout=5
        )

        res.raise_for_status()

        data = res.json()

    except Exception as error:

        print(
            "BestLimits error:",
            ins_code,
            error
        )

        return (
            None,
            None,
            None,
            None,
            []
        )


    best_limits = data.get(
        "bestLimits",
        []
    )


    if (
        not isinstance(best_limits, list)
        or len(best_limits) == 0
    ):

        return (
            None,
            None,
            None,
            None,
            []
        )


    # =========================
    # ردیف اول
    # =========================

    first = best_limits[0]


    buy_price = (
        first.get("buyPrice")
        or first.get("pMeDem")
    )

    buy_volume = (
        first.get("buyVolume")
        or first.get("qTitMeDem")
    )

    sell_price = (
        first.get("sellPrice")
        or first.get("pMeOf")
    )

    sell_volume = (
        first.get("sellVolume")
        or first.get("qTitMeOf")
    )


    # =========================
    # ساخت پنج ردیف Order Book
    # =========================

    order_book = []


    for index, row in enumerate(
        best_limits[:5]
    ):

        if not isinstance(row, dict):
            continue


        row_number = (
            row.get("number")
            or row.get("row")
            or index + 1
        )


        buy_order_count = (
            row.get("buyCount")
            or row.get("zOrdMeDem")
            or 0
        )


        row_buy_volume = (
            row.get("buyVolume")
            or row.get("qTitMeDem")
            or 0
        )


        row_buy_price = (
            row.get("buyPrice")
            or row.get("pMeDem")
            or 0
        )


        row_sell_price = (
            row.get("sellPrice")
            or row.get("pMeOf")
            or 0
        )


        row_sell_volume = (
            row.get("sellVolume")
            or row.get("qTitMeOf")
            or 0
        )


        sell_order_count = (
            row.get("sellCount")
            or row.get("zOrdMeOf")
            or 0
        )


        order_book.append({

            "ردیف":
                row_number,

            "تعداد سفارش خرید":
                buy_order_count,

            "حجم خرید":
                row_buy_volume,

            "قیمت خرید":
                row_buy_price,

            "قیمت فروش":
                row_sell_price,

            "حجم فروش":
                row_sell_volume,

            "تعداد سفارش فروش":
                sell_order_count
        })


    return (
        buy_price,
        buy_volume,
        sell_price,
        sell_volume,
        order_book
    )

def format_num(x):
    try:
        return f"{int(x):,}"
    except:
        return x
    
def parse_number(value):
    """
    تبدیل مقدار رشته‌ای به عدد.
    در صورت نامعتبر بودن مقدار، None برمی‌گرداند.
    """
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None

def get_iran_now():
    """
    زمان فعلی ایران
    """
    return datetime.now(
        IRAN_TIMEZONE
    )


def should_save_trade_value_snapshot():
    """
    فقط از ساعت 12 ظهر تا قبل از 24
    اجازه ذخیره Snapshot داریم.
    """

    now = get_iran_now()

    return 12 <= now.hour < 24


def collect_trade_values(rows):
    """
    ارزش معاملات تمام اختیارهای خرید را
    از MarketWatch استخراج می‌کند.

    کلید اصلی insCode است.
    """

    values = {}

    for row in rows:

        fields = row.split(",")

        if len(fields) < 25:
            continue

        ins_code = fields[0].strip()
        symbol = fields[2].strip()
        description = fields[3].strip()

        # تشخیص اختیار از شرح رسمی، نه صرفاً حرف اول نماد.
        if not is_option_description(description):
            continue

        trade_value = parse_number(
            fields[10]
        )

        if (
            not ins_code or
            trade_value is None
        ):
            continue

        values[ins_code] = {

            "symbol":
                symbol,

            "trade_value":
                trade_value
        }

    return values

def has_meaningful_trade_values(values):
    """
    بررسی می‌کند داده زنده ارزش معاملات
    واقعاً مقدار قابل استفاده داشته باشد.

    هدف:
    جلوگیری از overwrite شدن Snapshot سالم
    با یک فایل کاملاً صفر.
    """

    if not isinstance(values, dict):
        return False

    if not values:
        return False

    non_zero_count = 0

    for item in values.values():

        if not isinstance(item, dict):
            continue

        trade_value = parse_number(
            item.get("trade_value")
        )

        if (
            trade_value is not None
            and trade_value > 0
        ):
            non_zero_count += 1

    return non_zero_count > 0

def save_trade_value_snapshot(values):
    """
    از ساعت 12 ظهر تا 24، Snapshot جدید ذخیره می‌شود.

    ولی اگر داده دریافتی کاملاً صفر یا نامعتبر باشد،
    Snapshot قبلی پاک نمی‌شود.
    """

    if not should_save_trade_value_snapshot():
        return False

    if not isinstance(values, dict):
        return False

    if not values:
        return False

    # جلوگیری از خراب‌شدن Snapshot با داده صفر
    if not has_meaningful_trade_values(values):

        return False

    now = get_iran_now()

    payload = {
        "date":
            now.date().isoformat(),

        "updated_at":
            now.isoformat(),

        "count":
            len(values),

        "values":
            values
    }

    directory = os.path.dirname(
        TRADE_VALUE_SNAPSHOT_FILE
    )

    os.makedirs(
        directory,
        exist_ok=True
    )

    temporary_file = (
        TRADE_VALUE_SNAPSHOT_FILE
        + ".tmp"
    )

    try:

        with trade_value_snapshot_lock:

            with open(
                temporary_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

                file.flush()
                os.fsync(
                    file.fileno()
                )

            os.replace(
                temporary_file,
                TRADE_VALUE_SNAPSHOT_FILE
            )

        return True

    except Exception as error:

        print(
            "Trade value snapshot save error:",
            error
        )

        return False

def load_trade_value_snapshot():
    """
    خواندن آخرین Snapshot ذخیره‌شده
    """

    if not os.path.exists(
        TRADE_VALUE_SNAPSHOT_FILE
    ):
        return None

    try:

        with trade_value_snapshot_lock:

            with open(
                TRADE_VALUE_SNAPSHOT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                payload = json.load(file)

        if not isinstance(payload, dict):
            return None

        values = payload.get(
            "values"
        )

        if not isinstance(values, dict):
            return None

        return payload

    except Exception as error:

        print(
            "Trade value snapshot load error:",
            error
        )

        return None


def get_saved_trade_value(
    snapshot_values,
    ins_code,
    symbol=None
):
    """
    گرفتن ارزش معاملات ذخیره‌شده.

    ابتدا با insCode جستجو می‌کند.
    اگر پیدا نشد، با نام نماد نیز جستجو می‌کند.
    """

    if not isinstance(
        snapshot_values,
        dict
    ):
        return None

    ins_code = str(
        ins_code
    ).strip()


    # =====================================================
    # روش اصلی: insCode
    # =====================================================

    item = snapshot_values.get(
        ins_code
    )

    if item is not None:

        if isinstance(item, dict):

            value = parse_number(
                item.get(
                    "trade_value"
                )
            )

        else:

            value = parse_number(
                item
            )

        if value is not None:
            return value


    # =====================================================
    # روش دوم: پیدا کردن با نام نماد
    # =====================================================

    if symbol:

        symbol = normalize_symbol(symbol)

        for saved_item in (
            snapshot_values.values()
        ):

            if not isinstance(
                saved_item,
                dict
            ):
                continue

            saved_symbol = normalize_symbol(
                saved_item.get("symbol", "")
            )

            if saved_symbol != symbol:
                continue

            value = parse_number(
                saved_item.get(
                    "trade_value"
                )
            )

            if value is not None:
                return value


    return None


# =========================================================
# ORDER BOOK SNAPSHOT
# =========================================================

def should_save_order_book_snapshot(now=None):
    """
    Order Book فقط از ساعت 12:25 تا پایان دقیقه 12:35
    به‌روزرسانی می‌شود. بعد از آن Snapshot همان روز قفل است.
    """

    current_time = now or get_iran_now()

    current_minutes = (
        current_time.hour * 60
        + current_time.minute
    )

    return (
        12 * 60 + 25
        <= current_minutes
        < 12 * 60 + 36
    )


def load_order_book_snapshot():
    """
    خواندن آخرین Snapshot ذخیره‌شده سفارشات.
    """

    if not os.path.exists(
        ORDER_BOOK_SNAPSHOT_FILE
    ):
        return None

    try:

        with order_book_snapshot_lock:

            with open(
                ORDER_BOOK_SNAPSHOT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                payload = json.load(file)

        if not isinstance(payload, dict):
            return None

        order_books = payload.get(
            "order_books",
            {}
        )

        if not isinstance(order_books, dict):
            return None

        return payload

    except Exception as error:

        print(
            "Order book snapshot load error:",
            error
        )

        return None


def save_order_book_snapshot(
    ins_code,
    symbol,
    buy_price,
    buy_volume,
    sell_price,
    sell_volume,
    order_book
):
    """
    آخرین Order Book دریافت‌شده هر نماد را در بازه مجاز
    به Snapshot همان روز اضافه یا جایگزین می‌کند.
    """

    now = get_iran_now()

    if not should_save_order_book_snapshot(now):
        return False

    if (
        not ins_code
        or not isinstance(order_book, list)
        or not order_book
    ):
        return False

    ins_code = str(ins_code).strip()

    directory = os.path.dirname(
        ORDER_BOOK_SNAPSHOT_FILE
    )

    os.makedirs(
        directory,
        exist_ok=True
    )

    temporary_file = (
        ORDER_BOOK_SNAPSHOT_FILE
        + ".tmp"
    )

    try:

        with order_book_snapshot_lock:

            existing_payload = {}

            if os.path.exists(
                ORDER_BOOK_SNAPSHOT_FILE
            ):

                try:

                    with open(
                        ORDER_BOOK_SNAPSHOT_FILE,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        existing_payload = (
                            json.load(file)
                        )

                except Exception:
                    existing_payload = {}

            today = now.date().isoformat()

            if (
                isinstance(existing_payload, dict)
                and existing_payload.get("date") == today
                and isinstance(
                    existing_payload.get("order_books"),
                    dict
                )
            ):

                order_books = dict(
                    existing_payload["order_books"]
                )

            else:

                # اولین ذخیره در روز جدید، Snapshot روز قبل
                # را با مجموعه جدید همان روز جایگزین می‌کند.
                order_books = {}

            order_books[ins_code] = {
                "ins_code": ins_code,
                "symbol": str(symbol or "").strip(),
                "updated_at": now.isoformat(),
                "buy_price": buy_price,
                "buy_volume": buy_volume,
                "sell_price": sell_price,
                "sell_volume": sell_volume,
                "order_book": order_book
            }

            payload = {
                "date": today,
                "updated_at": now.isoformat(),
                "window": "12:25-12:35",
                "count": len(order_books),
                "order_books": order_books
            }

            with open(
                temporary_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2
                )

                file.flush()
                os.fsync(
                    file.fileno()
                )

            os.replace(
                temporary_file,
                ORDER_BOOK_SNAPSHOT_FILE
            )

        return True

    except Exception as error:

        print(
            "Order book snapshot save error:",
            error
        )

        return False


def get_saved_order_book(
    snapshot_order_books,
    ins_code,
    symbol=None
):
    """
    Order Book ذخیره‌شده را ابتدا با insCode و سپس
    در صورت نیاز با نام نماد پیدا می‌کند.
    """

    if not isinstance(
        snapshot_order_books,
        dict
    ):
        return None

    ins_code = str(ins_code).strip()

    item = snapshot_order_books.get(
        ins_code
    )

    if item is None and symbol:

        symbol = normalize_symbol(symbol)

        item = next(
            (
                saved_item
                for saved_item
                in snapshot_order_books.values()
                if isinstance(saved_item, dict)
                and normalize_symbol(
                    saved_item.get("symbol", "")
                ) == symbol
            ),
            None
        )

    if not isinstance(item, dict):
        return None

    order_book = item.get(
        "order_book"
    )

    if not isinstance(order_book, list):
        return None

    return (
        parse_number(item.get("buy_price")),
        parse_number(item.get("buy_volume")),
        parse_number(item.get("sell_price")),
        parse_number(item.get("sell_volume")),
        order_book
    )

def extract_expiry_data(desc):
    """
    استخراج تاریخ سررسید و تعداد روز باقی‌مانده از توضیحات نماد.
    """
    expire_date = ""
    days_remaining = None

    pattern_slash = re.search(r'\d{4}/\d{2}/\d{2}', desc)
    pattern_short_slash = re.search(r'(?<!\d)(\d{2})/(\d{2})/(\d{2})(?!\d)', desc)
    pattern8 = re.search(r'-(\d{8})', desc)
    pattern6 = re.search(r'-(\d{6})', desc)

    if pattern_slash:
        expire_date = pattern_slash.group(0)

    elif pattern_short_slash:
        expire_date = (
            f"{1400 + int(pattern_short_slash.group(1))}/"
            f"{pattern_short_slash.group(2)}/"
            f"{pattern_short_slash.group(3)}"
        )

    elif pattern8:
        raw = pattern8.group(1)
        expire_date = f"{raw[:4]}/{raw[4:6]}/{raw[6:8]}"

    elif pattern6:
        raw = pattern6.group(1)
        year = 1400 + int(raw[:2])
        expire_date = f"{year}/{raw[2:4]}/{raw[4:6]}"

    if expire_date:
        try:
            year, month, day = map(int, expire_date.split("/"))

            expiry_date = jdatetime.date(year, month, day)
            today_jalali = jdatetime.date.today()

            difference = (
                expiry_date.togregorian()
                - today_jalali.togregorian()
            )

            days_remaining = difference.days

        except (TypeError, ValueError):
            days_remaining = None

    return expire_date, days_remaining


@lru_cache(maxsize=16)
def get_iran_official_holiday_dates(start_year, end_year):
    """Return Iran's official public holidays for the requested Gregorian years."""
    years = range(int(start_year), int(end_year) + 1)
    return frozenset(
        holidays.country_holidays(
            "IR",
            years=years,
            language="fa_IR",
        ).keys()
    )


def calculate_trading_days_remaining(
    expiry_date,
    today=None,
    official_holidays=None,
):
    """Count Iran market days after today through the Jalali expiry date."""
    try:
        year, month, day = map(int, str(expiry_date).split("/"))
        expiry_gregorian = jdatetime.date(year, month, day).togregorian()
    except (TypeError, ValueError):
        return None

    today = today or datetime.now(IRAN_TIMEZONE).date()
    if expiry_gregorian <= today:
        return 0

    if official_holidays is None:
        official_holidays = get_iran_official_holiday_dates(
            today.year,
            expiry_gregorian.year,
        )
    else:
        official_holidays = set(official_holidays)

    trading_days = 0
    current_date = today + timedelta(days=1)
    while current_date <= expiry_gregorian:
        # datetime.weekday(): Monday=0, Thursday=3, Friday=4.
        if (
            current_date.weekday() not in {3, 4}
            and current_date not in official_holidays
        ):
            trading_days += 1
        current_date += timedelta(days=1)

    return trading_days

def generate_spread_data(
    base_symbol="",
    min_trade_value=None,
    days_value=None,
    days_operator=None,
    data_source_mode="live"
):
    """
    دریافت نمادهای اختیار خرید و اعمال فیلترهای اسپرد.

    base_symbol:
        نماد پایه مانند اهرم

    min_trade_value:
        حداقل ارزش معاملات به ریال

    days_value:
        تعداد روز تا سررسید

    days_operator:
        gte = بیشتر یا مساوی
        lte = کمتر یا مساوی
        eq  = مساوی
    """

    base_symbol = normalize_symbol(base_symbol)
    market_url = "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx"

    try:
        response = requests.get(market_url, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"

    except requests.RequestException as error:
        print("MarketWatch error:", error)
        return []

    rows = response.text.strip().split(";")
    option_mapping = build_dynamic_option_mapping(rows)

    # =========================================================
    # TRADE VALUE MODE
    # =========================================================

    saved_trade_values = {}
    snapshot_info = None

    saved_order_books = {}
    order_book_snapshot_info = None


    use_saved_trade_value = data_source_mode in {
        "saved_trade", "saved_trade_orders"
    }
    use_saved_order_books = data_source_mode == "saved_trade_orders"

    if use_saved_trade_value:

        # -----------------------------------------------------
        # حالت ذخیره‌شده
        #
        # فقط فایل خوانده می‌شود.
        # فایل تغییر نمی‌کند.
        # ارزش معاملات زنده استفاده نمی‌شود.
        # -----------------------------------------------------

        snapshot_info = (
            load_trade_value_snapshot()
        )


        if snapshot_info is None:

            raise RuntimeError(
                "فایل ارزش معاملات ذخیره‌شده وجود ندارد."
            )


        saved_trade_values = (
            snapshot_info.get(
                "values",
                {}
            )
        )


        if (
            not isinstance(
                saved_trade_values,
                dict
            )
            or not saved_trade_values
        ):

            raise RuntimeError(
                "فایل ارزش معاملات ذخیره‌شده خالی یا نامعتبر است."
            )

        if use_saved_order_books:
            order_book_snapshot_info = (
                load_order_book_snapshot()
            )

        if use_saved_order_books and order_book_snapshot_info is None:

            raise RuntimeError(
                "فایل سفارشات ذخیره‌شده وجود ندارد."
            )

        if order_book_snapshot_info:
            saved_order_books = (
                order_book_snapshot_info.get(
                    "order_books",
                    {}
                )
            )

        if use_saved_order_books and (
            not isinstance(saved_order_books, dict)
            or not saved_order_books
        ):

            raise RuntimeError(
                "فایل سفارشات ذخیره‌شده خالی یا نامعتبر است."
            )

        if (
            use_saved_order_books
            and snapshot_info.get("date")
            != order_book_snapshot_info.get("date")
        ):

            raise RuntimeError(
                "تاریخ فایل ارزش معاملات و سفارشات ذخیره‌شده یکسان نیست."
            )

    else:

        # -----------------------------------------------------
        # حالت زنده
        #
        # ارزش معاملات از MarketWatch خوانده می‌شود.
        # فقط در این حالت فایل می‌تواند آپدیت شود.
        # -----------------------------------------------------

        live_trade_values = (
            collect_trade_values(
                rows
            )
        )


        save_trade_value_snapshot(
            live_trade_values
        )

    # قیمت آخرین معامله تمام نمادهای بازار
    market_data = {}

    # قیمت پایانی نمادها
    market_close_data = {}


    for row in rows:

        fields = row.split(",")

        if len(fields) < 25:
            continue


        market_symbol = normalize_symbol(fields[2])

        market_last_price = parse_number(
            fields[7]
        )

        market_close_price = parse_number(
            fields[6]
        )


        if market_last_price is not None:

            market_data[
                market_symbol
            ] = market_last_price


        if market_close_price is not None:

            market_close_data[
                market_symbol
            ] = market_close_price

    candidates = []

    

    for row in rows:
        fields = row.split(",")

        if len(fields) < 25:
            continue

        ins_code = fields[0].strip()
        symbol = fields[2].strip()
        desc = fields[3].strip()
        # آخرین قیمت نماد اختیار
        option_last_price = parse_number(
            fields[7]
        )

        # قیمت پایانی نماد اختیار
        option_close_price = parse_number(
            fields[6]
        )

        # حجم معاملات نماد اختیار
        trade_volume = parse_number(
            fields[9]
        )
        # استخراج قیمت اعمال از توضیحات نماد
        strike = None

        strike_match = re.search(r'-(\d+)-', desc)

        if strike_match:
            strike = parse_number(strike_match.group(1))

        # فقط اختیار خرید
        if not is_option_description(desc, "call"):
            continue

        # حذف اعداد انتهای نماد، مانند ضهرم1234 ← ضهرم
        clean_symbol = normalize_symbol(re.sub(r'\d+', '', symbol))

        # پیدا کردن نماد پایه از mapping
        option_base_symbol = option_mapping.get(clean_symbol)

        if not option_base_symbol:
            continue

        # قیمت آخرین معامله نماد پایه
        base_price = market_data.get(
            option_base_symbol
        )

        # قیمت پایانی نماد پایه
        base_close_price = market_close_data.get(
            option_base_symbol
        )


        if base_price is None:
            continue

        # محاسبه اهرم
        leverage = None

        if (
            option_last_price is not None
            and option_last_price > 0
        ):
            leverage = round(
                base_price / option_last_price,
                2
            )

        # فیلتر نماد پایه
        if base_symbol and option_base_symbol != base_symbol:
            continue

        # =========================================================
        # ارزش معاملات
        # =========================================================

        # مقدار زنده
        if use_saved_trade_value:

            # فقط از فایل خوانده می‌شود
            trade_value = (
                get_saved_trade_value(
                    saved_trade_values,
                    ins_code,
                    symbol
                )
            )


            # اگر نماد در فایل نبود،
            # مقدار زنده جایگزین نمی‌شود.
            if trade_value is None:

                continue

        else:

            # فقط حالت زنده
            trade_value = parse_number(
                fields[10]
            )


        # فیلتر ارزش معاملات
        if min_trade_value is not None:

            if trade_value is None:
                continue

            if trade_value < min_trade_value:
                continue

        # تاریخ سررسید و روز باقی‌مانده
        expire_date, days_remaining = extract_expiry_data(desc)

        # موقعیت باز
        open_interest = parse_number(fields[24])

        # وضعیت اختیار خرید
        status = ""

        if strike is not None and base_price is not None:

            if base_price > strike:
                status = "ITM"

            elif base_price < strike:
                status = "OTM"

            else:
                status = "ATM"

        # فیلتر روز تا سررسید
        if days_value is not None:

            if days_remaining is None:
                continue

            if days_operator == "gte" and days_remaining < days_value:
                continue

            if days_operator == "lte" and days_remaining > days_value:
                continue

            if days_operator == "eq" and days_remaining != days_value:
                continue

        # فقط اطلاعات نمادهای عبورکرده ذخیره می‌شود.
        candidates.append({
            "ins_code": ins_code,
            "symbol": symbol,
            "base_symbol": option_base_symbol,

            "base_price": base_price,
            "option_last_price": option_last_price,
            "base_close_price": base_close_price,
            "option_close_price": option_close_price,
            "leverage": leverage,

            "strike": strike,
            "open_interest": open_interest,
            "status": status,

            "expire_date": expire_date,
            "days_remaining": days_remaining,
            "trade_value": trade_value,
            "trade_volume": trade_volume,
        })

    output = []

    # فقط برای نمادهای عبورکرده، اطلاعات سفارش‌ها دریافت می‌شود.
    for item in candidates:

        if use_saved_order_books:

            saved_limits = get_saved_order_book(
                saved_order_books,
                item["ins_code"],
                item["symbol"]
            )

            # در حالت ذخیره‌شده هیچ داده زنده‌ای
            # جایگزین Snapshot ناقص نمی‌شود.
            if saved_limits is None:
                continue

            (
                buy_price,
                buy_volume,
                sell_price,
                sell_volume,
                order_book
            ) = saved_limits

        else:

            (
                buy_price,
                buy_volume,
                sell_price,
                sell_volume,
                order_book
            ) = get_best_limits(
                item["ins_code"]
            )

            save_order_book_snapshot(
                item["ins_code"],
                item["symbol"],
                buy_price,
                buy_volume,
                sell_price,
                sell_volume,
                order_book
            )

        output.append({

            # فیلد فنی؛ در جدول نمایش داده نخواهد شد
            "__insCode": str(item["ins_code"]),

            "__orderBook": order_book,

            "__tradeVolume": (
                format_num(
                    item["trade_volume"]
                )
                if item["trade_volume"] is not None
                else ""
            ),

            "__optionClosePrice": (
                format_num(
                    item["option_close_price"]
                )
                if item["option_close_price"] is not None
                else ""
            ),

            "__baseClosePrice": (
                format_num(
                    item["base_close_price"]
                )
                if item["base_close_price"] is not None
                else ""
            ),

            "__tradeValueSource": (
                "snapshot"
                if use_saved_trade_value
                else "live"
            ),
            "__tradeValueSnapshotDate": (
                snapshot_info.get("date", "")
                if snapshot_info
                else ""
            ),

            "__tradeValueSnapshotUpdatedAt": (
                snapshot_info.get("updated_at", "")
                if snapshot_info
                else ""
            ),

            "__orderBookSource": (
                "snapshot"
                if use_saved_order_books
                else "live"
            ),

            "__orderBookSnapshotDate": (
                order_book_snapshot_info.get("date", "")
                if order_book_snapshot_info
                else ""
            ),

            "نماد اختیار": item["symbol"],
            "نماد پایه": item["base_symbol"],

            "آخرین قیمت نماد پایه": (
                format_num(item["base_price"])
                if item["base_price"] is not None
                else ""
            ),

            "آخرین قیمت نماد اختیار": (
                format_num(item["option_last_price"])
                if item["option_last_price"] is not None
                else ""
            ),

            "اهرم": (
                item["leverage"]
                if item["leverage"] is not None
                else ""
            ),

            "قیمت اعمال": (
                format_num(item["strike"])
                if item["strike"] is not None
                else ""
            ),

            "وضعیت": item["status"],

            "موقعیت باز": (
                format_num(item["open_interest"])
                if item["open_interest"] is not None
                else ""
            ),

            "ارزش معاملات": (
                format_num(item["trade_value"])
                if item["trade_value"] is not None
                else ""
            ),

            "تاریخ سررسید": item["expire_date"],

            "روز باقی‌مانده": (
                item["days_remaining"]
                if item["days_remaining"] is not None
                else ""
            ),

            "قیمت خرید": (
                format_num(buy_price)
                if buy_price is not None
                else ""
            ),

            "حجم خرید": (
                format_num(buy_volume)
                if buy_volume is not None
                else ""
            ),

            "قیمت فروش": (
                format_num(sell_price)
                if sell_price is not None
                else ""
            ),

            "حجم فروش": (
                format_num(sell_volume)
                if sell_volume is not None
                else ""
            )
        })

    return output


def generate_data(use_saved_trade_value=False):
    url = "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx"

    saved_trade_values = {}
    snapshot_info = None

    if use_saved_trade_value:
        snapshot_info = load_trade_value_snapshot()

        if snapshot_info is None:
            raise RuntimeError(
                "فایل ارزش معاملات ذخیره‌شده وجود ندارد."
            )

        saved_trade_values = snapshot_info.get(
            "values",
            {}
        )

        if not isinstance(saved_trade_values, dict) or not saved_trade_values:
            raise RuntimeError(
                "فایل ارزش معاملات ذخیره‌شده خالی یا نامعتبر است."
            )

    for _ in range(10):
        r = requests.get(url)
        r.encoding = "utf-8"
        rows = r.text.strip().split(';')
        option_mapping = build_dynamic_option_mapping(rows)

        if not use_saved_trade_value:
            save_trade_value_snapshot(
                collect_trade_values(rows)
            )

        market_data = {}
        for row in rows:
            f = row.split(',')
            if len(f) < 25:
                continue
            market_data[normalize_symbol(f[2])] = f[7]

        output = []
        today_jalali = jdatetime.date.today()

        for row in rows:
            f = row.split(',')
            if len(f) < 25:
                continue

            symbol = f[2].strip()
            desc = f[3].strip()

            ins_code = f[0].strip()
            #buy_price, buy_vol, sell_price, sell_vol = get_best_limits(ins_code)

            if not is_option_description(desc):
                continue

            base_key = normalize_symbol(re.sub(r'\d+', '', symbol))
            base_symbol = option_mapping.get(base_key, "")
            base_price = market_data.get(base_symbol, "")

            if not base_price.isdigit():
                continue

            last_price = f[7]
            close_price = f[6]

            if use_saved_trade_value:
                # فقط ستون ارزش معاملات از فایل خوانده می‌شود.
                trade_value = get_saved_trade_value(
                    saved_trade_values,
                    ins_code,
                    symbol
                )

                # در حالت ذخیره‌شده از مقدار زنده fallback نمی‌گیریم.
                # اگر مقدار این نماد داخل فایل نبود، فقط ستون ارزش معاملات خالی می‌ماند
                # و بقیه اطلاعات زنده همچنان نمایش داده می‌شوند.
            else:
                trade_value = parse_number(f[10])

            if not last_price.isdigit():
                continue

            last_price = float(last_price)
            base_price = float(base_price)

            # strike
            strike = ""
            m = re.search(r'-(\d+)-', desc)
            if m:
                strike = float(m.group(1))

            # expire date
            expire_date = ""
            days_remaining = ""

            pattern_slash = re.search(r'\d{4}/\d{2}/\d{2}', desc)
            pattern8 = re.search(r'-(\d{8})', desc)
            pattern6 = re.search(r'-(\d{6})', desc)

            if pattern_slash:
                expire_date = pattern_slash.group(0)
            elif pattern8:
                raw = pattern8.group(1)
                expire_date = f"{raw[:4]}/{raw[4:6]}/{raw[6:8]}"
            elif pattern6:
                raw = pattern6.group(1)
                year = 1400 + int(raw[:2])
                expire_date = f"{year}/{raw[2:4]}/{raw[4:6]}"

            if expire_date:
                try:
                    y, m, d = map(int, expire_date.split('/'))
                    expiry = jdatetime.date(y, m, d)
                    diff = expiry.togregorian() - today_jalali.togregorian()
                    days_remaining = diff.days
                except:
                    days_remaining = ""

            leverage = round(base_price / last_price, 2) if last_price > 0 else ""

            if base_price > 0 and strike != "":
                is_call = is_option_description(desc, "call")

                breakeven_calc = (strike + last_price) if is_call else (strike - last_price)

                intrinsic_diff = round((breakeven_calc / base_price) - 1, 4)
            else:
                intrinsic_diff = ""

            if is_option_description(desc, "call"):
                breakeven = round(strike + last_price, 2)
            else:
                breakeven = round(strike - last_price, 2)

            open_interest = f[24] if len(f) > 24 else ""

            # status
            if strike != "":
                if is_option_description(desc, "call"):
                    status = "ITM" if base_price > strike else ("OTM" if base_price < strike else "ATM")
                else:
                    status = "OTM" if base_price > strike else ("ITM" if base_price < strike else "ATM")
            else:
                status = ""

            output.append({
                "__tradeValueSource": (
                    "snapshot"
                    if use_saved_trade_value
                    else "live"
                ),

                "نماد اختیار": symbol,

                "قیمت نماد پایه": format_num(base_price),
                "قیمت اعمال": format_num(strike),

                "تاریخ سررسید": expire_date,

                "آخرین قیمت اختیار": format_num(last_price),
                "قیمت پایانی اختیار": format_num(close_price) if close_price.isdigit() else None,

                "ارزش معاملات": (
                    format_num(trade_value)
                    if trade_value is not None
                    else None
                ),

                "روز باقی‌مانده": days_remaining,
                "اهرم": leverage,
                "وضعیت": status,

                "موقعیت باز": format_num(open_interest),

                "فاصله تا سر‌به‌سر": round(intrinsic_diff * 100, 2) if intrinsic_diff != "" else "",
                "قیمت سر‌به‌سر": format_num(breakeven),
            })

        if len(output) > 0:
            return output

        time.sleep(2)

    return []


def parse_market_watch_init(response_text):
    """Return MarketWatch rows and first order-book levels from the batch feed."""
    market_rows = []
    best_limits = {}
    for section in str(response_text or "").split("@"):
        section_rows = [item for item in section.split(";") if item.strip()]
        if not section_rows:
            continue

        if not market_rows:
            for item in section_rows:
                fields = item.split(",")
                if len(fields) >= 26 and str(fields[1]).strip().upper().startswith("IR"):
                    market_rows = section_rows
                    break

        for item in section_rows:
            fields = item.split(",")
            if len(fields) < 8:
                continue
            ins_code = str(fields[0] or "").strip()
            row_number = stock_integer(fields[1])
            if not ins_code.isdigit() or row_number != 1:
                continue
            best_limits[ins_code] = {
                "best_buy_count": stock_integer(fields[2]),
                "best_sell_count": stock_integer(fields[3]),
                "best_buy_price": stock_number(fields[4]),
                "best_sell_price": stock_number(fields[5]),
                "best_buy_volume": stock_integer(fields[6]),
                "best_sell_volume": stock_integer(fields[7]),
            }

    return market_rows, best_limits


def fetch_market_watch_snapshot():
    """Fetch instruments and order-book level one in one TSETMC request."""
    try:
        response = requests.get(
            "https://old.tsetmc.com/tsev2/data/MarketWatchInit.aspx?h=0&r=0",
            headers=TSETMC_HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        response.encoding = "utf-8"
        market_rows, best_limits = parse_market_watch_init(response.text)
        if market_rows:
            return market_rows, best_limits
    except requests.RequestException:
        pass

    response = requests.get(
        "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx",
        headers=TSETMC_HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text.strip().split(";"), {}


def fetch_market_watch_rows():
    rows, _ = fetch_market_watch_snapshot()
    return rows


def calculate_option_spread_percent(best_buy_price, best_sell_price):
    """Return first ask divided by first bid minus one, as a percentage."""
    buy_price = parse_number(best_buy_price)
    sell_price = parse_number(best_sell_price)
    if (
        buy_price is None
        or sell_price is None
        or buy_price <= 0
        or sell_price <= 0
    ):
        return None
    return ((sell_price / buy_price) - 1) * 100


def calculate_option_leverage(base_price, option_last_price):
    """Return simple option leverage using the underlying's last price."""
    if (
        base_price is None
        or option_last_price is None
        or option_last_price <= 0
    ):
        return None
    return base_price / option_last_price


def calculate_call_option_status(base_price, strike):
    """Classify a call option as ITM, ATM, or OTM."""
    if base_price is None or strike is None:
        return None
    if base_price > strike:
        return "ITM"
    if base_price < strike:
        return "OTM"
    return "ATM"


def calculate_put_option_metrics(base_price, strike, premium):
    """Return the requested put break-even, distance, leverage and moneyness."""
    base_price = parse_number(base_price)
    strike = parse_number(strike)
    premium = parse_number(premium)
    if (
        base_price is None
        or strike is None
        or premium is None
        or base_price <= 0
        or premium <= 0
    ):
        return None
    status = "ITM" if base_price < strike else "OTM" if base_price > strike else "ATM"
    breakeven_price = strike - premium
    return {
        "breakeven_price": breakeven_price,
        "breakeven_distance": ((breakeven_price / base_price) - 1) * 100,
        "leverage": base_price / premium,
        "status": status,
    }


def fetch_option_best_buy_price(ins_code):
    """Return the first (best) buy-order price for an option contract."""
    response = requests.get(
        f"https://cdn.tsetmc.com/api/BestLimits/{ins_code}",
        headers=TSETMC_HEADERS,
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    best_limits = data.get("bestLimits") or []
    if not isinstance(best_limits, list) or not best_limits:
        return None

    first_row = min(
        (row for row in best_limits if isinstance(row, dict)),
        key=lambda row: stock_integer(row.get("number") or row.get("row")) or 1,
        default=None,
    )
    if first_row is None:
        return None

    return stock_number(
        first_row.get("pMeDem")
        if first_row.get("pMeDem") is not None
        else first_row.get("buyPrice")
    )


def build_option_burning_summary(
    bases,
    limit=20,
    best_buy_fetcher=fetch_option_best_buy_price,
):
    """Build ranked rows using contracts whose last price and best bid are valid."""
    option_groups = []
    special_ranges = {
        normalize_symbol("اهرم"): 4,
        normalize_symbol("موج"): 4,
        normalize_symbol("توان"): 4,
    }

    for base in bases:
        base_symbol = normalize_symbol(base.get("base_symbol"))
        allowed_range = special_ranges.get(base_symbol, 3)

        for group in base.get("groups") or []:
            trading_days = parse_number(group.get("trading_days_remaining"))
            if trading_days is None:
                trading_days = parse_number(group.get("days_remaining"))
            if trading_days is None or trading_days <= 0:
                continue

            eligible_options = [
                option
                for option in group.get("options") or []
                if (
                    (parse_number(option.get("option_last_price")) or 0) >= 10
                    and parse_number(option.get("breakeven_distance")) is not None
                )
            ]
            if not eligible_options:
                continue

            option_groups.append({
                "trading_days": trading_days,
                "allowed_range": allowed_range,
                "options": sorted(
                    eligible_options,
                    key=lambda option: parse_number(
                        option.get("breakeven_distance")
                    ),
                    reverse=True,
                ),
            })

    def resolve_group(group):
        """Pick the greatest breakeven only after validating the first bid."""
        for option in group["options"]:
            best_buy_price = parse_number(option.get("best_buy_price"))
            if best_buy_price is None:
                ins_code = option.get("ins_code")
                if not ins_code:
                    continue
                try:
                    best_buy_price = parse_number(best_buy_fetcher(ins_code))
                except Exception:
                    continue
            if best_buy_price is None or best_buy_price < 10:
                continue

            percentage = (
                parse_number(option.get("breakeven_distance"))
                / (group["trading_days"] * group["allowed_range"])
                * 100
            )
            return {
                "symbol": option.get("symbol"),
                "days_remaining": int(group["trading_days"]),
                "option_burning_percentage": round(percentage, 2),
                "option_last_price": parse_number(
                    option.get("option_last_price")
                ),
                "status": option.get("status"),
                "best_buy_price": best_buy_price,
                "spread_percent": parse_number(option.get("spread_percent")),
            }
        return None

    rows = []
    if option_groups:
        with ThreadPoolExecutor(max_workers=min(8, len(option_groups))) as executor:
            futures = [
                executor.submit(resolve_group, group)
                for group in option_groups
            ]
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception:
                    row = None
                if row is not None:
                    rows.append(row)

    rows.sort(
        key=lambda row: row["option_burning_percentage"],
        reverse=True,
    )
    return rows[:max(0, int(limit))]


def generate_market_expectations(use_saved_trade_value=False):
    """Build non-visual option rows and expiry-level expectation summaries."""
    try:
        rows, best_limits_by_code = fetch_market_watch_snapshot()
    except requests.RequestException as error:
        raise RuntimeError("دریافت اطلاعات بازار برای انتظارات بازار ناموفق بود.") from error

    option_mapping = build_dynamic_option_mapping(rows)
    market_prices = {}

    for row in rows:
        fields = row.split(",")
        if len(fields) < 25:
            continue
        price = parse_number(fields[7])
        if price is not None:
            market_prices[normalize_symbol(fields[2])] = price

    now = get_iran_now()
    should_use_snapshot = use_saved_trade_value or now.hour < 9
    snapshot = load_trade_value_snapshot() if should_use_snapshot else None
    snapshot_values = snapshot.get("values", {}) if snapshot else {}
    use_snapshot = bool(snapshot_values)

    if use_saved_trade_value and not use_snapshot:
        raise RuntimeError(
            "فایل ارزش معاملات ذخیره‌شده وجود ندارد یا خالی است."
        )

    all_option_trade_values = (
        snapshot_values if use_snapshot else collect_trade_values(rows)
    )

    if not use_snapshot:
        save_trade_value_snapshot(all_option_trade_values)

    total_option_market_trade_value = 0
    for saved_item in all_option_trade_values.values():
        raw_trade_value = (
            saved_item.get("trade_value")
            if isinstance(saved_item, dict)
            else saved_item
        )
        parsed_trade_value = parse_number(raw_trade_value)
        if parsed_trade_value is not None and parsed_trade_value > 0:
            total_option_market_trade_value += parsed_trade_value

    grouped = {}
    put_options = []
    discovered_roots = set()

    for row in rows:
        fields = row.split(",")
        if len(fields) < 25:
            continue

        ins_code = fields[0].strip()
        symbol = fields[2].strip()
        description = fields[3].strip()

        is_call_option = is_option_description(description, "call")
        is_put_option = is_option_description(description, "put")
        if not is_call_option and not is_put_option:
            continue

        root = option_symbol_root(symbol)
        base_symbol = option_mapping.get(root)
        if not base_symbol:
            continue

        discovered_roots.add(root)
        base_price = market_prices.get(base_symbol)
        option_last_price = parse_number(fields[7])
        strike_match = re.search(r"-([\d,.]+)-", description)
        strike = parse_number(strike_match.group(1)) if strike_match else None
        expiry_date, days_remaining = extract_expiry_data(description)
        open_interest = parse_number(fields[24])

        if (
            base_price is None
            or base_price <= 0
            or option_last_price is None
            or strike is None
            or days_remaining is None
        ):
            continue

        if use_snapshot:
            trade_value = get_saved_trade_value(
                snapshot_values, ins_code, symbol
            )
        else:
            trade_value = parse_number(fields[10])

        trade_value = trade_value if trade_value is not None else 0
        best_limit = best_limits_by_code.get(ins_code, {})
        best_buy_price = parse_number(best_limit.get("best_buy_price"))
        best_sell_price = parse_number(best_limit.get("best_sell_price"))
        spread_percent = calculate_option_spread_percent(
            best_buy_price,
            best_sell_price,
        )
        leverage = calculate_option_leverage(base_price, option_last_price)

        if is_put_option:
            metrics = calculate_put_option_metrics(
                base_price,
                strike,
                option_last_price,
            )
            if metrics is None:
                continue
            put_options.append({
                "ins_code": ins_code,
                "symbol": symbol,
                "days_remaining": days_remaining,
                "expiry_date": expiry_date,
                "trade_value": round(trade_value, 2),
                "strike": strike,
                "option_last_price": option_last_price,
                "base_price": base_price,
                "best_buy_price": best_buy_price,
                "best_sell_price": best_sell_price,
                "spread_percent": (
                    round(spread_percent, 2)
                    if spread_percent is not None
                    else None
                ),
                "breakeven_price": round(metrics["breakeven_price"], 2),
                "breakeven_distance": round(
                    metrics["breakeven_distance"], 2
                ),
                "leverage": round(metrics["leverage"], 2),
                "status": metrics["status"],
            })
            continue

        status = calculate_call_option_status(base_price, strike)
        breakeven_distance = (
            ((strike + option_last_price) / base_price) - 1
        ) * 100
        monthly_return = (
            breakeven_distance * 30 / days_remaining
            if days_remaining > 0
            else None
        )
        market_trade_value_share = (
            trade_value / total_option_market_trade_value
            if total_option_market_trade_value > 0
            else 0
        )

        group_key = (base_symbol, expiry_date, days_remaining)
        grouped.setdefault(group_key, []).append({
            "ins_code": ins_code,
            "symbol": symbol,
            "days_remaining": days_remaining,
            "open_interest": open_interest,
            "expiry_date": expiry_date,
            "trade_value": trade_value,
            "market_trade_value_share": market_trade_value_share,
            "strike": strike,
            "option_last_price": option_last_price,
            "base_price": base_price,
            "leverage": leverage,
            "status": status,
            "breakeven_distance": breakeven_distance,
            "monthly_return": monthly_return,
            "best_buy_price": best_buy_price,
            "best_sell_price": best_sell_price,
            "spread_percent": spread_percent,
        })

    bases = {}

    for (base_symbol, expiry_date, days_remaining), option_rows in grouped.items():
        trading_days_remaining = calculate_trading_days_remaining(expiry_date)
        total_trade_value = sum(item["trade_value"] for item in option_rows)

        for item in option_rows:
            item["weight"] = (
                item["trade_value"] / total_trade_value
                if total_trade_value > 0
                else 0
            )

        weighted_average = (
            sum(
                item["weight"] * item["breakeven_distance"]
                for item in option_rows
            )
            if total_trade_value > 0
            else None
        )
        spread_rows = [
            item
            for item in option_rows
            if item.get("spread_percent") is not None
        ]
        spread_trade_value = sum(item["trade_value"] for item in spread_rows)
        weighted_spread = (
            sum(
                item["trade_value"] * item["spread_percent"]
                for item in spread_rows
            ) / spread_trade_value
            if spread_trade_value > 0
            else (
                sum(item["spread_percent"] for item in spread_rows)
                / len(spread_rows)
                if spread_rows
                else None
            )
        )
        meaningful_rows = [
            item for item in option_rows if item["weight"] > 0.05
        ]
        minimum = (
            min(item["breakeven_distance"] for item in meaningful_rows)
            if meaningful_rows else None
        )
        maximum = (
            max(item["breakeven_distance"] for item in meaningful_rows)
            if meaningful_rows else None
        )

        option_rows.sort(key=lambda item: (item["strike"], item["symbol"]))
        for item in option_rows:
            item["trade_value"] = round(item["trade_value"], 2)
            item["weight"] = round(item["weight"] * 100, 2)
            item["market_trade_value_share"] = round(
                item["market_trade_value_share"] * 100, 2
            )
            item["breakeven_distance"] = round(
                item["breakeven_distance"], 2
            )
            item["leverage"] = (
                round(item["leverage"], 2)
                if item["leverage"] is not None
                else None
            )
            item["monthly_return"] = (
                round(item["monthly_return"], 2)
                if item["monthly_return"] is not None
                else None
            )
            item["spread_percent"] = (
                round(item["spread_percent"], 2)
                if item["spread_percent"] is not None
                else None
            )

        bases.setdefault(base_symbol, []).append({
            "group_id": f"{base_symbol}-{expiry_date}",
            "days_remaining": days_remaining,
            "trading_days_remaining": trading_days_remaining,
            "expiry_date": expiry_date,
            "total_trade_value": round(total_trade_value, 2),
            "weighted_average": (
                round(weighted_average, 2)
                if weighted_average is not None else None
            ),
            "weighted_spread": (
                round(weighted_spread, 2)
                if weighted_spread is not None else None
            ),
            "minimum": round(minimum, 2) if minimum is not None else None,
            "maximum": round(maximum, 2) if maximum is not None else None,
            "options": option_rows,
        })

    output = []
    for base_symbol in sorted(bases):
        groups = sorted(
            bases[base_symbol],
            key=lambda item: (item["days_remaining"], item["expiry_date"]),
        )
        output.append({"base_symbol": base_symbol, "groups": groups})

    option_burning = build_option_burning_summary(output, limit=20)
    put_options.sort(
        key=lambda item: (item["trade_value"], item["symbol"]),
        reverse=True,
    )

    return {
        "generated_at": now.isoformat(),
        "trade_value_source": "snapshot" if use_snapshot else "live",
        "snapshot_date": snapshot.get("date", "") if snapshot else "",
        "total_option_market_trade_value": round(
            total_option_market_trade_value, 2
        ),
        "discovered_option_roots": sorted(discovered_roots),
        "bases": output,
        "option_burning": option_burning,
        "put_options": put_options,
    }


@app.route("/option-bases")
def get_option_bases():
    try:
        rows = fetch_market_watch_rows()
        option_mapping = build_dynamic_option_mapping(rows)
        active_roots = {
            option_symbol_root(fields[2])
            for row in rows
            if len(fields := row.split(",")) >= 4
            and is_option_description(fields[3])
        }
        bases = sorted({
            option_mapping[root]
            for root in active_roots
            if root in option_mapping
        })
        return jsonify({
            "bases": bases,
            "mapping": {
                root: option_mapping[root]
                for root in active_roots
                if root in option_mapping
            },
        })
    except requests.RequestException:
        return jsonify({"bases": sorted(set(mapping.values()))})


@app.route("/market-expectations")
def get_market_expectations():
    use_saved_trade_value = request.args.get(
        "use_saved_value", default="0", type=str
    ).strip().lower() in {"1", "true", "yes", "on"}

    try:
        return Response(
            json.dumps(
                generate_market_expectations(use_saved_trade_value),
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except RuntimeError as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
        )


@app.route("/stocks")
def get_stocks():
    try:
        force_refresh = request.args.get(
            "refresh", default="0", type=str
        ).strip().lower() in {"1", "true", "yes", "on"}
        use_saved_data = request.args.get(
            "use_saved_data", default="0", type=str
        ).strip().lower() in {"1", "true", "yes", "on"}
        payload = get_stock_catalog(
            force_refresh=force_refresh and not use_saved_data,
            use_saved_data=use_saved_data,
        )

        return Response(
            json.dumps(payload, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
        )


@app.route("/all-stocks")
def get_all_stocks():
    try:
        force_refresh = request.args.get(
            "refresh",
            default="0",
            type=str,
        ).strip().lower() in {"1", "true", "yes", "on"}
        payload = get_all_stock_catalog(
            check_refresh=True,
            force_refresh=force_refresh,
        )
        return Response(
            json.dumps(payload, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (FileNotFoundError, ValueError, OSError, RuntimeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/all-stocks/history")
def get_all_stock_history():
    try:
        trade_date = request.args.get("date", default="", type=str).strip()
        symbol = request.args.get("symbol", default="", type=str).strip()
        if trade_date:
            datetime.strptime(trade_date, "%Y-%m-%d")
        snapshots, selected_date = read_all_stock_daily_snapshots(
            trade_date=trade_date or None,
            symbol=symbol or None,
        )
        return Response(
            json.dumps(
                {
                    "date": selected_date,
                    "count": len(snapshots),
                    "snapshots": snapshots,
                },
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except ValueError:
        return Response(
            json.dumps(
                {"error": "تاریخ باید با قالب YYYY-MM-DD ارسال شود."},
                ensure_ascii=False,
            ),
            status=400,
            content_type="application/json; charset=utf-8",
        )
    except (FileNotFoundError, OSError, RuntimeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
        )


@app.route("/stocks/history")
def get_stock_history():
    try:
        trade_date = request.args.get("date", default="", type=str).strip()
        symbol = request.args.get("symbol", default="", type=str).strip()
        if trade_date:
            datetime.strptime(trade_date, "%Y-%m-%d")

        snapshots, selected_date = read_daily_stock_snapshots(
            trade_date=trade_date or None,
            symbol=symbol or None,
        )
        return Response(
            json.dumps(
                {
                    "date": selected_date,
                    "count": len(snapshots),
                    "snapshots": snapshots,
                },
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except ValueError:
        return Response(
            json.dumps(
                {"error": "تاریخ باید با قالب YYYY-MM-DD ارسال شود."},
                ensure_ascii=False,
            ),
            status=400,
            content_type="application/json; charset=utf-8",
        )
    except (FileNotFoundError, OSError, RuntimeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
        )


@app.route("/stocks/metric-history")
def get_stock_metric_history():
    try:
        symbol = request.args.get("symbol", default="", type=str).strip()
        metric = request.args.get("metric", default="", type=str).strip()
        limit = request.args.get("limit", default=365, type=int)
        points = read_stock_metric_history(symbol, metric, limit)
        return Response(
            json.dumps(
                {
                    "symbol": symbol,
                    "metric": metric,
                    "label": STOCK_HISTORY_METRICS[metric],
                    "count": len(points),
                    "points": points,
                },
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (TypeError, ValueError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-watchlist", methods=["GET", "POST"])
def stock_watchlist_collection():
    try:
        warning = None
        snapshot_metadata = {}
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            added_row = add_stock_watchlist_symbol(body.get("symbol"))
            rows = read_stock_watchlist()
            status = 201
        else:
            force_refresh = request.args.get(
                "refresh", default="0", type=str
            ).strip().lower() in {"1", "true", "yes", "on"}
            use_saved_data = request.args.get(
                "use_saved_data", default="0", type=str
            ).strip().lower() in {"1", "true", "yes", "on"}
            if use_saved_data:
                rows, snapshot_metadata = apply_latest_stock_snapshots(
                    read_stock_watchlist()
                )
                missing_snapshot_count = snapshot_metadata[
                    "missing_snapshot_count"
                ]
                if missing_snapshot_count:
                    warning = (
                        f"برای {missing_snapshot_count} نماد داده روزانه ذخیره "
                        "نشده و آخرین مقدار دیده‌بان نمایش داده شد."
                    )
            elif force_refresh:
                rows, errors = refresh_stock_watchlist()
                if errors:
                    warning = (
                        f"اطلاعات {len(errors)} نماد از آخرین داده ذخیره‌شده حفظ شد."
                    )
            else:
                rows = read_stock_watchlist()
                snapshot_metadata = {}
            added_row = None
            status = 200

        payload = {
            "count": len(rows),
            "stocks": rows,
            "updated_at": datetime.now(IRAN_TIMEZONE).isoformat(),
        }
        if added_row is not None:
            payload["added"] = added_row
        if warning:
            payload["warning"] = warning
        if request.method == "GET" and snapshot_metadata:
            payload.update(snapshot_metadata)

        return Response(
            json.dumps(payload, ensure_ascii=False),
            status=status,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except ValueError as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (requests.RequestException, OSError, RuntimeError, TypeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=502,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-watchlist/<path:symbol>", methods=["DELETE"])
def stock_watchlist_item(symbol):
    try:
        if not delete_stock_watchlist_symbol(symbol):
            return Response(
                json.dumps(
                    {"error": "نماد موردنظر در دیده‌بان پیدا نشد."},
                    ensure_ascii=False,
                ),
                status=404,
                content_type="application/json; charset=utf-8",
                headers={"Cache-Control": "no-store"},
            )

        rows = read_stock_watchlist()
        return Response(
            json.dumps(
                {"count": len(rows), "stocks": rows},
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (OSError, RuntimeError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-notes", methods=["GET", "POST"])
def stock_notes_collection():
    try:
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            note = create_stock_note(
                body.get("symbol"),
                body.get("text"),
                body.get("importance"),
            )
            return Response(
                json.dumps({"note": note}, ensure_ascii=False),
                status=201,
                content_type="application/json; charset=utf-8",
                headers={"Cache-Control": "no-store"},
            )

        symbol = request.args.get("symbol", default="", type=str).strip()
        notes = read_stock_notes(symbol=symbol or None)
        symbol_count = len({normalize_symbol(note["symbol"]) for note in notes})
        return Response(
            json.dumps(
                {
                    "count": len(notes),
                    "symbol_count": symbol_count,
                    "symbol": normalize_symbol(symbol) if symbol else None,
                    "notes": notes,
                },
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except ValueError as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (OSError, RuntimeError, sqlite3.Error) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-notes/<int:note_id>", methods=["PUT", "DELETE"])
def stock_note_item(note_id):
    try:
        if request.method == "DELETE":
            if not delete_stock_note(note_id):
                return Response(
                    json.dumps(
                        {"error": "یادداشت موردنظر پیدا نشد."},
                        ensure_ascii=False,
                    ),
                    status=404,
                    content_type="application/json; charset=utf-8",
                    headers={"Cache-Control": "no-store"},
                )
            return Response(
                json.dumps({"deleted": True, "id": note_id}),
                content_type="application/json; charset=utf-8",
                headers={"Cache-Control": "no-store"},
            )

        body = request.get_json(silent=True) or {}
        note = update_stock_note(
            note_id,
            body.get("text"),
            body.get("importance"),
        )
        if note is None:
            return Response(
                json.dumps(
                    {"error": "یادداشت موردنظر پیدا نشد."},
                    ensure_ascii=False,
                ),
                status=404,
                content_type="application/json; charset=utf-8",
                headers={"Cache-Control": "no-store"},
            )
        return Response(
            json.dumps({"note": note}, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except ValueError as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (OSError, RuntimeError, sqlite3.Error) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-strategy", methods=["POST"])
def stock_strategy_filter():
    try:
        payload = request.get_json(silent=True) or {}
        return Response(
            json.dumps(
                get_stock_strategy(
                    payload.get("rules") or {},
                    use_saved_data=bool(payload.get("use_saved_data")),
                    source=payload.get("source") or "featured",
                ),
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-strategy/export", methods=["POST"])
def stock_strategy_export():
    try:
        payload = request.get_json(silent=True) or {}
        use_saved_data = bool(payload.get("use_saved_data"))
        result = get_stock_strategy(
            payload.get("rules") or {},
            use_saved_data=use_saved_data,
            source=payload.get("source") or "featured",
        )
        output = build_stock_strategy_excel(
            result,
            use_saved_data=use_saved_data,
        )
        filename = datetime.now(IRAN_TIMEZONE).strftime(
            "strategy-export-%Y%m%d-%H%M.xlsx"
        )
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            max_age=0,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=400,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/stock-buy-queues")
def stock_buy_queue_filter():
    try:
        return Response(
            json.dumps(
                get_stock_buy_queue_summary(
                    limit=request.args.get("count", default=10, type=int),
                    source=request.args.get("source") or "all",
                    use_previous_day=request.args.get(
                        "use_previous_day", default="0", type=str
                    ).strip().lower() in {"1", "true", "yes", "on"},
                ),
                ensure_ascii=False,
            ),
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        return Response(
            json.dumps({"error": str(error)}, ensure_ascii=False),
            status=500,
            content_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )


@app.route("/watch-market/history")
def get_watch_market_history():
    limit = request.args.get("limit", default=30, type=int)
    snapshots = read_market_daily_snapshots(limit=limit)
    return Response(
        json.dumps(
            {"count": len(snapshots), "snapshots": snapshots},
            ensure_ascii=False,
        ),
        content_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.route("/watch-market")
def get_watch_market_charts():
    force_refresh = request.args.get(
        "refresh",
        default="0",
        type=str,
    ).strip().lower() in {"1", "true", "yes", "on"}
    return Response(
        json.dumps(
            get_watch_market(force=force_refresh),
            ensure_ascii=False,
        ),
        content_type="application/json; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.route("/")
def index():
    try:
        all_market_rows, _ = read_all_stock_database()
        if all_market_rows:
            start_stock_price_history_backfill(all_market_rows)
            start_stock_strategy_history_backfill(all_market_rows)
    except (OSError, RuntimeError, sqlite3.Error):
        # Price-history backfill is auxiliary and must never block the UI.
        pass
    return Response(
        render_template("indextest.html"),
        content_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.route("/data")
def get_data():
    data_source_mode = request.args.get(
        "data_source", default="live", type=str
    ).strip().lower()
    if data_source_mode not in {
        "live", "saved_trade", "saved_trade_orders"
    }:
        data_source_mode = "live"

    try:
        data = generate_data(
            use_saved_trade_value=(data_source_mode != "live")
        )
    except RuntimeError as error:
        return Response(
            json.dumps(
                {"error": str(error)},
                ensure_ascii=False
            ),
            status=400,
            content_type="application/json; charset=utf-8"
        )

    return Response(
        json.dumps(data, ensure_ascii=False),
        content_type="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.route("/spread-data")
def get_spread_data():

    base_symbol = normalize_symbol(request.args.get(
        "base_symbol",
        default="",
        type=str
    ))

    value_input = request.args.get(
        "value",
        default="",
        type=str
    ).strip()

    data_source_mode = request.args.get(
        "data_source", default="live", type=str
    ).strip().lower()
    if data_source_mode not in {
        "live", "saved_trade", "saved_trade_orders"
    }:
        data_source_mode = "live"


    days_input = request.args.get(
        "days",
        default="",
        type=str
    ).strip()

    days_operator = request.args.get(
        "days_operator",
        default="",
        type=str
    ).strip()

    # انتخاب نماد پایه اجباری است تا برای همه نمادها
    # درخواست BestLimits ارسال نشود.
    if not base_symbol:
        return Response(
        json.dumps(
            data,
            ensure_ascii=False
        ),
        content_type=(
            "application/json; "
            "charset=utf-8"
        ),
        headers={
            "Cache-Control":
                "no-store, no-cache, must-revalidate, max-age=0",

            "Pragma":
                "no-cache",

            "Expires":
                "0"
        }
    )

    min_trade_value = None
    days_value = None

    # عدد واردشده در ارزش معاملات در 10,000,000 ضرب می‌شود.
    if value_input:
        try:
            min_trade_value = float(value_input) * 10_000_000

        except ValueError:
            return Response(
                json.dumps(
                    {"error": "مقدار ارزش معاملات نامعتبر است."},
                    ensure_ascii=False
                ),
                status=400,
                content_type="application/json; charset=utf-8"
            )

    if days_input:
        try:
            days_value = int(days_input)

        except ValueError:
            return Response(
                json.dumps(
                    {"error": "تعداد روز تا سررسید نامعتبر است."},
                    ensure_ascii=False
                ),
                status=400,
                content_type="application/json; charset=utf-8"
            )

        if days_operator not in {"gte", "lte", "eq"}:
            return Response(
                json.dumps(
                    {
                        "error": (
                            "برای فیلتر روز تا سررسید، "
                            "یکی از دکمه‌های بالا، پایین یا مساوی را انتخاب کنید."
                        )
                    },
                    ensure_ascii=False
                ),
                status=400,
                content_type="application/json; charset=utf-8"
            )

    try:

        data = generate_spread_data(
            base_symbol=base_symbol,
            min_trade_value=min_trade_value,
            days_value=days_value,
            days_operator=days_operator,
            data_source_mode=data_source_mode
        )

    except RuntimeError as error:

        return Response(
            json.dumps(
                {
                    "error":
                        str(error)
                },
                ensure_ascii=False
            ),
            status=400,
            content_type=(
                "application/json; "
                "charset=utf-8"
            )
        )

    return Response(
        json.dumps(data, ensure_ascii=False),
        content_type="application/json; charset=utf-8"
    )

if __name__ == "__main__":
    dashboard_port = int(
        os.environ.get("STOCK_DASHBOARD_PORT", "5050")
    )
    dashboard_debug = (
        os.environ.get("STOCK_DASHBOARD_DEBUG", "0") == "1"
    )

    app.run(
        host="0.0.0.0",
        port=dashboard_port,
        debug=dashboard_debug
    )
