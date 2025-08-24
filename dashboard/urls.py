"""
URL configuration for dashboard app
"""

from django.urls import path

from . import views

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
    
    # Nodes
    path("nodes/", views.nodes_view, name="nodes"),
    
    # API endpoints
    path("api/services/", views.api_services, name="api_services"),
    path("api/services/<str:service_id>/logs/", views.api_service_logs, name="api_service_logs"),
    path("api/containers/<str:container_id>/logs/", views.api_container_logs, name="api_container_logs"),
    path("api/nodes/", views.api_nodes, name="api_nodes"),
    path("api/system/", views.api_system_info, name="api_system_info"),
    path("api/services/create/", views.create_service, name="api_create_service"),
]
