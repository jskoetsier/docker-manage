from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, APIKey, ServicePermission, UserSession, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""

    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'last_activity', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'last_activity', 'is_api_enabled')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'is_api_enabled')
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Regular admins can only see non-superusers
            qs = qs.filter(is_superuser=False)
        return qs


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """API Key admin"""

    list_display = ('name', 'user', 'is_active', 'created_at', 'last_used', 'expires_at')
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = ('name', 'user__username')
    readonly_fields = ('key', 'created_at', 'last_used')
    ordering = ('-created_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields


@admin.register(ServicePermission)
class ServicePermissionAdmin(admin.ModelAdmin):
    """Service Permission admin"""

    list_display = ('user', 'service_name', 'permission', 'granted_by', 'created_at')
    list_filter = ('permission', 'created_at')
    search_fields = ('user__username', 'service_name', 'granted_by__username')
    ordering = ('-created_at',)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """User Session admin"""

    list_display = ('user', 'ip_address', 'is_active', 'created_at', 'last_activity')
    list_filter = ('is_active', 'created_at', 'last_activity')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('session_key', 'user_agent', 'created_at')
    ordering = ('-last_activity',)

    def has_add_permission(self, request):
        return False  # Sessions are created automatically


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit Log admin"""

    list_display = ('user', 'action', 'resource', 'ip_address', 'timestamp', 'success_icon')
    list_filter = ('action', 'success', 'timestamp')
    search_fields = ('user__username', 'action', 'resource', 'ip_address')
    readonly_fields = ('user', 'action', 'resource', 'details', 'ip_address', 'user_agent', 'timestamp', 'success', 'error_message')
    ordering = ('-timestamp',)

    def success_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✓</span>')
        else:
            return format_html('<span style="color: red;">✗</span>')
    success_icon.short_description = 'Success'

    def has_add_permission(self, request):
        return False  # Audit logs are created automatically

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete audit logs
