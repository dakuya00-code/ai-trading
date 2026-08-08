import os
import unittest
from contextlib import contextmanager

from collector.kis import MockKISCollector, build_collector_from_env


@contextmanager
def unset_live_env():
    keys = ['KIS_ENABLE_LIVE', 'KIS_APP_KEY', 'KIS_APP_SECRET', 'KIS_ACCESS_TOKEN', 'KIS_ACCOUNT_NO']
    saved = {k: os.environ.get(k) for k in keys}
    try:
        for k in keys:
            os.environ.pop(k, None)
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class CollectorTests(unittest.TestCase):
    def test_mock_collector_returns_snapshot(self):
        collector = MockKISCollector()
        snapshot = collector.fetch_snapshot('005930.KS')
        self.assertEqual(snapshot.symbol, '005930.KS')
        self.assertGreater(snapshot.price, 0)
        self.assertGreater(snapshot.moving_average_short, 0)
        self.assertGreater(snapshot.moving_average_long, 0)

    def test_default_collector_is_mock_when_live_disabled(self):
        with unset_live_env():
            collector = build_collector_from_env()
            self.assertEqual(collector.status.mode, 'mock')


if __name__ == '__main__':
    unittest.main()
