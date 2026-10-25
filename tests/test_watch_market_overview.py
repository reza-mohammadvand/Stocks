import unittest
from unittest.mock import patch

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

    def test_latest_watch_market_value_skips_missing_tail_values(self):
        self.assertEqual(
            stock_app.latest_watch_market_value([10, 12.5, None]),
            12.5,
        )
        self.assertIsNone(stock_app.latest_watch_market_value([None, "bad"]))


if __name__ == "__main__":
    unittest.main()
