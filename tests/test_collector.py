import unittest

from collector.kis import MockKISCollector, build_collector_from_env


class CollectorTests(unittest.TestCase):
    def test_mock_collector_returns_snapshot(self):
        collector = MockKISCollector()
        snapshot = collector.fetch_snapshot('005930.KS')
        self.assertEqual(snapshot.symbol, '005930.KS')
        self.assertGreater(snapshot.price, 0)
        self.assertGreater(snapshot.moving_average_short, 0)
        self.assertGreater(snapshot.moving_average_long, 0)

    def test_default_collector_is_mock_when_live_disabled(self):
        collector = build_collector_from_env()
        self.assertEqual(collector.status.mode, 'mock')


if __name__ == '__main__':
    unittest.main()
