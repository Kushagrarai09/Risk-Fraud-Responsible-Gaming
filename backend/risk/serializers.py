from rest_framework import serializers
from .models import ResponsibleGamingPolicy, UserRestriction, ActivityEvent, RiskAlert, RiskCase, AuditLog
class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponsibleGamingPolicy
        fields = ["daily_deposit_limit", "weekly_deposit_limit", "daily_loss_limit", "weekly_loss_limit", "updated_at", "version"]
        read_only_fields = ["updated_at", "version"]
class LimitUpdateSerializer(serializers.Serializer):
    daily_deposit_limit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    weekly_deposit_limit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    daily_loss_limit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    weekly_loss_limit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    def validate(self, attrs):
        if not attrs: raise serializers.ValidationError("Provide at least one limit.")
        return attrs
class RestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRestriction
        fields = ["id", "kind", "starts_at", "ends_at", "active", "reason", "created_at"]
        read_only_fields = ["id", "starts_at", "active", "created_at"]
class ActivityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEvent
        fields = ["id", "kind", "amount", "occurred_at", "metadata", "ip_hash", "device_hash"]
        read_only_fields = ["id", "occurred_at"]
class EventIngestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ActivityEvent.Kind.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, default=0)
    metadata = serializers.DictField(required=False, default=dict)
    ip_hash = serializers.CharField(required=False, allow_blank=True, max_length=128)
    device_hash = serializers.CharField(required=False, allow_blank=True, max_length=128)
class AlertSerializer(serializers.ModelSerializer):
    case_status = serializers.CharField(source="case.status", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    class Meta:
        model = RiskAlert
        fields = ["id", "username", "rule_code", "title", "severity", "evidence", "source", "anomaly_score", "model_version", "created_at", "case_status"]
class CaseSerializer(serializers.ModelSerializer):
    alert = AlertSerializer(read_only=True)
    assigned_username = serializers.CharField(source="assigned_to.username", read_only=True)
    class Meta:
        model = RiskCase
        fields = ["id", "alert", "status", "assigned_username", "decision_reason", "reviewed_at", "updated_at"]
class DecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[RiskCase.Status.UNDER_REVIEW, RiskCase.Status.DISMISSED, RiskCase.Status.ESCALATED, RiskCase.Status.RESOLVED])
    reason = serializers.CharField(max_length=2000, allow_blank=False)
class AuditSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    subject_username = serializers.CharField(source="subject_user.username", read_only=True)
    class Meta:
        model = AuditLog
        fields = ["id", "actor_username", "subject_username", "action", "object_type", "object_id", "details", "created_at", "request_id"]
