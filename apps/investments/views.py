from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render

from apps.transactions.models import Transaction

from .models import InvestmentPlan, UserInvestment


@login_required
def plans_landing(request):
    periodic_count = InvestmentPlan.objects.filter(category='periodic', is_active=True).count()
    flexible_count = InvestmentPlan.objects.filter(category='flexible', is_active=True).count()
    return render(request, 'investments/landing.html', {
        'periodic_count': periodic_count,
        'flexible_count': flexible_count,
    })


@login_required
def plans_periodic(request):
    plans = InvestmentPlan.objects.filter(category='periodic', is_active=True).order_by('id')
    return render(request, 'investments/periodic.html', {'plans': plans, 'active_tab': 'periodic'})


@login_required
def plans_flexible(request):
    plans = InvestmentPlan.objects.filter(category='flexible', is_active=True).order_by('id')
    return render(request, 'investments/flexible.html', {'plans': plans, 'active_tab': 'flexible'})


@login_required
def my_investments(request):
    investments = list(UserInvestment.objects.filter(user=request.user).select_related('plan'))
    for inv in investments:
        if inv.is_matured():
            with transaction.atomic():
                profile = request.user.profile
                payout = inv.expected_return
                profile.trading_balance -= inv.amount_invested
                if profile.trading_balance < Decimal('0'):
                    profile.trading_balance = Decimal('0')
                profile.current_balance += payout
                profile.save(update_fields=['current_balance', 'trading_balance', 'updated_at'])
                Transaction.objects.create(
                    user=request.user,
                    type='profit',
                    amount=payout,
                    balance_after=profile.current_balance,
                    status='completed',
                    remarks=f'Return on {inv.plan.name} investment',
                    related_investment=inv,
                )
                inv.status = 'completed'
                inv.save(update_fields=['status'])

    active = [i for i in investments if i.status in ('pending', 'active')]
    total_invested = sum((i.amount_invested for i in investments if i.status != 'cancelled'), 0)
    expected_return = sum((i.expected_return for i in active), 0)

    return render(request, 'investments/my.html', {
        'investments': investments,
        'total_invested': total_invested,
        'expected_return': expected_return,
        'active_count': len(active),
        'active_investments': [i for i in investments if i.status == 'active'],
    })
