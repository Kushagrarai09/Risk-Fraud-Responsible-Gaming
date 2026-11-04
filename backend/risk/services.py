from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import ActivityEvent, AuditLog, ResponsibleGamingPolicy, RiskAlert, RiskCase, UserRestriction

def audit(actor, action, subject_user=None, object_type="", object_id="", details=None):
    return AuditLog.objects.create(actor=actor, subject_user=subject_user, action=action, object_type=object_type, object_id=str(object_id), details=details or {})
def active_restriction(user):
    return next((r for r in user.restrictions.all() if r.is_current()), None)
def ensure_policy(user):
    policy, _ = ResponsibleGamingPolicy.objects.get_or_create(user=user)
    return policy
def _period_total(user, kind, since):
    return ActivityEvent.objects.filter(user=user, kind=kind, occurred_at__gte=since).aggregate(total=Sum("amount"))["total"] or Decimal("0")
def models_end_filter(now):
    from django.db.models import Q
    return Q(ends_at__isnull=True) | Q(ends_at__gt=now)
def enforce_deposit(user, amount, idempotency_key=""):
    now = timezone.now()
    with transaction.atomic():
        policy, _ = ResponsibleGamingPolicy.objects.select_for_update().get_or_create(user=user)
        restriction = UserRestriction.objects.filter(user=user, active=True, starts_at__lte=now).filter(models_end_filter(now)).order_by("-starts_at").first()
        if restriction:
            audit(user, "DEPOSIT_BLOCKED_RESTRICTION", user, "UserRestriction", restriction.id, {"kind": restriction.kind})
            raise ValueError(f"Deposits blocked by active {restriction.kind.lower()} restriction.")
        day_total = _period_total(user, ActivityEvent.Kind.DEPOSIT, now - timedelta(hours=24))
        week_total = _period_total(user, ActivityEvent.Kind.DEPOSIT, now - timedelta(days=7))
        if day_total + amount > policy.daily_deposit_limit:
            audit(user, "DEPOSIT_BLOCKED_DAILY_LIMIT", user, "ResponsibleGamingPolicy", policy.id, {"current": str(day_total), "attempt": str(amount), "limit": str(policy.daily_deposit_limit)})
            raise ValueError("Deposit would exceed the daily deposit limit.")
        if week_total + amount > policy.weekly_deposit_limit:
            audit(user, "DEPOSIT_BLOCKED_WEEKLY_LIMIT", user, "ResponsibleGamingPolicy", policy.id, {"current": str(week_total), "attempt": str(amount), "limit": str(policy.weekly_deposit_limit)})
            raise ValueError("Deposit would exceed the weekly deposit limit.")
        event = ActivityEvent.objects.create(user=user, kind=ActivityEvent.Kind.DEPOSIT, amount=amount, idempotency_key=idempotency_key or None)
        audit(user, "DEMO_DEPOSIT_ACCEPTED", user, "ActivityEvent", event.id, {"amount": str(amount)})
        return event
def enforce_loss(user, amount):
    now = timezone.now()
    with transaction.atomic():
        policy, _ = ResponsibleGamingPolicy.objects.select_for_update().get_or_create(user=user)
        day_total = _period_total(user, ActivityEvent.Kind.LOSS, now - timedelta(hours=24))
        week_total = _period_total(user, ActivityEvent.Kind.LOSS, now - timedelta(days=7))
        if day_total + amount > policy.daily_loss_limit or week_total + amount > policy.weekly_loss_limit:
            audit(user, "LOSS_LIMIT_THRESHOLD_REACHED", user, "ResponsibleGamingPolicy", policy.id, {"attempt": str(amount), "daily_total": str(day_total), "weekly_total": str(week_total)})
            raise ValueError("This event would exceed the configured loss limit.")
        return ActivityEvent.objects.create(user=user, kind=ActivityEvent.Kind.LOSS, amount=amount)
def create_alert(user, code, title, severity, evidence, event=None, source="RULE", anomaly_score=None, model_version=""):
    alert = RiskAlert.objects.create(user=user, event=event, rule_code=code, title=title, severity=severity, evidence=evidence, source=source, anomaly_score=anomaly_score, model_version=model_version)
    RiskCase.objects.create(alert=alert)
    return alert
def evaluate_event(event):
    from .models import RiskAlert
    from django.utils import timezone
    from datetime import timedelta
    alerts = []
    if event.kind == ActivityEvent.Kind.DEPOSIT:
        count = ActivityEvent.objects.filter(user=event.user, kind=ActivityEvent.Kind.DEPOSIT, occurred_at__gte=timezone.now()-timedelta(minutes=2)).count()
        if count >= 5: alerts.append(create_alert(event.user, "RAPID_DEPOSITS", "Rapid deposits detected", RiskAlert.Severity.MEDIUM, {"deposits_in_2_minutes": count, "threshold": 5}, event))
    if event.kind == ActivityEvent.Kind.BONUS_CLAIM:
        count = ActivityEvent.objects.filter(user=event.user, kind=ActivityEvent.Kind.BONUS_CLAIM, occurred_at__gte=timezone.now()-timedelta(hours=24)).count()
        if count > 1: alerts.append(create_alert(event.user, "BONUS_CLAIM_VELOCITY", "Repeated bonus claims need review", RiskAlert.Severity.HIGH, {"claims_in_24_hours": count}, event))
    if event.kind == ActivityEvent.Kind.BLOCKED_ACTION:
        alerts.append(create_alert(event.user, "RESTRICTED_ACTION_ATTEMPT", "Attempted action during a restriction", RiskAlert.Severity.CRITICAL, {"kind": event.kind}, event))
    return alerts
