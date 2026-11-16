"""BADANG read-only research screen; separate validation WSGI entrypoint."""
from flask import jsonify, request, render_template_string
from app import app
from badang_research_history_582 import research_history
from badang_support_decision_map_research import support_decision_map
from badang_analysis_v13 import analyze
from badang_volume_profile_542 import approximate_volume_profile
from badang_support_timestamp_gate_544 import FRAME_MS
from badang_research_regimes_555 import regime_at

FRAMES = {"15m": "15m", "30m": "30m", "1h": "1H", "4h": "4H", "1d": "1D"}

@app.get("/api/research-514")
def research_514():
    symbol = request.args.get("symbol", "BTC").upper()
    frame = request.args.get("frame", "1h").lower()
    if symbol not in ("BTC", "ETH") or frame not in FRAMES:
        return jsonify({"status":"unsupported","message":"BTC/ETH and 15m/30m/1h/4h/1d only"}), 400
    mode = "swing" if frame in ("4h", "1d") else "scalp"
    try:
        history = research_history(symbol + "USDT", FRAMES[frame], target_bars=600, max_pages=5)
        if history["status"] != "ok":
            return jsonify({"status":history["status"],"confirmed_bars":history.get("confirmed_bars",0),"trading_ready":False})
        bars = history["candles"]
        close_clock = int(bars[-1][0]) + FRAME_MS[frame]
        decision = support_decision_map(bars, symbol, frame, mode, exchange_now_ms=close_clock)
        if decision["status"] != "ok":
            return jsonify({"status":decision["status"],"trading_ready":False})
        analysis = analyze(bars, mode=mode, symbol=symbol)
        if analysis.get("status") != "ok":
            return jsonify({"status":analysis.get("status"),"trading_ready":False})
        profile = approximate_volume_profile(bars)
        rows = [{"close":float(x[4])} for x in bars]
        trend = regime_at(rows,len(rows)-1)
        selected = ("ema20","ema50","ema200","rsi","macd_histogram","atr14",
                    "volume_ratio","divergences","divergence_details","wave_candidates",
                    "fibonacci","trendlines","reasons","caveats","long_score","short_score")
        return jsonify({"status":"ok","symbol":symbol,"frame":frame,"source":history["source"],
            "confirmed_bars":len(bars),"last_closed_bar_open_ms":int(bars[-1][0]),
            "last_close":float(bars[-1][4]),"trend_20bar":trend,
            "analysis":{k:analysis.get(k) for k in selected},
            "support":decision["observation_zones"],"volume_profile_poc":profile.get("poc"),
            "volume_profile_method":profile.get("method"),"warnings":decision["warnings"]+
            ["Trend is trailing 20-bar regime, not forecast",
             "Wave candidates and divergence are unconfirmed, not guaranteed",
             "OI/CVD not included without verified live sources",
             "No auto trading, order execution or averaging down"],
            "trading_ready":False})
    except (ValueError, TypeError, KeyError) as exc:
        return jsonify({"status":"data_error","message":str(exc),"trading_ready":False}), 422
    except Exception:
        app.logger.exception("research 514 failed")
        return jsonify({"status":"source_unavailable","message":"Exchange data unavailable; retry later","trading_ready":False}), 503

