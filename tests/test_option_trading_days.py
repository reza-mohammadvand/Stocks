import unittest
from datetime import date

import app as stock_app


class OptionTradingDaysTests(unittest.TestCase):
    def test_option_spread_uses_first_ask_over_first_bid(self):
        self.assertAlmostEqual(
            stock_app.calculate_option_spread_percent(100, 110),
            10,
        )
        self.assertIsNone(stock_app.calculate_option_spread_percent(0, 110))

    def test_put_breakeven_is_strike_minus_premium(self):
        metrics = stock_app.calculate_put_option_metrics(100, 120, 5)

        self.assertEqual(metrics["breakeven_price"], 115)
        self.assertAlmostEqual(metrics["breakeven_distance"], 15)
        self.assertAlmostEqual(metrics["leverage"], 20)
        self.assertEqual(metrics["status"], "ITM")

    def test_market_watch_init_parser_returns_first_order_book_level(self):
        market_fields = [""] * 26
        market_fields[0] = "12345678901234567"
        market_fields[1] = "IRO1TEST0001"
        market_fields[2] = "آزمون"
        market_fields[3] = "شرکت آزمون"
        market_row = ",".join(market_fields)
        response = (
            f"irrelevant@{market_row}@"
            "12345678901234567,1,2,3,100,110,400,500;"
            "12345678901234567,2,1,1,90,120,300,200"
        )

        rows, limits = stock_app.parse_market_watch_init(response)

        self.assertEqual(rows, [market_row])
        self.assertEqual(limits["12345678901234567"]["best_buy_price"], 100)
        self.assertEqual(limits["12345678901234567"]["best_sell_price"], 110)

    def test_excludes_thursday_friday_and_official_holiday(self):
        # 2026-10-27 is Tuesday. The following five calendar days include
        # Wednesday (declared holiday here), Thursday and Friday.
        result = stock_app.calculate_trading_days_remaining(
            "1405/08/10",
            today=date(2026, 10, 27),
            official_holidays={date(2026, 10, 28)},
        )

        self.assertEqual(result, 2)

    def test_expired_contract_has_no_remaining_trading_day(self):
        result = stock_app.calculate_trading_days_remaining(
            "1405/08/04",
            today=date(2026, 10, 27),
            official_holidays=set(),
        )

        self.assertEqual(result, 0)

    def test_option_burning_returns_twenty_rows_with_best_buy_price(self):
        options = []
        for index in range(25):
            options.append({
                "ins_code": str(index),
                "symbol": f"اختیار{index}",
                "option_last_price": 100 + index,
                "breakeven_distance": index + 1,
                "status": "OTM",
            })

        bases = [{
            "base_symbol": "فولاد",
            "groups": [{
                "days_remaining": 10,
                "trading_days_remaining": 5,
                "options": [option],
            } for option in options],
        }]

        rows = stock_app.build_option_burning_summary(
            bases,
            limit=20,
            best_buy_fetcher=lambda ins_code: int(ins_code) + 1_000,
        )

        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["symbol"], "اختیار24")
        self.assertEqual(rows[0]["best_buy_price"], 1_024)
        self.assertNotIn("_ins_code", rows[0])

    def test_option_burning_excludes_best_bid_below_ten(self):
        bases = [{
            "base_symbol": "فولاد",
            "groups": [{
                "days_remaining": 10,
                "trading_days_remaining": 5,
                "options": [
                    {
                        "ins_code": "high",
                        "symbol": "اختیار با خرید نامعتبر",
                        "option_last_price": 100,
                        "breakeven_distance": 30,
                        "status": "OTM",
                    },
                    {
                        "ins_code": "valid",
                        "symbol": "اختیار معتبر",
                        "option_last_price": 90,
                        "breakeven_distance": 20,
                        "status": "OTM",
                    },
                ],
            }],
        }]
        best_bids = {"high": 9, "valid": 10}

        rows = stock_app.build_option_burning_summary(
            bases,
            best_buy_fetcher=best_bids.get,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "اختیار معتبر")
        self.assertEqual(rows[0]["best_buy_price"], 10)


if __name__ == "__main__":
    unittest.main()
