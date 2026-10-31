import unittest
from unittest.mock import patch

import app as stock_app


class StockStrategyTests(unittest.TestCase):
    @staticmethod
    def history(*rows):
        return {stock_app.normalize_symbol("نماد۱"): list(rows)}

    def test_all_enabled_strategy_rows_are_combined_with_and(self):
        current_rows = [{
            "symbol": "نماد۱",
            "company": "شرکت یک",
            "industry": "آزمایشی",
            "market_date": "2026-10-25",
            "price_power": 0,
            "order_book_buy_value": 500,
            "order_book_sell_value": 0,
            "trade_value": 100,
            "trade_to_float_percent": 2,
            "real_buy_power": 1.4,
        }]
        history = self.history(
            {
                "trade_date": "2026-10-24",
                "trade_value": 80,
                "trade_to_float_percent": 1,
                "real_buy_power": 1.1,
            },
            {
                "trade_date": "2026-10-23",
                "trade_value": 90,
                "trade_to_float_percent": 1.5,
                "real_buy_power": 1.2,
            },
        )
        rules = {
            "trade_value": {
                "enabled": True,
                "operator": "gte",
                "days": 2,
            },
            "trade_to_float_percent": {
                "enabled": True,
                "operator": "gte",
                "fixed": 1.8,
                "days": 2,
            },
            "real_buy_power": {
                "enabled": True,
                "operator": "gte",
                "fixed": 1.3,
                "days": 2,
            },
        }

        result = stock_app.evaluate_stock_strategy(current_rows, history, rules)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["active_filter_count"], 3)
        self.assertEqual(result["stocks"][0]["price_power"], 0)
        self.assertEqual(result["stocks"][0]["order_book_buy_value"], 500)
        self.assertEqual(result["stocks"][0]["order_book_sell_value"], 0)
        self.assertEqual(result["stocks"][0]["trade_value_average"], 85)
        self.assertEqual(
            result["stocks"][0]["trade_to_float_percent_average"],
            1.25,
        )
        self.assertEqual(result["stocks"][0]["real_buy_power_average"], 1.15)

        rules["real_buy_power"]["fixed"] = 1.5
        failed = stock_app.evaluate_stock_strategy(current_rows, history, rules)
        self.assertEqual(failed["count"], 0)

    def test_strategy_uses_available_history_and_reports_partial_average(self):
        current_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-25",
            "trade_value": 100,
        }]
        history = self.history({
            "trade_date": "2026-10-24",
            "trade_value": 80,
        })
        result = stock_app.evaluate_stock_strategy(
            current_rows,
            history,
            {
                "trade_value": {
                    "enabled": True,
                    "operator": "gte",
                    "days": 2,
                },
            },
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["partial_history_count"], 1)
        self.assertEqual(result["missing_history_count"], 0)
        self.assertEqual(result["stocks"][0]["trade_value_average"], 80)
        self.assertEqual(result["stocks"][0]["trade_value_history_count"], 1)
        self.assertEqual(
            result["history_coverage"]["trade_value"],
            {
                "requested_days": 2,
                "minimum_days_used": 1,
                "maximum_days_used": 1,
                "partial_symbol_count": 1,
            },
        )

    def test_zero_or_missing_values_are_excluded(self):
        current_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-25",
            "trade_value": 0,
        }]
        result = stock_app.evaluate_stock_strategy(
            current_rows,
            {},
            {
                "trade_value": {
                    "enabled": True,
                    "operator": "gte",
                    "days": 0,
                },
            },
        )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["excluded_zero_or_missing_count"], 1)

        current_rows[0]["trade_value"] = 100
        result = stock_app.evaluate_stock_strategy(
            current_rows,
            self.history({
                "trade_date": "2026-10-24",
                "trade_value": 0,
            }),
            {
                "trade_value": {
                    "enabled": True,
                    "operator": "gte",
                    "days": 2,
                },
            },
        )
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["missing_history_count"], 1)

    def test_strategy_can_evaluate_latest_saved_rows(self):
        live_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-26",
            "trade_value": 0,
        }]
        saved_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-25",
            "trade_value": 100,
        }]
        snapshot_metadata = {
            "data_source": "daily_snapshot",
            "saved_count": 1,
            "missing_snapshot_count": 0,
            "snapshot_date": "2026-10-25",
            "snapshot_date_jalali": "1405-08-03",
        }

        with (
            patch.object(
                stock_app,
                "read_stock_database",
                return_value=(live_rows, {"last_successful_update": "now"}),
            ),
            patch.object(
                stock_app,
                "apply_latest_stock_snapshots",
                return_value=(saved_rows, snapshot_metadata),
            ) as apply_snapshots,
            patch.object(stock_app, "read_stock_strategy_history", return_value={}),
        ):
            result = stock_app.get_stock_strategy({}, use_saved_data=True)

        apply_snapshots.assert_called_once_with(live_rows)
        self.assertEqual(result["data_source"], "daily_snapshot")
        self.assertEqual(result["stocks"][0]["trade_value"], 100)

    def test_money_flow_streak_average_and_quality_are_combined(self):
        current_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-27",
            "real_money_flow": 300,
            "money_flow_quality": 3.5,
        }]
        history = self.history(
            {
                "trade_date": "2026-10-26",
                "real_money_flow": 200,
                "money_flow_quality": 2.5,
            },
            {
                "trade_date": "2026-10-25",
                "real_money_flow": 100,
                "money_flow_quality": 1.5,
            },
            {
                "trade_date": "2026-10-24",
                "real_money_flow": -50,
                "money_flow_quality": -1,
            },
        )
        rules = {
            "real_money_flow": {
                "enabled": True,
                "consecutive_days": 3,
                "days": 2,
            },
            "money_flow_quality": {
                "enabled": True,
                "operator": "gte",
                "fixed": 2,
            },
        }

        result = stock_app.evaluate_stock_strategy(current_rows, history, rules)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["active_filter_count"], 2)
        self.assertEqual(
            result["stocks"][0]["real_money_flow_positive_streak"],
            3,
        )
        self.assertEqual(
            result["stocks"][0]["real_money_flow_average"],
            150,
        )

        history[stock_app.normalize_symbol("نماد۱")][1]["real_money_flow"] = -10
        failed = stock_app.evaluate_stock_strategy(current_rows, history, rules)
        self.assertEqual(failed["count"], 0)

    def test_zero_money_flow_inputs_disable_that_strategy_row(self):
        result = stock_app.evaluate_stock_strategy(
            [{"symbol": "نماد۱", "real_money_flow": None}],
            {},
            {
                "real_money_flow": {
                    "enabled": True,
                    "consecutive_days": 0,
                    "days": 0,
                },
            },
        )

        self.assertEqual(result["active_filter_count"], 0)
        self.assertEqual(result["count"], 1)

    def test_technical_indicator_calculations(self):
        values = [100, 101, 102, 103, 104, 105, 106, 107, 108, 110]

        self.assertAlmostEqual(
            stock_app.calculate_stock_ema([1, 2, 3, 4, 5], 3),
            4,
        )
        self.assertEqual(stock_app.calculate_stock_rsi(values, 5), 100)
        macd = stock_app.calculate_stock_macd(values, 3, 5, 3)
        self.assertIsNotNone(macd["macd"])
        self.assertIsNotNone(macd["signal"])
        self.assertAlmostEqual(
            macd["histogram"],
            macd["macd"] - macd["signal"],
        )

    def test_rsi_ema_and_macd_filters_are_combined(self):
        current_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-10",
            "closing_price": 110,
        }]
        history = self.history(*[
            {
                "trade_date": f"2026-10-{day:02d}",
                "closing_price": 99 + day,
            }
            for day in range(1, 10)
        ])
        rules = {
            "rsi": {
                "enabled": True,
                "operator": "gte",
                "fixed": 50,
                "period": 5,
            },
            "ema": {
                "enabled": True,
                "operator": "gte",
                "period": 5,
            },
            "macd": {
                "enabled": True,
                "operator": "gte",
                "compare_to": "signal",
                "fast_period": 3,
                "slow_period": 5,
                "signal_period": 3,
            },
        }

        result = stock_app.evaluate_stock_strategy(current_rows, history, rules)

        self.assertEqual(result["active_filter_count"], 3)
        self.assertEqual(result["count"], 1)
        stock = result["stocks"][0]
        self.assertEqual(stock["technical_history_count"], 10)
        self.assertEqual(stock["rsi"], 100)
        self.assertLess(stock["ema"], stock["closing_price"])
        self.assertGreaterEqual(stock["macd"], stock["macd_signal"])

    def test_technical_filter_reports_insufficient_closing_history(self):
        result = stock_app.evaluate_stock_strategy(
            [{
                "symbol": "نماد۱",
                "market_date": "2026-10-03",
                "closing_price": 103,
            }],
            self.history(
                {"trade_date": "2026-10-02", "closing_price": 102},
                {"trade_date": "2026-10-01", "closing_price": 101},
            ),
            {
                "rsi": {
                    "enabled": True,
                    "operator": "gte",
                    "fixed": 50,
                    "period": 14,
                },
            },
        )

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["missing_history_count"], 1)
        self.assertEqual(
            result["technical_coverage"]["rsi"],
            {
                "required_points": 15,
                "minimum_points_used": 3,
                "maximum_points_used": 3,
                "insufficient_symbol_count": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
