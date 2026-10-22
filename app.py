import os, time, math, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, render_template, request
app=Flask(__name__)
BASE='https://api.bitget.com'
S=requests.Session()
API_LOCK=__import__('threading').Lock()
LAST_API_CALL=[0.0]

def api(path, params=None):
    for attempt in range(5):
        with API_LOCK:
            elapsed=time.monotonic()-LAST_API_CALL[0]
            if elapsed<0.4:
                time.sleep(0.4-elapsed)
            LAST_API_CALL[0]=time.monotonic()
            try:
                r=S.get(BASE+path,params=params,timeout=15)
                if r.status_code==429:
                    retry=True
                else:
                    r.raise_for_status()
                    j=r.json()
                    if j.get('code')=='00000':
                        return j.get('data',[])
                    if str(j.get('code')) in ('429','40015','40017'):
                        retry=True
                    else:
                        raise ValueError(str(j.get('msg','API error')))
            except requests.exceptions.RequestException:
                if attempt==4:
                    raise
                retry=True
        if retry and attempt<4:
            time.sleep(min(2*(attempt+1),8))
    raise ValueError('Bitget API 요청 제한 또는 일시적 통신 오류')
def ema(a,n):
    v=a[0]; out=[]; k=2/(n+1)
    for x in a: v=x*k+v*(1-k); out.append(v)
    return out
def rsi(a,n=14):
    gains=[]; losses=[]
    for i in range(1,len(a)):
        d=a[i]-a[i-1]; gains.append(max(0,d)); losses.append(max(0,-d))
    g=sum(gains[:n])/n; l=sum(losses[:n])/n
    for i in range(n,len(gains)): g=(g*(n-1)+gains[i])/n; l=(l*(n-1)+losses[i])/n
    return 100 if l==0 else 100-100/(1+g/l)
def pivots(a,low=True,w=3):
    return [i for i in range(w,len(a)-w) if a[i]==(min if low else max)(a[i-w:i+w+1])]
def divergence(close,rsis):
    # Only confirmed pivots; momentum series aligned with close.
    for low in (True,False):
        ps=pivots(close,low)
        if len(ps)<2: continue
        i,j=ps[-2:]
        if j-i>40: continue
        if low and close[j]<close[i] and rsis[j]>rsis[i]+2: return 'bullish'
        if not low and close[j]>close[i] and rsis[j]<rsis[i]-2: return 'bearish'
    return 'none'
def candles(symbol, gran):
    from exchange_data import fastest_candles

    result = fastest_candles(symbol, gran)
    return result['candles']
