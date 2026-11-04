import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

class ResponsibleGamingPolicy(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rg_policy")
    daily_deposit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=2000)
    weekly_deposit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    daily_loss_limit = models.DecimalField(max_digits=12, decimal_places=2, default=2000)
    weekly_loss_limit = models.DecimalField(max_digits=12, decimal_places=2, default=5000)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

class UserRestriction(models.Model):
    class Kind(models.TextChoices):
        COOL_OFF = "COOL_OFF", "Cool off"
        SELF_EXCLUSION = "SELF_EXCLUSION", "Self exclusion"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="restrictions")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def is_current(self):
        return self.active and self.starts_at <= timezone.now() and (self.ends_at is None or self.ends_at > timezone.now())

class ActivityEvent(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        LOSS = "LOSS", "Loss"
        BET = "BET", "Bet"
        BONUS_CLAIM = "BONUS_CLAIM", "Bonus claim"
        BLOCKED_ACTION = "BLOCKED_ACTION", "Blocked action"
        LOGIN = "LOGIN", "Login"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_events")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    idempotency_key = models.CharField(max_length=128, blank=True, null=True)
    ip_hash = models.CharField(max_length=128, blank=True)
    device_hash = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "idempotency_key"], name="uniq_user_event_idem")]
        indexes = [models.Index(fields=["user", "kind", "occurred_at"], name="activity_user_kind_time")]

class RiskAlert(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="risk_alerts")
    event = models.ForeignKey(ActivityEvent, on_delete=models.SET_NULL, null=True, blank=True)
    rule_code = models.CharField(max_length=64)
    title = models.CharField(max_length=180)
    severity = models.CharField(max_length=12, choices=Severity.choices, default=Severity.MEDIUM)
    evidence = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=16, default="RULE")
    anomaly_score = models.FloatField(null=True, blank=True)
    model_version = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["severity", "created_at"], name="alert_severity_time")]

class RiskCase(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        DISMISSED = "DISMISSED", "Dismissed"
        ESCALATED = "ESCALATED", "Escalated"
        RESOLVED = "RESOLVED", "Resolved"
    alert = models.OneToOneField(RiskAlert, on_delete=models.CASCADE, related_name="case")
    status = models.CharField(max_length=20, choices=Status.choices, default="OPEN")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_risk_cases")
    decision_reason = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    subject_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="subject_audit_logs")
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    request_id = models.CharField(max_length=100, blank=True)
    class Meta: ordering = ["-created_at"]

class ModelVersion(models.Model):
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=80)
    artifact_path = models.CharField(max_length=255, blank=True)
    trained_at = models.DateTimeField(auto_now_add=True)
    metrics = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=False)
