    if os.environ.get('BADANG_DISABLE_COLLECTOR')=='1':return
    # A local lock prevents duplicate pollers across gunicorn workers on one machine.
    try:
        import fcntl
        lockfile=open('/tmp/badang_collector_v20.lock','w')
        fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
        BADANG_COLLECTOR['lockfile']=lockfile
    except (ImportError,OSError):return
    BADANG_COLLECTOR['started']=True
    threading.Thread(target=badang_collector_loop,name='badang-collector',daemon=True).start()

@app.route('/api/badang-collector')
def badang_collector_status():
    output={}
    for inst in BADANG_SYMBOLS:
        try:output[inst]=badang_observed_window(inst)
        except Exception as exc:output[inst]={'status':'ERROR','reason':type(exc).__name__}
    return jsonify(version='2.0.0',collector_running=BADANG_COLLECTOR['started'],
                   last_success=BADANG_COLLECTOR['last_success'],last_error=BADANG_COLLECTOR['last_error'],
                   instruments=output,note='REST polling cannot certify exchange-wide completeness; read-only research.')

badang_start_collector()

def research_v18(item, candles, session=None):
    """Integrate the new indicators without misrepresenting partial data as certainty."""
    inst = okx_symbol(item.get('symbol', ''))
    now = int(time.time() * 1000)
    result = {'version': '2.0.0', 'status': 'RESEARCH_ONLY', 'eligible_for_alert': False,
              'source_exchange': 'okx', 'instrument': inst, 'observed_at_ms': now,
              'collection': 'CONTINUOUS_REST_POLL_BTC_ETH' if inst in BADANG_SYMBOLS else 'ON_DEMAND', 'database_required': True,
              'vwap': vwap_from_candles(candles), 'complete_hour_cvd': False,
              'oi_change_15m_pct': None, 'oi_change_1h_pct': None,
              'oi_change_status': 'UNAVAILABLE', 'checks': {}, 'errors': {},
              'reason': '실제 거래 자료의 수집 범위를 표시하며 자동 진입 신호가 아님'}
    if not inst:
        result['data_status'] = 'UNSUPPORTED_SYMBOL';return result
    try:
        rows = fetch('/api/v5/public/open-interest', {'instType':'SWAP','instId':inst},session)
        r = next((r for r in rows if r.get('instId') == inst), None)
        ts = int(r['ts']) if r and r.get('ts') else 0
        result['oi_contracts'] = number(r.get('oi')) if r and abs(now-ts)<180000 else None
        result['oi_exchange_ts_ms'] = ts or None
    except Exception as exc:
        result['errors']['oi'] = type(exc).__name__;result['oi_contracts'] = None
    try:
        rows = fetch('/api/v5/public/funding-rate', {'instId':inst},session)
        r = next((r for r in rows if r.get('instId') == inst), None)
        result['funding_rate'] = number(r.get('fundingRate')) if r else None
    except Exception as exc:
        result['errors']['funding'] = type(exc).__name__;result['funding_rate'] = None
    history = oi_history(inst,now,session)
    result['oi_history'] = history
    result['oi_change_status'] = history['status']
    result['oi_change_15m_pct'] = history.get('change_15m_pct')
    result['oi_change_1h_pct'] = history.get('change_1h_pct')
    trades = badang_observed_window(inst) if inst in BADANG_SYMBOLS else trade_window(inst,now,session,pages=4)
    result['trade_window'] = trades
    result['trade_sample_count'] = trades['count']
    result['sample_delta_contracts'] = trades['cvd_contracts']
    result['sample_imbalance'] = trades['imbalance']
    result['sample_span_seconds'] = ((trades['newest_ts_ms']-trades['oldest_ts_ms'])/1000
                                     if trades['oldest_ts_ms'] is not None else None)
    result['cvd_15m_contracts'] = trades['cvd_contracts'] if trades['coverage_confirmed'] else None
    result['trade_vwap_15m'] = trades['vwap'] if trades['coverage_confirmed'] else None
    result['trade_vwap_status'] = trades['status']
    side = item.get('recommendation')
    imbalance = trades['imbalance']
    result['checks'] = {
        'trend_aligned': item.get('trend_aligned') is True,
        'oi_history_available': history.get('change_15m_pct') is not None,
        'recent_trade_sample_agrees': side in ('LONG','SHORT') and imbalance is not None and trades['count']>=40 and
              (imbalance >= .12 if side=='LONG' else imbalance <= -.12),
        'trade_window_complete': trades['coverage_confirmed'],
        'vwap_confirmed': side in ('LONG','SHORT') and trades['coverage_confirmed'] and trades['vwap'] is not None and
              item.get('entry_reference') is not None and
              (float(item['entry_reference']) > trades['vwap'] if side=='LONG' else float(item['entry_reference']) < trades['vwap'])
    }
    result['data_status'] = 'OI_OK_TRADES_UNVERIFIED' if history['status']=='OK' else 'PARTIAL'
    return result



@app.route('/api/badang-version')
def badang_version():
    return jsonify(version='2.0.4', mode='READ_ONLY',
        trades='BTC/ETH: continuously polled public trades in SQLite, completeness unverified',
        cvd='OBSERVED_15M_UNCERTIFIED', vwap='OBSERVED_TRADES_AND_CANDLE_APPROX',
        signals='TECHNICAL_CANDIDATES_WITH_DATA_CAVEATS',
        note='A complete historical tick feed cannot be guaranteed by bounded public REST calls.')

@app.route('/api/badang-health')
def badang_health():
    """Live OKX API diagnostics. This is NOT a trading recommendation."""
    from badang_derivatives_v15 import fetch
    checks = {}
    for name, path, params in [
        ('server_time','/api/v5/public/time',{}),
        ('btc_oi','/api/v5/public/open-interest',{'instType':'SWAP','instId':'BTC-USDT-SWAP'}),
        ('btc_funding','/api/v5/public/funding-rate',{'instId':'BTC-USDT-SWAP'}),
        ('btc_trades','/api/v5/market/history-trades',{'instId':'BTC-USDT-SWAP','limit':'1'}),
        ('btc_oi_history','/api/v5/rubik/stat/contracts/open-interest-history',{'instId':'BTC-USDT-SWAP','period':'5m','limit':'2'}),
        ('eth_oi','/api/v5/public/open-interest',{'instType':'SWAP','instId':'ETH-USDT-SWAP'}),
        ('eth_funding','/api/v5/public/funding-rate',{'instId':'ETH-USDT-SWAP'}),
        ('eth_trades','/api/v5/market/history-trades',{'instId':'ETH-USDT-SWAP','limit':'1'})
    ]:
        try:
            rows=fetch(path,params)
            checks[name]={'status':'OK' if rows else 'EMPTY','count':len(rows)}
        except Exception as exc:
            checks[name]={'status':'ERROR','error_type':type(exc).__name__}
    return jsonify(version='2.0.1', live_test=True,
                   all_ok=all(v['status']=='OK' for v in checks.values()), checks=checks,
                   note='Data API diagnostics only. Complete 15m CVD is not guaranteed.')


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
