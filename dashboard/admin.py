from django.contrib import admin
from .models import (
    ServiceLog, ServiceGroup, ServiceGroupMapping,
    ComposeStack, DeploymentHistory, Metric, Dashboard, DashboardPanel
)


@admin.register(ServiceLog)
class ServiceLogAdmin(admin.ModelAdmin):
    list_display = ['service_id', 'level', 'timestamp', 'message_preview']
    list_filter = ['level', 'timestamp', 'service_name']
    search_fields = ['service_id', 'service_name', 'message']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'


@admin.register(ServiceGroup)
class ServiceGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'services_count', 'created_by', 'created_at']
    list_filter = ['created_by', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def services_count(self, obj):
        return obj.get_services_count()
    services_count.short_description = 'Services Count'


@admin.register(ServiceGroupMapping)
class ServiceGroupMappingAdmin(admin.ModelAdmin):
    list_display = ['group', 'service_name', 'service_id', 'added_by', 'added_at']
    list_filter = ['group', 'added_by', 'added_at']
    search_fields = ['service_name', 'service_id', 'group__name']
    readonly_fields = ['added_at']


@admin.register(ComposeStack)
class ComposeStackAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'services_count', 'created_by', 'created_at']
    list_filter = ['status', 'created_by', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DeploymentHistory)
class DeploymentHistoryAdmin(admin.ModelAdmin):
    list_display = ['stack', 'status', 'deployed_by', 'deployed_at']
    list_filter = ['status', 'deployed_by', 'deployed_at']
    search_fields = ['stack__name', 'deployed_by__username']
    readonly_fields = ['deployed_at']
    date_hierarchy = 'deployed_at'


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ['measurement', 'timestamp', 'tags_preview', 'fields_preview', 'created_at']
    list_filter = ['measurement', 'timestamp', 'created_at']
    search_fields = ['measurement', 'tags', 'fields']
    date_hierarchy = 'timestamp'
    readonly_fields = ['created_at']
    
    def tags_preview(self, obj):
        tags_str = str(obj.tags)
        return tags_str[:50] + '...' if len(tags_str) > 50 else tags_str
    tags_preview.short_description = 'Tags'
    
    def fields_preview(self, obj):
        fields_str = str(obj.fields)
        return fields_str[:50] + '...' if len(fields_str) > 50 else fields_str
    fields_preview.short_description = 'Fields'
    
    def get_queryset(self, request):
        # Limit to recent metrics to avoid performance issues
        qs = super().get_queryset(request)
        return qs.order_by('-timestamp')[:10000]


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'is_template', 'is_public', 'panels_count', 'created_at', 'updated_at']
    list_filter = ['is_template', 'is_public', 'created_by', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    filter_horizontal = ['shared_with']
    readonly_fields = ['created_at', 'updated_at']
    
    def panels_count(self, obj):
        return obj.panels.count()
    panels_count.short_description = 'Panels'


@admin.register(DashboardPanel)
class DashboardPanelAdmin(admin.ModelAdmin):
    list_display = ['title', 'dashboard', 'panel_type', 'measurement', 'position', 'size', 'created_at']
    list_filter = ['panel_type', 'measurement', 'dashboard', 'created_at']
    search_fields = ['title', 'dashboard__name', 'measurement']
    readonly_fields = ['created_at', 'updated_at']
    
    def position(self, obj):
        return f"({obj.x}, {obj.y})"
    position.short_description = 'Position (x, y)'
    
    def size(self, obj):
        return f"{obj.width}x{obj.height}"
    size.short_description = 'Size (w×h)'