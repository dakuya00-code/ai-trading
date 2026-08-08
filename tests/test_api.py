import unittest

from app.main import backtest, health, plan, predict
from app.models import BacktestRequest, MarketSnapshot


class ApiTests(unittest.TestCase):
    def test_health_endpoint(self):
        body = health()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "model_api")

    def test_plan_endpoint(self):
        payload = MarketSnapshot(
            symbol="005930.KS",
            price=72000,
            moving_average_short=71500,
            moving_average_long=70000,
            rsi=45,
            sentiment=0.4,
        )
        body = plan(payload)
        self.assertEqual(body.signal, "buy")
        self.assertGreater(body.quantity, 0)

    def test_backtest_endpoint(self):
        result = backtest(
            BacktestRequest(
                snapshots=[
                    MarketSnapshot(
                        symbol="005930.KS",
                        price=72000,
                        moving_average_short=71500,
                        moving_average_long=70000,
                        rsi=45,
                        sentiment=0.4,
                    )
                ]
            )
        )
        self.assertGreaterEqual(result.trades, 0)
        self.assertGreaterEqual(result.initial_cash, 0)


if __name__ == "__main__":
    unittest.main()
