from __future__ import annotations

from app.models import MarketSnapshot, PredictionResponse


def predict_signal(snapshot: MarketSnapshot) -> PredictionResponse:
    score = 0.0
    rationale: list[str] = []

    if snapshot.moving_average_short > snapshot.moving_average_long:
        score += 0.5
        rationale.append("단기 이동평균이 장기 이동평균보다 높습니다.")
    elif snapshot.moving_average_short < snapshot.moving_average_long:
        score -= 0.5
        rationale.append("단기 이동평균이 장기 이동평균보다 낮습니다.")

    if snapshot.price > snapshot.moving_average_long:
        score += 0.25
        rationale.append("현재가가 장기 이동평균 위에 있습니다.")
    elif snapshot.price < snapshot.moving_average_long:
        score -= 0.25
        rationale.append("현재가가 장기 이동평균 아래에 있습니다.")

    if snapshot.rsi is not None:
        if snapshot.rsi < 30:
            score += 0.2
            rationale.append("RSI가 과매도 구간입니다.")
        elif snapshot.rsi > 70:
            score -= 0.2
            rationale.append("RSI가 과매수 구간입니다.")
        else:
            rationale.append("RSI가 중립 구간입니다.")

    if snapshot.sentiment is not None:
        score += snapshot.sentiment * 0.3
        if snapshot.sentiment > 0:
            rationale.append("외부 심리가 긍정적입니다.")
        elif snapshot.sentiment < 0:
            rationale.append("외부 심리가 부정적입니다.")

    if score >= 0.35:
        signal = "buy"
    elif score <= -0.35:
        signal = "sell"
    else:
        signal = "hold"

    confidence = min(0.99, max(0.05, abs(score)))
    if not rationale:
        rationale.append("입력된 지표가 제한적이어서 중립으로 판단했습니다.")

    return PredictionResponse(
        symbol=snapshot.symbol,
        signal=signal,
        confidence=round(confidence, 3),
        rationale=rationale,
    )
