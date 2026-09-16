import unittest
from unittest.mock import patch

import pandas as pd

from mini_bloomberg.core.ticker import parse_ticker
from mini_bloomberg.data.providers.tushare_provider import (
    _IS_FIELDS,
    _income,
    _periods,
    search_securities,
)


class TushareProviderTests(unittest.TestCase):
    def test_china_ticker_mapping(self):
        sh = parse_ticker("600519 CH Equity")
        sz = parse_ticker("000001 CH Equity")
        bj = parse_ticker("430047 CH Equity")
        self.assertTrue(sh.is_china)
        self.assertEqual(sh.tushare_symbol, "600519.SH")
        self.assertEqual(sh.yfinance_symbol, "600519.SS")
        self.assertEqual(sz.tushare_symbol, "000001.SZ")
        self.assertEqual(bj.tushare_symbol, "430047.BJ")

    def test_income_mapping_rounds_monetary_values(self):
        row = pd.Series({
            "end_date": "20241231", "revenue": 100.4, "oper_cost": 40.2,
            "sell_exp": 10.2, "admin_exp": 5.3, "operate_profit": 30.1,
            "n_income_attr_p": 20.2,
        })
        result = _income(row, "600519", "FY")
        self.assertEqual(result.revenue, 100)
        self.assertEqual(result.gross_profit, 60)
        self.assertEqual(result.sga_expenses, 16)
        self.assertEqual(result.fiscal_year, "2024")

    def test_quarterly_flow_values_are_deaccumulated(self):
        frame = pd.DataFrame([
            {"end_date": "20240331", "total_revenue": 100.0, "oper_cost": 60.0},
            {"end_date": "20240630", "total_revenue": 230.0, "oper_cost": 140.0},
        ])
        periods = _periods(frame, _IS_FIELDS, cumulative=True)
        self.assertEqual(periods[0].fields["Total Revenue"], 100.0)
        self.assertEqual(periods[1].fields["Total Revenue"], 130.0)
        self.assertEqual(periods[1].fields["Gross Profit"], 50.0)

    def test_security_search_by_code_name_and_pinyin(self):
        universe = [
            {"ts_code": "600519.SH", "symbol": "600519", "name": "贵州茅台",
             "industry": "白酒", "cnspell": "GZMT"},
            {"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行",
             "industry": "银行", "cnspell": "PAYH"},
        ]
        with patch(
            "mini_bloomberg.data.providers.tushare_provider._stock_universe",
            return_value=universe,
        ):
            self.assertEqual(search_securities("600519")[0]["ticker"], "600519 CH Equity")
            self.assertEqual(search_securities("茅台")[0]["name"], "贵州茅台")
            self.assertEqual(search_securities("PAYH")[0]["symbol"], "000001")


if __name__ == "__main__":
    unittest.main()
