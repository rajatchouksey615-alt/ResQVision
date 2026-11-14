from django.contrib import admin

from apps.organizations.models import Organization, OrganizationMembership


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Organization)
class OrganizationAdmin(ReadOnlyAdmin):
    list_display = ("code", "display_name", "organization_kind", "is_active")
    list_filter = ("organization_kind", "is_active")
    search_fields = ("code", "display_name")


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(ReadOnlyAdmin):
    list_display = ("user", "organization", "role_group", "status")
    list_filter = ("role_group", "status")
    search_fields = ("user__email", "organization__code")
