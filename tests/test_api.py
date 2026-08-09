import unittest
from base64 import b64encode

from starlette.testclient import TestClient

from app import main as app_main
from app.main import app, backtest, backtest_historical, collector_status, execute_trade, health, live_portfolio, market_snapshot, plan, portfolio, predict, status
from app.models import BacktestRequest, MarketSnapshot
from collector.kis import MockKISCollector


class ApiTests(unittest.TestCase):

    def test_basic_auth_protects_public_surface(self):
        original_enabled = app_main.BASIC_AUTH_ENABLED
        original_user = app_main.BASIC_AUTH_USER
        original_password = app_main.BASIC_AUTH_PASSWORD
        try:
            app_main.BASIC_AUTH_ENABLED = True
            app_main.BASIC_AUTH_USER = 'admin'
            app_main.BASIC_AUTH_PASSWORD = 'secret'
            client = TestClient(app)
            response = client.get('/')
            self.assertEqual(response.status_code, 401)
            token = b64encode(b'admin:secret').decode()
            ok = client.get('/', headers={'Authorization': f'Basic {token}'})
            self.assertEqual(ok.status_code, 200)
        finally:
            app_main.BASIC_AUTH_ENABLED = original_enabled
            app_main.BASIC_AUTH_USER = original_user
            app_main.BASIC_AUTH_PASSWORD = original_password
    def test_health_and_status_endpoints(self):
        health_body = health()
        self.assertEqual(health_body['status'], 'ok')
        self.assertEqual(health_body['service'], 'model_api')
        status_body = status()
        self.assertEqual(status_body['health'], 'ok')
        self.assertIn('collector_mode', status_body)
        self.assertIn('event_count', status_body)
        self.assertIn('portfolio_positions', status_body)
        self.assertIn('portfolio_source', status_body)

    def test_collector_status_and_market_snapshot(self):
        original = app.state.collector
        try:
            app.state.collector = MockKISCollector()
            collector_body = collector_status()
            self.assertIn('mode', collector_body)
            snapshot = market_snapshot('005930.KS')
            self.assertIsInstance(snapshot, MarketSnapshot)
            self.assertEqual(snapshot.symbol, '005930.KS')
        finally:
            app.state.collector = original

    def test_portfolio_endpoint_exists(self):
        body = portfolio()
        self.assertIn('positions', body.model_dump())

    def test_live_portfolio_guard(self):
        body = portfolio()
        self.assertIn('source', body.model_dump())
        try:
            live_portfolio()
        except Exception:
            pass

    def test_live_portfolio_cache_avoids_repeat_fetches(self):
        original_collector = app.state.collector
        original_account = app_main.KIS_ACCOUNT_NO
        original_cache = getattr(app.state, 'live_portfolio_cache', None)

        class FakeStatus:
            configured = True
            mode = 'kis-live'
            last_error = None

            def to_dict(self):
                return {'mode': self.mode, 'configured': self.configured, 'last_error': self.last_error}

        class FakeCollector:
            def __init__(self):
                self.status = FakeStatus()
                self.calls = 0

            def fetch_holdings(self, account_no):
                self.calls += 1
                return {
                    'holdings': [
                        {
                            'pdno': '005930',
                            'prdt_name': '삼성전자',
                            'hldg_qty': '10',
                            'pchs_avg_pric': '70000',
                            'prpr': '72000',
                            'evlu_amt': '720000',
                            'pchs_amt': '700000',
                            'evlu_pfls_amt': '20000',
                            'evlu_pfls_rt': '2.86',
                        }
                    ]
                }

        fake = FakeCollector()
        try:
            app.state.collector = fake
            app_main.KIS_ACCOUNT_NO = '12345678-01'
            app.state.live_portfolio_cache = {'summary': None, 'fetched_at': 0.0}
            first = app_main._portfolio_view(source='live')
            second = app_main._portfolio_view(source='live')
            self.assertEqual(fake.calls, 1)
            self.assertEqual(first.positions_count, 1)
            self.assertEqual(second.positions_count, 1)
            self.assertEqual(first.source, 'kis-live')
        finally:
            app.state.collector = original_collector
            app_main.KIS_ACCOUNT_NO = original_account
            app.state.live_portfolio_cache = original_cache


    def test_strategy_state_endpoint_exists(self):
        from app.main import strategy_state
        body = strategy_state()
        self.assertIn('buy_threshold', body)
        self.assertIn('notebook_sources', body)

    def test_execute_endpoint_dry_run(self):
        from app.models import TradePlan
        payload = TradePlan(symbol='005930.KS', signal='buy', quantity=1, entry_price=72000, stop_loss=69900, take_profit=76300, confidence=0.9, rationale=['test'])
        result = execute_trade(payload)
        self.assertEqual(result.symbol, '005930.KS')
        self.assertIn(result.status, ('dry-run', 'submitted'))

    def test_historical_backtest_endpoint_exists(self):
        self.assertTrue(callable(backtest_historical))
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
