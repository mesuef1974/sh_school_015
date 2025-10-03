from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    """Return d[key] for dict-like rows in table_detail template (read-only tables)."""
    try:
        return d.get(key)
    except Exception:
        try:
            return d[key]
        except Exception:
            return None


@register.filter(name="get_attr")
def get_attr(obj, field_name):
    """
    Safely retrieve an attribute from a model instance for display in tables.
    - Returns None if missing.
    - For related objects and other non-primitive values, returns their string representation.
    """
    if obj is None or not field_name:
        return None
    # Dict support fallback
    try:
        if isinstance(obj, dict):
            return obj.get(field_name)
    except Exception:
        pass
    try:
        val = getattr(obj, field_name)
    except Exception:
        return None
    try:
        # Avoid calling callables; display as string if needed
        if callable(val):
            return str(val)
        # For None
        if val is None:
            return None
        # For FK or other model objects, show __str__
        return val if isinstance(val, (int, float, bool, str)) else str(val)
    except Exception:
        return None
