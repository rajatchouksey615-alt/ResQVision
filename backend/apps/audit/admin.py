from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "actor_kind", "action", "outcome", "resource_type")
    list_filter = ("actor_kind", "outcome", "resource_type")
    ordering = ("-occurred_at",)
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)
    search_fields = ("action", "actor_ref_snapshot", "actor_service_ref")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
