"""Read-only position scenario math; never generates orders or entry signals."""
import math

def _number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def position_scenario(side, existing_quantity, existing_entry, added_quantity,
                      added_entry, exit_price, fee_pct=0, slippage_pct=0):
    """Compute weighted entry and hypothetical P/L for linear USDT contracts.

    Quantities are base-asset units, not margin or leveraged notional.
    Fees/slippage are assumed percentages of entry+exit notional.
    """
    if side not in ('LONG', 'SHORT'):
        raise ValueError('side must be LONG or SHORT')
    nums = [_number(v) for v in (existing_quantity, existing_entry,
                                 added_quantity, added_entry, exit_price,
                                 fee_pct, slippage_pct)]
    if any(v is None for v in nums):
        raise ValueError('all inputs must be finite numbers')
    q0, p0, q1, p1, px, fee, slip = nums
    if q0 < 0 or q1 < 0 or q0 + q1 <= 0 or px <= 0 or fee < 0 or slip < 0:
        raise ValueError('invalid quantity, price or cost')
    if (q0 > 0 and p0 <= 0) or (q1 > 0 and p1 <= 0):
        raise ValueError('active entry price must be positive')
    quantity = q0 + q1
    entry_notional = q0 * p0 + q1 * p1
    average = entry_notional / quantity
    exit_notional = quantity * px
    sign = 1 if side == 'LONG' else -1
    gross = sign * (exit_notional - entry_notional)
    assumed_cost = (entry_notional + exit_notional) * (fee + slip) / 100
    return {'side': side, 'quantity': quantity, 'average_entry': average,
            'exit_price': px, 'gross_pnl_usdt': gross,
            'assumed_cost_usdt': assumed_cost,
            'net_pnl_estimate_usdt': gross - assumed_cost,
            'liquidation_price': None, 'probability': None,
            'basis': 'hypothetical linear USDT position, not a live quote or order'}
