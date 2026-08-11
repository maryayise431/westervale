import base64
import io
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

import segno

from apps.core.helpers import validate_uploaded_image
from apps.core.notify import notify_admins
from apps.investments.models import InvestmentPlan, UserInvestment
from apps.transactions.models import Transaction

from .models import Deposit


WALLET_LABELS = {
    'BTC': 'Bitcoin (BTC)',
    'ETH': 'Ethereum (ETH)',
}

QR_STATIC_IMAGES = {
    'BTC': 'images/btc_qrcode_image.jpeg',
    'ETH': 'images/eth_qrcode_image.jpeg',
}

_QR_CACHE = {}


def qr_data_uri(data, scale=6):
    """Return a self-contained PNG data URI for the given text (local QR, no external API)."""
    if data not in _QR_CACHE:
        buffer = io.BytesIO()
        segno.make(data, error='m').save(buffer, kind='png', scale=scale, border=2)
        _QR_CACHE[data] = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')
    return _QR_CACHE[data]


def build_wallet_options():
    return [
        {
            'key': key,
            'address': address,
            'label': WALLET_LABELS.get(key, key),
            'qr': qr_data_uri(address),
            'qr_static': QR_STATIC_IMAGES.get(key),
        }
        for key, address in settings.WALLET_ADDRESSES.items()
    ]


@login_required
def index(request):
    """Main deposit page: wallet address cards + amount/proof submission form."""
    wallet_options = build_wallet_options()

    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()
        try:
            amount = float(amount)
        except ValueError:
            messages.error(request, 'Please enter a valid amount.')
            return redirect('deposits:index')
        if amount <= 0:
            messages.error(request, 'Please enter an amount greater than zero.')
            return redirect('deposits:index')

        chosen = request.POST.get('wallet_asset', settings.DEPOSIT_WALLET_ASSET).strip()
        if chosen not in settings.WALLET_ADDRESSES:
            chosen = settings.DEPOSIT_WALLET_ASSET
        wallet = settings.WALLET_ADDRESSES[chosen]

        proof = request.FILES.get('payment_proof')
        ok, error = validate_uploaded_image(proof)
        if not ok:
            messages.error(request, error)
            return redirect('deposits:index')

        deposit = Deposit.objects.create(
            user=request.user,
            amount=Decimal(str(amount)),
            wallet_address_sent_to=wallet,
            payment_proof=proof,
            notes=request.POST.get('notes', '').strip(),
            status='pending',
        )
        Transaction.objects.create(
            user=request.user,
            type='deposit',
            amount=deposit.amount,
            status='pending',
            payment_method='Crypto',
            remarks='Deposit',
            related_deposit=deposit,
        )
        notify_admins(
            f'New Deposit Request — {request.user.username}',
            f'{request.user.get_full_name()} ({request.user.email}) submitted a '
            f'${deposit.amount:,.2f} deposit.\n'
            f'Reference: {deposit.reference or deposit.pk}\n'
            f'Wallet: {deposit.wallet_address_sent_to}',
        )
        messages.success(
            request,
            'Deposit submitted. Our team will verify it and credit your balance shortly.',
        )
        return redirect('deposits:history')

    return render(request, 'deposits/index.html', {'wallet_options': wallet_options})


@login_required
def initiate(request, plan_slug):
    plan = get_object_or_404(InvestmentPlan, slug=plan_slug, is_active=True)

    if request.method == 'POST':
        amount = request.POST.get('amount', '').strip()
        try:
            amount = Decimal(amount)
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, 'Please enter a valid amount.')
            return redirect('deposits:initiate', plan_slug=plan.slug)
        if amount < plan.min_amount:
            messages.error(request, f'The minimum for this plan is ${plan.min_amount:,.2f}.')
            return redirect('deposits:initiate', plan_slug=plan.slug)

        profile = request.user.profile
        if profile.current_balance < amount:
            messages.error(request, 'Your balance is not enough for this deposit. Please fund your account first.')
            return redirect('deposits:index')

        with transaction.atomic():
            profile.current_balance -= amount
            profile.trading_balance += amount
            profile.save(update_fields=['current_balance', 'trading_balance', 'updated_at'])
            investment = UserInvestment.objects.create(
                user=request.user,
                plan=plan,
                amount_invested=amount,
                status='active',
            )
            investment.activate()
            deposit = Deposit.objects.create(
                user=request.user,
                investment=investment,
                amount=amount,
                status='approved',
                source='balance',
            )
            Transaction.objects.create(
                user=request.user,
                type='investment',
                amount=amount,
                balance_after=profile.current_balance,
                status='completed',
                remarks=f'Funded {plan.name} (${amount:,.2f})',
                related_investment=investment,
            )
        messages.success(request, f'Your balance was debited ${amount:,.2f} and your investment is now active.')
        return redirect('deposits:detail', deposit_id=deposit.pk)

    return render(request, 'deposits/initiate.html', {'plan': plan})


@login_required
def confirm(request, deposit_id):
    deposit = get_object_or_404(
        Deposit.objects.select_related('investment__plan'), pk=deposit_id, user=request.user
    )
    if deposit.payment_proof:
        messages.info(request, 'This deposit already has a proof attached.')
        return redirect('deposits:detail', deposit_id=deposit.pk)

    if request.method == 'POST':
        proof = request.FILES.get('payment_proof')
        ok, error = validate_uploaded_image(proof)
        if not ok:
            messages.error(request, error)
            return redirect('deposits:confirm', deposit_id=deposit.pk)

        deposit.payment_proof = proof
        deposit.notes = request.POST.get('notes', '').strip()
        deposit.save()
        messages.success(
            request,
            'Payment proof submitted. Our team will verify it and credit your balance shortly.',
        )
        return redirect('deposits:detail', deposit_id=deposit.pk)

    return render(request, 'deposits/confirm.html', {'deposit': deposit})


@login_required
def detail(request, deposit_id):
    deposit = get_object_or_404(
        Deposit.objects.select_related('investment__plan'), pk=deposit_id, user=request.user
    )
    return render(request, 'deposits/detail.html', {'deposit': deposit})


@login_required
def history(request):
    deposits = Deposit.objects.filter(user=request.user)
    for deposit in deposits:
        if deposit.wallet_address_sent_to:
            deposit.qr_uri = qr_data_uri(deposit.wallet_address_sent_to)
    return render(request, 'deposits/history.html', {
        'deposits': deposits,
        'wallet_options': build_wallet_options(),
    })
