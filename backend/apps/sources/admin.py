from django.contrib import admin

from apps.sources.models import VideoSource


@admin.register(VideoSource)
class VideoSourceAdmin(admin.ModelAdmin):
    list_display = (
        "source_code",
        "name",
        "source_type",
        "authorization_status",
        "availability_status",
    )
    list_filter = ("source_type", "authorization_status", "availability_status")
    search_fields = ("source_code", "name")
    readonly_fields = tuple(field.name for field in VideoSource._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
