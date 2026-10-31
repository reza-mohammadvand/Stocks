import gc
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import app as stock_app


class WatchMarketOverviewTests(unittest.TestCase):
    def test_option_leverage_and_call_status(self):
        self.assertEqual(
            stock_app.calculate_option_leverage(1_200, 100),
            12,
        )
        self.assertIsNone(stock_app.calculate_option_leverage(1_200, 0))
        self.assertEqual(stock_app.calculate_call_option_status(1_200, 1_000), "ITM")
        self.assertEqual(stock_app.calculate_call_option_status(1_000, 1_000), "ATM")
        self.assertEqual(stock_app.calculate_call_option_status(800, 1_000), "OTM")

    def test_parse_rahavard_quote_uses_last_trade_and_converts_to_toman(self):
        config = {
            "key": "nimai_dollar",
            "name": "دلار نیمایی",
            "unit": "تومان",
            "divisor": 10,
            "tone": "currency",
            "source_url": "https://rahavard365.com/asset/43157",
        }
        payload = {
            "last_trade": {
                "end_date_time": "2026-10-19T08:06:05+03:30",
                "close_price": 1_827_334,
                "close_price_change": 5_466,
                "close_price_change_percent": 0.003,
            },
            "trades": [
                {
                    "date_time": "2026-10-18T08:16:04+03:30",
                    "close_price": 1_821_868,
                }
            ],
        }

        result = stock_app.parse_rahavard_quote(payload, config)

        self.assertEqual(result["price"], 182_733.4)
        self.assertEqual(result["change"], 546.6)
        self.assertAlmostEqual(result["change_percent"], 0.3)
        self.assertEqual(result["market_time"], "2026-10-19T08:06:05+03:30")

    def test_parse_rahavard_quote_can_prefer_latest_daily_trade(self):
        config = {
            "key": "dollar",
            "name": "دلار آمریکا",
            "unit": "تومان",
            "divisor": 10,
            "prefer_daily_trade": True,
            "source_url": "https://rahavard365.com/asset/2",
        }
        payload = {
            "last_trade": {},
            "header_last_trade": {"real_close_price": 0},
            "trades": [
                {
                    "date_time": "2026-10-18T20:15:00+03:30",
                    "close_price": 2_628_000,
                    "close_price_change": -10_000,
                    "close_price_change_percent": -0.0038,
                }
            ],
        }

        result = stock_app.parse_rahavard_quote(payload, config)

        self.assertEqual(result["price"], 262_800)
        self.assertEqual(result["change"], -1_000)
        self.assertAlmostEqual(result["change_percent"], -0.38)

    def test_normalize_live_quote_uses_broadcast_last_trade(self):
        config = {
            "key": "dollar",
            "name": "دلار آمریکا",
            "unit": "تومان",
            "divisor": 10,
            "source_url": "https://rahavard365.com/asset/2",
        }
        result = stock_app.normalize_rahavard_live_quote(
            {
                "price": 2_650_000,
                "price_change": 12_000,
                "change_percent": 0.00455,
                "market_time": "2026-10-19T14:15:00+03:30",
            },
            config,
        )

        self.assertEqual(result["price"], 265_000)
        self.assertEqual(result["change"], 1_200)
        self.assertAlmostEqual(result["change_percent"], 0.455)
        self.assertEqual(result["source"], "rahavard365-live")

    def test_live_required_asset_never_falls_back_to_historical_trade(self):
        config = {
            "key": "dollar",
            "asset_id": 2,
            "name": "دلار آمریکا",
            "unit": "تومان",
            "divisor": 10,
            "live_required": True,
            "source_url": "https://rahavard365.com/asset/2",
        }
        with patch.object(stock_app.requests, "get") as request_get:
            with self.assertRaises(ValueError):
                stock_app.fetch_rahavard_watch_asset(config, live_quotes={})
            request_get.assert_not_called()

    def test_rahavard_asset_prefers_newer_api_quote_over_stale_live_quote(self):
        config = {
            "key": "gold_ounce",
            "asset_id": 2016,
            "name": "gold ounce",
            "unit": "USD",
            "divisor": 1,
            "source_url": "https://rahavard365.com/asset/2016",
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "last_trade": {
                    "end_date_time": "2026-10-31T01:00:01+03:30",
                    "close_price": 3_876,
                    "close_price_change": -4,
                    "close_price_change_percent": -0.001,
                },
            },
        }

        with patch.object(stock_app.requests, "get", return_value=response):
            result = stock_app.fetch_rahavard_watch_asset(
                config,
                live_quotes={
                    2016: {
                        "price": 4_048,
                        "price_change": -11,
                        "change_percent": -0.0027,
                        "market_time": "2026-10-28T15:04:30+03:30",
                    },
                },
            )

        self.assertEqual(result["price"], 3_876)
        self.assertEqual(result["source"], "rahavard365")

    def test_rahavard_asset_keeps_newer_live_quote(self):
        config = {
            "key": "nimai_dollar",
            "asset_id": 43157,
            "name": "NIMA dollar",
            "unit": "toman",
            "divisor": 10,
            "source_url": "https://rahavard365.com/asset/43157",
        }
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {
                "last_trade": {
                    "end_date_time": "2026-10-31T08:09:30+03:30",
                    "close_price": 1_871_664,
                },
            },
        }

        with patch.object(stock_app.requests, "get", return_value=response):
            result = stock_app.fetch_rahavard_watch_asset(
                config,
                live_quotes={
                    43157: {
                        "price": 1_875_000,
                        "market_time": "2026-10-31T08:10:00+03:30",
                    },
                },
            )

        self.assertEqual(result["price"], 187_500)
        self.assertEqual(result["source"], "rahavard365-live")

    def test_global_copper_is_converted_from_pounds_to_metric_tons(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "chart": {
                "result": [{
                    "meta": {
                        "regularMarketPrice": 4.5,
                        "regularMarketChange": 0.1,
                        "regularMarketChangePercent": 2.27,
                        "regularMarketTime": 1_798_000_000,
                    },
                }],
            },
        }
        with patch.object(stock_app.requests, "get", return_value=response):
            quote = stock_app.fetch_global_copper_quote()

        self.assertEqual(quote["unit"], "دلار/تن")
        self.assertAlmostEqual(
            quote["price"],
            round(4.5 * stock_app.POUNDS_PER_METRIC_TON, 2),
        )
        self.assertAlmostEqual(
            quote["change"],
            round(0.1 * stock_app.POUNDS_PER_METRIC_TON, 2),
        )

    def test_bourseeye_ime_commodity_quotes_are_parsed_per_kilogram(self):
        rows = [
            {
                "tag_id": 1511,
                "code": "SteelRebar",
                "name": "میلگرد",
                "price_rials": "1114800.0",
                "price_date": "2026-10-27",
                "price_change_percent": "0.28",
                "unit_price_rials": "1114800",
                "unit": "کیلوگرم",
            },
            {
                "tag_id": 1512,
                "code": "ZincIngot",
                "name": "شمش روی",
                "price_rials": "7991000.0",
                "price_date": "2026-10-27",
                "price_change_percent": "-0.59",
                "unit_price_rials": "7991000",
                "unit": "کیلوگرم",
            },
            {
                "tag_id": 1510,
                "code": "IronOrePlt",
                "name": "گندله سنگ آهن",
                "price_rials": "232040.0",
                "price_date": "2026-10-27",
                "price_change_percent": "3.40",
                "unit_price_rials": "232040",
                "unit": "کیلوگرم",
            },
        ]
        embedded = "".join(
            json.dumps(row, ensure_ascii=False).replace('"', r'\"')
            for row in rows
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.text = f"<script>{embedded}</script>"

        with patch.object(stock_app.requests, "get", return_value=response):
            quotes = stock_app.fetch_bourseeye_commodity_quotes()

        self.assertEqual(quotes["steel_rebar"]["price"], 111_480)
        self.assertEqual(quotes["zinc_ingot"]["price"], 799_100)
        self.assertEqual(quotes["iron_ore_pellet"]["price"], 23_204)
        self.assertEqual(quotes["steel_rebar"]["unit"], "تومان/کیلوگرم")
        self.assertEqual(quotes["zinc_ingot"]["change_percent"], -0.59)

    def test_latest_watch_market_value_skips_missing_tail_values(self):
        self.assertEqual(
            stock_app.latest_watch_market_value([10, 12.5, None]),
            12.5,
        )
        self.assertIsNone(stock_app.latest_watch_market_value([None, "bad"]))

    def test_industry_money_flows_are_parsed_and_sorted(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = json.dumps(
            [
                ["01", "زراعت", *([0] * 13), -30_000_000_000],
                ["13", "کانه‌های فلزی", *([0] * 13), 80_000_000_000],
                ["24", "محصولات شیمیایی", *([0] * 13), -120_000_000_000],
                ["gold-funds", "صندوق‌های طلا", *([0] * 13), 90_000_000_000],
                ["silver-funds", "صندوق‌های نقره", *([0] * 13), 70_000_000_000],
            ],
            ensure_ascii=False,
        ).encode("utf-8")
        with patch.object(stock_app.requests, "get", return_value=response):
            rows = stock_app.fetch_tradersarena_industry_money_flows()

        self.assertEqual(rows[0]["name"], "کانه‌های فلزی")
        self.assertEqual(rows[0]["value"], 8)
        self.assertEqual(rows[1]["value"], -3)
        self.assertEqual(rows[2]["value"], -12)
        self.assertEqual(len(rows), 3)

    def test_stock_trade_value_excludes_all_fund_categories(self):
        summary = {
            "m": [0, 900_000_000_000],
            "st": [0, 320_000_000_000],
            "sf": [0, 80_000_000_000],
            "nsf": [0, 400_000_000_000],
            "cf": [0, 100_000_000_000],
        }

        value = stock_app.extract_tradersarena_stock_trade_value(summary)

        self.assertEqual(value, 32)

    def test_fixed_income_flow_is_moved_to_its_dedicated_card(self):
        visible, dedicated = stock_app.split_dedicated_industry_money_flows([
            {"key": "13", "name": "فلزات", "value": -10},
            {
                "key": "fixed-income-funds",
                "name": "صندوق‌های درآمد ثابت",
                "value": 240.35,
            },
        ])

        self.assertEqual([item["key"] for item in visible], ["13"])
        self.assertEqual(dedicated["fixed_income"]["value"], 240.35)


class WatchMarketDailySnapshotTests(unittest.TestCase):
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

    def test_market_snapshot_upserts_latest_values_for_the_day(self):
        captured_at = datetime(
            2026,
            10,
            26,
            12,
            30,
            tzinfo=stock_app.IRAN_TIMEZONE,
        )
        payload = {
            "market_date": "1405/08/04",
            "total_market_trade_value": 12_345,
            "overview": {
                "prices": [{"key": "dollar", "price": 100_000}],
                "flows": [{"key": "stock_market", "value": 10}],
                "industry_flows": [{"key": "13", "name": "فلزات", "value": 5}],
            },
        }
        stock_app.save_market_daily_snapshot(payload, captured_at)

        payload["total_market_trade_value"] = 13_000
        payload["overview"]["prices"][0]["price"] = 101_500
        payload["overview"]["flows"][0]["value"] = 12
        stock_app.save_market_daily_snapshot(payload, captured_at.replace(hour=18))

        snapshots = stock_app.read_market_daily_snapshots()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["free_dollar_price"], 101_500)
        self.assertEqual(snapshots[0]["total_market_trade_value"], 13_000)
        self.assertEqual(snapshots[0]["money_flows"][0]["value"], 12)
        self.assertEqual(snapshots[0]["industry_flows"][0]["name"], "فلزات")

        with stock_app.app.test_client() as client:
            response = client.get("/watch-market/history?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)


if __name__ == "__main__":
    unittest.main()
