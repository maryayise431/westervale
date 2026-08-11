from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import Permission

from apps.accounts.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.decorators import staff_required
from apps.core.helpers import get_client_ip, money
from apps.deposits.models import Deposit
from apps.investments.models import UserInvestment
from apps.transactions.models import Transaction
from apps.withdrawals.models import Withdrawal

from .models import AuditLog

SORT_OPTIONS = {
    'newest': ('-created_at',),
    'oldest': ('created_at',),
    'amount_high': ('-amount', '-created_at'),
    'amount_low': ('amount', '-created_at'),
}


def _log(request, action, target_user=None, field_changed='', old_value='', new_value=''):
    AuditLog.objects.create(
        admin=request.user,
        action=action,
        target_user=target_user,
        field_changed=field_changed,
        old_value=str(old_value)[:500],
        new_value=str(new_value)[:500],
        ip_address=get_client_ip(request),
    )


def _credit(user, amount, txn_type, remarks, payment_method='', related=None):
    profile = user.profile
    profile.current_balance += Decimal(str(amount))
    profile.save(update_fields=['current_balance', 'updated_at'])
    return _settle_txn(user, txn_type, amount, profile.current_balance, 'completed',
                       payment_method, remarks, related)


def _debit(user, amount, txn_type, remarks, payment_method='', related=None):
    profile = user.profile
    profile.current_balance -= Decimal(str(amount))
    profile.save(update_fields=['current_balance', 'updated_at'])
    return _settle_txn(user, txn_type, amount, profile.current_balance, 'completed',
                       payment_method, remarks, related)


def _settle_txn(user, txn_type, amount, balance_after, status, payment_method, remarks, related):
    """Mark the matching pending transaction as reviewed, or create one from scratch.

    When a user submits a deposit/withdrawal a pending transaction is logged in
    their history immediately. Admin approval settles that same row instead of
    appending a duplicate completed entry.
    """
    if related is not None:
        lookup = {'user': user, 'type': txn_type, 'status': 'pending',
                  'related_deposit': related if txn_type == 'deposit' else None,
                  'related_withdrawal': related if txn_type == 'withdrawal' else None}
        pending = Transaction.objects.filter(**lookup).first()
        if pending is not None:
            pending.status = status
            pending.amount = amount
            pending.balance_after = balance_after
            pending.remarks = remarks or pending.remarks
            pending.payment_method = payment_method or pending.payment_method
            pending.save()
            return pending
    return Transaction.objects.create(
        user=user,
        type=txn_type,
        amount=amount,
        balance_after=balance_after,
        status=status,
        payment_method=payment_method,
        remarks=remarks,
        related_deposit=related if txn_type == 'deposit' else None,
        related_withdrawal=related if txn_type == 'withdrawal' else None,
        related_investment=related if txn_type == 'investment' else None,
    )


def _mark_rejected(user, txn_type, related, remarks):
    """Flip the pending transaction row for a rejected deposit/withdrawal."""
    lookup = {'user': user, 'type': txn_type, 'status': 'pending',
              'related_deposit': related if txn_type == 'deposit' else None,
              'related_withdrawal': related if txn_type == 'withdrawal' else None}
    txn = Transaction.objects.filter(**lookup).first()
    if txn is not None:
        txn.status = 'rejected'
        txn.remarks = remarks or txn.remarks
        txn.save()


DEBIT_TYPES = ('withdrawal', 'investment')


def _signed_amount(txn_type, amount):
    """Signed balance effect of a transaction amount (+credit / -debit)."""
    value = Decimal(str(amount))
    return -value if txn_type in DEBIT_TYPES else value


def _balance_effect(txn_type, amount, status):
    """Signed effect applied to a balance for a given transaction state."""
    return _signed_amount(txn_type, amount) if status == 'completed' else Decimal('0')


@staff_required
def index(request):
    users = User.objects.exclude(is_staff=True)
    deposits = Deposit.objects.filter(status='pending')
    withdrawals = Withdrawal.objects.filter(status='pending')

    revenue = users.aggregate(total=Sum('profile__current_balance'))['total'] or 0
    trading_balance = users.aggregate(total=Sum('profile__trading_balance'))['total'] or 0

    context = {
        'total_users': users.count(),
        'active_investors': UserInvestment.objects.filter(status__in=['active', 'pending']).values(
            'user').distinct().count(),
        'pending_deposits': deposits.count(),
        'pending_withdrawals': withdrawals.count(),
        'revenue': float(revenue),
        'trading_balance': float(trading_balance),
        'recent_deposits': deposits.select_related('user')[:5],
        'recent_withdrawals': withdrawals.select_related('user')[:5],
        'recent_transactions': Transaction.objects.select_related('user')[:8],
        'recent_audit': AuditLog.objects.select_related('admin')[:8],
    }
    return render(request, 'adminpanel/index.html', context)


@staff_required
def user_list(request):
    qs = User.objects.exclude(is_staff=True).select_related('profile')
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))
    paginator = Paginator(qs.order_by('-date_joined'), 25)
    return render(request, 'adminpanel/user_list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'search': search,
    })


@staff_required
def user_detail(request, pk):
    user = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            profile = user.profile
            old_balance = profile.current_balance
            old_status = profile.account_status

            new_balance = money(request.POST.get('current_balance', profile.current_balance))
            new_trading = money(request.POST.get('trading_balance', profile.trading_balance))
            status = request.POST.get('account_status', profile.account_status)

            if status not in ('trading', 'not_trading'):
                status = profile.account_status

            profile.current_balance = new_balance
            profile.trading_balance = new_trading
            profile.account_status = status
            profile.save()

            if new_balance != old_balance:
                _log(request, 'Balance Updated', user, 'current_balance', old_balance, new_balance)
            if status != old_status:
                _log(request, 'Status Changed', user, 'account_status', old_status, status)
        messages.success(request, f'Updated {user.username}.')
        return redirect('adminpanel:user_detail', pk=pk)

    return render(request, 'adminpanel/user_detail.html', {
        'target': user,
        'transactions': user.transactions.all()[:10],
        'investments': user.investments.all()[:10],
    })


@staff_required
def user_toggle_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        profile = user.profile
        old_status = profile.account_status
        profile.account_status = 'not_trading' if old_status == 'trading' else 'trading'
        profile.save(update_fields=['account_status', 'updated_at'])
        _log(request, 'Status Toggled', user, 'account_status', old_status, profile.account_status)
        messages.success(request, f'{user.username} is now {"Trading" if profile.account_status == "trading" else "Not Trading"}.')
    return redirect('adminpanel:user_detail', pk=pk)


@staff_required
def user_set_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif password1 != password2:
            messages.error(request, 'The two passwords did not match.')
        elif user.check_password(password1):
            messages.error(request, 'New password must be different from the current one.')
        else:
            user.set_password(password1)
            user.save()
            _log(request, 'Password Reset', user, 'password', '***', '***')
            messages.success(request, f'Password updated for {user.username}.')
        return redirect('adminpanel:user_detail', pk=pk)
    return redirect('adminpanel:user_detail', pk=pk)


@staff_required
def deposit_list(request):
    qs = Deposit.objects.select_related('user', 'investment__plan')
    status = request.GET.get('status', '')
    if status in dict(Deposit.STATUS_CHOICES):
        qs = qs.filter(status=status)
    sort = request.GET.get('sort', 'newest')
    qs = qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS['newest']))
    paginator = Paginator(qs, 25)
    return render(request, 'adminpanel/deposit_list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'status': status,
        'sort': sort,
    })


@staff_required
def deposit_detail(request, pk):
    deposit = get_object_or_404(
        Deposit.objects.select_related('user', 'user__profile', 'investment__plan'), pk=pk
    )
    return render(request, 'adminpanel/deposit_detail.html', {
        'deposit': deposit,
        'transactions': deposit.transactions.all()[:10],
    })


