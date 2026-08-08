import unittest

from agent.loop import TradingLoop
from collector.kis import MockKISCollector


class AgentTests(unittest.TestCase):
    def test_trading_loop_returns_plan_and_order(self):
        loop = TradingLoop(collector=MockKISCollector())
        result = loop.step("005930.KS")
        self.assertEqual(result["plan"]["symbol"], "005930.KS")
        self.assertIsNotNone(result["order"])


if __name__ == "__main__":
    unittest.main()
