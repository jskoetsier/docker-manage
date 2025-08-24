from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import User, AuditLog, UserSession
import secrets


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login events"""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Create audit log
    AuditLog.objects.create(
        user=user,
        action='login',
        ip_address=ip_address,
        user_agent=user_agent,
        success=True
    )

    # Update user last activity
    user.last_activity = timezone.now()
    user.save(update_fields=['last_activity'])

    # Create or update user session
    session_key = request.session.session_key
    if session_key:
        UserSession.objects.update_or_create(
            session_key=session_key,
            defaults={
                'user': user,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'is_active': True,
                'last_activity': timezone.now()
            }
        )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout events"""
    if user:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Create audit log
        AuditLog.objects.create(
            user=user,
            action='logout',
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )

        # Deactivate user session
        session_key = request.session.session_key
        if session_key:
            UserSession.objects.filter(session_key=session_key).update(is_active=False)


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    username = credentials.get('username', 'Unknown')

    AuditLog.objects.create(
        user=None,
        action='login',
        resource=f'Failed login attempt for: {username}',
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
        error_message='Invalid credentials'
    )


@receiver(post_save, sender=User)
def log_user_creation(sender, instance, created, **kwargs):
    """Log user creation events"""
    if created:
        AuditLog.objects.create(
            user=instance,
            action='create_user',
            resource=f'User created: {instance.username}',
            ip_address='127.0.0.1',  # System action
            success=True
        )


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'


def generate_api_key():
    """Generate a secure API key"""
    return secrets.token_urlsafe(48)
