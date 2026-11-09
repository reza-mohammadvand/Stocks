import gc
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import app as stock_app


class StockWatchlistTests(unittest.TestCase):
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

    def test_watchlist_rows_persist_update_and_delete(self):
        stock_app.save_stock_watchlist_row({
            "symbol": "فولاد",
            "company": "فولاد مبارکه",
            "market_value": 100,
        })
        stock_app.save_stock_watchlist_row({
            "symbol": "فولاد",
            "company": "فولاد مبارکه",
            "market_value": 200,
        })

        rows = stock_app.read_stock_watchlist()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "فولاد")
        self.assertEqual(rows[0]["market_value"], 200)

        self.assertTrue(stock_app.delete_stock_watchlist_symbol("فولاد"))
        self.assertEqual(stock_app.read_stock_watchlist(), [])
        self.assertFalse(stock_app.delete_stock_watchlist_symbol("فولاد"))

    def test_watchlist_rejects_rights_symbols(self):
        with self.assertRaisesRegex(ValueError, "حق‌تقدم"):
            stock_app.save_stock_watchlist_row({
                "symbol": "پکویرح",
                "company": "حق تقدم پکویر",
            })
        self.assertEqual(stock_app.read_stock_watchlist(), [])

    def test_watchlist_api_add_get_and_delete(self):
        resolved_row = {
            "symbol": "آزمایشی",
            "ins_code": "12345",
            "company": "شرکت آزمایشی",
            "industry": "آزمایش",
            "market_value": 1_000_000,
            "trade_value": 50_000,
        }

        with (
            patch.object(stock_app, "fetch_stock_market_map", return_value={}),
            patch.object(stock_app, "fetch_stock_row", return_value=resolved_row),
            stock_app.app.test_client() as client,
        ):
            response = client.post(
                "/stock-watchlist",
                json={"symbol": "آزمایشی"},
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.get_json()["count"], 1)

            persisted = client.get("/stock-watchlist")
            self.assertEqual(persisted.status_code, 200)
            self.assertEqual(persisted.get_json()["stocks"][0]["symbol"], "آزمایشی")

            duplicate = client.post(
                "/stock-watchlist",
                json={"symbol": "آزمایشی"},
            )
            self.assertEqual(duplicate.status_code, 400)

            deleted = client.delete("/stock-watchlist/آزمایشی")
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(deleted.get_json()["count"], 0)

    def test_refresh_keeps_stored_fields_when_online_row_is_partial(self):
        stock_app.save_stock_watchlist_row({
            "symbol": "فولاد",
            "company": "فولاد مبارکه",
            "market_value": 100,
            "closing_price": 10,
        })
        with patch.object(
            stock_app,
            "fetch_live_stock_catalog",
            return_value=([{"symbol": "فولاد", "closing_price": 20}], []),
        ):
            rows, errors = stock_app.refresh_stock_watchlist()

        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["closing_price"], 20)
        self.assertEqual(rows[0]["company"], "فولاد مبارکه")
        self.assertEqual(rows[0]["market_value"], 100)

    def test_stock_row_keeps_fresh_quote_when_optional_feeds_fail(self):
        fallback = {
            "symbol": "TEST",
            "ins_code": "123",
            "company": "Stored company",
            "industry": "Stored industry",
            "share_count": 1_000,
            "daily_upper_price": 220,
            "daily_lower_price": 180,
            "monthly_average_volume": 500,
        }
        instrument = {
            "instrumentInfo": {
                "insCode": "123",
                "lVal18AFC": "TEST",
                "lVal30": "Fresh company",
                "dEven": 20261108,
                "zTitad": 1_000,
                "qTotTran5JAvg": 600,
                "kAjCapValCpsIdx": 25,
                "sector": {"lSecVal": "Fresh industry"},
                "staticThreshold": {
                    "psGelStaMax": 220,
                    "psGelStaMin": 180,
                },
            },
        }
        closing = {
            "market_date": "2026-11-08",
            "price": 205,
            "last_price": 200,
            "closing_price": 195,
            "yesterday_price": 190,
            "trade_value": 9_000,
            "trade_volume": 45,
        }

        with (
            patch.object(stock_app, "fetch_tsetmc_json", return_value=instrument),
            patch.object(stock_app, "find_stock_instrument") as search,
            patch.object(stock_app, "fetch_closing_data", return_value=closing),
            patch.object(
                stock_app,
                "fetch_stock_client_type",
                side_effect=stock_app.requests.RequestException("client failed"),
            ),
            patch.object(
                stock_app,
                "fetch_stock_order_book_totals",
                side_effect=stock_app.requests.RequestException("book failed"),
            ),
        ):
            row = stock_app.fetch_stock_row(
                "TEST",
                {
                    "TEST": {
                        "price": 100,
                        "last_price": 100,
                        "closing_price": 100,
                        "trade_value": 100,
                        "trade_volume": 1,
                    },
                },
                fallback,
            )

        search.assert_not_called()
        self.assertEqual(row["last_price"], 200)
        self.assertEqual(row["closing_price"], 195)
        self.assertEqual(row["trade_value"], 9_000)
        self.assertEqual(row["price_power_status"], "positive")
        self.assertEqual(row["daily_upper_price"], 220)
        self.assertIsNone(row["real_buy_volume"])
        self.assertIsNone(row["order_book_buy_value"])
        self.assertIn("client-type", row["_fetch_warning"])
        self.assertIn("best-limits", row["_fetch_warning"])

    def test_watchlist_api_can_show_latest_daily_snapshot(self):
        stock_app.save_stock_watchlist_row({
            "symbol": "فولاد",
            "company": "فولاد مبارکه",
            "closing_price": 999,
            "market_date": "2026-10-19",
        })
        stock_app.save_daily_stock_snapshots(
            [{
                "symbol": "فولاد",
                "company": "فولاد مبارکه",
                "closing_price": 123,
                "market_date": "2026-10-19",
            }],
            datetime(
                2026,
                10,
                19,
                12,
                30,
                tzinfo=stock_app.IRAN_TIMEZONE,
            ),
        )

        with stock_app.app.test_client() as client:
            response = client.get("/stock-watchlist?use_saved_data=1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["data_source"], "daily_snapshot")
        self.assertEqual(payload["stocks"][0]["closing_price"], 123)
        self.assertEqual(payload["missing_snapshot_count"], 0)


if __name__ == "__main__":
    unittest.main()