def analyze(symbol,gran):
    rows=candles(symbol,gran); c=[float(x[4]) for x in rows]; h=[float(x[2]) for x in rows]; l=[float(x[3]) for x in rows]; v=[float(x[5]) for x in rows]
    e20=ema(c,20);e50=ema(c,50);e200=ema(c,200)
    rs=[50.0]*15
    for k in range(16,len(c)+1): rs.append(rsi(c[:k]))
    rs=rs[:len(c)]
    mac=[a-b for a,b in zip(ema(c,12),ema(c,26))]; sig=ema(mac,9)
    vol=sum(v[-21:-1])/20; ratio=v[-1]/vol if vol else 0
    prev_hi=max(h[-21:-1]);prev_lo=min(l[-21:-1]); price=c[-1]
    bull=e20[-1]>e50[-1]>e200[-1] and mac[-1]>sig[-1] and 48<=rs[-1]<=72
    bear=e20[-1]<e50[-1]<e200[-1] and mac[-1]<sig[-1] and 28<=rs[-1]<=52
    div=divergence(c,rs)
    br_up=price>prev_hi and ratio>=1.2; br_down=price<prev_lo and ratio>=1.2
    # Wick-heavy breakout is considered a potential false breakout.
    rng=max(h[-1]-l[-1],1e-12); pos=(price-l[-1])/rng
    fake_up=br_up and pos<0.65; fake_down=br_down and pos>0.35
    direction='LONG' if bull else 'SHORT' if bear else 'WAIT'
    if direction=='LONG' and fake_up or direction=='SHORT' and fake_down: direction='WAIT'
    if direction=='LONG' and div=='bearish' or direction=='SHORT' and div=='bullish': direction='WAIT'
    # ATR 14, stop behind recent swing with ATR buffer.
    trs=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,len(c))]
    atr=sum(trs[-14:])/14
    stop=(min(l[-11:-1])-0.2*atr) if direction=='LONG' else (max(h[-11:-1])+0.2*atr) if direction=='SHORT' else None
    risk=abs(price-stop) if stop is not None else 0
    target=(price+2*risk if direction=='LONG' else price-2*risk if direction=='SHORT' else None)
    if risk<=0 or (target is not None and target<=0): direction='WAIT';stop=None;target=None
    return {'rows':rows,'symbol':symbol,'timeframe':gran,'price':price,'rsi':round(rs[-1],1),'volume_ratio':round(ratio,2),'divergence':div,'trend':'UP' if e20[-1]>e50[-1]>e200[-1] else 'DOWN' if e20[-1]<e50[-1]<e200[-1] else 'MIXED','breakout':'UP' if br_up else 'DOWN' if br_down else 'NONE','fake_breakout':fake_up or fake_down,'direction':direction,'stop':stop,'target':target,'support':prev_lo,'resistance':prev_hi,'last_closed':int(rows[-1][0]),'atr':atr,'swing_low':min(l[-11:-1]),'swing_high':max(h[-11:-1]),'reason':'확정봉 EMA20/50/200, MACD, RSI, 거래량 및 돌파 검증'}
def symbols(min_turnover):
    data=api('/api/v2/mix/market/tickers',{'productType':'USDT-FUTURES'})
    out=[]
    for x in data:
        try:
            sym=x['symbol']; turn=float(x.get('usdtVolume',0))
            if sym.endswith('USDT') and turn>=min_turnover: out.append((sym,turn))
        except (ValueError,KeyError,TypeError): pass
    return sorted(out,key=lambda z:z[1],reverse=True)
def flow_analysis(symbol, frame, setup):
    """Candle-based proxy, not true trade-side CVD or net capital flow."""
    rows=setup['rows']
    cl=[float(r[4]) for r in rows]; op=[float(r[1]) for r in rows]
    # Bitget candle index 6 is quote currency turnover when available.
    turnover=[float(r[6]) if len(r)>6 else float(r[5])*cl[i] for i,r in enumerate(rows)]
    signed=[(1 if cl[i]>op[i] else -1 if cl[i]<op[i] else 0)*turnover[i] for i in range(len(rows))]
    recent=sum(signed[-5:]); prior=sum(signed[-10:-5]); volume=sum(turnover[-5:]); baseline=sum(turnover[-25:-5])/4
    strength=volume/baseline if baseline>0 else 0
    pressure=recent/max(volume,1e-12)
    if strength>=1.1 and pressure>=0.16: state='BUY'
    elif strength>=1.1 and pressure<=-0.16: state='SELL'
    else: state='NEUTRAL'
    return {'state':state,'pressure':round(pressure*100,1),'turnover_ratio':round(strength,2),
      'delta_proxy':round(recent,2),'delta_change':round(recent-prior,2),
      'method':'양봉/음봉 거래대금 기반 추정치 (실제 CVD·순자금 유입 아님)',
      'oi':'UNAVAILABLE','funding':'UNAVAILABLE'}

def score_direction(setup,higher,flow,direction,lower):
    up=direction=='LONG'; trend='UP' if up else 'DOWN'; opposite='bearish' if up else 'bullish'
    score=0
    score+=25 if setup['trend']==trend else 0
    score+=20 if higher==trend else 0
    score+=15 if (setup['rsi']>=52 if up else setup['rsi']<=48) else 0
    score+=15 if (flow['state']=='BUY' if up else flow['state']=='SELL') else 0
    score+=10 if setup['volume_ratio']>=1.1 else 0
    score+=10 if lower['divergence']==('bullish' if up else 'bearish') else 0
    score+=5 if not setup['fake_breakout'] and setup['divergence']!=opposite else 0
    return score

