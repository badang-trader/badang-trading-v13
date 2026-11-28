"""Replay v13 technical candidates and final review on closed Bitget candles."""
import argparse
import json
from bisect import bisect_right
from datetime import datetime
from pathlib import Path

from app import (
    ROUNDTRIP_FEE_PCT, ROUNDTRIP_SLIPPAGE_PCT, V13_MODE_FRAMES,
    apply_v13_entry_checks, inspect_frame_410, price_action_45,
    v13_current_structure, v13_trend,
)
from badang_analysis_v13 import analyze, ema, technical_direction
from badang_censored_equity_replay import replay
from badang_decision_427 import decision_review, structure_review
from badang_historical_integrity import FRAME_MS, audit_historical_candles
from badang_prospective_holdout_gate import audit_nonoverlap
from badang_signal_audit_439 import reconcile
from badang_walkforward_audit import audit_trades


REPLAY_WINDOW_BARS = 350
BANDS = ('80-84', '85-89', '90+')


def collect_signals(histories, symbol, mode, cutoff, *, reviews=None):
    frames = V13_MODE_FRAMES[mode]
    setup = frames[0]
    rows = histories[symbol, setup]
    closes = {tf: [row[0] + FRAME_MS[tf] for row in histories[symbol, tf]] for tf in frames}
    technical, ready = [], []
    counts = {'scored_bars': 0, 'trend_aligned_signals': 0, 'price_action_signals': 0,
              'entry_checks_passed': 0, 'final_review_signals': 0}
    for index, bar in enumerate(rows):
        if bar[0] <= cutoff:
            continue
        as_of = closes[setup][index]
        prefixes = {}
        for tf in frames:
            end = bisect_right(closes[tf], as_of)
            if end < 205 or as_of - closes[tf][end - 1] >= FRAME_MS[tf]:
                break
            prefixes[tf] = histories[symbol, tf][max(0, end - REPLAY_WINDOW_BARS):end]
        if len(prefixes) != len(frames):
            continue

        counts['scored_bars'] += 1
        output = analyze(prefixes[setup], mode=mode, symbol=symbol)
        if output.get('status') != 'ok':
            raise ValueError(f'Invalid technical result {symbol}/{mode}/{bar[0]}')
        output.update(technical_direction(output))
        side, score = output['technical_side'], output['technical_score']
        if score < 80 or side not in ('LONG', 'SHORT'):
            continue
        signal = {'bar': index, 'known_at_bar': index, 'signal_timestamp': bar[0],
                  'mode': mode, 'side': side, 'score': score}
        technical.append(dict(signal, stop=output['stop_loss'], target=output['take_profit_1']))
        trends, current_structure = {}, {}
        for tf, prefix in prefixes.items():
            series = [row[4] for row in prefix]
            e20, e50 = ema(series, 20)[-1], ema(series, 50)[-1]
            trends[tf] = v13_trend(e20, e50)
            current_structure[tf] = v13_current_structure(series[-1], e20, e50)
        expected = 'UP' if side == 'LONG' else 'DOWN'
        counts['trend_aligned_signals'] += all(trend == expected for trend in trends.values())

        # Existing scanner functions ignore the final row. Use an excluded
        # marker at the next opening timestamp without reading that future bar.
        inputs = {tf: prefix + [[prefix[-1][0] + FRAME_MS[tf], *prefix[-1][1:]]]
                  for tf, prefix in prefixes.items()}
        action = price_action_45(inputs[setup], trends, mode)
        review = {
            'symbol': symbol, 'mode': mode, 'signal_close_ms': as_of, 'technical_side': side,
            'technical_score': score, 'trends': trends, 'price_action_side': action.get('side'),
            'price_action': action.get('kind'), 'blocked_by': [],
        }
        if reviews is not None:
            reviews.append(review)
        if action.get('side') not in ('LONG', 'SHORT'):
            review.update(stage='PRICE_ACTION_WAIT', blocked_by=[
                {'check': 'price_action', 'reason': action['reason']}])
            continue
        counts['price_action_signals'] += 1
        audits = {tf: inspect_frame_410({'candles': data, 'exchange': 'bitget'}, tf, as_of)
                  for tf, data in inputs.items()}
        output.update(exchange='bitget', analysis_reference_price=output['entry_reference'])
        apply_v13_entry_checks(output, action, trends, audits, current_structure, mode)
        precision = output['signal_precision_418']
        if precision['status'] != 'CANDIDATE':
            review.update(stage='ENTRY_CHECKS_WAIT', blocked_by=[
                {'check': name, 'reason': check['reason'],
                 **({'evidence': check['evidence']} if 'evidence' in check else {})}
                for name, check in precision['checks'].items()
                if not check['passed'] and check.get('applicable', True)
            ])
            continue
        counts['entry_checks_passed'] += 1
        structures = {tf: structure_review(data, tf, as_of) for tf, data in inputs.items()}
        decision = decision_review(output, structures, mode)
        output['decision_427'] = decision
        if decision['state'] != 'READY_REVIEW':
            review.update(stage='DECISION_WAIT', blocked_by=[
                {'check': 'decision', 'reason': reason} for reason in decision['reasons']])
            continue
        reconciliation = reconcile(output)
        if reconciliation['status'] != 'REVIEW_ONLY':
            review.update(stage='RECONCILIATION_WAIT', blocked_by=[
                {'check': 'reconciliation', 'reason': reason} for reason in reconciliation['reasons']])
            continue
        review['stage'] = 'READY_REVIEW'
        counts['final_review_signals'] += 1
        plan = decision['plan']
        ready.append(dict(signal, stop=plan['stop'], target=plan['tp1']))
    return technical, ready, counts


