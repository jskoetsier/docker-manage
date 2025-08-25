from django import template

register = template.Library()

@register.filter
def multiply(value, factor):
    """
    Multiply the given value by the factor.
    Usage: {{ value|multiply:factor }}
    """
    try:
        return float(value) * float(factor)
    except (ValueError, TypeError):
        return 0