@staff_required
def deposit_review(request, pk, action):
    deposit = get_object_or_404(
        Deposit.objects.select_related('user', 'investment__plan'), pk=pk
    )
    if deposit.status != 'pending':
        messages.warning(request, 'This deposit has already been reviewed.')
        return redirect('adminpanel:deposit_list')

    if request.method == 'POST':
        remarks = request.POST.get('admin_remarks', '').strip()
        if action == 'approve':
            with transaction.atomic():
                deposit.status = 'approved'
                deposit.admin_remarks = remarks
                deposit.reviewed_at = timezone.now()
                deposit.reviewed_by = request.user
                deposit.save()
                if deposit.source != 'balance':
                    _credit(deposit.user, deposit.amount, 'deposit', 'Deposit', 'Crypto', deposit)
                if deposit.investment:
                    deposit.investment.activate()
                    if deposit.source != 'balance':
                        investor_profile = deposit.user.profile
                        investor_profile.trading_balance += deposit.investment.amount_invested
                        investor_profile.save(update_fields=['trading_balance', 'updated_at'])
            _log(request, 'Deposit Approved', deposit.user, 'status', 'pending', 'approved')
            messages.success(request, f'Deposit of ${deposit.amount:,.2f} approved and credited.')
        else:
            deposit.status = 'rejected'
            deposit.admin_remarks = remarks
            deposit.reviewed_at = timezone.now()
            deposit.reviewed_by = request.user
            deposit.save()
            if deposit.investment:
                deposit.investment.status = 'cancelled'
                deposit.investment.save(update_fields=['status'])
            _mark_rejected(deposit.user, 'deposit', deposit, remarks)
            _log(request, 'Deposit Rejected', deposit.user, 'status', 'pending', 'rejected')
            messages.info(request, f'Deposit of ${deposit.amount:,.2f} rejected.')
    return redirect('adminpanel:deposit_list')


@staff_required
def withdrawal_list(request):
    qs = Withdrawal.objects.select_related('user')
    status = request.GET.get('status', '')
    if status in dict(Withdrawal.STATUS_CHOICES):
        qs = qs.filter(status=status)
    sort = request.GET.get('sort', 'newest')
    qs = qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS['newest']))
    paginator = Paginator(qs, 25)
    return render(request, 'adminpanel/withdrawal_list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'status': status,
        'sort': sort,
    })


@staff_required
def withdrawal_review(request, pk, action):
    withdrawal = get_object_or_404(Withdrawal.objects.select_related('user'), pk=pk)
    if withdrawal.status != 'pending':
        messages.warning(request, 'This withdrawal has already been reviewed.')
        return redirect('adminpanel:withdrawal_list')

    if request.method == 'POST':
        remarks = request.POST.get('admin_remarks', '').strip()
        now = timezone.now()
        if action == 'approve':
            if float(withdrawal.amount) > float(withdrawal.user.profile.current_balance):
                messages.error(request, 'Insufficient balance to honour this withdrawal.')
                return redirect('adminpanel:withdrawal_list')
            with transaction.atomic():
                withdrawal.status = 'approved'
                withdrawal.admin_remarks = remarks
                withdrawal.reviewed_at = now
                withdrawal.reviewed_by = request.user
                withdrawal.save()
                _debit(withdrawal.user, withdrawal.amount, 'withdrawal',
                       'Withdrawal', 'Crypto', withdrawal)
            _log(request, 'Withdrawal Approved', withdrawal.user, 'status', 'pending', 'approved')
            messages.success(request, f'Withdrawal of ${withdrawal.amount:,.2f} approved and debited.')
        else:
            withdrawal.status = 'rejected'
            withdrawal.admin_remarks = remarks
            withdrawal.reviewed_at = now
            withdrawal.reviewed_by = request.user
            withdrawal.save()
            _mark_rejected(withdrawal.user, 'withdrawal', withdrawal, remarks)
            _log(request, 'Withdrawal Rejected', withdrawal.user, 'status', 'pending', 'rejected')
            messages.info(request, f'Withdrawal of ${withdrawal.amount:,.2f} rejected.')
    return redirect('adminpanel:withdrawal_list')


@staff_required
def transaction_list(request):
    qs = Transaction.objects.select_related('user')
    sort = request.GET.get('sort', 'newest')
    qs = qs.order_by(*SORT_OPTIONS.get(sort, SORT_OPTIONS['newest']))
    paginator = Paginator(qs, 25)
    return render(request, 'adminpanel/transaction_list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'sort': sort,
    })


