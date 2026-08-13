from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.investments.models import UserInvestment


DEFAULT_SECTOR_RULES = [
    ('Growth Equity', ('growth', 'ultra', 'supreme', 'legendary', 'meteor', 'galaxy', 'cosmic')),
    ('Precious Metals', ('gold', 'silver', 'platinum', 'rose gold', 'white gold', 'metal', 'bullion')),
    ('Hard Assets', ('diamond', 'emerald', 'sapphire', 'ruby', 'obsidian', 'titanium', 'gem')),
    ('Income & Growth', ('monthly', 'weekly', '1x', '2x', 'basic', 'starter', 'bronze')),
]
DEFAULT_SECTOR = 'Diversified'


def _as_decimal(value):
    return Decimal(str(value))


def _clamp(value, low, high):
    return max(low, min(high, value))


def _sector_rules():
    return getattr(settings, 'PORTFOLIO_SECTOR_RULES', DEFAULT_SECTOR_RULES)


def _sector_for(plan_name, rules):
    name = plan_name.lower()
    for sector, keywords in rules:
        for keyword in keywords:
            if keyword in name:
                return sector
    return DEFAULT_SECTOR


def _ticker(slug):
    ticker = slug.replace('-', '').upper()
    return ticker[:8]


def _progress_at(investment, moment):
    if investment.status == 'completed':
        return Decimal('1')
    if investment.status != 'active' or not investment.start_date or not investment.maturity_date:
        return Decimal('0')
    total = (investment.maturity_date - investment.start_date).total_seconds()
    if total <= 0:
        return Decimal('1')
    elapsed = (moment - investment.start_date).total_seconds()
    return _clamp(Decimal(str(elapsed / total)), Decimal('0'), Decimal('1'))


def _value_at(investment, progress_frac):
    if investment.status == 'completed':
        return _as_decimal(investment.expected_return)
    growth = _as_decimal(investment.expected_return) - _as_decimal(investment.amount_invested)
    return (_as_decimal(investment.amount_invested) + growth * progress_frac).quantize(Decimal('0.01'))


def _current_value(investment):
    if investment.status == 'completed':
        return _as_decimal(investment.expected_return)
    return _as_decimal(investment.current_value)


def _annual_return_percent(investment):
    duration_days = max(1, investment.plan.duration_days)
    if _as_decimal(investment.amount_invested) <= 0:
        return Decimal('0')
    total_return = _as_decimal(investment.expected_return) / _as_decimal(investment.amount_invested) - Decimal('1')
    return total_return / Decimal(str(duration_days)) * Decimal('365')


def _build_holdings(investments, rules):
    grouped = defaultdict(list)
    for inv in investments:
        grouped[inv.plan].append(inv)

    holdings = []
    for plan, items in grouped.items():
        value = sum((_current_value(i) for i in items), Decimal('0'))
        prev_value = sum((_value_at(i, _progress_at(i, timezone.now() - timedelta(days=1))) for i in items), Decimal('0'))
        amount = sum((_as_decimal(i.amount_invested) for i in items), Decimal('0'))
        expected = sum((_as_decimal(i.expected_return) for i in items), Decimal('0'))
        holdings.append({
            'ticker': _ticker(plan.slug),
            'name': plan.name,
            'sector': _sector_for(plan.name, rules),
            'value': float(value),
            'prev_value': float(prev_value),
            'day_change': float(value - prev_value),
            'amount_invested': float(amount),
            'expected_return': float(expected),
            'annual_return': float(sum((_annual_return_percent(i) for i in items), Decimal('0')) / len(items)),
            'count': len(items),
        })
    holdings.sort(key=lambda h: h['value'], reverse=True)
    return holdings


def _empty_payload():
    now = timezone.now().isoformat()
    return {
        'has_holdings': False,
        'generated_at': now,
        'summary': {
            'total_value': 0,
            'total_profit': 0,
            'amount_invested': 0,
        },
        'holdings': [],
        'sectors': [],
        'history': {'labels': [], 'portfolio': [], 'benchmark': []},
        'dividend_yield': 0,
        'annual_dividend_income': 0,
        'ytd_performance': 0,
        'benchmark_performance': 0,
        'holding_count': 0,
        'sector_count': 0,
        'concentration_risk': 'N/A',
        'last_updated': now,
    }


