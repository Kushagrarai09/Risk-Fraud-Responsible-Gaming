from datetime import timedelta
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from .models import ActivityEvent, AuditLog, RiskAlert, RiskCase, UserRestriction
from .serializers import PolicySerializer, LimitUpdateSerializer, EventIngestSerializer, CaseSerializer, DecisionSerializer, AuditSerializer
from .services import audit, ensure_policy, enforce_deposit, enforce_loss, evaluate_event, create_alert
@api_view(["GET"])
@permission_classes([])
def health(request): return JsonResponse({"status":"ok","service":"risk-fraud-responsible-gaming"})
class MyPolicyView(APIView):
    def get(self, request): return Response(PolicySerializer(ensure_policy(request.user)).data)
class LimitsView(APIView):
    def post(self, request):
        s=LimitUpdateSerializer(data=request.data); s.is_valid(raise_exception=True); policy=ensure_policy(request.user)
        for field,value in s.validated_data.items(): setattr(policy,field,value)
        policy.version+=1; policy.save(); audit(request.user,"POLICY_LIMITS_UPDATED",request.user,"ResponsibleGamingPolicy",policy.id,{"version":policy.version,"changed_fields":list(s.validated_data.keys())})
        return Response(PolicySerializer(policy).data)
class RestrictionView(APIView):
    kind=None
    def post(self, request):
        duration_days=request.data.get("duration_days")
        if self.kind==UserRestriction.Kind.SELF_EXCLUSION:
            ends_at=None
            if duration_days is not None:
                try:
                    days=int(duration_days)
                    if days<1 or days>36500: raise ValueError()
                    ends_at=timezone.now()+timedelta(days=days)
                except (ValueError,TypeError): return Response({"detail":"duration_days must be an integer from 1 to 36500."},status=400)
        else:
            try:
                days=int(duration_days)
                if days<1 or days>30: raise ValueError()
                ends_at=timezone.now()+timedelta(days=days)
            except (ValueError,TypeError): return Response({"detail":"Cool-off duration_days must be from 1 to 30."},status=400)
        restriction=UserRestriction.objects.create(user=request.user,kind=self.kind,ends_at=ends_at,reason="User requested")
        audit(request.user,"RESTRICTION_STARTED",request.user,"UserRestriction",restriction.id,{"kind":restriction.kind,"ends_at":restriction.ends_at.isoformat() if restriction.ends_at else None})
        return Response({"id":restriction.id,"kind":restriction.kind,"starts_at":restriction.starts_at,"ends_at":restriction.ends_at,"active":restriction.active},status=201)
class CoolOffView(RestrictionView): kind=UserRestriction.Kind.COOL_OFF
class SelfExclusionView(RestrictionView): kind=UserRestriction.Kind.SELF_EXCLUSION
class DepositView(APIView):
    def post(self, request):
        s=EventIngestSerializer(data={**request.data,"kind":"DEPOSIT"}); s.is_valid(raise_exception=True); key=request.headers.get("Idempotency-Key","")
        if key:
            old=ActivityEvent.objects.filter(user=request.user,idempotency_key=key).first()
            if old: return Response({"id":str(old.id),"status":"already_processed"},status=200)
        try: event=enforce_deposit(request.user,s.validated_data["amount"],key)
        except ValueError as exc: return Response({"detail":str(exc)},status=409)
        evaluate_event(event); return Response({"id":str(event.id),"status":"accepted","amount":str(event.amount)},status=201)
class LossView(APIView):
    def post(self, request):
        s=EventIngestSerializer(data={**request.data,"kind":"LOSS"}); s.is_valid(raise_exception=True)
        try: event=enforce_loss(request.user,s.validated_data["amount"])
        except ValueError as exc: return Response({"detail":str(exc)},status=409)
        evaluate_event(event); return Response({"id":str(event.id),"status":"accepted"},status=201)
class EventIngestView(APIView):
    def post(self, request):
        s=EventIngestSerializer(data=request.data); s.is_valid(raise_exception=True); key=request.headers.get("Idempotency-Key","")
        if key:
            old=ActivityEvent.objects.filter(user=request.user,idempotency_key=key).first()
            if old: return Response({"id":str(old.id),"status":"already_processed"},status=200)
        d=s.validated_data
        try:
            with transaction.atomic(): event=ActivityEvent.objects.create(user=request.user,kind=d["kind"],amount=d["amount"],idempotency_key=key or None,metadata=d["metadata"],ip_hash=d.get("ip_hash",""),device_hash=d.get("device_hash",""))
        except IntegrityError:
            old=ActivityEvent.objects.filter(user=request.user,idempotency_key=key).first()
            if old: return Response({"id":str(old.id),"status":"already_processed"},status=200)
            raise
        evaluate_event(event); return Response({"id":str(event.id),"status":"accepted"},status=201)
class CaseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=CaseSerializer; permission_classes=[IsAdminUser]
    queryset=RiskCase.objects.select_related("alert","alert__user","assigned_to").all()
class CaseDecisionView(APIView):
    permission_classes=[IsAdminUser]
    def post(self,request,pk):
        s=DecisionSerializer(data=request.data); s.is_valid(raise_exception=True)
        try: case=RiskCase.objects.select_related("alert").get(pk=pk)
        except RiskCase.DoesNotExist: return Response({"detail":"Case not found."},status=404)
        case.status=s.validated_data["status"]; case.decision_reason=s.validated_data["reason"]; case.assigned_to=request.user; case.reviewed_at=timezone.now(); case.save()
        audit(request.user,"RISK_CASE_DECISION",case.alert.user,"RiskCase",case.id,{"status":case.status,"reason":case.decision_reason,"alert_id":case.alert_id})
        return Response(CaseSerializer(case).data)
class AuditListView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request): return Response(AuditSerializer(AuditLog.objects.select_related("actor","subject_user").all()[:500],many=True).data)
class TrainDemoModelView(APIView):
    permission_classes=[IsAdminUser]
    def post(self,request):
        from .ml import train_demo_model
        path,version=train_demo_model(); audit(request.user,"DEMO_MODEL_TRAINED",request.user,"ModelVersion",version,{"path":path})
        return Response({"status":"trained","version":version,"note":"Trained on synthetic data only."})
class ScoreDemoModelView(APIView):
    permission_classes=[IsAdminUser]
    def post(self,request):
        from .ml import FEATURES,score_features
        try: result=score_features(request.data)
        except ValueError as exc: return Response({"detail":str(exc)},status=409)
        if result["prediction"]==-1:
            create_alert(request.user,"MODEL_ANOMALY","Unusual activity pattern (model review)",RiskAlert.Severity.MEDIUM,{"features":{k:request.data.get(k,0) for k in FEATURES},"interpretation":"Anomaly only; not proof of wrongdoing"},source="MODEL",anomaly_score=result["anomaly_score"],model_version=result["model_version"])
        audit(request.user,"DEMO_MODEL_SCORED",request.user,"ModelVersion",result["model_version"],result); return Response(result)
