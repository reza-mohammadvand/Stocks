import gc
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import app as stock_app


class MarketIndexHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_file = stock_app.STOCK_DATABASE_FILE
        self.original_database_ready = stock_app.stock_database_ready
        self.original_index_state = dict(stock_app.market_index_history_state)
        stock_app.STOCK_DATABASE_FILE = os.path.join(
            self.temporary_directory.name,
            "stocks.db",
        )
        stock_app.stock_database_ready = False
        stock_app.market_index_history_state.update({
            "last_backfill_date": None,
            "last_daily_attempt_date": None,
            "error": None,
        })

    def tearDown(self):
        stock_app.STOCK_DATABASE_FILE = self.original_database_file
        stock_app.stock_database_ready = self.original_database_ready
        stock_app.market_index_history_state.clear()
        stock_app.market_index_history_state.update(self.original_index_state)
        gc.collect()
        self.temporary_directory.cleanup()

    def test_history_parser_keeps_the_latest_requested_closes(self):
        payload = {
            "indexB2": [
                {"dEven": 20261101, "xNivInuClMresIbs": 100},
                {"dEven": 20261102, "xNivInuClMresIbs": 110},
                {"dEven": 20261103, "xNivInuClMresIbs": 120},
            ]
        }

        points = stock_app.parse_tsetmc_market_index_history(payload, 2)

        self.assertEqual(
            [point["trade_date"] for point in points],
            ["2026-11-02", "2026-11-03"],
        )
        self.assertEqual(points[-1]["closing_value"], 120)

    def test_daily_close_is_stored_once_after_market_close(self):
        captured_at = datetime(
            2026,
            11,
            10,
            12,
            31,
            tzinfo=stock_app.IRAN_TIMEZONE,
        )
        point = {
            "trade_date": "2026-11-10",
            "closing_value": 8_357_887.77,
        }
        with patch.object(
            stock_app,
            "fetch_market_index_last_day",
            return_value=point,
        ) as fetch:
            self.assertEqual(
                stock_app.save_daily_market_index_snapshot(captured_at),
                1,
            )
            self.assertEqual(
                stock_app.save_daily_market_index_snapshot(captured_at),
                0,
            )

        self.assertEqual(fetch.call_count, 1)
        stored = stock_app.read_market_index_history()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["trade_date"], "2026-11-10")
        self.assertEqual(stored[0]["source"], "daily_close")

    def test_both_industry_strategies_receive_same_period_index_growth(self):
        rows = [
            {
                "symbol": "الف۱",
                "company": "الف یک",
                "industry": "صنعت الف",
                "market_date": "2026-11-04",
                "closing_price": 100,
            },
            {
                "symbol": "الف۲",
                "company": "الف دو",
                "industry": "صنعت الف",
                "market_date": "2026-11-04",
                "closing_price": 200,
            },
        ]
        history = {
            stock_app.normalize_symbol("الف۱"): [
                {"trade_date": "2026-11-03", "closing_price": 100},
                {"trade_date": "2026-11-02", "closing_price": 100},
                {"trade_date": "2026-11-01", "closing_price": 100},
            ],
            stock_app.normalize_symbol("الف۲"): [
                {"trade_date": "2026-11-03", "closing_price": 150},
                {"trade_date": "2026-11-02", "closing_price": 125},
                {"trade_date": "2026-11-01", "closing_price": 100},
            ],
        }
        index_history = [
            {"trade_date": "2026-11-01", "closing_value": 100},
            {"trade_date": "2026-11-02", "closing_value": 110},
            {"trade_date": "2026-11-03", "closing_value": 120},
            {"trade_date": "2026-11-04", "closing_value": 130},
            # This future point must not leak into a previous-day strategy.
            {"trade_date": "2026-11-05", "closing_value": 999},
        ]

        industry_result = stock_app.evaluate_stock_strategy(
            rows,
            history,
            {"industry_growth": {"enabled": True, "days": 3}},
            market_index_history=index_history,
        )
        self.assertEqual(industry_result["count"], 1)
        self.assertAlmostEqual(
            industry_result["stocks"][0][
                "industry_market_index_growth_percent"
            ],
            30,
        )
        self.assertEqual(
            industry_result["stocks"][0][
                "industry_market_index_growth_days_used"
            ],
            3,
        )

        comparison_result = stock_app.evaluate_stock_strategy(
            rows,
            history,
            {
                "symbol_industry_compare": {
                    "enabled": True,
                    "symbol": "الف۱",
                    "days": 3,
                    "include_industry": True,
                }
            },
            market_index_history=index_history,
        )
        self.assertEqual(comparison_result["count"], 2)
        for row in comparison_result["stocks"]:
            self.assertAlmostEqual(
                row["symbol_industry_market_index_growth_percent"],
                30,
            )


if __name__ == "__main__":
    unittest.main()
