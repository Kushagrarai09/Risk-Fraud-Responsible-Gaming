from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from .models import ActivityEvent, ResponsibleGamingPolicy, UserRestriction, RiskAlert, RiskCase, AuditLog
User=get_user_model()
@pytest.mark.django_db
def test_deposit_limit_rejects_over_limit():
 user=User.objects.create_user(username="demo",password="safe-test-password"); ResponsibleGamingPolicy.objects.create(user=user,daily_deposit_limit=Decimal("2000")); ActivityEvent.objects.create(user=user,kind="DEPOSIT",amount=Decimal("1800")); client=APIClient(); client.force_authenticate(user=user); response=client.post("/api/v1/activity/deposits/",{"amount":"300"},format="json"); assert response.status_code==409; assert ActivityEvent.objects.filter(user=user,kind="DEPOSIT").count()==1
@pytest.mark.django_db
def test_self_exclusion_blocks_demo_deposit():
 user=User.objects.create_user(username="excluded",password="safe-test-password"); UserRestriction.objects.create(user=user,kind="SELF_EXCLUSION",ends_at=None); client=APIClient(); client.force_authenticate(user=user); response=client.post("/api/v1/activity/deposits/",{"amount":"10"},format="json"); assert response.status_code==409
@pytest.mark.django_db
def test_event_idempotency():
 user=User.objects.create_user(username="event-user",password="safe-test-password"); client=APIClient(); client.force_authenticate(user=user); first=client.post("/api/v1/risk/events/",{"kind":"LOGIN"},format="json",HTTP_IDEMPOTENCY_KEY="event-1"); second=client.post("/api/v1/risk/events/",{"kind":"LOGIN"},format="json",HTTP_IDEMPOTENCY_KEY="event-1"); assert first.status_code==201 and second.status_code==200; assert ActivityEvent.objects.filter(user=user).count()==1
@pytest.mark.django_db
def test_staff_can_decide_case_and_audit_is_written():
 staff=User.objects.create_user(username="reviewer",password="safe-test-password",is_staff=True); user=User.objects.create_user(username="subject",password="safe-test-password"); alert=RiskAlert.objects.create(user=user,rule_code="TEST",title="Test alert",severity="MEDIUM"); case=RiskCase.objects.create(alert=alert); client=APIClient(); client.force_authenticate(user=staff); response=client.post(f"/api/v1/risk/cases/{case.id}/decision/",{"status":"UNDER_REVIEW","reason":"Reviewing evidence"},format="json"); assert response.status_code==200; assert AuditLog.objects.filter(action="RISK_CASE_DECISION").exists()
@pytest.mark.django_db
def test_non_staff_cannot_read_cases():
 user=User.objects.create_user(username="ordinary",password="safe-test-password"); client=APIClient(); client.force_authenticate(user=user); assert client.get("/api/v1/risk/cases/").status_code==403
