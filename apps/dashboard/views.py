from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.platform_settings import get_platform_settings
from apps.dashboard.market import fetch_candles, market_snapshot, market_symbols
from apps.dashboard.portfolio import portfolio_payload
from apps.deposits.models import Deposit
from apps.investments.models import UserInvestment
from apps.transactions.models import Transaction
from apps.withdrawals.models import Withdrawal


def _month_label(dt):
    return dt.strftime('%b %Y')


def _growth_series(user):
    """Build (labels, values) of cumulative balance over the last 12 months."""
    now = timezone.now()
    start = now - timedelta(days=365)
    txns = Transaction.objects.filter(
        user=user, status='completed', created_at__gte=start
    ).order_by('created_at')

    labels, values = [], []
    running = Decimal('0')
    bucket = defaultdict(Decimal)

    months = []
    cursor = start.replace(day=1)
    while cursor <= now:
        months.append(cursor)
        cursor = (cursor + timedelta(days=32)).replace(day=1)

    for month in months:
        label = _month_label(month)
        for txn in txns.filter(created_at__year=month.year, created_at__month=month.month):
            amount = Decimal(str(txn.amount))
            if txn.type in ('withdrawal', 'investment'):
                running -= amount
            else:
                running += amount
            bucket[label] = running

        if label in bucket:
            labels.append(label)
            values.append(float(bucket[label]))
        else:
            labels.append(label)
            values.append(float(running))

    if not txns.exists():
        labels = [_month_label(m) for m in months]
        values = [20.0] * len(labels)

    return labels, values


@login_required
def dashboard_index(request):
    profile = request.user.profile
    transactions = Transaction.objects.filter(user=request.user)[:15]

    deposits = Deposit.objects.filter(user=request.user, status='approved', source='external')
    withdrawals = Withdrawal.objects.filter(user=request.user, status='approved')
    investments = list(UserInvestment.objects.filter(user=request.user).exclude(status='cancelled').select_related('plan'))
    active_investments = [i for i in investments if i.status == 'active']

    non_cancelled = UserInvestment.objects.filter(user=request.user).exclude(status='cancelled')
    profit_total = non_cancelled.annotate(
        profit=F('expected_return') - F('amount_invested')
    ).aggregate(t=Sum('profit'))['t'] or 0
    amount_invested_total = non_cancelled.aggregate(t=Sum('amount_invested'))['t'] or 0

    active_holdings_override = get_platform_settings().get('active_holdings')
    active_holdings_display = (
        profile.active_holdings
        if profile.active_holdings is not None
        else (
            active_holdings_override
            if active_holdings_override is not None
            else len(active_investments)
        )
    )

    context = {
        'profile': profile,
        'transactions': transactions,
        'total_deposits': float(deposits.aggregate(t=Sum('amount'))['t'] or 0),
        'total_withdrawals': float(withdrawals.aggregate(t=Sum('amount'))['t'] or 0),
        'active_investments': len(active_investments),
        'active_holdings_display': active_holdings_display,
        'net_profit': float(profile.net_profit) if profile.net_profit is not None else float(profit_total),
        'amount_invested': float(profile.amount_invested) if profile.amount_invested is not None else float(amount_invested_total),
        'active_performances': active_investments,
        'market_symbols': market_symbols(),
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def market_data(request):
    return JsonResponse(market_snapshot())


@login_required
def market_candles(request):
    symbol = request.GET.get('symbol', 'AAPL')
    timeframe = request.GET.get('range', '1D')
    data = fetch_candles(symbol, timeframe)
    if data is None:
        return JsonResponse({'error': 'Could not load price history.'}, status=502)
    return JsonResponse(data)


@login_required
def chart_data(request):
    labels, values = _growth_series(request.user)
    return JsonResponse({'labels': labels, 'values': values})


@login_required
def portfolio_data(request):
    return JsonResponse(portfolio_payload(request.user))
