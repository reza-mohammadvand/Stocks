import unittest
from datetime import date

import app as stock_app


class OptionTradingDaysTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
