from pathlib import Path
import tempfile
import unittest

from app.events import SQLiteEventStore


class PersistenceTests(unittest.TestCase):
    def test_sqlite_store_persists_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / 'events.db'
            store = SQLiteEventStore(db_path)
            store.record(kind='order', level='info', message='주문 기록', symbol='005930.KS', quantity=10)
            store.record(kind='fill', level='info', message='체결 기록', symbol='005930.KS', return_pct=1.23)
            self.assertEqual(store.count(), 2)
            store.close()

            reopened = SQLiteEventStore(db_path)
            events = reopened.list(limit=10)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]['kind'], 'fill')
            self.assertEqual(events[1]['kind'], 'order')
            reopened.close()


if __name__ == '__main__':
    unittest.main()
