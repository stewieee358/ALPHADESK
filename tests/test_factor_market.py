from datetime import date, timedelta
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from mini_bloomberg.core.errors import DataSourceError
from mini_bloomberg.core.ticker import parse_ticker
from mini_bloomberg.data.factor_prices import load_factor_prices, DEFAULT_SYMBOLS
from mini_bloomberg.data.schemas import PriceBar, PriceHistory
from mini_bloomberg.functions.alpha import ALPHA, parse_alpha_args


def history(ticker, days=365):
    offset = sum(map(ord, ticker.symbol)) % 19
    today = date.today()
    bars = [PriceBar(date=(today - timedelta(days=i)).isoformat(), close=100 + offset + i * (offset + 1) / 100,
                     open=99 + offset, high=110 + offset, low=90 + offset, volume=1000 + offset)
            for i in range(61)]
    return PriceHistory(symbol=ticker.symbol, bars=bars, source="FixtureProvider", fetched_at="2026-01-01T00:00:00+00:00")


class MarketTests(unittest.TestCase):
    @patch('mini_bloomberg.data.factor_prices.get_price_history', side_effect=history)
    def test_date_filter_alignment_and_provenance(self, fetch):
        end = date.today() - timedelta(days=5)
        begin = end - timedelta(days=30)
        panel = load_factor_prices(start=begin.isoformat(), end=end.isoformat())
        self.assertEqual(len(panel.histories), 12)
        for value in panel.histories.values():
            self.assertEqual(value.bars[0].date, begin.isoformat())
            self.assertEqual(value.bars[-1].date, end.isoformat())
            self.assertEqual(len(value.bars), 31)
        self.assertEqual(panel.sources[0]['source'], 'FixtureProvider')
        self.assertEqual(fetch.call_count, 12)

    @patch('mini_bloomberg.data.factor_prices.get_price_history', side_effect=history)
    def test_market_default_function_and_json(self, fetch):
        result = ALPHA().run(days=30)
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['data']['dataset'], 'market')
        self.assertEqual(len(result['data']['sources']), 12)
        self.assertTrue(all(row['security'].endswith('US Equity') for row in result['data']['latest']))
        json.dumps(result, allow_nan=False)

    @patch('mini_bloomberg.data.factor_prices.get_price_history')
    def test_bad_input_no_network(self, fetch):
        for kwargs in [{'symbols': 'AAPL,MSFT'}, {'symbols': 'AAPL,' * 11 + 'AAPL'}, {'days': -1},
                       {'start': 'wrong'}, {'end': (date.today() + timedelta(days=1)).isoformat()}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                load_factor_prices(**kwargs)
        fetch.assert_not_called()

    def test_failed_stock_no_synthetic_or_silent_drop(self):
        def fail(ticker, days):
            if ticker.symbol == 'AAPL': raise DataSourceError('URL?apikey=SECRET')
            return history(ticker, days)
        with patch('mini_bloomberg.data.factor_prices.get_price_history', side_effect=fail):
            result = ALPHA().run()
        self.assertEqual(result['status'], 'error')
        self.assertIn('AAPL', result['message'])
        self.assertNotIn('SECRET', result['message'])

    def test_misaligned_sessions_stay_missing(self):
        def missing(ticker, days):
            value = history(ticker, days)
            if ticker.symbol == 'AAPL': value.bars = value.bars[1:]
            return value
        with patch('mini_bloomberg.data.factor_prices.get_price_history', side_effect=missing):
            result = ALPHA().run(days=30, expression='close')
        self.assertEqual(result['status'], 'ok', result)
        apple = next(row for row in result['data']['latest'] if row['security'].startswith('AAPL '))
        self.assertIsNone(apple['factor'])
        self.assertTrue(any('Latest dates differ' in note for note in result['data']['notes']))

    def test_empty_fmp_falls_back_and_cached_order_is_unchanged(self):
        from mini_bloomberg.data.equity_price import get_price_history
        ticker = parse_ticker('AAPL')
        value = history(ticker)
        original_dates = [b.date for b in value.bars]
        with patch('mini_bloomberg.data.equity_price.fmp_provider.get_price_history', return_value=value):
            a = get_price_history(ticker)
            b = get_price_history(ticker)
        self.assertEqual([bar.date for bar in a.bars], [bar.date for bar in b.bars])
        self.assertEqual([bar.date for bar in value.bars], original_dates)
        with patch('mini_bloomberg.data.equity_price.fmp_provider.get_price_history', return_value=PriceHistory(symbol='AAPL')), \
             patch('mini_bloomberg.data.equity_price.openbb_provider.get_price_history', return_value=value):
            self.assertEqual(get_price_history(ticker).source, 'OpenBB/yfinance')

    def test_openbb_requests_calendar_start_and_stamps_fetch(self):
        from mini_bloomberg.data.providers.openbb_provider import get_price_history
        with patch('mini_bloomberg.data.providers.openbb_provider._obb') as obb:
            obb.return_value.equity.price.historical.return_value = SimpleNamespace(
                results=[PriceBar(date=date.today().isoformat(), close=100)])
            result = get_price_history.__wrapped__(parse_ticker('AAPL'), days=100)
            request = obb.return_value.equity.price.historical.call_args.kwargs
            self.assertEqual(request['start_date'], (date.today() - timedelta(days=100)).isoformat())
            self.assertEqual(result.source, 'OpenBB/yfinance')
            self.assertIsNotNone(result.fetched_at)

    @patch('mini_bloomberg.data.factor_prices.get_price_history', side_effect=history)
    def test_web_and_parser(self, fetch):
        from fastapi.testclient import TestClient
        from mini_bloomberg.web.server import app
        command = f'ALPHA --symbols {DEFAULT_SYMBOLS} --days 30 --expression rank(close)'
        self.assertEqual(parse_alpha_args(command.split()[1:])['days'], 30)
        with TestClient(app) as client:
            response = client.post('/api/command', json={'command': command})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok', response.json())
        self.assertEqual(response.json()['provider'], 'FixtureProvider')
