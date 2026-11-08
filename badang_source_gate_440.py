"""Prevent cross-venue derivatives snapshots being represented as Bitget evidence."""

def same_venue_derivatives(candle_exchange, research):
    research = research if isinstance(research, dict) else {}
    source = str(research.get('source_exchange') or '').lower()
    candle = str(candle_exchange or '').lower()
    matched = bool(source and candle and source == candle)
    return {
        'same_exchange': matched,
        'source_exchange': source or None,
        'funding_rate': research.get('funding_rate') if matched else None,
        'oi_contracts': research.get('oi_contracts') if matched else None,
        'oi_change_1h_pct': research.get('oi_change_1h_pct') if matched else None,
        'status': 'MATCHED' if matched else 'CROSS_EXCHANGE_EXCLUDED',
    }
