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
        password = request.POST.get('password', '')
        method = request.POST.get('method', '').strip().lower()

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

        if not check_password(password, request.user.password):
            messages.error(request, 'Incorrect password. Please try again.')
            return redirect('withdrawals:request')

        if method == 'bank':
            bank_details = {
                'bank_account_holder': request.POST.get('bank_account_holder', '').strip(),
                'bank_account_number': request.POST.get('bank_account_number', '').strip(),
                'bank_account_type': request.POST.get('bank_account_type', '').strip(),
                'bank_routing_number': request.POST.get('bank_routing_number', '').strip(),
                'bank_name': request.POST.get('bank_name', '').strip(),
            }
            if not all(bank_details.values()):
                messages.error(request, 'Please complete all bank account fields.')
                return redirect('withdrawals:request')
            withdrawal = Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                method='bank',
                wallet_address='Bank Transfer',
                password_confirmed=True,
                **bank_details,
            )
            transaction_method = 'Bank Transfer'
            payout_info = (
                f'Bank: {withdrawal.bank_name}\n'
                f'Account holder: {withdrawal.bank_account_holder}\n'
                f'Account number: {withdrawal.bank_account_number}\n'
                f'Account type: {withdrawal.bank_account_type}\n'
                f'ACH routing: {withdrawal.bank_routing_number}'
            )
        else:
            wallet = request.POST.get('wallet_address', '').strip()
            if not wallet:
                messages.error(request, 'Please provide your wallet address.')
                return redirect('withdrawals:request')
            withdrawal = Withdrawal.objects.create(
                user=request.user,
                amount=amount,
                method='crypto',
                wallet_address=wallet,
                password_confirmed=True,
            )
            transaction_method = 'Crypto'
            payout_info = f'Wallet: {withdrawal.wallet_address}'

        Transaction.objects.create(
            user=request.user,
            type='withdrawal',
            amount=withdrawal.amount,
            status='pending',
            remarks='Withdrawal',
            payment_method=transaction_method,
            related_withdrawal=withdrawal,
        )
        notify_admins(
            f'New Withdrawal Request — {request.user.username}',
            f'{request.user.get_full_name()} ({request.user.email}) requested a '
            f'${withdrawal.amount:,.2f} {withdrawal.get_method_display()} withdrawal.\n'
            f'{payout_info}',
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
