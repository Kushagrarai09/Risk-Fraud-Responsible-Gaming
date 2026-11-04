from celery import shared_task
from .models import ActivityEvent
from .services import evaluate_event
@shared_task
def evaluate_event_task(event_id):
    try: event = ActivityEvent.objects.get(pk=event_id)
    except ActivityEvent.DoesNotExist: return {"status": "missing"}
    alerts = evaluate_event(event)
    return {"status": "evaluated", "alerts_created": len(alerts)}
