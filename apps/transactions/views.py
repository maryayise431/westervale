from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Transaction


@login_required
def transaction_history(request):
    qs = Transaction.objects.filter(user=request.user).select_related(
        'related_deposit', 'related_withdrawal', 'related_investment'
    )

    search = request.GET.get('q', '').strip()
    txn_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    sort = request.GET.get('sort', '-created_at')

    if search:
        qs = qs.filter(remarks__icontains=search)
    if txn_type in dict(Transaction.TYPE_CHOICES):
        qs = qs.filter(type=txn_type)
    if status in dict(Transaction.STATUS_CHOICES):
        qs = qs.filter(status=status)

    allowed_sorts = {
        'created_at': 'created_at',
        '-created_at': '-created_at',
        'amount': 'amount',
        '-amount': '-amount',
    }
    qs = qs.order_by(allowed_sorts.get(sort, '-created_at'))

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page,
        'search': search,
        'txn_type': txn_type,
        'status': status,
        'sort': sort,
        'type_choices': Transaction.TYPE_CHOICES,
        'status_choices': Transaction.STATUS_CHOICES,
    }
    return render(request, 'transactions/history.html', context)
