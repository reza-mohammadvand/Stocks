import gc
import os
import tempfile
import unittest
from datetime import datetime

import app as stock_app


class StockSnapshotTests(unittest.TestCase):
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
    def row(symbol, closing_price, market_date="2026-10-19"):
        return {
            "symbol": symbol,
            "market_date": market_date,
            "closing_price": closing_price,
        }

    def test_standard_and_extended_session_snapshot_rules(self):
        standard = self.row("فولاد", 100)
        extended = self.row("عیار", 200)

        result = stock_app.save_daily_stock_snapshots(
            [standard, extended],
            self.at(12, 29),
        )
        self.assertEqual(result["inserted_count"], 0)

        result = stock_app.save_daily_stock_snapshots(
            [standard, extended],
            self.at(12, 30),
        )
        self.assertEqual(result["inserted_count"], 1)

        stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 150), extended],
            self.at(17, 59),
        )
        snapshots, _ = stock_app.read_daily_stock_snapshots("2026-10-19")
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["data"]["closing_price"], 100)

        stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 175), extended],
            self.at(18, 0),
        )
        result = stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 190), self.row("عیار", 250)],
            self.at(18, 10),
        )
        self.assertEqual(result["inserted_count"], 0)

        snapshots, _ = stock_app.read_daily_stock_snapshots("2026-10-19")
        by_symbol = {snapshot["symbol"]: snapshot for snapshot in snapshots}
        self.assertEqual(len(by_symbol), 2)
        self.assertEqual(by_symbol["فولاد"]["data"]["closing_price"], 100)
        self.assertEqual(by_symbol["عیار"]["data"]["closing_price"], 200)
        self.assertEqual(by_symbol["عیار"]["captured_at"], self.at(18, 0).isoformat())
        self.assertEqual(by_symbol["فولاد"]["session_type"], "standard")
        self.assertEqual(by_symbol["عیار"]["session_type"], "extended")

        with stock_app.app.test_client() as client:
            response = client.get(
                "/stocks/history?date=2026-10-19&symbol=عیار"
            )
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["snapshots"][0]["symbol"], "عیار")

            invalid_response = client.get("/stocks/history?date=2026-19-10")
            self.assertEqual(invalid_response.status_code, 400)

    def test_stale_market_date_is_not_archived(self):
        result = stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 100, market_date="2026-10-18")],
            self.at(13, 0),
        )
        self.assertEqual(result["inserted_count"], 0)
        snapshots, selected_date = stock_app.read_daily_stock_snapshots()
        self.assertEqual(snapshots, [])
        self.assertIsNone(selected_date)


if __name__ == "__main__":
    unittest.main()
