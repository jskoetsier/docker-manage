from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Extended user model with additional fields"""

    ROLE_CHOICES = [
        ("admin", "Administrator"),
        ("manager", "Manager"),
        ("viewer", "Viewer"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="viewer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)
    is_api_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "accounts_user"

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        role_permissions = {
            "admin": [
                "view_dashboard",
                "view_services",
                "create_service",
                "modify_service",
                "delete_service",
                "view_nodes",
                "manage_users",
                "view_api_keys",
                "create_api_key",
                "delete_api_key",
                "view_audit_logs",
            ],
            "manager": [
                "view_dashboard",
                "view_services",
                "create_service",
                "modify_service",
                "delete_service",
                "view_nodes",
            ],
            "viewer": ["view_dashboard", "view_services", "view_nodes"],
        }
        return permission in role_permissions.get(self.role, [])

    def can_modify_services(self):
        return self.role in ["admin", "manager"]

    def can_create_services(self):
        return self.role in ["admin", "manager"]

    def can_delete_services(self):
        return self.role in ["admin", "manager"]

    def can_manage_users(self):
        return self.role == "admin"


class APIKey(models.Model):
    """API Key model for authentication"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_apikey"

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class ServicePermission(models.Model):
    """Service-level permissions for users"""

    PERMISSION_CHOICES = [
        ("view", "View"),
        ("modify", "Modify"),
        ("delete", "Delete"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_name = models.CharField(max_length=100)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES)
    granted_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="granted_permissions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_servicepermission"
        unique_together = ["user", "service_name", "permission"]


class UserSession(models.Model):
    """Track user sessions for security"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounts_usersession"


class AuditLog(models.Model):
    """Audit logging for user actions"""

    ACTION_CHOICES = [
        ("login", "User Login"),
        ("logout", "User Logout"),
        ("create_service", "Create Service"),
        ("modify_service", "Modify Service"),
        ("delete_service", "Delete Service"),
        ("scale_service", "Scale Service"),
        ("restart_service", "Restart Service"),
        ("create_user", "Create User"),
        ("modify_user", "Modify User"),
        ("delete_user", "Delete User"),
        ("create_api_key", "Create API Key"),
        ("delete_api_key", "Delete API Key"),
        ("access_denied", "Access Denied"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource = models.CharField(
        max_length=200, blank=True
    )  # service name, user id, etc.
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "accounts_auditlog"
        ordering = ["-timestamp"]

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.action} - {self.timestamp}"
