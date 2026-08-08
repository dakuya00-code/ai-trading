from pathlib import Path
import tempfile
import unittest

from app.portfolio import PortfolioPosition, PortfolioStore, summary_from_live_holdings
from collector.kis import MockKISCollector


class PortfolioTests(unittest.TestCase):
    def test_portfolio_snapshot_calculates_multi_symbol_pnl(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(Path(tmp) / 'portfolio.json')
            store.upsert(PortfolioPosition(symbol='005930.KS', name='삼성전자', quantity=10, avg_price=70000))
            store.upsert(PortfolioPosition(symbol='000660.KS', name='SK하이닉스', quantity=5, avg_price=130000))
            summary = store.snapshot(MockKISCollector())
            self.assertEqual(summary.positions_count, 2)
            self.assertGreater(summary.total_market_value, 0)
            self.assertIn('005930.KS', {row.symbol for row in summary.positions})
            self.assertIn('000660.KS', {row.symbol for row in summary.positions})

    def test_portfolio_roundtrip_persists_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'portfolio.json'
            store = PortfolioStore(path)
            store.upsert(PortfolioPosition(symbol='005930.KS', name='삼성전자', quantity=3, avg_price=72000))
            reopened = PortfolioStore(path)
            symbols = {pos.symbol for pos in reopened.list()}
            self.assertIn('005930.KS', symbols)

    def test_live_holdings_summary_parses_kis_rows(self):
        payload = {
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
        summary = summary_from_live_holdings(payload)
        self.assertEqual(summary.positions_count, 1)
        self.assertEqual(summary.source, 'kis-live')
        self.assertEqual(summary.positions[0].symbol, '005930')


if __name__ == '__main__':
    unittest.main()
