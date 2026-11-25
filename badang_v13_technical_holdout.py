"""Replay v13's technical candidate list on verified Bitget candle prefixes."""
import argparse
import json
from bisect import bisect_right
from datetime import datetime
from pathlib import Path

from app import ROUNDTRIP_FEE_PCT, ROUNDTRIP_SLIPPAGE_PCT
from badang_analysis_v13 import analyze, ema, technical_direction
from badang_censored_equity_replay import replay
from badang_historical_integrity import FRAME_MS, audit_historical_candles
from badang_prospective_holdout_gate import audit_nonoverlap
from badang_walkforward_audit import audit_trades


MODES = {'scalp': ('15m', '30m', '1H'), 'swing': ('1H', '4H', '1D')}
BANDS = ('80-84', '85-89', '90+')


def collect_signals(histories, symbol, mode, cutoff):
    frames = MODES[mode]
    setup = frames[0]
    rows = histories[symbol, setup]
    closes = {tf: [row[0] + FRAME_MS[tf] for row in histories[symbol, tf]] for tf in frames}
    signals = []
    eligible, trend_aligned = 0, 0
    for index, bar in enumerate(rows):
        if bar[0] <= cutoff:
            continue
        as_of = closes[setup][index]
        prefixes = {}
        for tf in frames:
            end = bisect_right(closes[tf], as_of)
            keys = histories[symbol, tf]
            if end < 205 or as_of - closes[tf][end - 1] >= FRAME_MS[tf]:
                break
            # Match the live indicator warmup minimum and use only what had closed.
            prefixes[tf] = keys[max(0, end - 300):end]
        if len(prefixes) != len(frames):
            continue
        eligible += 1
        output = analyze(prefixes[setup], mode=mode, symbol=symbol)
        candidate = technical_direction(output)
        side, score = candidate['technical_side'], candidate['technical_score']
        if score < 80 or side not in ('LONG', 'SHORT'):
            continue
        aligned = True
        for tf, prefix in prefixes.items():
            series = [row[4] for row in prefix]
            delta = ema(series, 20)[-1] - ema(series, 50)[-1]
            if not (delta > 0 if side == 'LONG' else delta < 0):
                aligned = False
        trend_aligned += aligned
        signals.append({'bar': index, 'known_at_bar': index,
                        'signal_timestamp': bar[0], 'mode': mode, 'side': side,
                        'score': score, 'stop': output['stop_loss'],
                        'target': output['take_profit_1']})
    return signals, eligible, trend_aligned


def group_metrics(trades):
    """Closed trades determine outcome statistics. Open trades stay censored."""
    groups = []
    for mode in MODES:
        for side in ('LONG', 'SHORT'):
            for band in BANDS:
                selected = [t for t in trades if (t['mode'], t['side'], t['band']) == (mode, side, band)]
                closed = sorted((t for t in selected if t['exit_reason'] != 'END_OF_DATA'),
                                key=lambda t: t['exit_timestamp'] + FRAME_MS[t['timeframe']])
                returns = [t['net_return'] for t in closed]
                equity = peak = 1.
                drawdown = max_streak = streak = 0
                for value in returns:
                    equity *= max(0, 1 + value)
                    peak = max(peak, equity)
                    drawdown = max(drawdown, (peak - equity) / peak)
                    streak = streak + 1 if value < 0 else 0
                    max_streak = max(max_streak, streak)
                groups.append({
                    'mode': mode, 'side': side, 'band': band, 'closed': len(returns),
                    'open': len(selected) - len(returns),
                    'win_rate': sum(value > 0 for value in returns) / len(returns) if returns else None,
                    'unit_notional_net_return': equity - 1 if returns else None,
                    'closed_trade_drawdown': drawdown if returns else None,
                    'max_consecutive_losses': max_streak if returns else None,
                })
    return groups