def audit_signals_on_15m(rows, signals, signal_timeframe):
    """Fill after signal confirmation and use one observable clock for exits."""
    step = FRAME_MS['15m']
    close_indices = {row[0] + step: index for index, row in enumerate(rows)}
    indexed = []
    missing = 0
    for signal in signals:
        signal_close = signal['signal_timestamp'] + FRAME_MS[signal_timeframe]
        index = close_indices.get(signal_close)
        if index is None:
            missing += 1
            continue
        # audit_trades will enter at the next bar open. The mapped row
        # ends at the signal close and its price never enters the trade.
        indexed.append(dict(signal, bar=index, known_at_bar=index, signal_timestamp=rows[index][0]))
    report = audit_trades(rows, indexed, fee_rate=ROUNDTRIP_FEE_PCT / 200,
                          slippage_rate=ROUNDTRIP_SLIPPAGE_PCT / 200)
    trades = [dict(trade, timeframe='15m', signal_timeframe=signal_timeframe)
              for trade in report['trades']]
    return trades, missing


def group_metrics(trades):
    """Closed trades determine outcome statistics. Open trades stay censored."""
    groups = []
    for mode in V13_MODE_FRAMES:
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
        # Recognize executions and mark all positions on the Bitget 15m grid.
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


def trade_ledger(trades):
    """Expose stable position keys and separate realized exits from open marks."""
    rows = []
    for trade in sorted(trades, key=lambda t: (t['entry_timestamp'], t['symbol'], t['mode'])):
        duration = FRAME_MS[trade['timeframe']]
        last_close = trade['exit_timestamp'] + duration
        is_open = trade['exit_reason'] == 'END_OF_DATA'
        rows.append({
            'symbol': trade['symbol'], 'mode': trade['mode'], 'side': trade['side'],
            'score_band': trade['band'],
            'signal_timeframe': trade['signal_timeframe'], 'execution_timeframe': trade['timeframe'],
            'signal_close_ms': trade['signal_timestamp'] + duration,
            'entry_ms': trade['entry_timestamp'], 'entry': trade['entry_price'],
            'stop': trade['stop_price'], 'target': trade['target_price'],
            'status': 'OPEN' if is_open else 'CLOSED',
            'exit_reason': None if is_open else trade['exit_reason'],
            'exit_confirmed_close_ms': None if is_open else last_close,
            'exit_price': None if is_open else trade['exit_price'],
            'realized_net_return': None if is_open else trade['net_return'],
            'mark_close_ms': last_close if is_open else None,
            'mark_price': trade['exit_price'] if is_open else None,
        })
    return rows


