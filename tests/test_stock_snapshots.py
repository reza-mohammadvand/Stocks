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
        standard["price_power"] = 1
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
        self.assertEqual(snapshots[0]["data"]["price_power"], 1)

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

    def test_latest_saved_mode_uses_each_symbols_newest_available_day(self):
        first_day_standard = self.row("فولاد", 100)
        first_day_extended = self.row("عیار", 200)
        stock_app.save_daily_stock_snapshots(
            [first_day_standard],
            self.at(12, 30),
        )
        stock_app.save_daily_stock_snapshots(
            [first_day_extended],
            self.at(18, 0),
        )

        second_day = datetime(
            2026,
            10,
            20,
            12,
            30,
            tzinfo=stock_app.IRAN_TIMEZONE,
        )
        stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 150, market_date="2026-10-20")],
            second_day,
        )

        snapshots = stock_app.read_latest_daily_stock_snapshots(
            ["فولاد", "عیار"]
        )
        by_symbol = {snapshot["symbol"]: snapshot for snapshot in snapshots}
        self.assertEqual(by_symbol["فولاد"]["trade_date"], "2026-10-20")
        self.assertEqual(by_symbol["فولاد"]["data"]["closing_price"], 150)
        self.assertEqual(by_symbol["عیار"]["trade_date"], "2026-10-19")
        self.assertEqual(by_symbol["عیار"]["data"]["closing_price"], 200)

        rows, metadata = stock_app.apply_latest_stock_snapshots([
            {"symbol": "فولاد", "closing_price": 999},
            {"symbol": "عیار", "closing_price": 999},
            {"symbol": "بدون‌آرشیو", "closing_price": 300},
        ])
        saved_rows = {row["symbol"]: row for row in rows}
        self.assertEqual(saved_rows["فولاد"]["closing_price"], 150)
        self.assertEqual(saved_rows["عیار"]["closing_price"], 200)
        self.assertEqual(saved_rows["بدون‌آرشیو"]["closing_price"], 300)
        self.assertEqual(metadata["saved_count"], 2)
        self.assertEqual(metadata["missing_snapshot_count"], 1)
        self.assertTrue(metadata["mixed_snapshot_dates"])

    def test_stocks_api_can_return_latest_saved_rows(self):
        stock_app.replace_stock_database(
            [{"symbol": "فولاد", "closing_price": 999}],
            self.at(12, 0).isoformat(),
            1,
        )
        stock_app.save_daily_stock_snapshots(
            [self.row("فولاد", 125)],
            self.at(12, 30),
        )

        with stock_app.app.test_client() as client:
            response = client.get("/stocks?use_saved_data=1")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["data_source"], "daily_snapshot")
        by_symbol = {row["symbol"]: row for row in payload["stocks"]}
        self.assertEqual(by_symbol["فولاد"]["closing_price"], 125)
        self.assertFalse(payload["refreshing"])

    def test_stock_metric_history_returns_daily_points_in_date_order(self):
        first_row = self.row("فولاد", 100)
        first_row["trade_value"] = 10_000_000_000
        stock_app.save_daily_stock_snapshots([first_row], self.at(12, 30))

        second_time = datetime(
            2026,
            10,
            20,
            12,
            30,
            tzinfo=stock_app.IRAN_TIMEZONE,
        )
        second_row = self.row(
            "فولاد",
            110,
            market_date="2026-10-20",
        )
        second_row["trade_value"] = 20_000_000_000
        stock_app.save_daily_stock_snapshots([second_row], second_time)

        with stock_app.app.test_client() as client:
            response = client.get(
                "/stocks/metric-history"
                "?symbol=فولاد&metric=trade_value&limit=365"
            )
            invalid = client.get(
                "/stocks/metric-history?symbol=فولاد&metric=unknown"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            [point["date"] for point in payload["points"]],
            ["2026-10-19", "2026-10-20"],
        )
        self.assertEqual(payload["points"][1]["value"], 20_000_000_000)
        self.assertEqual(invalid.status_code, 400)

    def test_calculate_stock_indicators(self):
        indicators = stock_app.calculate_stock_indicators({
            "last_price": 1_020,
            "closing_price": 1_000,
            "trade_value": 1_000_000_000,
            "trade_volume": 1_000,
            "share_count": 10_000,
            "floating_share_percent": 20,
            "real_buy_volume": 600,
            "legal_buy_volume": 400,
            "real_sell_volume": 400,
            "legal_sell_volume": 600,
            "real_buy_count": 3,
            "real_sell_count": 4,
        })

        self.assertEqual(indicators["trade_to_float_percent"], 50)
        self.assertEqual(indicators["real_money_flow"], 200_000_000)
        self.assertEqual(indicators["money_flow_quality"], 20)
        self.assertEqual(indicators["real_buy_per_capita"], 200_000_000)
        self.assertEqual(indicators["real_sell_per_capita"], 100_000_000)
        self.assertEqual(indicators["real_buy_power"], 2)
        self.assertEqual(indicators["price_power"], 1)

        self.assertEqual(
            stock_app.calculate_stock_indicators({
                "last_price": 980,
                "closing_price": 1_000,
            })["price_power"],
            -1,
        )
        self.assertEqual(
            stock_app.calculate_stock_indicators({
                "last_price": 1_000,
                "closing_price": 1_000,
            })["price_power"],
            0,
        )

        empty = stock_app.calculate_stock_indicators({})
        self.assertTrue(all(value is None for value in empty.values()))

    def test_manual_floating_share_overrides_survive_refresh_merge(self):
        rows = stock_app.merge_stock_rows(
            [
                "فزر", "سامان", "ومپنا", "شرانل", "کزغال",
                "اهرم", "توان", "موج", "جوانه کوچک",
                "شتاب", "جهش", "پالایش", "دارا یکم",
            ],
            [
                {"symbol": "فزر", "floating_share_percent": None},
                {"symbol": "سامان", "floating_share_percent": 99},
            ],
            [],
        )
        by_symbol = {row["symbol"]: row for row in rows}

        self.assertEqual(by_symbol["فزر"]["floating_share_percent"], 38)
        self.assertEqual(by_symbol["سامان"]["floating_share_percent"], 5.7)
        self.assertEqual(by_symbol["ومپنا"]["floating_share_percent"], 10)
        self.assertEqual(by_symbol["شرانل"]["floating_share_percent"], 11)
        self.assertEqual(by_symbol["کزغال"]["floating_share_percent"], 18)
        self.assertIsNone(by_symbol["اهرم"]["floating_share_percent"])
        self.assertIsNone(by_symbol["توان"]["floating_share_percent"])
        self.assertIsNone(by_symbol["موج"]["floating_share_percent"])
        self.assertIsNone(by_symbol["جوانه کوچک"]["floating_share_percent"])
        self.assertIsNone(by_symbol["شتاب"]["floating_share_percent"])
        self.assertIsNone(by_symbol["جهش"]["floating_share_percent"])
        self.assertIsNone(by_symbol["پالایش"]["floating_share_percent"])
        self.assertIsNone(by_symbol["دارا یکم"]["floating_share_percent"])


if __name__ == "__main__":
    unittest.main()
