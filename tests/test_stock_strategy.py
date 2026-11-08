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

    def test_strategy_can_use_complete_market_source_and_history(self):
        all_market_rows = [{
            "symbol": "نماد کامل",
            "market_date": "2026-10-26",
            "trade_value": 120,
        }]
        all_market_history = {
            stock_app.normalize_symbol("نماد کامل"): [{
                "trade_date": "2026-10-25",
                "trade_value": 100,
            }],
        }

        with (
            patch.object(
                stock_app,
                "read_all_stock_database",
                return_value=(all_market_rows, {"last_successful_update": "all-now"}),
            ) as read_all,
            patch.object(
                stock_app,
                "read_stock_database",
            ) as read_featured,
            patch.object(
                stock_app,
                "read_stock_strategy_history",
                return_value=all_market_history,
            ) as read_history,
        ):
            result = stock_app.get_stock_strategy(
                {
                    "trade_value": {
                        "enabled": True,
                        "operator": "gte",
                        "days": 1,
                    },
                },
                source="all",
            )

        read_all.assert_called_once_with()
        read_featured.assert_not_called()
        read_history.assert_called_once_with(
            source="all",
            symbols=["نماد کامل"],
        )
        self.assertEqual(result["source"], "all")
        self.assertEqual(result["source_updated_at"], "all-now")
        self.assertEqual(result["stocks"][0]["symbol"], "نماد کامل")

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

    def test_buy_queue_summary_ranks_by_buy_queue_value(self):
        current_rows = [
            {
                "symbol": "نماد۱",
                "market_date": "2026-10-27",
                "order_book_buy_value": 500,
                "order_book_sell_value": 0,
            },
            {
                "symbol": "نماد۲",
                "market_date": "2026-10-27",
                "order_book_buy_value": 1_000,
                "order_book_sell_value": 0,
            },
            {
                "symbol": "بدون صف",
                "market_date": "2026-10-27",
                "order_book_buy_value": 900,
                "order_book_sell_value": 10,
            },
        ]
        history = {
            stock_app.normalize_symbol("نماد۱"): [
                {
                    "trade_date": "2026-10-26",
                    "trade_value": 4_000,
                    "order_book_buy_value": 400,
                    "order_book_sell_value": 0,
                },
                {
                    "trade_date": "2026-10-25",
                    "trade_value": 1_500,
                    "order_book_buy_value": 300,
                    "order_book_sell_value": 0,
                },
                {
                    "trade_date": "2026-10-24",
                    "trade_value": 1_000,
                    "order_book_buy_value": 200,
                    "order_book_sell_value": 20,
                },
            ],
            stock_app.normalize_symbol("نماد۲"): [
                {
                    "trade_date": "2026-10-26",
                    "trade_value": 3_000,
                    "order_book_buy_value": 0,
                    "order_book_sell_value": 100,
                },
            ],
        }

        result = stock_app.build_stock_buy_queue_summary(
            current_rows,
            history,
            limit=1,
        )

        self.assertEqual(result["matched_count"], 2)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["stocks"][0]["symbol"], "نماد۲")
        self.assertEqual(result["stocks"][0]["previous_trade_value"], 3_000)
        self.assertEqual(result["stocks"][0]["previous_to_queue_percent"], 300)
        self.assertEqual(
            result["stocks"][0]["consecutive_previous_queue_days"],
            0,
        )

        all_results = stock_app.build_stock_buy_queue_summary(
            current_rows,
            history,
            limit=10,
        )
        first_symbol = next(
            item for item in all_results["stocks"] if item["symbol"] == "نماد۱"
        )
        self.assertEqual(first_symbol["consecutive_previous_queue_days"], 2)

        previous_day_result = stock_app.build_stock_buy_queue_summary(
            current_rows,
            history,
            limit=10,
            use_previous_day=True,
            reference_date="2026-10-27",
        )
        self.assertEqual(previous_day_result["data_mode"], "previous_day")
        self.assertEqual(previous_day_result["matched_count"], 1)
        self.assertEqual(
            previous_day_result["stocks"][0]["symbol"],
            "نماد۱",
        )
        self.assertEqual(
            previous_day_result["stocks"][0]["market_date"],
            "2026-10-26",
        )
        self.assertEqual(
            previous_day_result["stocks"][0]["buy_queue_value"],
            400,
        )
        self.assertEqual(
            previous_day_result["stocks"][0]["previous_trade_value"],
            1_500,
        )

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

    def test_technical_indicators_match_standard_reference_values(self):
        # Wilder's published-style RSI sample contains both gains and losses,
        # so it verifies the initial SMA and every recursive smoothing step.
        rsi_prices = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10,
            45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28,
            46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
        ]
        self.assertAlmostEqual(
            stock_app.calculate_stock_rsi(rsi_prices, 14),
            57.91502067008556,
            places=10,
        )

        prices = [
            100, 102, 101, 105, 107, 106, 110, 108, 112, 115,
            113, 117, 120, 118, 121, 125, 123, 127, 130, 128,
            132, 135, 133, 138, 140, 137, 142, 145, 143, 148,
            150, 147, 152, 155, 153, 158, 160, 157, 162, 165,
        ]
        self.assertAlmostEqual(
            stock_app.calculate_stock_ema(prices, 20),
            147.63780986334072,
            places=10,
        )
        macd = stock_app.calculate_stock_macd(prices, 12, 26, 9)
        self.assertAlmostEqual(macd["macd"], 11.663368405614875, places=10)
        self.assertAlmostEqual(macd["signal"], 11.550048656429457, places=10)
        self.assertAlmostEqual(macd["histogram"], 0.11331974918541832, places=10)

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

    def test_industry_growth_filters_below_each_industry_average(self):
        current_rows = [
            {
                "symbol": "الف۱",
                "industry": "صنعت الف",
                "market_date": "2026-10-04",
                "closing_price": 120,
            },
            {
                "symbol": "الف۲",
                "industry": "صنعت الف",
                "market_date": "2026-10-04",
                "closing_price": 100,
            },
            {
                "symbol": "ب۱",
                "industry": "صنعت ب",
                "market_date": "2026-10-04",
                "closing_price": 90,
            },
            {
                "symbol": "ب۲",
                "industry": "صنعت ب",
                "market_date": "2026-10-04",
                "closing_price": 110,
            },
        ]
        history = {
            stock_app.normalize_symbol(row["symbol"]): [
                {
                    "trade_date": f"2026-10-0{day}",
                    "closing_price": 100,
                }
                for day in range(1, 4)
            ]
            for row in current_rows
        }
        rules = {
            "industry_growth": {
                "enabled": True,
                "days": 3,
            },
        }

        result = stock_app.evaluate_stock_strategy(current_rows, history, rules)

        self.assertEqual(result["active_filter_count"], 1)
        self.assertEqual(
            {stock["symbol"] for stock in result["stocks"]},
            {"الف۲", "ب۱"},
        )
        stocks = {stock["symbol"]: stock for stock in result["stocks"]}
        self.assertAlmostEqual(stocks["الف۲"]["industry_growth_percent"], 0)
        self.assertAlmostEqual(
            stocks["الف۲"]["industry_average_growth_percent"],
            10,
        )
        self.assertAlmostEqual(
            stocks["الف۲"]["below_industry_average_percent"],
            10,
        )
        self.assertEqual(stocks["الف۲"]["industry_growth_days_used"], 3)
        self.assertEqual(stocks["الف۲"]["industry_growth_member_count"], 2)

        rules["industry_growth"]["days"] = 5
        partial = stock_app.evaluate_stock_strategy(current_rows, history, rules)
        coverage = partial["history_coverage"]["industry_growth"]
        self.assertEqual(coverage["partial_symbol_count"], 4)
        self.assertEqual(coverage["minimum_days_used"], 3)
        self.assertEqual(coverage["maximum_days_used"], 3)

    def test_symbol_industry_comparison_can_include_or_hide_peers(self):
        current_rows = [
            {
                "symbol": "الف۱",
                "industry": "صنعت الف",
                "market_date": "2026-10-04",
                "closing_price": 120,
            },
            {
                "symbol": "الف۲",
                "industry": "صنعت الف",
                "market_date": "2026-10-04",
                "closing_price": 100,
            },
            {
                "symbol": "ب۱",
                "industry": "صنعت ب",
                "market_date": "2026-10-04",
                "closing_price": 90,
            },
        ]
        history = {
            stock_app.normalize_symbol(row["symbol"]): [
                {
                    "trade_date": f"2026-10-0{day}",
                    "closing_price": 100,
                }
                for day in range(1, 4)
            ]
            for row in current_rows
        }
        rules = {
            "symbol_industry_compare": {
                "enabled": True,
                "symbol": "الف۱",
                "days": 3,
                "include_industry": True,
            },
        }

        result = stock_app.evaluate_stock_strategy(
            current_rows,
            history,
            rules,
        )

        self.assertEqual(result["active_filter_count"], 1)
        self.assertTrue(result["symbol_industry_target_found"])
        self.assertEqual(result["symbol_industry_target_industry"], "صنعت الف")
        self.assertEqual(
            {stock["symbol"] for stock in result["stocks"]},
            {"الف۱", "الف۲"},
        )
        stocks = {stock["symbol"]: stock for stock in result["stocks"]}
        self.assertAlmostEqual(
            stocks["الف۱"]["symbol_industry_return_percent"],
            20,
        )
        self.assertAlmostEqual(
            stocks["الف۱"]["symbol_industry_average_return_percent"],
            10,
        )
        self.assertAlmostEqual(
            stocks["الف۲"]["symbol_industry_return_percent"],
            0,
        )
        self.assertEqual(stocks["الف۱"]["symbol_industry_days_used"], 3)

        rules["symbol_industry_compare"]["include_industry"] = False
        selected_only = stock_app.evaluate_stock_strategy(
            current_rows,
            history,
            rules,
        )
        self.assertEqual(selected_only["count"], 1)
        self.assertEqual(selected_only["stocks"][0]["symbol"], "الف۱")

        rules["symbol_industry_compare"]["symbol"] = "ناموجود"
        missing = stock_app.evaluate_stock_strategy(
            current_rows,
            history,
            rules,
        )
        self.assertEqual(missing["count"], 0)
        self.assertFalse(missing["symbol_industry_target_found"])

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

    def test_rsi_can_filter_between_two_thresholds(self):
        current_rows = [{
            "symbol": "نماد۱",
            "market_date": "2026-10-06",
            "closing_price": 101,
        }]
        history = self.history(*[
            {"trade_date": f"2026-10-0{index + 1}", "closing_price": price}
            for index, price in enumerate([100, 101, 102, 101, 102])
        ])
        rules = {
            "rsi": {
                "enabled": True,
                "operator": "between",
                "fixed": 70,
                "maximum": 50,
                "period": 5,
            },
        }

        result = stock_app.evaluate_stock_strategy(current_rows, history, rules)

        self.assertEqual(result["count"], 1)
        self.assertAlmostEqual(result["stocks"][0]["rsi"], 60)
        self.assertEqual(result["rules"]["rsi"]["fixed"], 50)
        self.assertEqual(result["rules"]["rsi"]["maximum"], 70)

        rules["rsi"].update({"fixed": 40, "maximum": 55})
        failed = stock_app.evaluate_stock_strategy(current_rows, history, rules)
        self.assertEqual(failed["count"], 0)

    def test_ema_can_filter_real_upward_and_downward_crossovers(self):
        self.assertEqual(
            stock_app.calculate_stock_ema_crossover(
                [10, 10, 10, 10, 10, 20],
                2,
                4,
            ),
            1,
        )
        self.assertEqual(
            stock_app.calculate_stock_ema_crossover(
                [20, 20, 20, 20, 20, 10],
                2,
                4,
            ),
            -1,
        )

        history = self.history(*[
            {"trade_date": f"2026-10-0{day}", "closing_price": 10}
            for day in range(1, 6)
        ])
        rules = {
            "ema": {
                "enabled": True,
                "mode": "crossover",
                "operator": "gte",
                "period": 2,
                "long_period": 4,
            },
        }
        result = stock_app.evaluate_stock_strategy(
            [{
                "symbol": "نماد۱",
                "market_date": "2026-10-06",
                "closing_price": 20,
            }],
            history,
            rules,
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["stocks"][0]["ema_cross_direction"], 1)
        self.assertEqual(
            result["technical_coverage"]["ema"]["required_points"],
            5,
        )


if __name__ == "__main__":
    unittest.main()
