import os
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request
import requests
import pandas as pd
import re
import jdatetime
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

# جلوگیری از خواندن/نوشتن همزمان فایل سفارشات
order_book_snapshot_lock = threading.Lock()


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


def fetch_market_watch_rows():
    response = requests.get(
        "https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx",
        timeout=15,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text.strip().split(";")


def generate_market_expectations(use_saved_trade_value=False):
    """Build non-visual option rows and expiry-level expectation summaries."""
    try:
        rows = fetch_market_watch_rows()
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
    discovered_roots = set()

    for row in rows:
        fields = row.split(",")
        if len(fields) < 25:
            continue

        ins_code = fields[0].strip()
        symbol = fields[2].strip()
        description = fields[3].strip()

        if not is_option_description(description, "call"):
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
            "symbol": symbol,
            "days_remaining": days_remaining,
            "open_interest": open_interest,
            "expiry_date": expiry_date,
            "trade_value": trade_value,
            "market_trade_value_share": market_trade_value_share,
            "strike": strike,
            "option_last_price": option_last_price,
            "base_price": base_price,
            "breakeven_distance": breakeven_distance,
            "monthly_return": monthly_return,
        })

    bases = {}

    for (base_symbol, expiry_date, days_remaining), option_rows in grouped.items():
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
            item["monthly_return"] = (
                round(item["monthly_return"], 2)
                if item["monthly_return"] is not None
                else None
            )

        bases.setdefault(base_symbol, []).append({
            "group_id": f"{base_symbol}-{expiry_date}",
            "days_remaining": days_remaining,
            "expiry_date": expiry_date,
            "total_trade_value": round(total_trade_value, 2),
            "weighted_average": (
                round(weighted_average, 2)
                if weighted_average is not None else None
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

    return {
        "generated_at": now.isoformat(),
        "trade_value_source": "snapshot" if use_snapshot else "live",
        "snapshot_date": snapshot.get("date", "") if snapshot else "",
        "total_option_market_trade_value": round(
            total_option_market_trade_value, 2
        ),
        "discovered_option_roots": sorted(discovered_roots),
        "bases": output,
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


@app.route("/")
def index():
    return render_template("indextest.html")


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
