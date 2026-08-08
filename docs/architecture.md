# Architecture

- `collector/` — mock KIS snapshot collector placeholder
- `app/strategy.py` — signal heuristic
- `app/risk.py` — position sizing and stop/target generation
- `executor/` — converts trade plans to order instructions
- `agent/` — orchestrates a one-step trading loop
- `backtest/` — simple backtest runner for development
