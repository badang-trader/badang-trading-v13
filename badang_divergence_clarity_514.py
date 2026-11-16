"""Read-only explanation of simultaneous RSI divergences, without directional overclaim."""
LABELS = {
    "regular_bullish": ("반등 가능성", "가격 저점은 낮아졌지만 RSI 저점은 높아졌습니다."),
    "hidden_bearish": ("하락 지속 가능성", "가격 고점은 낮아졌지만 RSI 고점은 높아졌습니다."),
    "regular_bearish": ("하락 전환 가능성", "가격 고점은 높아졌지만 RSI 고점은 낮아졌습니다."),
    "hidden_bullish": ("상승 지속 가능성", "가격 저점은 높아졌지만 RSI 저점은 낮아졌습니다."),
}
def explain_conflict(signals):
    """Use only currently valid confirmed-pivot observations, never old/invalidated ones."""
    if not isinstance(signals, (list, tuple)):
        return {"status":"invalid_input","headline":"신호 확인 불가","items":[]}
    active = []
    for s in signals:
        if not isinstance(s, dict) or s.get("type") not in LABELS:
            continue
        if s.get("status") in ("INVALIDATED", "HISTORICAL"):
            continue
        if s.get("pivot_confirmed") is not True or s.get("recent") is not True:
            continue
        if s.get("status") != "RECENT_UNCONFIRMED_REVERSAL":
            continue
        active.append(s)
    bull = [s for s in active if "bullish" in s["type"]]
    bear = [s for s in active if "bearish" in s["type"]]
    if bull and bear:
        headline = "반등과 하락 지속 신호가 함께 있어 방향 확인이 필요합니다."
        status = "mixed"
    elif bull:
        headline = "상승 관련 단서가 있으나 가격 확인이 필요합니다."
        status = "bullish_observation"
    elif bear:
        headline = "하락 관련 단서가 있으나 가격 확인이 필요합니다."
        status = "bearish_observation"
    else:
        headline = "현재 유효한 최근 다이버전스가 확인되지 않았습니다."
        status = "no_current_signal"
    items = [{"type":s["type"],"title":LABELS[s["type"]][0],
              "meaning":LABELS[s["type"]][1],
              "timeframe":s.get("timeframe"),"pivot_time":s.get("second_time")}
             for s in active]
    return {"status":status,"headline":headline,"items":items,
            "warning":"다이버전스는 매수·매도 확정 신호가 아닙니다. 추세, 지지·저항, 거래량을 함께 확인하세요."}
