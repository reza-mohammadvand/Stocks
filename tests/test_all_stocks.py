import gc
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import app as stock_app


class AllStockDailyTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_file = stock_app.STOCK_DATABASE_FILE
        self.original_database_ready = stock_app.stock_database_ready
        stock_app.STOCK_DATABASE_FILE = os.path.join(
            self.temporary_directory.name,
            "stocks.db",
        )
        stock_app.stock_database_ready = False

    def tearDown(self):
        stock_app.STOCK_DATABASE_FILE = self.original_database_file
        stock_app.stock_database_ready = self.original_database_ready
        gc.collect()
        self.temporary_directory.cleanup()

    @staticmethod
    def at(hour, minute):
        return datetime(
            2026,
            10,
            19,
            hour,
            minute,
            tzinfo=stock_app.IRAN_TIMEZONE,
        )

    @staticmethod
    def market_row(ins_code, instrument_id, symbol, name, category):
        fields = [""] * 26
        fields[0] = ins_code
        fields[1] = instrument_id
        fields[2] = symbol
        fields[3] = name
        fields[6] = "1000"
        fields[7] = "1010"
        fields[9] = "250000"
        fields[10] = "252500000"
        fields[13] = "990"
        fields[21] = "5000000000"
        fields[25] = category
        return ",".join(fields)

    def test_market_watch_parser_keeps_only_equities_without_number_suffix(self):
        response_text = ";".join([
            self.market_row(
                "10000000000000001", "IRO1TEST0001", "آزمون", "شرکت آزمون", "N1"
            ),
            self.market_row(
                "10000000000000002", "IRT3FIXD0001", "ثابت", "صندوق درآمد ثابت", "1A"
            ),
            self.market_row(
                "10000000000000003", "IRTKGOLD0001", "طلا", "صندوق کالایی طلا", "QS"
            ),
            self.market_row(
                "10000000000000004", "IRO9OPTN0001", "ضآزمون", "اختیار خرید", "3A"
            ),
            self.market_row(
                "10000000000000005", "IRB3BOND0001", "اخزا", "اسناد خزانه", "17"
            ),
            self.market_row(
                "10000000000000006", "IRO1TEST0002", "آزمون12", "نماد فرعی", "N1"
            ),
        ])

        rows = stock_app.parse_all_stock_market_watch(response_text)

        self.assertEqual([row["symbol"] for row in rows], ["آزمون"])
        self.assertEqual(rows[0]["session_type"], "standard")
        self.assertEqual(rows[0]["share_count"], 5_000_000_000)

    def test_due_phases_are_completed_only_once_per_tehran_day(self):
        self.assertEqual(stock_app.all_stock_due_phases(self.at(12, 29), {}), [])
        self.assertEqual(
            stock_app.all_stock_due_phases(self.at(12, 30), {}),
            ["standard"],
        )
        self.assertEqual(
            stock_app.all_stock_due_phases(self.at(18, 0), {}),
            ["standard"],
        )
        metadata = {"standard_completed_date": "2026-10-19"}
        self.assertEqual(
            stock_app.all_stock_due_phases(self.at(18, 0), metadata),
            [],
        )
        self.assertEqual(stock_app.all_stock_due_phases(self.at(23, 0), metadata), [])

    def test_phase_is_published_and_archived_atomically(self):
        row = {
            "position": 4,
            "symbol": "آزمون",
            "category": "N1",
            "session_type": "standard",
            "market_date": "2026-10-19",
            "closing_price": 1200,
            "last_price": 1210,
            "trade_value": 250_000_000,
        }

        result = stock_app.save_all_stock_phase([row], "standard", self.at(12, 30))
        rows, metadata = stock_app.read_all_stock_database()
        snapshots, selected_date = stock_app.read_all_stock_daily_snapshots()

        self.assertEqual(result["snapshot_count"], 1)
        self.assertEqual(rows[0]["symbol"], "آزمون")
        self.assertEqual(rows[0]["snapshot_date"], "2026-10-19")
        self.assertEqual(metadata["standard_completed_date"], "2026-10-19")
        self.assertEqual(selected_date, "2026-10-19")
        self.assertEqual(snapshots[0]["data"]["closing_price"], 1200)
        self.assertEqual(
            stock_app.all_stock_due_phases(self.at(17, 0), metadata),
            [],
        )

    def test_partial_close_row_keeps_previous_static_and_client_fields(self):
        fresh = [{
            "symbol": "آزمون",
            "position": 0,
            "category": "N1",
            "session_type": "standard",
            "market_date": "2026-10-19",
            "last_price": 1300,
            "industry": None,
            "real_buy_volume": None,
        }]
        previous = [{
            "symbol": "آزمون",
            "industry": "محصولات آزمون",
            "real_buy_volume": 5000,
            "last_price": 1200,
        }]

        merged = stock_app.merge_all_stock_rows(fresh, previous)

        self.assertEqual(merged[0]["last_price"], 1300)
        self.assertEqual(merged[0]["industry"], "محصولات آزمون")
        self.assertEqual(merged[0]["real_buy_volume"], 5000)

    def test_complete_market_row_prefers_authoritative_closing_quote(self):
        instrument = {
            "position": 0,
            "symbol": "TEST",
            "company": "Company",
            "category": "N1",
            "session_type": "standard",
            "ins_code": "123",
            "market_date": "2026-11-07",
            "price": 100,
            "last_price": 100,
            "closing_price": 100,
            "yesterday_price": 95,
            "trade_value": 100,
            "trade_volume": 1,
            "share_count": 1_000,
        }
        instrument_info = {
            "instrumentInfo": {
                "insCode": "123",
                "lVal18AFC": "TEST",
                "lVal30": "Company",
                "dEven": 20261108,
                "zTitad": 1_000,
                "qTotTran5JAvg": 500,
                "kAjCapValCpsIdx": 20,
                "sector": {"lSecVal": "Industry"},
                "staticThreshold": {
                    "psGelStaMax": 220,
                    "psGelStaMin": 180,
                },
            },
        }
        zero_client_type = {
            key: 0
            for key in (
                "real_buy_volume",
                "real_buy_count",
                "legal_buy_volume",
                "legal_buy_count",
                "real_sell_volume",
                "real_sell_count",
                "legal_sell_volume",
                "legal_sell_count",
            )
        }
        zero_order_book = {
            key: 0
            for key in (
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
        }

        with (
            patch.object(
                stock_app,
                "fetch_tsetmc_json",
                return_value=instrument_info,
            ),
            patch.object(
                stock_app,
                "fetch_closing_data",
                return_value={
                    "market_date": "2026-11-08",
                    "price": 205,
                    "last_price": 200,
                    "closing_price": 195,
                    "yesterday_price": 190,
                    "trade_value": 9_000,
                    "trade_volume": 45,
                },
            ),
            patch.object(
                stock_app,
                "fetch_stock_client_type",
                return_value=zero_client_type,
            ),
            patch.object(
                stock_app,
                "fetch_stock_order_book_totals",
                return_value=zero_order_book,
            ),
        ):
            row, warnings = stock_app.fetch_all_stock_row(instrument)

        self.assertEqual(warnings, [])
        self.assertEqual(row["market_date"], "2026-11-08")
        self.assertEqual(row["last_price"], 200)
        self.assertEqual(row["closing_price"], 195)
        self.assertEqual(row["trade_value"], 9_000)
        self.assertEqual(row["daily_upper_price"], 220)
        self.assertEqual(row["price_power_status"], "positive")

    def test_stale_market_day_is_checked_without_replacing_finalized_rows(self):
        current_row = {
            "position": 0,
            "symbol": "آزمون",
            "category": "N1",
            "session_type": "standard",
            "market_date": "2026-10-19",
            "closing_price": 1200,
        }
        stock_app.save_all_stock_phase([current_row], "standard", self.at(12, 30))
        stale_row = {
            **current_row,
            "closing_price": 999,
        }

        result = stock_app.save_all_stock_phase(
            [stale_row],
            "standard",
            datetime(2026, 10, 20, 12, 30, tzinfo=stock_app.IRAN_TIMEZONE),
        )
        rows, metadata = stock_app.read_all_stock_database()

        self.assertEqual(result["row_count"], 0)
        self.assertEqual(rows[0]["closing_price"], 1200)
        self.assertEqual(metadata["standard_completed_date"], "2026-10-20")

    def test_manual_publish_updates_current_rows_without_archiving(self):
        row = {
            "position": 0,
            "symbol": "آزمون",
            "category": "N1",
            "session_type": "standard",
            "market_date": "2026-10-19",
            "closing_price": 1400,
        }

        result = stock_app.publish_all_stock_current_phase(
            [row],
            "standard",
            self.at(11, 0),
        )
        rows, metadata = stock_app.read_all_stock_database()
        snapshots, selected_date = stock_app.read_all_stock_daily_snapshots()

        self.assertTrue(result["published"])
        self.assertEqual(rows[0]["closing_price"], 1400)
        self.assertIsNone(selected_date)
        self.assertEqual(snapshots, [])
        self.assertNotIn("standard_completed_date", metadata)
        self.assertEqual(metadata["last_manual_update"], self.at(11, 0).isoformat())

    def test_manual_publish_preserves_rows_when_market_day_is_stale(self):
        current_row = {
            "position": 0,
            "symbol": "آزمون",
            "category": "N1",
            "session_type": "standard",
            "market_date": "2026-10-19",
            "closing_price": 1400,
        }
        stock_app.publish_all_stock_current_phase(
            [current_row],
            "standard",
            self.at(11, 0),
        )

        stale_result = stock_app.publish_all_stock_current_phase(
            [{**current_row, "closing_price": 900}],
            "standard",
            datetime(2026, 10, 20, 11, 0, tzinfo=stock_app.IRAN_TIMEZONE),
        )
        rows, _ = stock_app.read_all_stock_database()

        self.assertFalse(stale_result["published"])
        self.assertEqual(rows[0]["closing_price"], 1400)


if __name__ == "__main__":
    unittest.main()