def build_payload(user):
    investments = list(UserInvestment.objects.filter(
        user=user
    ).exclude(status='cancelled').select_related('plan'))

    if not investments:
        return _empty_payload()

    rules = _sector_rules()
    holdings = _build_holdings(investments, rules)

    total_value = sum((Decimal(str(h['value'])) for h in holdings), Decimal('0'))
    amount_invested = sum((Decimal(str(h['amount_invested'])) for h in holdings), Decimal('0'))

    sector_map = defaultdict(Decimal)
    for h in holdings:
        sector_map[h['sector']] += Decimal(str(h['value']))
    sectors = [
        {'name': name, 'value': float(value), 'weight': float(value / total_value * 100)}
        for name, value in sorted(sector_map.items(), key=lambda kv: -kv[1])
    ]

    payout_ratio = _as_decimal(getattr(settings, 'PORTFOLIO_DIVIDEND_PAYOUT_RATIO', 0.4))
    annual_dividend = Decimal('0')
    for h in holdings:
        annual_dividend += Decimal(str(h['value'])) * _as_decimal(str(h['annual_return'])) / Decimal('100') * payout_ratio
    dividend_yield = float(annual_dividend / total_value * 100) if total_value else 0

    now = timezone.now()
    try:
        jan1 = timezone.make_aware(datetime(now.year, 1, 1))
    except (ValueError, OverflowError):
        jan1 = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    value_at_jan1 = sum(
        (_value_at(i, _progress_at(i, jan1)) for i in investments), Decimal('0')
    )
    ytd_performance = float((total_value / value_at_jan1 - 1) * 100) if value_at_jan1 else 0

    benchmark_annual = _as_decimal(str(getattr(settings, 'PORTFOLIO_BENCHMARK_ANNUAL_RETURN', 0.10)))
    days_ytd = max(0, (now - jan1).days)
    benchmark_performance = float(((Decimal('1') + benchmark_annual) ** _as_decimal(str(days_ytd / 365.0)) - 1) * 100)

    history_days = getattr(settings, 'PORTFOLIO_HISTORY_DAYS', 30)
    labels, portfolio_series = [], []
    for offset in range(history_days - 1, -1, -1):
        moment = now - timedelta(days=offset)
        value = sum(
            (_value_at(i, _progress_at(i, moment)) for i in investments), Decimal('0')
        )
        labels.append(moment.strftime('%b %d'))
        portfolio_series.append(float(value))

    start_value = _as_decimal(str(portfolio_series[0] or 1))
    benchmark_series = [
        float(start_value * (Decimal('1') + benchmark_annual) ** _as_decimal(str(d / 365.0)))
        for d in range(history_days)
    ]

    top_weight = sectors[0]['weight'] if sectors else 0
    if top_weight >= 40:
        concentration_risk = 'High'
    elif top_weight >= 25:
        concentration_risk = 'Moderate'
    else:
        concentration_risk = 'Low'

    total_weight = sum((Decimal(str(h['value'])) for h in holdings), Decimal('0'))
    for h in holdings:
        h['weight'] = float(Decimal(str(h['value'])) / total_weight * 100) if total_weight else 0

    return {
        'has_holdings': True,
        'generated_at': now.isoformat(),
        'summary': {
            'total_value': float(total_value),
            'total_profit': float(total_value - amount_invested),
            'amount_invested': float(amount_invested),
        },
        'holdings': holdings,
        'sectors': sectors,
        'history': {
            'labels': labels,
            'portfolio': portfolio_series,
            'benchmark': benchmark_series,
        },
        'dividend_yield': dividend_yield,
        'annual_dividend_income': float(annual_dividend),
        'ytd_performance': ytd_performance,
        'benchmark_performance': benchmark_performance,
        'holding_count': len(holdings),
        'sector_count': len(sectors),
        'concentration_risk': concentration_risk,
        'last_updated': now.isoformat(),
    }


class PortfolioSource:
    def build(self, user):
        raise NotImplementedError


class LocalPortfolioSource(PortfolioSource):
    def build(self, user):
        return build_payload(user)


_SOURCES = {
    'local': LocalPortfolioSource,
}


def get_portfolio_source():
    name = getattr(settings, 'PORTFOLIO_DATA_SOURCE', 'local')
    source_cls = _SOURCES.get(name, LocalPortfolioSource)
    return source_cls()


def portfolio_payload(user):
    return get_portfolio_source().build(user)
