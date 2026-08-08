import asyncio
import unittest

from app.events import RealtimeHub


class RealtimeTests(unittest.TestCase):
    def test_hub_fanout_to_queue(self):
        async def main():
            hub = RealtimeHub()
            hub.set_loop(asyncio.get_running_loop())
            queue = hub.subscribe()
            hub.publish({'kind': 'order', 'message': '주문 발생'})
            item = await asyncio.wait_for(queue.get(), timeout=1)
            self.assertEqual(item['kind'], 'order')
            self.assertEqual(item['message'], '주문 발생')
            hub.unsubscribe(queue)

        asyncio.run(main())


if __name__ == '__main__':
    unittest.main()
