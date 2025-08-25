"""
URL configuration for dashboard app
"""

from django.urls import path

from . import views
from . import dashboard_views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),

    # Services
    path("services/", views.services_view, name="services"),
    path("services/create/", views.create_service_view, name="create_service"),
    path("services/import-compose/", views.import_compose_view, name="import_compose"),
    path("services/review-import/", views.review_compose_import_view, name="review_compose_import"),
    path("services/clear-import/", views.clear_compose_import_view, name="clear_compose_import"),
    path("services/save-stack/", views.save_compose_as_stack_view, name="save_compose_stack"),
    path("services/<str:service_id>/", views.service_detail_view, name="service_detail"),
    path("services/<str:service_id>/logs/", views.service_logs_view, name="service_logs"),
    path("services/<str:service_id>/restart/", views.restart_service, name="restart_service"),
    path("services/<str:service_id>/scale/", views.scale_service, name="scale_service"),
    path("services/<str:service_id>/remove/", views.remove_service, name="remove_service"),

    # Service Groups
    path("groups/", views.service_groups_view, name="service_groups"),

    # Stacks
    path("stacks/", views.stacks_view, name="stacks"),
    path("stacks/<int:stack_id>/", views.stack_detail_view, name="stack_detail"),
    path("stacks/<int:stack_id>/edit/", views.stack_edit_view, name="stack_edit"),
    path("stacks/<int:stack_id>/deploy/", views.stack_deploy_view, name="stack_deploy"),
    path("stacks/<int:stack_id>/delete/", views.stack_delete_view, name="stack_delete"),

    # Nodes
    path("nodes/", views.nodes_view, name="nodes"),

    # Analytics and Historical Metrics
    path("analytics/", dashboard_views.analytics_dashboard, name="analytics"),
    path("historical-metrics/", dashboard_views.historical_metrics, name="historical_metrics"),
    path("predictive-analytics/", dashboard_views.predictive_analytics, name="predictive_analytics"),

    # Custom Dashboards
    path("dashboards/", dashboard_views.custom_dashboards, name="custom_dashboards"),
    path("dashboards/builder/", dashboard_views.dashboard_builder, name="dashboard_builder"),
    path("dashboards/builder/<int:dashboard_id>/", dashboard_views.dashboard_builder, name="edit_dashboard"),
    path("dashboards/<int:dashboard_id>/", dashboard_views.view_dashboard, name="view_dashboard"),

    # API endpoints - Existing
    path("api/services/", views.api_services, name="api_services"),
    path("api/services/<str:service_id>/logs/", views.api_service_logs, name="api_service_logs"),
    path("api/containers/<str:container_id>/logs/", views.api_container_logs, name="api_container_logs"),
    path("api/nodes/", views.api_nodes, name="api_nodes"),
    path("api/system/", views.api_system_info, name="api_system_info"),
    path("api/services/create/", views.create_service, name="api_create_service"),
    
    # API endpoints - New Analytics and Dashboard APIs
    path("api/metrics/", dashboard_views.api_metrics_data, name="api_metrics_data"),
    path("api/dashboards/<int:dashboard_id>/data/", dashboard_views.api_dashboard_data, name="api_dashboard_data"),
    path("api/dashboards/<int:dashboard_id>/share/", dashboard_views.api_share_dashboard, name="api_share_dashboard"),
    path("api/dashboards/<int:dashboard_id>/delete/", dashboard_views.api_delete_dashboard, name="api_delete_dashboard"),
    path("api/export/", dashboard_views.api_export_data, name="api_export_data"),
    path("api/dashboard-templates/", dashboard_views.api_dashboard_templates, name="api_dashboard_templates"),
    path("api/dashboard-templates/<int:template_id>/create/", dashboard_views.api_create_from_template, name="api_create_from_template"),
]
