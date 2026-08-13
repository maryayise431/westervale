from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.investments.models import UserInvestment
from apps.transactions.models import Transaction

from .forms import (
    ForgotPasswordForm, LoginForm, ProfileForm, RegisterForm,
    ResetPasswordConfirmForm, VerifyOTPForm,
)
from .models import User, UserProfile
from .otp import create_and_send_otp, verify_code


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    ref = request.GET.get('ref', '').strip()[:12]
    initial = {'referral_code': ref} if ref else None
    form = RegisterForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password1'],
            username=form.cleaned_data['username'],
            is_active=False,
        )
        profile = user.profile
        profile.apply_referral(form.cleaned_data.get('referral_code', ''))
        profile.current_balance = settings.WELCOME_BONUS
        profile.save(update_fields=['current_balance', 'updated_at'])
        Transaction.objects.create(
            user=user,
            type='bonus',
            amount=settings.WELCOME_BONUS,
            balance_after=settings.WELCOME_BONUS,
            status='completed',
            payment_method='System',
            remarks='Welcome bonus',
        )
        create_and_send_otp(user, 'registration')
        request.session['pending_verification'] = {
            'user_id': user.pk,
            'purpose': 'registration',
        }
        request.session.save()
        messages.success(
            request,
            'Account created. A 6-digit verification code has been sent to your email.',
        )
        return redirect('accounts:verify_otp')

    return render(request, 'auth/register.html', {'form': form})


def check_email(request):
    """AJAX endpoint used for real-time uniqueness validation."""
    email = request.GET.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'available': False, 'error': 'Enter an email address.'})
    exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'available': not exists, 'error': 'An account with this email already exists.' if exists else ''})


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    pending = request.session.get('pending_verification')
    if not pending:
        messages.error(request, 'Please start the verification process again.')
        return redirect('accounts:login')

    user = User.objects.filter(pk=pending.get('user_id')).first()
    if user is None:
        request.session.pop('pending_verification', None)
        return redirect('accounts:login')

    purpose = pending.get('purpose')
    form = VerifyOTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        ok, error = verify_code(user, purpose, form.cleaned_data['code'])
        if ok:
            request.session.pop('pending_verification', None)
            if purpose == 'registration':
                user.is_active = True
                user.save(update_fields=['is_active'])
                login(request, user)
                messages.success(
                    request,
                    'Your email has been verified. Welcome to Westervale Capital! Your $20.00 bonus is ready.',
                )
                return redirect('dashboard:index')
            # Password reset: proceed to new password
            request.session['password_reset_user_id'] = user.pk
            messages.success(request, 'Code verified. Now choose a new password.')
            return redirect('accounts:reset_password')
        messages.error(request, error)

    return render(request, 'auth/verify_otp.html', {
        'form': form,
        'purpose': purpose,
        'email': user.email,
    })


def resend_otp_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    pending = request.session.get('pending_verification')
    if not pending:
        messages.error(request, 'Nothing to resend. Please start over.')
        return redirect('accounts:login')
    user = User.objects.filter(pk=pending.get('user_id')).first()
    if user is None:
        return redirect('accounts:login')
    create_and_send_otp(user, pending.get('purpose'))
    messages.success(request, 'A new verification code has been sent to your email.')
    return redirect('accounts:verify_otp')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your email is not verified yet. Check your inbox for the verification code.')
                return redirect('accounts:login')
            if user.is_staff:
                messages.info(request, 'Staff accounts sign in through the manager login page.')
                return redirect('accounts:manager_login')
            login(request, user)
            next_url = request.GET.get('next') or 'dashboard:index'
            return redirect(next_url)
        messages.error(request, 'Invalid email or password.')
        return redirect('accounts:login')

    return render(request, 'auth/login.html', {'form': form})


def manager_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('adminpanel:index')
        return redirect('dashboard:index')

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_staff:
                messages.error(request, 'You do not have manager access. Use the regular login page.')
                return redirect('accounts:manager_login')
            if not user.is_active:
                messages.error(request, 'Your account is inactive. Contact the administrator.')
                return redirect('accounts:manager_login')
            login(request, user)
            next_url = request.GET.get('next') or 'adminpanel:index'
            return redirect(next_url)
        messages.error(request, 'Invalid email or password.')
        return redirect('accounts:manager_login')

    return render(request, 'auth/manager_login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            messages.error(request, 'No account was found with that email address.')
            return render(request, 'auth/forgot_password.html', {'form': form})

        create_and_send_otp(user, 'reset')
        request.session['pending_verification'] = {
            'user_id': user.pk,
            'purpose': 'reset',
        }
        request.session.save()
        messages.success(request, 'A password reset code has been sent to your email.')
        return redirect('accounts:verify_otp')

    return render(request, 'auth/forgot_password.html', {'form': form})


def reset_password_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        messages.error(request, 'Please verify your identity first.')
        return redirect('accounts:forgot_password')
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        request.session.pop('password_reset_user_id', None)
        return redirect('accounts:forgot_password')

    form = ResetPasswordConfirmForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password1'])
        user.is_active = True
        user.save(update_fields=['password', 'is_active'])
        request.session.pop('password_reset_user_id', None)
        login(request, user)
        messages.success(request, 'Your password has been reset. You are now signed in.')
        return redirect('dashboard:index')

    return render(request, 'auth/reset_confirm.html', {'form': form})


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile)

    non_cancelled = UserInvestment.objects.filter(user=request.user).exclude(status='cancelled')
    profit_total = non_cancelled.annotate(
        profit=F('expected_return') - F('amount_invested')
    ).aggregate(t=Sum('profit'))['t'] or 0
    amount_invested_total = non_cancelled.aggregate(t=Sum('amount_invested'))['t'] or 0

    return render(request, 'profile/profile.html', {
        'form': form,
        'profile': profile,
        'net_profit': float(profit_total),
        'amount_invested': float(amount_invested_total),
    })


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your password has been changed.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'profile/change_password.html', {'form': form})