PAGE = """<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BADANG 5.14 연구 검증</title><style>body{font-family:system-ui;background:#101b2c;color:#f1f5fa;margin:0;padding:18px;max-width:850px;margin:auto}h1{font-size:24px}select,button{font-size:17px;padding:12px;border-radius:8px;border:0;margin:5px}button{background:#3a8bdc;color:white}section{background:#1b2b40;border-radius:12px;padding:16px;margin:12px 0}pre{white-space:pre-wrap;word-break:break-word;font-size:13px;color:#d5e5f5}small{color:#b8c8dc}a{color:#8ac5ff}.zone{border-bottom:1px solid #496078;padding:12px 0}</style>
<h1>BADANG Trading 5.14 · 연구 검증</h1><p>직접 검색하고 대응하는 분석 화면 · 주문 실행 없음</p>
<label>코인 <select id="symbol"><option>BTC</option><option>ETH</option></select></label>
<label>시간봉 <select id="frame"><option>15m</option><option>30m</option><option selected>1h</option><option>4h</option><option>1d</option></select></label>
<button onclick="search()">분석 검색</button><p><a href="/">기존 전체 스캐너 열기</a></p><div id="out"><small>검색을 누르면 확정된 Bitget 봉으로 분석합니다.</small></div>
<script>
function esc(x){return String(x??'정보 없음').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function fmt(x){return typeof x==='number'?x.toLocaleString('en-US',{maximumFractionDigits:4}):esc(x)}
async function search(){
let out=document.getElementById('out');out.textContent='거래소 확정봉 조회 및 분석 중...';
try{let s=document.getElementById('symbol').value,f=document.getElementById('frame').value;
let r=await fetch('/api/research-514?symbol='+encodeURIComponent(s)+'&frame='+encodeURIComponent(f));let d=await r.json();
if(d.status!=='ok'){out.innerHTML='<section>분석 불가: '+esc(d.status)+' '+esc(d.message||'')+'</section>';return}
let a=d.analysis;
let zones=d.support.map(z=>'<div class="zone"><b>'+z.order+'차 지지 관찰: '+fmt(z.zone_lower)+' ~ '+fmt(z.zone_upper)+'</b><p>근거 등급: '+esc(z.evidence_grade)+' / 참고 점수: '+fmt(z.evidence_score_not_probability)+' (확률 아님)</p><small>무효화: '+esc(z.invalidated_if)+' / 다음 지지: '+(z.next_observation_zone?fmt(z.next_observation_zone.lower)+' ~ '+fmt(z.next_observation_zone.upper):'표시 가능한 구간 없음')+'</small></div>').join('');
out.innerHTML='<section><h2>'+esc(d.symbol)+' / '+esc(d.frame)+'</h2><p>마지막 확정 종가: <b>'+fmt(d.last_close)+'</b></p><p>20봉 추세: '+esc(d.trend_20bar)+' · 확정봉 '+d.confirmed_bars+'개</p><small>데이터: '+esc(d.source)+'</small></section>'+
'<section><h2>지지 구간 · 선택과 대응</h2>'+(zones||'검증 가능한 지지 구간 없음. 임의 매수 지점은 만들지 않습니다.')+'</section>'+
'<section><h2>기술적 분석</h2><p>EMA20 '+fmt(a.ema20)+' · EMA50 '+fmt(a.ema50)+' · EMA200 '+fmt(a.ema200)+'</p><p>RSI '+fmt(a.rsi)+' · MACD 히스토그램 '+fmt(a.macd_histogram)+' · ATR '+fmt(a.atr14)+'</p><p>거래량 비율 '+fmt(a.volume_ratio)+' · 매물대 추정 POC '+fmt(d.volume_profile_poc)+'</p><p>롱 근거 점수 '+fmt(a.long_score)+' · 숏 근거 점수 '+fmt(a.short_score)+' (수익 확률 아님)</p></section>'+
'<section><h2>엘리엇 파동 후보 · 피보나치 · 다이버전스</h2><pre>'+esc(JSON.stringify({waves:a.wave_candidates,fibonacci:a.fibonacci,divergences:a.divergence_details,trendlines:a.trendlines},null,2))+'</pre></section>'+
'<section><h2>분석 근거 및 한계</h2><pre>'+esc(JSON.stringify({reasons:a.reasons,warnings:d.warnings},null,2))+'</pre></section>';
}catch(e){out.textContent='조회 실패: '+e.message}}
</script></html>"""

@app.get("/research")
def research_page():
    return render_template_string(PAGE)
