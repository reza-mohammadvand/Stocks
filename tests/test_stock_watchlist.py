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
