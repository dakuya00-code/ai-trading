import unittest

from app.main import backtest, collector_status, health, market_snapshot, plan, portfolio, predict, status
from app.models import BacktestRequest, MarketSnapshot


class ApiTests(unittest.TestCase):
    def test_health_and_status_endpoints(self):
        health_body = health()
        self.assertEqual(health_body['status'], 'ok')
        self.assertEqual(health_body['service'], 'model_api')
        status_body = status()
        self.assertEqual(status_body['health'], 'ok')
        self.assertIn('collector_mode', status_body)
        self.assertIn('event_count', status_body)
        self.assertIn('portfolio_positions', status_body)

    def test_collector_status_and_market_snapshot(self):
        collector_body = collector_status()
        self.assertIn('mode', collector_body)
        snapshot = market_snapshot('005930.KS')
        self.assertIsInstance(snapshot, MarketSnapshot)
        self.assertEqual(snapshot.symbol, '005930.KS')

    def test_portfolio_endpoint_exists(self):
        body = portfolio()
        self.assertIn('positions', body.model_dump())

    def test_plan_and_backtest_endpoints(self):
        payload = MarketSnapshot(
            symbol='005930.KS',
            price=72000,
            moving_average_short=71500,
            moving_average_long=70000,
            rsi=45,
            sentiment=0.4,
        )
        pred = predict(payload)
        self.assertEqual(pred.signal, 'buy')
        body = plan(payload)
        self.assertEqual(body.signal, 'buy')
        self.assertGreater(body.quantity, 0)
        result = backtest(
            BacktestRequest(
                snapshots=[payload]
            )
        )
        self.assertGreaterEqual(result.trades, 0)
        self.assertGreaterEqual(result.initial_cash, 0)


if __name__ == '__main__':
    unittest.main()
