from django.conf import settings
from django.db import models
from django.db.models import CASCADE, SET_NULL


class AuditLog(models.Model):
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='audit_entries')
    action = models.CharField(max_length=100)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True,
        related_name='audited_entries'
    )
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.admin.username} · {self.action}'
