import unittest

from app.models import MarketSnapshot
from app.strategy import predict_signal


class PredictionTests(unittest.TestCase):
    def test_buy_signal(self):
        snapshot = MarketSnapshot(
            symbol="005930.KS",
            price=72000,
            moving_average_short=71500,
            moving_average_long=70000,
            rsi=45,
            sentiment=0.4,
        )
        result = predict_signal(snapshot)
        self.assertEqual(result.signal, "buy")
        self.assertEqual(result.symbol, "005930.KS")
        self.assertGreater(result.confidence, 0.3)

    def test_sell_signal(self):
        snapshot = MarketSnapshot(
            symbol="000660.KS",
            price=110000,
            moving_average_short=112000,
            moving_average_long=115000,
            rsi=78,
            sentiment=-0.5,
        )
        result = predict_signal(snapshot)
        self.assertEqual(result.signal, "sell")

    def test_hold_signal(self):
        snapshot = MarketSnapshot(
            symbol="035420.KS",
            price=180000,
            moving_average_short=180000,
            moving_average_long=180000,
            rsi=55,
            sentiment=0.0,
        )
        result = predict_signal(snapshot)
        self.assertEqual(result.signal, "hold")


if __name__ == "__main__":
    unittest.main()
