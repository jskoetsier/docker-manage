"""
Context processors for global template variables
"""

from .version import get_build_info, get_version, get_version_display


def version_context(request):
    """Add version information to template context"""
    return {
        "app_version": get_version(),
        "app_version_display": get_version_display(),
        "build_info": get_build_info(),
    }
