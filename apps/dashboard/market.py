"""Live market data for the dashboard.

Quotes, company profiles and fundamentals come from Finnhub (FINNHUB_API_KEY).
Historical price candles fall back to Yahoo Finance's public chart API because
the current Finnhub plan does not include the /stock/candle endpoint.

Every upstream call is cached for MARKET_CACHE_SECONDS (two minutes), so the
dashboard only hits the APIs once per symbol every two minutes.
"""

import json
import time
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

FINNHUB_BASE = 'https://finnhub.io/api/v1'
YAHOO_BASE = 'https://query1.finance.yahoo.com/v8/finance/chart'

# range-key -> (Yahoo range, interval)
YAHOO_RANGES = {
    '1D': ('1d', '5m'),
    '1W': ('5d', '60m'),
    '1M': ('1mo', '1d'),
    '3M': ('3mo', '1d'),
    '1Y': ('1y', '1d'),
}


def market_symbols():
    return list(getattr(settings, 'MARKET_SYMBOLS', ['AAPL', 'BRK.B', 'KO', 'CVX']))


def _cache_ttl():
    return int(getattr(settings, 'MARKET_CACHE_SECONDS', 120))


def _http_json(url, timeout=12):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WestervaleCapital/1.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


def _finnhub_get(path, params):
    key = getattr(settings, 'FINNHUB_API_KEY', '')
    if not key:
        return None
    cache_key = 'finnhub:%s:%s' % (path, urllib.parse.urlencode(params))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    data = _http_json(FINNHUB_BASE + path + '?' + urllib.parse.urlencode(dict(params, token=key)))
    if data is not None:
        cache.set(cache_key, data, _cache_ttl())
    return data


def fetch_quote(symbol):
    data = _finnhub_get('/quote', {'symbol': symbol})
    if not data or data.get('c') is None:
        return None
    return {
        'symbol': symbol,
        'price': data['c'],
        'change': data.get('d'),
        'change_pct': data.get('dp'),
        'open': data.get('o'),
        'high': data.get('h'),
        'low': data.get('l'),
        'prev_close': data.get('pc'),
        'timestamp': data.get('t'),
    }


def fetch_profile(symbol):
    data = _finnhub_get('/stock/profile2', {'symbol': symbol})
    if not data or not data.get('name'):
        return None
    return {
        'symbol': symbol,
        'name': data.get('name'),
        'logo': data.get('logo'),
        'exchange': data.get('exchange'),
        'industry': data.get('finnhubIndustry'),
        'country': data.get('country'),
        'currency': data.get('currency'),
        'website': data.get('weburl'),
        'market_cap': data.get('marketCapitalization'),
        'shares_outstanding': data.get('shareOutstanding'),
        'ipo': data.get('ipo'),
    }


def fetch_metrics(symbol):
    data = _finnhub_get('/stock/metric', {'symbol': symbol, 'metric': 'all'})
    if not data or not isinstance(data, dict) or 'metric' not in data:
        return None
    m = data.get('metric') or {}
    return {
        'symbol': symbol,
        'market_cap': m.get('marketCapitalization'),
        'pe': m.get('peAnnual') or m.get('peTTM'),
        'eps': m.get('epsAnnual') or m.get('epsTTM'),
        'revenue_ps': m.get('revenuePerShareAnnual'),
        'gross_margin': m.get('grossMarginAnnual'),
        'net_margin': m.get('netMarginAnnual'),
        'profit_margin': m.get('profitMargin'),
        'dividend_yield': m.get('dividendYieldIndicatedAnnual'),
        'dividend_ps': m.get('dividendPerShareAnnual'),
    }


def _symbol_snapshot(symbol):
    return {
        'symbol': symbol,
        'quote': fetch_quote(symbol),
        'profile': fetch_profile(symbol),
        'metrics': fetch_metrics(symbol),
    }


def market_snapshot():
    return {
        'symbols': market_symbols(),
        'generated_at': timezone.now().isoformat(),
        'cache_seconds': _cache_ttl(),
        'items': [_symbol_snapshot(s) for s in market_symbols()],
    }


def fetch_candles(symbol, timeframe):
    timeframe = (timeframe or '1D').upper()
    if timeframe not in YAHOO_RANGES:
        timeframe = '1D'
    rng, interval = YAHOO_RANGES[timeframe]
    cache_key = 'yahoo:%s:%s:%s' % (symbol.upper(), rng, interval)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = YAHOO_BASE + '/' + urllib.parse.quote(symbol.upper()) + '?' + urllib.parse.urlencode(
        {'range': rng, 'interval': interval}
    )
    data = _http_json(url)
    if not data:
        return None
    result = (data.get('chart', {}).get('result') or [None])[0]
    if not result:
        return None

    timestamps = result.get('timestamp') or []
    quote_series = (result.get('indicators', {}).get('quote', [{}])[0]) or {}
    closes = quote_series.get('close') or []
    volumes = quote_series.get('volume') or []

    points = [
        {'t': t, 'c': c, 'v': v}
        for t, c, v in zip(timestamps, closes, volumes)
        if c is not None
    ]
    if not points:
        return None

    meta = result.get('meta') or {}
    payload = {
        'symbol': symbol.upper(),
        'timeframe': timeframe,
        'currency': meta.get('currency'),
        'regular_market_price': meta.get('regularMarketPrice'),
        'previous_close': meta.get('chartPreviousClose'),
        'points': points,
    }
    cache.set(cache_key, payload, _cache_ttl())
    return payload


def cache_timestamp():
    """Seconds since epoch — used by views/templates when showing staleness."""
    return int(time.time())