def run(folder, cutoff, *, end_ms=None):
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

    available_end = min(rows[-1][0] + FRAME_MS[tf]
                        for (_, tf), rows in histories.items() if tf == '15m')
    end = available_end if end_ms is None else end_ms
    if end_ms is not None and (type(end) is not int or not cutoff < end <= available_end
                               or end % FRAME_MS['15m']):
        raise ValueError('Replay end must be a verifiable 15m close after cutoff')
    histories = {key: [row for row in rows if row[0] + FRAME_MS[key[1]] <= end]
                 for key, rows in histories.items()}
    cohorts, reviews = [], []
    trades = {'technical': [], 'final_review': []}
    for symbol in ('BTC', 'ETH'):
        for mode, (setup, *_) in V13_MODE_FRAMES.items():
            rows = histories[symbol, setup]
            eligible_rows = [row for row in rows if row[0] > cutoff]
            gate = audit_nonoverlap(eligible_rows, cutoff=cutoff, min_bars=1)
            technical, ready, counts = collect_signals(histories, symbol, mode, cutoff, reviews=reviews)
            fills, missing_execution = {}, {}
            for scope, signals in (('technical', technical), ('final_review', ready)):
                executions, missing_execution[scope] = audit_signals_on_15m(
                    histories[symbol, '15m'], signals, setup)
                trades[scope].extend(dict(trade, symbol=symbol) for trade in executions)
                fills[scope] = len(executions)
            cohorts.append({'symbol': symbol, 'mode': mode, 'post_cutoff_bars': len(eligible_rows),
                            'temporal_gate': gate['status'] if eligible_rows else 'NO_POST_CUTOFF_BARS',
                            **counts, 'technical_signals': len(technical),
                            'filled_positions': fills['technical'], 'final_review_fills': fills['final_review'],
                            'signals_without_execution_coverage': missing_execution})
    return {'source': 'BITGET_PUBLIC_HISTORY_API', 'cutoff_ms': cutoff, 'end_ms': end,
            'status': 'DESCRIPTIVE_ONLY' if trades['technical'] else 'NO_FILLED_POSITIONS',
            'scope': 'Technical candidate and final scanner review; historical OI/CVD unavailable',
            'analysis_window_max_bars': REPLAY_WINDOW_BARS,
            'execution_timeframe': '15m',
            'execution': 'Next 15m open after signal close, first target only, stop first on same 15m bar, '
                         'costs on both sides, one position per symbol and mode',
            'cohorts': cohorts, 'groups': group_metrics(trades['technical']),
            'account': account_metrics(trades['technical'], histories, cutoff, end),
            'trades': trade_ledger(trades['technical']),
            'final_review': {
                'status': 'DESCRIPTIVE_ONLY' if trades['final_review'] else 'NO_FILLED_POSITIONS',
                'reviews': sorted(reviews, key=lambda row: (row['signal_close_ms'], row['symbol'], row['mode'])),
                'groups': group_metrics(trades['final_review']),
                'trades': trade_ledger(trades['final_review']),
                'account': account_metrics(trades['final_review'], histories, cutoff, end),
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', type=Path)
    parser.add_argument('--cutoff', required=True, help='Prior research boundary in ISO 8601 with timezone.')
    parser.add_argument('--end', help='Optional fixed 15m close in ISO 8601 with timezone.')
    args = parser.parse_args()
    bounds = {}
    for name in ('cutoff', 'end'):
        value = getattr(args, name)
        if value is None:
            continue
        try:
            instant = datetime.fromisoformat(value)
        except ValueError:
            parser.error(f'--{name} must be an ISO 8601 timestamp')
        if instant.tzinfo is None:
            parser.error(f'--{name} must include a timezone')
        bounds[name] = int(instant.timestamp() * 1000)
    print(json.dumps(run(args.history, bounds['cutoff'], end_ms=bounds.get('end')), indent=2))


if __name__ == '__main__':
    main()
