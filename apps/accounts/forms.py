import re

from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import User, UserProfile


class RegisterForm(forms.Form):
    username = forms.CharField(
        label='Username',
        min_length=3,
        max_length=30,
        strip=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a display name', 'autocomplete': 'off'}),
    )
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com', 'autocomplete': 'email'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a strong password', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat your password', 'autocomplete': 'new-password'}),
    )
    referral_code = forms.CharField(
        required=False,
        max_length=12,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional referral code'}),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', username):
            raise forms.ValidationError('Only letters, numbers, dots, underscores and dashes are allowed.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1', '')
        validate_password(password1)
        return password1

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'The two passwords do not match.')
        return cleaned


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com', 'autocomplete': 'email'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password', 'autocomplete': 'current-password'}),
    )

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip().lower()


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your account email', 'autocomplete': 'email'}),
    )

    def clean_email(self):
        return self.cleaned_data.get('email', '').strip().lower()


class VerifyOTPForm(forms.Form):
    code = forms.CharField(
        label='Verification Code',
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-input',
            'placeholder': '••••••',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'maxlength': '6',
        }),
    )

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if not code.isdigit():
            raise forms.ValidationError('The code must contain only numbers.')
        return code


class ResetPasswordConfirmForm(forms.Form):
    password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password', 'autocomplete': 'new-password'}),
    )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1', '')
        validate_password(password1)
        return password1

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'The two passwords do not match.')
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('phone', 'address', 'occupation', 'country', 'city', 'profile_picture')
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Occupation'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
