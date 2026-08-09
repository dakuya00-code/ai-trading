from __future__ import annotations

from app.models import MarketSnapshot, PredictionResponse
from app.strategy_state import StrategyState, load_strategy_state


def predict_signal(snapshot: MarketSnapshot, state: StrategyState | None = None) -> PredictionResponse:
    state = state or load_strategy_state()
    score = 0.0
    rationale: list[str] = []

    trend_strength = getattr(snapshot, 'trend_strength', 0.0) or 0.0
    if snapshot.moving_average_short > snapshot.moving_average_long:
        score += state.trend_weight
        rationale.append("단기 이동평균이 장기 이동평균보다 높습니다.")
    elif snapshot.moving_average_short < snapshot.moving_average_long:
        score -= state.trend_weight
        rationale.append("단기 이동평균이 장기 이동평균보다 낮습니다.")

    if snapshot.price > snapshot.moving_average_long:
        score += state.price_weight
        rationale.append("현재가가 장기 이동평균 위에 있습니다.")
    elif snapshot.price < snapshot.moving_average_long:
        score -= state.price_weight
        rationale.append("현재가가 장기 이동평균 아래에 있습니다.")

    if trend_strength:
        if trend_strength > 0:
            score += min(0.15, trend_strength * 5)
            rationale.append(f"추세 강도는 양수입니다({trend_strength:.4f}).")
        else:
            score += max(-0.15, trend_strength * 5)
            rationale.append(f"추세 강도는 음수입니다({trend_strength:.4f}).")

    if snapshot.rsi is not None:
        if snapshot.rsi < 30:
            score += state.rsi_weight
            rationale.append("RSI가 과매도 구간입니다.")
        elif snapshot.rsi > 70:
            score -= state.rsi_weight
            rationale.append("RSI가 과매수 구간입니다.")
        else:
            rationale.append("RSI가 중립 구간입니다.")

    if snapshot.sentiment is not None:
        score += snapshot.sentiment * state.sentiment_weight
        if snapshot.sentiment > 0:
            rationale.append("외부 심리가 긍정적입니다.")
        elif snapshot.sentiment < 0:
            rationale.append("외부 심리가 부정적입니다.")

    if score >= state.buy_threshold:
        signal = "buy"
    elif score <= state.sell_threshold:
        signal = "sell"
    else:
        signal = "hold"

    threshold = max(abs(state.buy_threshold), abs(state.sell_threshold), 1e-9)
    confidence = min(0.99, max(0.05, abs(score) / threshold))
    rationale.append(f"현재 임계값은 buy>={state.buy_threshold:.2f}, sell<={state.sell_threshold:.2f} 입니다.")
    if not rationale:
        rationale.append("입력된 지표가 제한적이어서 중립으로 판단했습니다.")

    return PredictionResponse(
        symbol=snapshot.symbol,
        signal=signal,
        confidence=round(confidence, 3),
        rationale=rationale,
    )
