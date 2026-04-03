from django.contrib import admin
from .models import (
    DjangoOrganization, DjangoUser, DjangoPatient, AuditEntry, SystemConfig,
    DjangoPtoRequest, DjangoAvailabilityRule, DjangoScheduleTemplate, DjangoRoom,
)


@admin.register(DjangoOrganization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "city", "state", "is_active", "created_at")
    list_filter = ("org_type", "state", "is_active")
    search_fields = ("name", "city", "state")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Basic Info", {"fields": ("name", "org_type", "is_active", "ext_id")}),
        ("Address", {"fields": ("address", "city", "state", "zip")}),
        ("Notes", {"fields": ("notes", "created_at")}),
    )


@admin.register(DjangoUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "role", "specialty", "organization", "is_active", "is_verified")
    list_filter = ("role", "specialty", "is_active", "is_verified", "mfa_enabled")
    search_fields = ("email", "first_name", "last_name", "npi")
    readonly_fields = ("created_at",)
    raw_id_fields = ("organization",)
    fieldsets = (
        ("Identity", {"fields": ("email", "first_name", "last_name", "phone", "ext_id")}),
        ("Clinical", {"fields": ("role", "specialty", "npi", "provider_type")}),
        ("Access", {"fields": ("is_active", "is_verified", "mfa_enabled", "organization")}),
        ("Metadata", {"fields": ("created_at",)}),
    )


@admin.register(DjangoPatient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "status", "organization", "created_at")
    list_filter = ("status", "gender", "organization")
    search_fields = ("first_name", "last_name", "email", "phone")
    readonly_fields = ("created_at",)
    raw_id_fields = ("organization", "primary_provider")
    fieldsets = (
        ("Demographics", {"fields": ("first_name", "last_name", "date_of_birth", "gender", "ext_id")}),
        ("Contact", {"fields": ("email", "phone", "address")}),
        ("Clinical", {"fields": ("status", "organization", "primary_provider")}),
        ("Metadata", {"fields": ("created_at",)}),
    )


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ("action", "user_email", "resource_type", "resource_id", "ip_address", "created_at")
    list_filter = ("action", "resource_type")
    search_fields = ("user_email", "resource_id", "details")
    readonly_fields = ("created_at", "user_email", "action", "resource_type", "resource_id", "details", "ip_address")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "is_sensitive", "updated_at")
    search_fields = ("key", "description")
    readonly_fields = ("updated_at",)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if obj and obj.is_sensitive and not request.user.is_superuser:
            return [f for f in fields if f != "value"]
        return fields


# ─── Calendar / Scheduling Admin ─────────────────────────────────────────────

@admin.register(DjangoPtoRequest)
class PtoRequestAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "type", "status", "date_from", "date_to", "duration", "created_at")
    list_filter = ("type", "status")
    search_fields = ("provider_name", "reason", "coverage_provider")
    readonly_fields = ("ext_id", "user_ext_id", "created_at")
    list_editable = ("status",)
    ordering = ("-created_at",)


@admin.register(DjangoAvailabilityRule)
class AvailabilityRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "priority", "applies_to", "enabled")
    list_filter = ("type", "enabled")
    search_fields = ("name", "description", "applies_to")
    list_editable = ("enabled", "priority")
    ordering = ("priority", "name")


@admin.register(DjangoScheduleTemplate)
class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "badge", "status", "days", "applied_to", "usage_count")
    list_filter = ("badge", "status")
    search_fields = ("name", "description", "applied_to")
    list_editable = ("status",)
    ordering = ("name",)


@admin.register(DjangoRoom)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "status", "icon")
    list_filter = ("type", "status")
    search_fields = ("name",)
    list_editable = ("status",)
    ordering = ("name",)
