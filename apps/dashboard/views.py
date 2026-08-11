from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

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

    context = {
        'profile': profile,
        'transactions': transactions,
        'total_deposits': float(deposits.aggregate(t=Sum('amount'))['t'] or 0),
        'total_withdrawals': float(withdrawals.aggregate(t=Sum('amount'))['t'] or 0),
        'active_investments': len(active_investments),
        'active_performances': active_investments,
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def chart_data(request):
    labels, values = _growth_series(request.user)
    return JsonResponse({'labels': labels, 'values': values})