def scenario(setup,direction,mode):
    price=setup['price']; atr=setup['atr']; up=direction=='LONG'
    if price<=0 or atr<=0: return None
    # Entry near confirmed close; not a live executable quote.
    entry=price
    stop=(min(setup['swing_low'],entry-1.2*atr) if up else max(setup['swing_high'],entry+1.2*atr))
    risk=(entry-stop) if up else (stop-entry)
    if risk<=0 or risk/entry>0.2: return None
    minimum=1.5 if mode=='scalp' else 2.0
    # TP1/TP2 are modeled R-multiple objectives, not predicted resistance.
    tp1=entry+(risk if up else -risk)*minimum
    tp2=entry+(risk if up else -risk)*(minimum+1)
    if min(stop,tp1,tp2)<=0: return None
    return {'entry':entry,'stop':stop,'tp1':tp1,'tp2':tp2,'rr1':minimum,'rr2':minimum+1,
      'invalidation':f"확정봉 종가가 {'손절선 아래' if up else '손절선 위'}에서 마감",'basis':'확정봉 종가 기준 가상 진입, 최근 구조/ATR 손절, R배수 목표'}

def scan_one(sym,mode):
    frames=['5m','15m','1H'] if mode=='scalp' else ['1H','4H','1D']
    lower,setup,higher=[analyze(sym,f) for f in frames]
    lower.pop('rows', None)
    higher.pop('rows', None)
    flow=flow_analysis(sym,frames[1],setup)
    setup.pop('rows', None)
    ls=score_direction(setup,higher['trend'],flow,'LONG',lower)
    ss=score_direction(setup,higher['trend'],flow,'SHORT',lower)
    direction='LONG' if ls>=ss else 'SHORT'
    chosen=max(ls,ss)
    aligned=setup['trend']==('UP' if direction=='LONG' else 'DOWN') and higher['trend']==setup['trend']
    opposite='bearish' if direction=='LONG' else 'bullish'
    flow_ok=flow['state']==('BUY' if direction=='LONG' else 'SELL')
    safe=not setup['fake_breakout'] and setup['divergence']!=opposite and lower['divergence']!=opposite
    plan=scenario(setup,direction,mode)
    valid=chosen>=65 and aligned and flow_ok and safe and plan is not None
    reasons=[]
    if not aligned: reasons.append('상위봉 추세 불일치')
    if not flow_ok: reasons.append('수급 추정치 미확인/반대')
    if not safe: reasons.append('다이버전스/돌파 경고')
    if plan is None: reasons.append('가격 시나리오 불가')
    if chosen<65: reasons.append('점수 부족')
    return {'symbol':sym,'mode':mode,'signal':direction if valid else 'WAIT',
      'lean':direction,'long_score':ls,'short_score':ss,'setup':setup,'higher':higher['trend'],
      'trigger':lower['divergence'],'flow':flow,'plan':plan if valid else None,
      'status':'조건부 후보 · 실제 진입 전 확인' if valid else '관망',
      'reason':', '.join(reasons) if reasons else '조건 충족 (수익 보장 아님)'}
