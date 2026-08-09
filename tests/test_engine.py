import unittest
from unittest import TestCase

from app.engine import analyze_snapshot, plan_trade, run_backtest
from app.models import BacktestRequest, MarketSnapshot


class EngineTests(unittest.TestCase):
    def test_plan_trade_buy_has_quantity_and_stops(self):
        snapshot = MarketSnapshot(
            symbol="005930.KS",
            price=72000,
            moving_average_short=71500,
            moving_average_long=70000,
            rsi=45,
            sentiment=0.4,
        )
        plan = plan_trade(snapshot)
        self.assertEqual(plan.signal, "buy")
        self.assertGreater(plan.quantity, 0)
        self.assertIsNotNone(plan.stop_loss)
        self.assertIsNotNone(plan.take_profit)

    def test_analyze_snapshot_returns_hold_when_flat(self):
        snapshot = MarketSnapshot(
            symbol="035420.KS",
            price=180000,
            moving_average_short=180000,
            moving_average_long=180000,
            rsi=55,
            sentiment=0.0,
        )
        pred = analyze_snapshot(snapshot)
        self.assertEqual(pred.signal, "hold")

    def test_backtest_with_empty_input(self):
        result = run_backtest(BacktestRequest())
        self.assertEqual(result.trades, 0)
        self.assertEqual(result.final_cash, result.initial_cash)
        self.assertTrue(result.notes)


class StrategyLearningTests(TestCase):
    def test_backtest_updates_strategy_state(self):
        from app.strategy_state import StrategyState, StrategyStateStore
        from app import engine as app_engine
        from tempfile import TemporaryDirectory
        from pathlib import Path
        with TemporaryDirectory() as td:
            store = StrategyStateStore(Path(td) / "strategy.json")
            store.save(StrategyState())
            original = app_engine.learn_from_backtest
            try:
                app_engine.learn_from_backtest = store.update_from_backtest
                result = app_engine.run_backtest(BacktestRequest(snapshots=[MarketSnapshot(symbol="005930.KS", price=72000, moving_average_short=71500, moving_average_long=70000, rsi=45, sentiment=0.4)]))
                state = store.load()
                self.assertIn("학습 반영", result.notes[-1])
                self.assertGreaterEqual(state.trade_samples, 0)
            finally:
                app_engine.learn_from_backtest = original


if __name__ == "__main__":
    unittest.main()
