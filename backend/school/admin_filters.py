from django.contrib import admin
from .models import Term


class CurrentTermFilter(admin.SimpleListFilter):
    title = "الترم"
    parameter_name = "term_scope"

    def lookups(self, request, model_admin):
        return (
            ("current", "الترم الحالي"),
            ("all", "كل الترمات"),
        )

    def queryset(self, request, queryset):
        val = self.value()
        if val == "current":
            t = Term.objects.filter(is_current=True).order_by("-id").first()
            return queryset.filter(term=t) if t else queryset.none()
        # default fallthrough returns queryset unchanged (acts like 'all')
        return queryset
