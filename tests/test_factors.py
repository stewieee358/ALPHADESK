import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from mini_bloomberg.factors import DataLoader, ExpressionEngine, FactorEvaluator
from mini_bloomberg.factors.operators.wq_brain_ops import trade_when
from mini_bloomberg.functions.alpha import ALPHA, parse_alpha_args


class FactorTests(unittest.TestCase):
    def setUp(self):
        self.close = pd.DataFrame(np.arange(60).reshape(6, 10) + 10.,
            index=pd.date_range('2024-01-01', periods=6), columns=list('ABCDEFGHIJ'))
        self.engine = ExpressionEngine(DataLoader.from_dataframe({'close': self.close}))

    def test_expression_rank(self):
        assert_frame_equal(self.engine.evaluate('rank(ts_delta(close, 2))'), self.close.diff(2).rank(axis=1, pct=True))

    def test_assignments_comparisons_keyword_names(self):
        result = self.engine.evaluate('x = close > 25; if_else(and(x, close < 60), close, 0)')
        assert_frame_equal(result, self.close.where((self.close > 25) & (self.close < 60), 0))

    def test_keyword_args_and_power_precedence(self):
        self.assertEqual(self.engine.evaluate('-2**2'), -4)
        self.assertEqual(self.engine.evaluate('2**3**2'), 512)
        result = self.engine.evaluate('normalize(close, useStd=true)')
        np.testing.assert_allclose(result.mean(axis=1), 0, atol=1e-12)

    def test_reject_unsupported_or_future_access(self):
        for expression in ['close @ close', 'close.__class__', '__import__("os")',
                           'close[0]', 'ts_delay(close, -1)', 'delay(close, d=-1)',
                           'close $', 'rank(', '2**99999999', 'import os']:
            with self.subTest(expression=expression), self.assertRaises(Exception):
                self.engine.evaluate(expression)

    def test_trade_when_initial_hold_exit_priority(self):
        alpha = self.close.iloc[:4, :1]
        trigger = pd.DataFrame([0, 1, 0, 1], index=alpha.index, columns=alpha.columns)
        exit_cond = pd.DataFrame([0, 0, 0, 1], index=alpha.index, columns=alpha.columns)
        result = trade_when(trigger, alpha, exit_cond)
        self.assertTrue(np.isnan(result.iloc[0, 0]))
        self.assertEqual(result.iloc[2, 0], alpha.iloc[1, 0])
        self.assertTrue(np.isnan(result.iloc[3, 0]))
        assert_frame_equal(trade_when(1, alpha, -1), alpha)

    def test_forward_returns_compound_and_do_not_double_shift(self):
        returns = self.close.pct_change(fill_method=None)
        evaluator = FactorEvaluator(self.close, returns, holding_period=2)
        assert_frame_equal(evaluator.forward_returns, self.close.shift(-2) / self.close - 1)
        with self.assertRaises(ValueError): evaluator.cumulative_layered_returns()

    def test_gaps_do_not_fill_returns(self):
        close = self.close.copy(); close.iloc[2, 0] = np.nan
        ctx = DataLoader.from_dataframe({'close': close})
        self.assertTrue(np.isnan(ctx['returns'].iloc[3, 0]))

    def test_csv_codes_dates_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'prices.csv'
            p.write_text('trade_date,ts_code,close\n20240102,000001,12\n20240101,000001,10\n')
            ctx = DataLoader.from_csv(str(p))
            self.assertEqual(ctx.stocks.tolist(), ['000001'])
            self.assertEqual(ctx.dates[0], pd.Timestamp('2024-01-01'))
            with p.open('a') as f: f.write('20240101,000001,11\n')
            with self.assertRaises(ValueError): DataLoader.from_csv(str(p))

    def test_demo_json_and_error_paths(self):
        result = ALPHA().run(dataset="demo")
        self.assertEqual(result['status'], 'ok', result)
        json.dumps(result, allow_nan=False)
        self.assertEqual(len(result['data']['curve']), 252)
        self.assertIn('SYNTHETIC', result['data']['notes'][0])
        for kwargs in [{'dataset': '../../.env'}, {'dataset': 'missing.csv'}, {'expression': '3'}, {'expression': 'unknown(close)'}]:
            self.assertEqual(ALPHA().run(**({'dataset': 'demo'} | kwargs))['status'], 'error')

    def test_quantiles_without_scipy(self):
        result = self.engine.evaluate('ts_quantile(close, 3, driver="gaussian")')
        self.assertEqual(result.shape, self.close.shape)
        self.assertTrue(np.isfinite(result.to_numpy()).all())

    def test_registries_and_parsing(self):
        from mini_bloomberg.cli.dispatcher import _registry, _parse_function_kwargs
        from mini_bloomberg.web.server import _get_registry, _parse_kwargs
        from mini_bloomberg.agents.tools import FUNCTIONS_BY_NAME
        self.assertIs(_registry()['ALPHA'], ALPHA)
        self.assertIs(_get_registry()['ALPHA'], ALPHA)
        self.assertIsInstance(FUNCTIONS_BY_NAME['alpha'], ALPHA)
        args = '--dataset demo --expression rank(ts_delta(close, 5))'.split()
        self.assertEqual(_parse_function_kwargs('ALPHA', args), _parse_kwargs('ALPHA', args))
        self.assertEqual(parse_alpha_args(args)['expression'], 'rank(ts_delta(close, 5))')
        quoted = '--expression ts_quantile(close, 3, driver="gaussian")'.split()
        self.assertIn('"gaussian"', parse_alpha_args(quoted)['expression'])

    def test_web_command(self):
        from fastapi.testclient import TestClient
        from mini_bloomberg.web.server import app
        with TestClient(app) as client:
            response = client.post('/api/command', json={'command': 'ALPHA --dataset demo --expression rank(ts_delta(close, 5)) <GO>'})
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(result['status'], 'ok', result)
            self.assertEqual(result['provider'], 'Local factor engine')


if __name__ == '__main__':
    unittest.main()
