from django.contrib import admin
from .models import ResponsibleGamingPolicy, UserRestriction, ActivityEvent, RiskAlert, RiskCase, AuditLog, ModelVersion
admin.site.register([ResponsibleGamingPolicy, UserRestriction, ActivityEvent, RiskAlert, RiskCase, AuditLog, ModelVersion])