@staff_required
def transaction_edit(request, pk=None):
    txn = get_object_or_404(Transaction, pk=pk) if pk else None
    target_user_id = request.POST.get('user', txn.user_id if txn else None)

    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=target_user_id) if target_user_id else None
        if target_user is None:
            messages.error(request, 'Please select a user.')
            return redirect('adminpanel:transaction_create' if pk is None else 'adminpanel:transaction_edit', pk=pk)

        txn_type = request.POST.get('type', '')
        amount = money(request.POST.get('amount'))
        status = request.POST.get('status', 'completed')
        remarks = request.POST.get('remarks', '').strip()
        payment_method = request.POST.get('payment_method', '').strip()

        if txn_type not in dict(Transaction.TYPE_CHOICES):
            messages.error(request, 'Invalid transaction type.')
            return redirect('adminpanel:transaction_create' if pk is None else 'adminpanel:transaction_edit', pk=pk)
        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('adminpanel:transaction_create' if pk is None else 'adminpanel:transaction_edit', pk=pk)

        raw_date = request.POST.get('created_at', '').strip()
        posted_at = parse_datetime(raw_date) if raw_date else None
        if raw_date and not posted_at:
            messages.error(request, 'Invalid date and time.')
            return redirect('adminpanel:transaction_create' if pk is None else 'adminpanel:transaction_edit', pk=pk)
        if posted_at is None:
            posted_at = txn.created_at if txn else timezone.now()
        elif timezone.is_naive(posted_at):
            posted_at = timezone.make_aware(posted_at)

        with transaction.atomic():
            profile = target_user.profile
            if txn is None:
                # Creating a completed transaction also updates the user balance
                effect = _balance_effect(txn_type, amount, status)
                if effect:
                    profile.current_balance += effect
                    profile.save(update_fields=['current_balance', 'updated_at'])
                txn = Transaction.objects.create(
                    user=target_user,
                    type=txn_type,
                    amount=amount,
                    status=status,
                    remarks=remarks or txn_type.title(),
                    payment_method=payment_method,
                    balance_after=profile.current_balance if status == 'completed' else None,
                    created_at=posted_at,
                )
                _log(request, 'Transaction Created', target_user, 'amount', '', amount)
                messages.success(
                    request,
                    'Transaction created and balance updated.' if status == 'completed'
                    else 'Transaction history added. No balance was moved.'
                )
            else:
                old_user = txn.user
                old_effect = _balance_effect(txn.type, txn.amount, txn.status)
                new_effect = _balance_effect(txn_type, amount, status)
                if old_user.pk == target_user.pk:
                    delta = new_effect - old_effect
                    if delta:
                        profile.current_balance += delta
                        profile.save(update_fields=['current_balance', 'updated_at'])
                else:
                    old_profile = old_user.profile
                    if old_effect:
                        old_profile.current_balance -= old_effect
                        old_profile.save(update_fields=['current_balance', 'updated_at'])
                    if new_effect:
                        profile.current_balance += new_effect
                        profile.save(update_fields=['current_balance', 'updated_at'])
                old_amount = txn.amount
                txn.user = target_user
                txn.type = txn_type
                txn.amount = amount
                txn.status = status
                txn.remarks = remarks or txn.remarks
                txn.payment_method = payment_method or txn.payment_method
                txn.created_at = posted_at
                txn.balance_after = profile.current_balance if status == 'completed' else None
                txn.save()
                _log(request, 'Transaction Edited', target_user, 'amount', old_amount, amount)
                messages.success(request, 'Transaction updated and balance adjusted.')
        return redirect('adminpanel:transaction_list')

    users = User.objects.exclude(is_staff=True).select_related('profile')
    return render(request, 'adminpanel/transaction_form.html', {
        'txn': txn,
        'users': users,
        'type_choices': Transaction.TYPE_CHOICES,
        'status_choices': Transaction.STATUS_CHOICES,
        'selected_user_id': target_user_id,
    })


@staff_required
def transaction_delete(request, pk):
    txn = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        if txn.status == 'completed':
            profile = txn.user.profile
            profile.current_balance -= _signed_amount(txn.type, txn.amount)
            profile.save(update_fields=['current_balance', 'updated_at'])
        _log(request, 'Transaction Deleted', txn.user, 'amount', txn.amount, '')
        txn.delete()
        messages.success(
            request,
            'Transaction deleted and balance updated.' if txn.status == 'completed'
            else 'Transaction history deleted. No balance was moved.'
        )
    return redirect('adminpanel:transaction_list')


@staff_required
def audit_log_view(request):
    qs = AuditLog.objects.select_related('admin', 'target_user')
    paginator = Paginator(qs.order_by('-timestamp'), 50)
    return render(request, 'adminpanel/audit_log.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
    })
