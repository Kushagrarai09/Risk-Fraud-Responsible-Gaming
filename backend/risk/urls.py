from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MyPolicyView, LimitsView, CoolOffView, SelfExclusionView, DepositView, LossView, EventIngestView, CaseViewSet, CaseDecisionView, AuditListView, TrainDemoModelView, ScoreDemoModelView
router=DefaultRouter(); router.register("risk/cases",CaseViewSet,basename="risk-case")
urlpatterns=[path("policies/me/",MyPolicyView.as_view()),path("policies/limits/",LimitsView.as_view()),path("policies/cool-off/",CoolOffView.as_view()),path("policies/self-exclusion/",SelfExclusionView.as_view()),path("activity/deposits/",DepositView.as_view()),path("activity/losses/",LossView.as_view()),path("risk/events/",EventIngestView.as_view()),path("risk/cases/<int:pk>/decision/",CaseDecisionView.as_view()),path("audit-logs/",AuditListView.as_view()),path("ml/train-demo/",TrainDemoModelView.as_view()),path("ml/score-demo/",ScoreDemoModelView.as_view())]+router.urls
