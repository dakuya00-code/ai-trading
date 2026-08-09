from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


class MarketSnapshot(BaseModel):
    symbol: str = Field(..., examples=["005930.KS"])
    price: float = Field(..., gt=0)
    moving_average_short: float = Field(..., gt=0)
    moving_average_long: float = Field(..., gt=0)
    rsi: float | None = Field(default=None, ge=0, le=100)
    sentiment: float | None = Field(default=None, ge=-1, le=1)
    volume: float | None = Field(default=None, ge=0)

    @computed_field
    @property
    def trend_strength(self) -> float:
        baseline = max(self.moving_average_long, 1e-9)
        return (self.moving_average_short - self.moving_average_long) / baseline


class PredictionResponse(BaseModel):
    symbol: str
    signal: Literal["buy", "sell", "hold"]
    confidence: float
    rationale: list[str]
    model: str = "heuristic-v1"


class TradePlan(BaseModel):
    symbol: str
    signal: Literal["buy", "sell", "hold"]
    quantity: int
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float
    rationale: list[str]


class BacktestRequest(BaseModel):
    initial_cash: float = Field(default=10_000_000, gt=0)
    snapshots: list[MarketSnapshot] = Field(default_factory=list)


class BacktestResult(BaseModel):
    initial_cash: float
    final_cash: float
    trades: int
    wins: int
    losses: int
    return_pct: float
    max_drawdown_pct: float
    notes: list[str]


class PortfolioPositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    name: str = ''
    quantity: int = Field(..., ge=0)
    avg_price: float = Field(..., ge=0)
    sector: str = ''
    memo: str = ''


class PortfolioPositionResponse(PortfolioPositionRequest):
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    updated_at: str | None = None


class PortfolioSummaryResponse(BaseModel):
    positions: list[PortfolioPositionResponse]
    total_market_value: float
    total_cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    positions_count: int
    updated_at: str | None = None
    source: str = 'local'


class PortfolioUpsertResponse(BaseModel):
    ok: bool
    position: PortfolioPositionResponse


class HistoricalBacktestRequest(BaseModel):
    symbol: str = Field(..., examples=["005930.KS"])
    period: str = Field(default="1y", pattern="^(1mo|3mo|6mo|1y|2y)$")
    initial_cash: float = Field(default=10_000_000, gt=0)


class ExecutionResponse(BaseModel):
    symbol: str
    side: str
    quantity: int
    limit_price: float | None = None
    dry_run: bool
    submitted: bool
    status: str
    order_id: str | None = None
    message: str = ''
    raw: dict[str, object] = Field(default_factory=dict)
