from unittest import TestCase

from app.dashboard import dashboard_html


class DashboardTests(TestCase):
    def test_dashboard_contains_key_sections(self):
        html = dashboard_html()
        self.assertIn('ai-trading 모니터링 대시보드', html)
        self.assertIn('/predict', html)
        self.assertIn('/plan', html)
        self.assertIn('/backtest', html)
        self.assertIn('8010', html)
