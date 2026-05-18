from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get a value from a dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0

@register.filter
def split(value, delimiter):
    """Split a string by delimiter."""
    if isinstance(value, str):
        return value.split(delimiter)
    return value