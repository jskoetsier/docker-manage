from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import APIKey

User = get_user_model()


class APIKeyAuthentication(BaseAuthentication):
    """
    Custom API Key authentication for REST API endpoints
    """
    
    def authenticate(self, request):
        # Check for API key in header or query parameter
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        
        if not api_key:
            return None  # No API key provided, fall back to other authentication
        
        try:
            api_key_obj = APIKey.objects.select_related('user').get(
                key=api_key,
                is_active=True
            )
            
            if not api_key_obj.is_valid():
                raise AuthenticationFailed('Invalid or expired API key')
            
            # Update last used timestamp
            api_key_obj.last_used = timezone.now()
            api_key_obj.save(update_fields=['last_used'])
            
            return (api_key_obj.user, api_key_obj)
            
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('Invalid API key')
    
    def authenticate_header(self, request):
        return 'X-API-Key'