def account_metrics(trades, histories, cutoff, end):
    events = []
    for i, t in enumerate(trades):
        # Mark all positions on the same 15m Bitget grid while preserving
        # each strategy's close time for exit recognition.
        event = {'id': str(i), 'symbol': t['symbol'], 'timeframe': '15m',
                 'side': t['side'], 'entry_ts': t['entry_timestamp'],
                 'entry_price': t['entry_price'], 'leverage': 1,
                 'reason': 'END_OF_DATA' if t['exit_reason'] == 'END_OF_DATA' else 'CLOSED'}
        if event['reason'] == 'CLOSED':
            event.update(exit_ts=t['exit_timestamp'] + FRAME_MS[t['timeframe']],
                         net_return=t['net_return'])
        events.append(event)
    if not events:
        return {'status': 'NO_FILLED_POSITIONS', 'observed_close_drawdown': None}
    timestamps = {row[0] + FRAME_MS['15m'] for row in histories['BTC', '15m']
                  if cutoff < row[0] + FRAME_MS['15m'] <= end}
    result = replay(events, histories, timestamps)
    snapshots = result['snapshots']
    peak = 10000.
    drawdown = 0.
    for snap in snapshots:
        equity = snap['strict_observed_equity']
        if equity is not None:
            peak = max(peak, equity)
            drawdown = max(drawdown, (peak - equity) / peak)
    return {
        'status': 'BITGET_15M_CLOSE_MARKS', 'initial_capital': 10000,
        'realized_pnl': snapshots[-1]['realized_pnl'],
        'final_unrealized_pnl': snapshots[-1]['observed_unrealized_pnl'],
        'observed_close_drawdown': drawdown,
        'peak_concurrent_positions': max(snap['active_count'] for snap in snapshots),
        'open_positions': len(result['unclosed_ids']),
        'missing_equity_marks': sum(snap['strict_observed_equity'] is None for snap in snapshots),
        'margin_rejections': len(result['rejected']),
        'assumptions': 'Unleveraged, 5% initial allocation per trade, 30% aggregate cap, no intrabar equity.',
    }


def run(folder, cutoff):
    histories = {}
    for symbol in ('BTC', 'ETH'):
        for tf in FRAME_MS:
            payload = json.loads((folder / f'{symbol}_{tf}.json').read_text())
            provenance = payload['provenance']
            if (provenance['source'] != 'BITGET_PUBLIC_HISTORY_API'
                    or provenance['instrument'] != symbol + 'USDT'
                    or provenance['productType'] != 'USDT-FUTURES'):
                raise ValueError(f'Unexpected data provenance: {symbol}/{tf}')
            rows = payload['candles']
            audit_historical_candles(rows, tf, asof_ms=provenance['asof_ms'])
            histories[symbol, tf] = rows

    end = min(rows[-1][0] + FRAME_MS[tf] for (_, tf), rows in histories.items() if tf == '15m')
    histories = {key: [row for row in rows if row[0] + FRAME_MS[key[1]] <= end]
                 for key, rows in histories.items()}
    cohorts, trades = [], []
    for symbol in ('BTC', 'ETH'):
        for mode, (setup, *_) in MODES.items():
            rows = histories[symbol, setup]
            eligible_rows = [row for row in rows if row[0] > cutoff]
            gate = audit_nonoverlap(eligible_rows, cutoff=cutoff, min_bars=1)
            signals, analyzed, aligned = collect_signals(histories, symbol, mode, cutoff)
            report = audit_trades(rows, signals, fee_rate=ROUNDTRIP_FEE_PCT / 200,
                                  slippage_rate=ROUNDTRIP_SLIPPAGE_PCT / 200)
            trades.extend(dict(t, symbol=symbol, timeframe=setup) for t in report['trades'])
            cohorts.append({'symbol': symbol, 'mode': mode, 'post_cutoff_bars': len(eligible_rows),
                            'temporal_gate': gate['status'] if eligible_rows else 'NO_POST_CUTOFF_BARS', 'scored_bars': analyzed,
                            'technical_signals': len(signals), 'trend_aligned_signals': aligned,
                            'filled_positions': len(report['trades'])})
    return {'source': 'BITGET_PUBLIC_HISTORY_API', 'cutoff_ms': cutoff, 'end_ms': end,
            'status': 'DESCRIPTIVE_ONLY' if trades else 'NO_FILLED_POSITIONS',
            'scope': 'v13 technical candidate score and indicative levels only; no OI/CVD or final price-action gate',
            'execution': 'Next open, stop first on collision, costs on both sides, one position per symbol and mode',
            'cohorts': cohorts, 'groups': group_metrics(trades),
            'account': account_metrics(trades, histories, cutoff, end)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', type=Path)
    parser.add_argument('--cutoff', required=True, help='Prior research boundary in ISO 8601 with timezone.')
    args = parser.parse_args()
    cutoff = datetime.fromisoformat(args.cutoff)
    if cutoff.tzinfo is None:
        parser.error('--cutoff must include a timezone')
    print(json.dumps(run(args.history, int(cutoff.timestamp() * 1000)), indent=2))


if __name__ == '__main__':
    main()
