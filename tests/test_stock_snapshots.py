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
        first_row.update({
            "price_power": 0,
            "last_price": 100,
            "order_book_buy_value": 1_000,
            "order_book_sell_value": 0,
        })
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
        second_row.update({
            "price_power": 0,
            "last_price": 90,
            "order_book_buy_value": 0,
            "order_book_sell_value": 1_000,
        })
        stock_app.save_daily_stock_snapshots([second_row], second_time)
        stock_app.store_stock_price_history(
            "فولاد",
            "123",
            [
                {
                    "trade_date": "2026-10-19",
                    "raw_closing_price": 100,
                    "adjusted_closing_price": 100,
                    "raw_last_price": 100,
                    "daily_high_price": 100,
                    "daily_low_price": 90,
                },
                {
                    "trade_date": "2026-10-20",
                    "raw_closing_price": 110,
                    "adjusted_closing_price": 110,
                    "raw_last_price": 90,
                    "daily_high_price": 120,
                    "daily_low_price": 90,
                },
            ],
        )

        with stock_app.app.test_client() as client:
            response = client.get(
                "/stocks/metric-history"
                "?symbol=فولاد&metric=trade_value&limit=365"
            )
            price_power_response = client.get(
                "/stocks/metric-history"
                "?symbol=فولاد&metric=price_power&limit=365"
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
        self.assertEqual(price_power_response.status_code, 200)
        self.assertEqual(
            [
                point["status"]
                for point in price_power_response.get_json()["points"]
            ],
            ["buy_queue_neutral", "sell_queue"],
        )
        self.assertEqual(invalid.status_code, 400)

    def test_price_power_status_uses_all_seven_market_states(self):
        cases = (
            (100, 100, 100, 90, "buy_queue_neutral"),
            (100, 95, 100, 90, "buy_queue"),
            (98, 95, 100, 90, "positive"),
            (92, 95, 100, 90, "negative"),
            (90, 90, 100, 90, "sell_queue_neutral"),
            (90, 95, 100, 90, "sell_queue"),
            (95, 95, 100, 90, "neutral"),
        )

        for last_price, closing_price, upper, lower, expected in cases:
            with self.subTest(expected=expected):
                row = {
                    "last_price": last_price,
                    "closing_price": closing_price,
                    "daily_upper_price": upper,
                    "daily_lower_price": lower,
                }
                self.assertEqual(
                    stock_app.stock_price_power_status(row),
                    expected,
                )
                self.assertEqual(
                    stock_app.stock_strategy_buy_queue_state(row),
                    expected in {"buy_queue", "buy_queue_neutral"},
                )

        # Conditions are evaluated top-to-bottom: equality with the daily high
        # wins before the generic last-price-equals-closing-price condition.
        self.assertEqual(
            stock_app.stock_price_power_status({
                "last_price": 28_330,
                "closing_price": 28_330,
                "daily_high_price": 28_330,
                "daily_low_price": 28_200,
            }),
            "buy_queue_neutral",
        )

        # TSETMC reports zero daily highs/lows for instruments without a
        # completed trade. Zero is not a price boundary, so use the static
        # daily range instead.
        self.assertEqual(
            stock_app.stock_price_power_status({
                "last_price": 100,
                "closing_price": 100,
                "daily_high_price": 0,
                "daily_low_price": 0,
                "daily_upper_price": 100,
                "daily_lower_price": 90,
            }),
            "buy_queue_neutral",
        )

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
        self.assertEqual(indicators["price_power_status"], "positive")

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

    def test_price_history_is_adjusted_across_corporate_action(self):
        payload = {
            "closingPriceDaily": [
                {
                    "dEven": 20261021,
                    "pClosing": 60,
                    "pDrCotVal": 61,
                    "priceYesterday": 50,
                },
                {
                    "dEven": 20261020,
                    "pClosing": 100,
                    "pDrCotVal": 101,
                    "priceYesterday": 100,
                },
                {
                    "dEven": 20261019,
                    "pClosing": 100,
                    "pDrCotVal": 100,
                    "priceYesterday": 98,
                },
            ],
        }

        points = stock_app.parse_tsetmc_price_history(payload, limit=120)

        self.assertEqual(
            [point["adjusted_closing_price"] for point in points],
            [60, 50, 50],
        )

    def test_backfill_and_daily_close_feed_strategy_price_history(self):
        points = [
            {
                "trade_date": "2026-10-20",
                "raw_closing_price": 100,
                "adjusted_closing_price": 100,
                "raw_last_price": 101,
                "daily_high_price": 102,
                "daily_low_price": 98,
            },
            {
                "trade_date": "2026-10-19",
                "raw_closing_price": 90,
                "adjusted_closing_price": 90,
                "raw_last_price": 91,
                "daily_high_price": 92,
                "daily_low_price": 88,
            },
        ]
        stored = stock_app.store_stock_price_history(
            "فولاد",
            "123",
            points,
        )
        stock_app.save_daily_stock_price_points(
            [{
                "symbol": "فولاد",
                "ins_code": "123",
                "market_date": "2026-10-21",
                "closing_price": 55,
                "last_price": 56,
                "yesterday_price": 50,
                "daily_high_price": 57,
                "daily_low_price": 52,
            }],
            datetime(
                2026,
                10,
                21,
                12,
                30,
                tzinfo=stock_app.IRAN_TIMEZONE,
            ),
        )
        stock_app.save_daily_stock_price_points(
            [{
                "symbol": "فولاد",
                "ins_code": "123",
                "market_date": "2026-10-21",
                "closing_price": 57,
                "last_price": 58,
                "yesterday_price": 50,
                "daily_high_price": 59,
                "daily_low_price": 53,
            }],
            datetime(
                2026,
                10,
                21,
                13,
                0,
                tzinfo=stock_app.IRAN_TIMEZONE,
            ),
        )

        history = stock_app.read_stock_price_history(["فولاد"])[
            stock_app.normalize_symbol("فولاد")
        ]
        strategy_history = stock_app.read_stock_strategy_history(
            symbols=["فولاد"]
        )[stock_app.normalize_symbol("فولاد")]

        self.assertEqual(stored, 2)
        self.assertEqual(
            [point["closing_price"] for point in history],
            [57, 50, 45],
        )
        self.assertEqual(
            [point["closing_price"] for point in strategy_history],
            [57, 50, 45],
        )
        self.assertEqual(
            stock_app.pending_stock_price_history_rows([
                {"symbol": "فولاد", "ins_code": "123"},
            ]),
            [],
        )

    def test_sixty_day_strategy_metrics_are_built_and_persisted(self):
        price_points = [{
            "trade_date": "2026-10-20",
            "raw_closing_price": 100,
            "raw_last_price": 110,
            "trade_value": 10_000,
            "trade_volume": 100,
            "trade_count": 12,
        }]
        client_payload = {
            "clientType": [{
                "recDate": 20261020,
                "buy_I_Value": 6_000,
                "sell_I_Value": 2_000,
                "buy_I_Count": 3,
                "sell_I_Count": 2,
                "buy_I_Volume": 60,
                "sell_I_Volume": 20,
                "buy_N_Volume": 40,
                "sell_N_Volume": 80,
            }],
        }
        client_points = stock_app.parse_tsetmc_client_type_history(
            client_payload,
            limit=60,
        )
        points = stock_app.build_stock_strategy_history_points(
            price_points,
            client_points,
            share_count=10_000,
            floating_share_percent=20,
            limit=60,
        )
        stored = stock_app.store_stock_strategy_history(
            "فولاد",
            "123",
            points,
        )
        history = stock_app.read_stock_strategy_metric_history(["فولاد"])[
            stock_app.normalize_symbol("فولاد")
        ]

        self.assertEqual(stored, 1)
        self.assertEqual(points[0]["price_power"], 1)
        self.assertEqual(points[0]["trade_to_float_percent"], 5)
        self.assertEqual(points[0]["real_money_flow"], 4_000)
        self.assertEqual(points[0]["money_flow_quality"], 40)
        self.assertEqual(points[0]["real_buy_per_capita"], 2_000)
        self.assertEqual(points[0]["real_sell_per_capita"], 1_000)
        self.assertEqual(points[0]["real_buy_power"], 2)
        self.assertTrue(history[0]["trade_to_float_is_estimated"])
        daily_row = {
            "symbol": "فولاد",
            "ins_code": "123",
            "market_date": "2026-10-20",
            "trade_value": 20_000,
            "trade_volume": 120,
            "price_power": -1,
            "trade_to_float_percent": 6,
            "real_money_flow": 5_000,
            "money_flow_quality": 25,
            "real_buy_per_capita": 2_500,
            "real_sell_per_capita": 1_000,
            "real_buy_power": 2.5,
        }
        stock_app.save_daily_stock_strategy_points([daily_row], self.at(12, 30))
        stock_app.save_daily_stock_strategy_points(
            [{**daily_row, "trade_value": 30_000}],
            self.at(13, 0),
        )
        exact_history = stock_app.read_stock_strategy_metric_history(["فولاد"])[
            stock_app.normalize_symbol("فولاد")
        ][0]
        self.assertEqual(exact_history["trade_value"], 20_000)
        self.assertFalse(exact_history["trade_to_float_is_estimated"])
        self.assertEqual(
            stock_app.pending_stock_strategy_history_rows([
                {
                    "symbol": "فولاد",
                    "ins_code": "123",
                    "share_count": 10_000,
                    "floating_share_percent": 20,
                },
            ]),
            [],
        )

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
