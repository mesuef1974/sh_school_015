from django import template

register = template.Library()


@register.filter(name="cls_label")
def cls_label(value):
    """Return a short label for a Class instance: grade-section (e.g., 7-A).

    Accepts an object with attributes `grade` and `section` (like school.models.Class).
    If section is empty/None, returns just the grade as string.
    """
    if value is None:
        return ""
    grade = getattr(value, "grade", None)
    section = getattr(value, "section", "") or ""
    if section:
        try:
            section = section.strip()
        except Exception:
            pass
        return f"{grade}-{section}"
    return f"{grade}"


@register.filter(name="get_attr")
def get_attr(obj, key):
    """Safely get an attribute or dict item from an object in templates.

    - If obj is a dict or has __getitem__, try obj[key].
    - Then try getattr(obj, key).
    - If key is an int-like string and obj is indexable, try integer index.
    - Returns empty string on any failure, to keep templates resilient.
    """
    if obj is None or key is None:
        return ""
    # Normalize key
    try:
        k = key
        # 1) Mapping or sequence access
        try:
            return obj[k]
        except Exception:
            pass
        # 2) Attribute access
        try:
            return getattr(obj, k)
        except Exception:
            pass
        # 3) Integer index
        try:
            idx = int(k)
            return obj[idx]
        except Exception:
            pass
    except Exception:
        return ""
    return ""
