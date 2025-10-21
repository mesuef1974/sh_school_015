"""
Caching utilities and decorators for school application
Provides smart caching for frequently accessed data
"""

from functools import wraps
from typing import Optional, Callable
from django.core.cache import caches, cache as default_cache
from django.db.models import Model, QuerySet
from django.db.models.signals import post_save, post_delete
import hashlib
import json


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from prefix and arguments

    Args:
        prefix: Cache key prefix (e.g., 'class_list', 'student_detail')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        String cache key
    """
    parts = [str(prefix)]

    # Add positional args
    for arg in args:
        if isinstance(arg, Model):
            parts.append(f"{arg.__class__.__name__}_{arg.pk}")
        else:
            parts.append(str(arg))

    # Add keyword args (sorted for consistency)
    if kwargs:
        kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
        kwargs_hash = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
        parts.append(kwargs_hash)

    return ":".join(parts)


def cached_query(
    timeout: Optional[int] = None,
    cache_name: str = "default",
    key_prefix: Optional[str] = None,
    invalidate_on: Optional[list] = None,
):
    """
    Decorator to cache function results with automatic invalidation

    Usage:
        @cached_query(timeout=600, cache_name='attendance', key_prefix='daily_summary')
        def get_daily_summary(date, class_id):
            return AttendanceDaily.objects.filter(date=date, school_class_id=class_id)

    Args:
        timeout: Cache timeout in seconds (None = use cache default)
        cache_name: Name of cache backend to use ('default', 'long_term', 'attendance')
        key_prefix: Prefix for cache keys
        invalidate_on: List of model classes that should invalidate this cache when saved/deleted
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the cache backend
            cache_backend = caches[cache_name] if cache_name else default_cache

            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = make_cache_key(prefix, *args, **kwargs)

            # Try to get from cache
            result = cache_backend.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)

            # Convert QuerySet to list for caching
            if isinstance(result, QuerySet):
                result = list(result)

            cache_backend.set(cache_key, result, timeout)
            return result

        # Store metadata for cache invalidation
        wrapper._cache_name = cache_name
        wrapper._key_prefix = key_prefix or func.__name__
        wrapper._invalidate_on = invalidate_on or []

        return wrapper

    return decorator


def invalidate_cache_for_model(model_class: type, cache_patterns: list = None):
    """
    Invalidate cache entries when a model is saved or deleted

    Usage:
        invalidate_cache_for_model(Student, ['student_list', 'class_students'])

    Args:
        model_class: Model class to watch
        cache_patterns: List of cache key prefixes to invalidate
    """

    def on_change(sender, instance, **kwargs):
        for pattern in cache_patterns or []:
            # Clear all keys matching pattern
            for cache_name in ["default", "long_term", "attendance"]:
                cache_backend = caches[cache_name]
                # Note: Redis doesn't support wildcard delete in django-redis
                # We use versioning instead by incrementing VERSION
                try:
                    cache_backend.delete_pattern(f"*{pattern}*")
                except AttributeError:
                    # Fallback: clear entire cache (not ideal but safe)
                    cache_backend.clear()

    post_save.connect(on_change, sender=model_class, weak=False)
    post_delete.connect(on_change, sender=model_class, weak=False)


# Caching decorators for common queries


def cache_class_data(timeout: int = 3600):
    """Cache class-related data (long-lived)"""
    return cached_query(timeout=timeout, cache_name="long_term", key_prefix="class")


def cache_student_data(timeout: int = 1800):
    """Cache student-related data (medium-lived)"""
    return cached_query(timeout=timeout, cache_name="default", key_prefix="student")


def cache_attendance_data(timeout: int = 600):
    """Cache attendance data (short-lived)"""
    return cached_query(timeout=timeout, cache_name="attendance", key_prefix="attendance")


def cache_term_data(timeout: int = 3600):
    """Cache term/academic year data (long-lived)"""
    return cached_query(timeout=timeout, cache_name="long_term", key_prefix="term")


# Pre-built cached queries


@cache_term_data(timeout=7200)
def get_current_term():
    """Get current active term (cached for 2 hours)"""
    from .models import Term

    return Term.objects.filter(is_current=True).select_related("academic_year").first()


@cache_class_data(timeout=3600)
def get_active_classes():
    """Get all active classes (cached for 1 hour)"""
    from .models import Class

    return list(Class.objects.all().select_related("wing").order_by("grade", "section"))


@cache_student_data(timeout=1800)
def get_class_students(class_id: int, active_only: bool = True):
    """Get students for a class (cached for 30 minutes)"""
    from .models import Student

    qs = Student.objects.filter(class_fk_id=class_id)
    if active_only:
        qs = qs.filter(active=True)
    return list(qs.order_by("full_name"))


@cache_attendance_data(timeout=300)
def get_daily_attendance_summary(date, class_id=None):
    """Get daily attendance summary (cached for 5 minutes)"""
    from .models import AttendanceDaily

    qs = AttendanceDaily.objects.filter(date=date)
    if class_id:
        qs = qs.filter(school_class_id=class_id)
    return list(qs.select_related("student", "school_class", "wing", "term"))


class CacheInvalidator:
    """
    Utility class to handle cache invalidation on model changes
    Call setup() in AppConfig.ready() to register signal handlers
    """

    @staticmethod
    def setup():
        """Register all cache invalidation handlers"""
        from .models import (
            Class,
            Student,
            Term,
            AcademicYear,
            AttendanceRecord,
            AttendanceDaily,
            ExitEvent,
        )

        # Invalidate class cache when Class, Wing, or Student count changes
        invalidate_cache_for_model(Class, ["class", "student"])

        # Invalidate student cache when Student changes
        invalidate_cache_for_model(Student, ["student", "class"])

        # Invalidate attendance cache when attendance records change
        invalidate_cache_for_model(AttendanceRecord, ["attendance"])
        invalidate_cache_for_model(AttendanceDaily, ["attendance"])
        invalidate_cache_for_model(ExitEvent, ["attendance", "exit"])

        # Invalidate term cache when Term or AcademicYear changes
        invalidate_cache_for_model(Term, ["term"])
        invalidate_cache_for_model(AcademicYear, ["term"])


# Manual cache invalidation functions


def clear_all_caches():
    """Clear all caches (use with caution)"""
    for cache_name in ["default", "long_term", "attendance"]:
        caches[cache_name].clear()


def clear_cache_for_date(date):
    """Clear attendance caches for a specific date"""
    cache_backend = caches["attendance"]
    # Try to clear date-specific keys
    try:
        cache_backend.delete_pattern(f"*{date}*")
    except AttributeError:
        # Fallback: clear all attendance cache
        cache_backend.clear()


def clear_cache_for_class(class_id: int):
    """Clear caches related to a specific class"""
    patterns = [f"*class*{class_id}*", f"*student*{class_id}*"]
    for cache_name in ["default", "long_term", "attendance"]:
        cache_backend = caches[cache_name]
        for pattern in patterns:
            try:
                cache_backend.delete_pattern(pattern)
            except AttributeError:
                cache_backend.clear()
                break


def warm_cache():
    """
    Pre-populate cache with frequently accessed data
    Call this after migrations or during deployment
    """
    # Warm up commonly accessed data
    get_current_term()
    get_active_classes()

    # Optionally warm up class students (comment out if too many classes)
    # from .models import Class
    # for cls in Class.objects.all()[:10]:  # Limit to first 10 classes
    #     get_class_students(cls.id)
