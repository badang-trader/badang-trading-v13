"""Read-only combined scenario explanation. No trade recommendation or orders."""
from math import isfinite

def summarize_scenarios(support_map, analysis, divergence=None):
    """Combine independently validated evidence without manufacturing confidence."""
    if not isinstance(support_map, dict) or not isinstance(analysis, dict):
        return {"status":"unavailable","headline":"분석 자료를 확인할 수 없습니다.","long_evidence":[],"short_evidence":[]}
    if support_map.get("status")!="ok" or analysis.get("status")!="ok":
        return {"status":"data_warning","headline":"일부 분석 자료가 유효하지 않아 방향을 확정할 수 없습니다.",
                "long_evidence":[],"short_evidence":[],
                "source_status":{"support":support_map.get("status"),"analysis":analysis.get("status")}}
    long_evidence=[]
    short_evidence=[]
    price=support_map.get("reference_close")
    if type(price) not in (int,float) or not isfinite(price) or price<=0:
        return {"status":"data_warning","headline":"기준 가격을 확인할 수 없습니다.",
                "long_evidence":[],"short_evidence":[]}
    zones=support_map.get("observation_zones",[])
    if not isinstance(zones,list):
        return {"status":"data_warning","headline":"지지 구간 자료를 확인할 수 없습니다.",
                "long_evidence":[],"short_evidence":[]}
    zones=[z for z in zones if isinstance(z,dict) and type(z.get("zone_lower")) in (int,float)
           and type(z.get("zone_upper")) in (int,float)
           and isfinite(z["zone_lower"]) and isfinite(z["zone_upper"])
           and 0<z["zone_lower"]<=z["zone_upper"]<price]
    zones.sort(key=lambda z:z["zone_upper"],reverse=True)
    first=zones[0] if zones else None
    next_zone=zones[1] if len(zones)>1 else None
    if first:
        long_evidence.append("현재 가격 아래에 관찰할 과거 지지 구간이 있습니다.")
        short_evidence.append("지지 구간 아래로 종가가 확정되면 하락 위험을 다시 평가해야 합니다.")
    else:
        short_evidence.append("검증된 가까운 지지 구간을 찾지 못했습니다.")
    div=divergence if isinstance(divergence,dict) else {}
    if div.get("status") in ("mixed","bullish_observation"):
        long_evidence.append("RSI에서 상승 관련 단서가 관찰됩니다.")
    if div.get("status") in ("mixed","bearish_observation"):
        short_evidence.append("RSI에서 하락 관련 단서가 관찰됩니다.")
    trend=analysis.get("trend")
    if trend=="UP":
        long_evidence.append("기존 분석의 추세는 상승입니다.")
    elif trend=="DOWN":
        short_evidence.append("기존 분석의 추세는 하락입니다.")
    return {"status":"observation_only","headline":"상승·하락 근거를 함께 확인하고 가격 반응을 기다립니다.",
            "reference_close":price,
            "nearest_support":{"lower":first["zone_lower"],"upper":first["zone_upper"]} if first else None,
            "next_support_if_broken":{"lower":next_zone["zone_lower"],"upper":next_zone["zone_upper"]} if next_zone else None,
            "long_evidence":long_evidence,"short_evidence":short_evidence,
            "wave_candidates":analysis.get("wave_candidates",[]),
            "rebound_probability":None,"trade_signal":None,
            "warning":"지지·저항은 관찰 구간이며 매수·매도 또는 추가 진입 지시가 아닙니다."}
