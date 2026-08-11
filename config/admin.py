from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User


class ManagerAccountsAdminSite(AdminSite):
    """Django admin is restricted to superusers and only used to create
    manager / admin-panel accounts. All day-to-day management happens in the
    custom admin panel (/admin-panel/)."""

    site_header = _('Westervale Capital — Manager Accounts')
    site_title = _('Westervale Capital Manager Accounts')
    index_title = _('Create manager and admin-panel accounts')

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def login(self, request, extra_context=None):
        if not request.user.is_superuser and request.user.is_authenticated and request.user.is_staff:
            # Staff users who are not superusers are redirected to the custom admin panel.
            return None
        return super().login(request, extra_context=extra_context)


manager_admin = ManagerAccountsAdminSite(name='nexus_manager_admin')


class ManagerUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username', 'first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Password'), {'fields': ('plain_password',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('last_login', 'date_joined', 'plain_password')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )
    ordering = ('email',)
    list_display = ('email', 'username', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('email', 'username')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')


manager_admin.register(User, ManagerUserAdmin)
manager_admin.register(Group, GroupAdmin)


class GroupManagerCreationForm(forms.ModelForm):
    """Add form for the default admin (/admin/auth/group/add/). Saving a Group
    here also creates a manager (staff) account with the given name, email and
    password, used to sign in at /manager/login/ and run /admin-panel/."""

    email = forms.EmailField(label=_('Email'), max_length=254)
    password1 = forms.CharField(
        label=_('Password'),
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = Group
        fields = ('name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The two password fields didn't match."))
        return password2


class ManagerGroupAdmin(GroupAdmin):
    """The default admin's Group add form doubles as the 'create manager
    account' screen: name + email + password (+ confirm). Saving creates a
    staff user that can sign in at /manager/login/.
    """

    add_form = GroupManagerCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'email', 'password1', 'password2'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def save_model(self, request, obj, form, change):
        if change:
            obj.save()
            return
        obj.save()
        user = User.objects.create_user(
            email=form.cleaned_data['email'],
            username=form.cleaned_data['name'][:30] or '',
            password=form.cleaned_data['password1'],
            is_staff=True,
            is_active=True,
        )
        user.first_name = form.cleaned_data['name']
        user.save(update_fields=['first_name'])
        user.groups.add(obj)
        self.message_user(request, f'Manager account created for {user.email}.')


admin.site.unregister(Group)
admin.site.register(Group, ManagerGroupAdmin)
