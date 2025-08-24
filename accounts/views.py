from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.forms import PasswordResetForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User, APIKey, AuditLog, UserSession
from .forms import CustomUserCreationForm, CustomUserChangeForm, APIKeyForm
from .decorators import role_required, audit_action
from .signals import generate_api_key
import json


class LoginView(TemplateView):
    template_name = 'accounts/login.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    next_url = request.GET.get('next', 'dashboard')
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Your account has been disabled.')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
        
        return render(request, self.template_name)


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


@role_required('admin')
def register_view(request):
    """User registration view (admin only)"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} has been created successfully.')
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


@role_required('admin')
def user_list_view(request):
    """User list view (admin only)"""
    query = request.GET.get('q', '')
    users = User.objects.all()
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'total_users': users.count()
    }
    
    return render(request, 'accounts/user_list.html', context)


@role_required('admin')
def user_detail_view(request, user_id):
    """User detail view (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    # Get user's recent activity
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
    active_sessions = UserSession.objects.filter(user=user, is_active=True)
    api_keys = APIKey.objects.filter(user=user)
    
    context = {
        'profile_user': user,
        'recent_logs': recent_logs,
        'active_sessions': active_sessions,
        'api_keys': api_keys
    }
    
    return render(request, 'accounts/user_detail.html', context)


@role_required('admin')
def user_edit_view(request, user_id):
    """Edit user view (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} has been updated successfully.')
            return redirect('user_detail', user_id=user.id)
    else:
        form = CustomUserChangeForm(instance=user)
    
    return render(request, 'accounts/user_edit.html', {'form': form, 'profile_user': user})


@role_required('admin')
@audit_action('delete_user')
def user_delete_view(request, user_id):
    """Delete user view (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.user == user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_detail', user_id=user.id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} has been deleted successfully.')
        return redirect('user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'profile_user': user})


@login_required
def profile_view(request):
    """User profile view"""
    user = request.user
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
    active_sessions = UserSession.objects.filter(user=user, is_active=True)
    api_keys = APIKey.objects.filter(user=user)
    
    context = {
        'recent_logs': recent_logs,
        'active_sessions': active_sessions,
        'api_keys': api_keys
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """Edit profile view"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, 'Your profile has been updated successfully.')
        return redirect('profile')
    
    return render(request, 'accounts/profile_edit.html')


@login_required
def api_key_list_view(request):
    """API key list view"""
    api_keys = APIKey.objects.filter(user=request.user)
    return render(request, 'accounts/api_keys.html', {'api_keys': api_keys})


@login_required
@audit_action('create_api_key')
def api_key_create_view(request):
    """Create API key view"""
    if not request.user.is_api_enabled:
        messages.error(request, 'API access is not enabled for your account.')
        return redirect('api_key_list')
    
    if request.method == 'POST':
        form = APIKeyForm(request.POST)
        if form.is_valid():
            api_key = form.save(commit=False)
            api_key.user = request.user
            api_key.key = generate_api_key()
            api_key.save()
            messages.success(request, f'API key "{api_key.name}" has been created successfully.')
            return redirect('api_key_list')
    else:
        form = APIKeyForm()
    
    return render(request, 'accounts/api_key_create.html', {'form': form})


@login_required
@audit_action('delete_api_key')
def api_key_delete_view(request, key_id):
    """Delete API key view"""
    api_key = get_object_or_404(APIKey, id=key_id, user=request.user)
    
    if request.method == 'POST':
        key_name = api_key.name
        api_key.delete()
        messages.success(request, f'API key "{key_name}" has been deleted successfully.')
        return redirect('api_key_list')
    
    return render(request, 'accounts/api_key_confirm_delete.html', {'api_key': api_key})


@role_required('admin')
def audit_log_view(request):
    """Audit log view (admin only)"""
    query = request.GET.get('q', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    
    logs = AuditLog.objects.all()
    
    if query:
        logs = logs.filter(
            Q(resource__icontains=query) |
            Q(details__icontains=query) |
            Q(ip_address__icontains=query)
        )
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available actions for filter
    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'actions': actions,
        'total_logs': logs.count()
    }
    
    return render(request, 'accounts/audit_logs.html', context)


@login_required
@require_http_methods(["POST"])
def terminate_session_view(request, session_id):
    """Terminate user session"""
    session = get_object_or_404(UserSession, id=session_id, user=request.user)
    session.is_active = False
    session.save()
    
    return JsonResponse({'status': 'success', 'message': 'Session terminated successfully.'})


# API Views for AJAX requests
@login_required
def api_user_activity(request):
    """Get user activity data for charts"""
    user = request.user
    
    # Get activity data for the last 30 days
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    activity_logs = AuditLog.objects.filter(
        user=user,
        timestamp__gte=thirty_days_ago
    ).values('action').annotate(count=models.Count('id'))
    
    return JsonResponse({
        'activity': list(activity_logs)
    })


@role_required('admin')
def api_user_stats(request):
    """Get user statistics for admin dashboard"""
    total_users = User.objects.count()
    active_users = User.objects.filter(
        last_activity__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    users_by_role = User.objects.values('role').annotate(count=models.Count('id'))
    
    return JsonResponse({
        'total_users': total_users,
        'active_users': active_users,
        'users_by_role': list(users_by_role)
    })