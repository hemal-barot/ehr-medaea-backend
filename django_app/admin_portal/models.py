from django.db import models


class DjangoOrganization(models.Model):
    """Mirror of FastAPI Organization for Django admin management."""
    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="FastAPI ID")
    name = models.CharField(max_length=255)
    org_type = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DjangoUser(models.Model):
    """Mirror of FastAPI User for Django admin management."""
    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="FastAPI ID")
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=50, default="doctor")
    specialty = models.CharField(max_length=100, blank=True)
    npi = models.CharField(max_length=20, blank=True, verbose_name="NPI")
    provider_type = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    organization = models.ForeignKey(
        DjangoOrganization, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Provider / User"
        verbose_name_plural = "Providers / Users"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class DjangoPatient(models.Model):
    """Mirror of FastAPI Patient for Django admin management."""
    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other"), ("U", "Unknown")]
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive"), ("deceased", "Deceased")]

    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="FastAPI ID")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    organization = models.ForeignKey(
        DjangoOrganization, on_delete=models.SET_NULL, null=True, blank=True
    )
    primary_provider = models.ForeignKey(
        DjangoUser, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class AuditEntry(models.Model):
    """Audit log entries for admin review."""
    ACTION_CHOICES = [
        ("login", "Login"),
        ("logout", "Logout"),
        ("create", "Create"),
        ("read", "Read"),
        ("update", "Update"),
        ("delete", "Delete"),
    ]
    user_email = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=36, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.user_email} at {self.created_at}"


class SystemConfig(models.Model):
    """System-wide configuration managed by admins."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"
        ordering = ["key"]

    def __str__(self):
        return self.key


# ─── Calendar / Scheduling models ────────────────────────────────────────────

class DjangoPtoRequest(models.Model):
    """View-only mirror of pto_requests for admin oversight."""
    TYPE_CHOICES = [("PTO", "PTO"), ("Sick", "Sick Leave"), ("Conference", "Conference"), ("Blocked", "Blocked Time")]
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("denied", "Denied")]

    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True, verbose_name="FastAPI ID")
    user_ext_id = models.CharField(max_length=36, blank=True, verbose_name="Provider FastAPI ID")
    provider_name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="PTO")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    date_from = models.CharField(max_length=20)
    date_to = models.CharField(max_length=20)
    duration = models.CharField(max_length=50, blank=True)
    coverage_provider = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "PTO / Leave Request"
        verbose_name_plural = "PTO / Leave Requests"
        ordering = ["-created_at"]
        managed = False
        db_table = "pto_requests"

    def __str__(self):
        return f"{self.provider_name} – {self.type} ({self.date_from} → {self.date_to})"


class DjangoAvailabilityRule(models.Model):
    """Scheduling availability rules."""
    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    priority = models.IntegerField(default=1)
    description = models.TextField(blank=True)
    applies_to = models.CharField(max_length=100, default="All Providers")
    conditions = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Availability Rule"
        verbose_name_plural = "Availability Rules"
        ordering = ["priority", "name"]
        managed = False
        db_table = "availability_rules"

    def __str__(self):
        status = "ON" if self.enabled else "OFF"
        return f"[{status}] {self.name}"


class DjangoScheduleTemplate(models.Model):
    """Schedule templates."""
    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    badge = models.CharField(max_length=50, default="Provider")
    status = models.CharField(max_length=20, default="active")
    description = models.TextField(blank=True)
    days = models.CharField(max_length=100, blank=True)
    hours = models.CharField(max_length=100, blank=True)
    types = models.CharField(max_length=255, blank=True)
    applied_to = models.CharField(max_length=255, blank=True)
    usage_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Schedule Template"
        verbose_name_plural = "Schedule Templates"
        ordering = ["name"]
        managed = False
        db_table = "schedule_templates"

    def __str__(self):
        return f"{self.name} ({self.badge})"


class DjangoRoom(models.Model):
    """Physical clinic rooms."""
    TYPE_CHOICES = [("General", "General"), ("Procedure", "Procedure"),
                    ("Specialty", "Specialty"), ("Consult", "Consult"), ("Diagnostic", "Diagnostic")]
    STATUS_CHOICES = [("available", "Available"), ("occupied", "Occupied"),
                      ("reserved", "Reserved"), ("maintenance", "Maintenance")]

    ext_id = models.CharField(max_length=36, unique=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, blank=True)
    icon = models.CharField(max_length=50, default="fa-door-open")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Room"
        verbose_name_plural = "Rooms"
        ordering = ["name"]
        managed = False
        db_table = "rooms"

    def __str__(self):
        return f"{self.name} [{self.status}]"
