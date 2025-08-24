from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import AuditLog
from .signals import get_client_ip


def role_required(required_role):
    """
    Decorator to require a specific role or higher.
    Role hierarchy: admin > manager > viewer
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            role_hierarchy = {'viewer': 1, 'manager': 2, 'admin': 3}
            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 0)
            
            if user_level >= required_level:
                return view_func(request, *args, **kwargs)
            else:
                # Log access denied
                AuditLog.objects.create(
                    user=user,
                    action='access_denied',
                    resource=f'Required role: {required_role}, User role: {user.role}',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False,
                    error_message=f'Insufficient permissions. Required: {required_role}'
                )
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Insufficient permissions'
                    }, status=403)
                else:
                    messages.error(request, 'You do not have permission to access this page.')
                    return redirect('dashboard')
        
        return _wrapped_view
    return decorator


def permission_required(permission):
    """
    Decorator to check specific permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.has_permission(permission):
                return view_func(request, *args, **kwargs)
            else:
                # Log access denied
                AuditLog.objects.create(
                    user=request.user,
                    action='access_denied',
                    resource=f'Required permission: {permission}',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=False,
                    error_message=f'Missing permission: {permission}'
                )
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Insufficient permissions'
                    }, status=403)
                else:
                    messages.error(request, 'You do not have permission to perform this action.')
                    return redirect('dashboard')
        
        return _wrapped_view
    return decorator


def audit_action(action):
    """
    Decorator to automatically log user actions
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            start_time = timezone.now()
            success = True
            error_message = ''
            resource = ''
            
            try:
                # Extract resource from URL parameters
                if 'service_id' in kwargs:
                    resource = f"Service ID: {kwargs['service_id']}"
                elif 'user_id' in kwargs:
                    resource = f"User ID: {kwargs['user_id']}"
                elif 'key_id' in kwargs:
                    resource = f"API Key ID: {kwargs['key_id']}"
                
                response = view_func(request, *args, **kwargs)
                
                # Check if response indicates failure
                if hasattr(response, 'status_code') and response.status_code >= 400:
                    success = False
                    error_message = f"HTTP {response.status_code}"
                
                return response
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            
            finally:
                # Create audit log
                try:
                    AuditLog.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        action=action,
                        resource=resource,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=success,
                        error_message=error_message,
                        details={
                            'method': request.method,
                            'path': request.path,
                            'duration_ms': int((timezone.now() - start_time).total_seconds() * 1000)
                        }
                    )
                except Exception:
                    # Don't let audit logging break the application
                    pass
        
        return _wrapped_view
    return decorator


def api_key_required(view_func):
    """
    Decorator for API endpoints that require API key authentication
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check for API key in header
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'status': 'error',
                'message': 'API key required'
            }, status=401)
        
        try:
            from .models import APIKey
            api_key_obj = APIKey.objects.select_related('user').get(
                key=api_key,
                is_active=True
            )
            
            if not api_key_obj.is_valid():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid or expired API key'
                }, status=401)
            
            # Update last used timestamp
            api_key_obj.last_used = timezone.now()
            api_key_obj.save(update_fields=['last_used'])
            
            # Set request.user to the API key owner
            request.user = api_key_obj.user
            request.api_key = api_key_obj
            
            return view_func(request, *args, **kwargs)
            
        except APIKey.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid API key'
            }, status=401)
    
    return _wrapped_view


def service_permission_required(permission_type):
    """
    Decorator to check service-level permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            service_id = kwargs.get('service_id')
            
            if not service_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Service ID required'
                }, status=400)
            
            user = request.user
            
            # Admin users have all permissions
            if user.role == 'admin':
                return view_func(request, *args, **kwargs)
            
            # Check role-based permissions
            if permission_type == 'view' and user.role in ['manager', 'viewer']:
                return view_func(request, *args, **kwargs)
            elif permission_type in ['modify', 'delete'] and user.role == 'manager':
                return view_func(request, *args, **kwargs)
            
            # Check service-specific permissions
            from .models import ServicePermission
            has_permission = ServicePermission.objects.filter(
                user=user,
                service_name=service_id,  # In a real app, you'd resolve service ID to name
                permission=permission_type
            ).exists()
            
            if has_permission:
                return view_func(request, *args, **kwargs)
            
            # Log access denied
            AuditLog.objects.create(
                user=user,
                action='access_denied',
                resource=f'Service: {service_id}, Permission: {permission_type}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False,
                error_message=f'Insufficient service permissions'
            )
            
            return JsonResponse({
                'status': 'error',
                'message': 'Insufficient permissions for this service'
            }, status=403)
        
        return _wrapped_view
    return decorator


def superuser_required(view_func):
    """
    Decorator to require superuser status
    """
    def check_superuser(user):
        return user.is_superuser
    
    return user_passes_test(check_superuser)(view_func)


def active_user_required(view_func):
    """
    Decorator to ensure user account is active
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_active:
            messages.error(request, 'Your account has been deactivated.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def rate_limit(max_requests=100, window_minutes=60, per_user=True):
    """
    Simple rate limiting decorator
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            from django.core.cache import cache
            from django.utils import timezone
            
            if per_user and request.user.is_authenticated:
                key = f"rate_limit_user_{request.user.id}_{view_func.__name__}"
            else:
                key = f"rate_limit_ip_{get_client_ip(request)}_{view_func.__name__}"
            
            current_time = timezone.now()
            window_start = current_time - timezone.timedelta(minutes=window_minutes)
            
            # Get current request count
            requests = cache.get(key, [])
            
            # Filter requests within the window
            requests = [req_time for req_time in requests if req_time > window_start]
            
            if len(requests) >= max_requests:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            
            # Add current request
            requests.append(current_time)
            cache.set(key, requests, timeout=window_minutes * 60)
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator