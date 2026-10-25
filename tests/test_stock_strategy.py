import unittest

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


if __name__ == "__main__":
    unittest.main()