# Watchlist symbols are evaluated regardless of signal strength or turnover filter.
MAJORS = ['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','BNBUSDT','DOGEUSDT','ADAUSDT','LINKUSDT','AVAXUSDT','SUIUSDT']
@app.route('/api/majors')
def majors():
    mode=request.args.get('mode','scalp')
    if mode not in ('scalp','swing'): return jsonify(error='잘못된 분석 모드'),400
    try:
        available={s for s,_ in symbols(0)}
    except Exception as e:
        return jsonify(error='Bitget 종목 목록 조회 실패: '+str(e)),502
    results=[]; errors=[]
    selected=[s for s in MAJORS if s in available]
    for s in MAJORS:
        if s not in available: errors.append({'symbol':s,'error':'현재 USDT 선물 종목 목록에 없음'})
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(scan_one,s,mode):s for s in selected}
        for fut in as_completed(futures):
            try: results.append(fut.result())
            except Exception as e: errors.append({'symbol':futures[fut],'error':str(e)[:120]})
    results.sort(key=lambda x:MAJORS.index(x['symbol']))
    return jsonify(results=results,errors=errors,server_time=int(time.time()))
@app.route('/')
def home(): return render_template('index.html')
@app.route('/api/scan')
def scan():
    mode=request.args.get('mode','scalp'); mode=mode if mode in ('scalp','swing') else 'scalp'
    try: minimum=max(0,float(request.args.get('min_turnover',1000000)))
    except ValueError: return jsonify(error='거래대금 설정 오류'),400
    try: syms=symbols(minimum)
    except Exception as e: return jsonify(error='Bitget 종목 조회 실패: '+str(e)),502
    # Limit work per request to protect free hosting; all eligible symbols scanned in batches by client.
    try: offset=max(0,int(request.args.get('offset',0)))
    except ValueError: offset=0
    batch=syms[offset:offset+5]; results=[]; errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(scan_one,s,mode):s for s,_ in batch}
        for fut in as_completed(futures):
            try: results.append(fut.result())
            except Exception as e: errors.append({'symbol':futures[fut],'error':str(e)[:120]})
    return jsonify(total=len(syms),offset=offset,next_offset=offset+len(batch),results=results,errors=errors,server_time=int(time.time()),recommendations=recommend_candidates(results))
def recommend_candidates(results, min_score=80, min_rr=1.5):
    candidates = []

    for item in results:
        direction = item.get('signal')
        if direction not in ('LONG', 'SHORT'):
            continue

        score = item.get(
            'long_score' if direction == 'LONG' else 'short_score',
            0
        )
        if score < min_score:
            continue

        plan = item.get('plan')
        if not isinstance(plan, dict):
            continue

        entry = plan.get('entry')
        stop = plan.get('stop')
        tp1 = plan.get('tp1')

        if any(v is None for v in (entry, stop, tp1)):
            continue

        risk = abs(entry - stop)
        reward = abs(tp1 - entry)

        if risk <= 0 or reward / risk < min_rr:
            continue

        if direction == 'LONG' and not (stop < entry < tp1):
            continue
        if direction == 'SHORT' and not (tp1 < entry < stop):
            continue

        candidate = dict(item)
        candidate['recommend_score'] = score
        candidate['recommend_direction'] = direction
        candidate['risk_reward'] = round(reward / risk, 2)
        candidates.append(candidate)

    return sorted(
        candidates,
        key=lambda x: x['recommend_score'],
        reverse=True
    )
    

@app.route('/api/test-exchanges')
def test_exchanges():
    from exchange_data import fastest_candles

    symbol = request.args.get('symbol', 'BTCUSDT')
    timeframe = request.args.get('timeframe', '5m')

    if timeframe not in ('5m', '15m', '1H', '4H', '1D'):
        return jsonify(error='Invalid timeframe'), 400

    exchange = request.args.get('exchange', 'auto').lower()
    exchanges = None if exchange == 'auto' else (exchange,)
    if exchange not in ('auto', 'bitget', 'binance', 'okx'):
        return jsonify(error='Invalid exchange'), 400

    try:
        result = fastest_candles(symbol, timeframe, exchanges=exchanges)
        return jsonify(
            status='ok',
            exchange=result['exchange'],
            symbol=result['symbol'],
            timeframe=result['timeframe'],
            candle_count=len(result['candles']),
            latency_ms=result['latency_ms']
        )
    except Exception as e:
        return jsonify(status='error', error=str(e)), 502

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
