from django.contrib import admin as django_admin
from django.contrib.admin import AdminSite, ModelAdmin
from django.utils.translation import gettext_lazy as _

from .models import Staff


class RestrictedAdminSite(AdminSite):
    site_header = _("لوحة الإدارة")
    site_title = _("لوحة الإدارة")
    index_title = _("مرحباً بكم في لوحة الإدارة")

    def has_permission(self, request):
        # Only allow authenticated and active users who are either:
        # - Django superusers, or
        # - Linked to Staff with role 'admin'
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        try:
            return Staff.objects.filter(user=user, role="admin").exists()
        except Exception:
            return False


# Instantiate restricted admin site
restricted_admin_site = RestrictedAdminSite(name="restricted_admin")

# Mirror existing registrations from the default admin site
# This allows us to keep using the app's admin.py without duplicate registrations
try:
    # Ensure all admin modules are loaded so default site has full registry
    django_admin.autodiscover()

    for model, model_admin in list(django_admin.site._registry.items()):
        admin_class = model_admin.__class__
        try:
            restricted_admin_site.register(model, admin_class)
        except Exception:
            # As a fallback, try to register with a bare ModelAdmin
            try:
                restricted_admin_site.register(model, ModelAdmin)
            except Exception:
                # Silently ignore models that cannot be registered (rare)
                pass
except Exception:
    # If mirroring fails for any reason, keep the restricted site with no models
    # (better to fail-closed than fail-open)
    pass
