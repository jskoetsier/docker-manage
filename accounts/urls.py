from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User Management (Admin only)
    path('users/', views.user_list_view, name='user_list'),
    path('users/register/', views.register_view, name='register'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete_view, name='user_delete'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    
    # API Keys
    path('api-keys/', views.api_key_list_view, name='api_key_list'),
    path('api-keys/create/', views.api_key_create_view, name='api_key_create'),
    path('api-keys/<int:key_id>/delete/', views.api_key_delete_view, name='api_key_delete'),
    
    # Audit Logs (Admin only)
    path('audit-logs/', views.audit_log_view, name='audit_logs'),
    
    # Session Management
    path('sessions/<int:session_id>/terminate/', views.terminate_session_view, name='terminate_session'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        success_url='/accounts/password-reset/done/'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset/complete/'
    ), name='password_reset_confirm'),
    
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Settings (Admin only)
    path('settings/', views.settings_view, name='settings'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('export-logs/', views.export_logs_view, name='export_logs'),
    
    # API Endpoints
    path('api/user-activity/', views.api_user_activity, name='api_user_activity'),
    path('api/user-stats/', views.api_user_stats, name='api_user_stats'),
    path('api/system-uptime/', views.api_system_uptime, name='api_system_uptime'),
]