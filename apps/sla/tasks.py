from celery import shared_task

from apps.helpdesks.models import HelpDesk
from .models import ServiceQueue
from .services import enqueue, process_queue, try_assign


@shared_task
def auto_assign_helpdesk(hd_id):
    try:
        hd = HelpDesk.objects.select_related(
            'service__category__department'
        ).get(pk=hd_id)
    except HelpDesk.DoesNotExist:
        return

    assigned = try_assign(hd)
    if not assigned:
        enqueue(hd)


@shared_task
def process_department_queue(department_id):
    process_queue(department_id)


@shared_task
def recalculate_queue_scores():
    """Periodic task: recalculate urgency scores and attempt assignment for all queued HDs."""
    department_ids = (
        ServiceQueue.objects
        .select_related('help_desk__service__category__department')
        .values_list('help_desk__service__category__department_id', flat=True)
        .distinct()
    )
    for dept_id in department_ids:
        process_queue(dept_id)


@shared_task
def process_all_queues():
    """Runs at business hours start (08:30 Mon-Fri) to assign tickets queued overnight or on weekends."""
    department_ids = (
        ServiceQueue.objects
        .select_related('help_desk__service__category__department')
        .values_list('help_desk__service__category__department_id', flat=True)
        .distinct()
    )
    for dept_id in department_ids:
        process_queue(dept_id)
