from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render

from apps.core.notify import notify_admins
from apps.transactions.models import Transaction

from .models import Withdrawal


@login_required
def withdrawal_request(request):
    profile = request.user.profile
    available = profile.current_balance
    minimum = settings.WITHDRAWAL_MINIMUM

    if request.method == 'POST':
        amount_raw = request.POST.get('amount', '').strip()
        wallet = request.POST.get('wallet_address', '').strip()
        password = request.POST.get('password', '')

        try:
            amount = float(amount_raw)
        except ValueError:
            messages.error(request, 'Please enter a valid amount.')
            return redirect('withdrawals:request')

        if amount < minimum:
            messages.error(request, f'The minimum withdrawal amount is ${minimum:,.2f}.')
            return redirect('withdrawals:request')

        if amount > float(available):
            messages.error(request, 'The amount exceeds your available balance.')
            return redirect('withdrawals:request')

        if not wallet:
            messages.error(request, 'Please provide your wallet address.')
            return redirect('withdrawals:request')

        if not check_password(password, request.user.password):
            messages.error(request, 'Incorrect password. Please try again.')
            return redirect('withdrawals:request')

        withdrawal = Withdrawal.objects.create(
            user=request.user,
            amount=amount,
            wallet_address=wallet,
            password_confirmed=True,
        )
        Transaction.objects.create(
            user=request.user,
            type='withdrawal',
            amount=withdrawal.amount,
            status='pending',
            remarks='Withdrawal',
            related_withdrawal=withdrawal,
        )
        notify_admins(
            f'New Withdrawal Request — {request.user.username}',
            f'{request.user.get_full_name()} ({request.user.email}) requested a '
            f'${withdrawal.amount:,.2f} withdrawal.\n'
            f'Wallet: {withdrawal.wallet_address}',
        )
        messages.success(
            request,
            'Withdrawal request submitted. Our team will review it and process your payout.',
        )
        return redirect('withdrawals:history')

    return render(request, 'withdrawals/request.html', {
        'profile': profile,
        'available': available,
        'minimum': minimum,
    })


@login_required
def withdrawal_history(request):
    withdrawals = Withdrawal.objects.filter(user=request.user)
    return render(request, 'withdrawals/history.html', {'withdrawals': withdrawals})
