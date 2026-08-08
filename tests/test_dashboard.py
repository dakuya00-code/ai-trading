from unittest import TestCase

from app.dashboard import dashboard_html


class DashboardTests(TestCase):
    def test_dashboard_contains_tabs_and_monitoring_features(self):
        html = dashboard_html()
        self.assertIn('ai-trading 모니터링', html)
        self.assertIn('개요', html)
        self.assertIn('차트', html)
        self.assertIn('주문·체결 로그', html)
        self.assertIn('보유현황', html)
        self.assertIn('KIS 수집기', html)
        self.assertIn('/events', html)
        self.assertIn('/collector/status', html)
        self.assertIn('/market/', html)
        self.assertIn('chartCanvas', html)
        self.assertIn('autoRefresh', html)
        self.assertIn('refreshEvery', html)
        self.assertIn('portfolioPick', html)
        self.assertIn('tagPortfolio', html)
        self.assertIn('selectedCurrentPrice', html)
        self.assertIn('selectedUnrealizedPnl', html)
        self.assertIn('refreshState', html)
        self.assertIn('marketAwareRefresh', html)
        self.assertIn('원시 포트폴리오 JSON', html)
