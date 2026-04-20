from django.db.models import Sum
from django.utils import timezone

from apps.helpdesks.models import HelpDesk
from config.business_hours import add_business_hours, is_business_hours
from .models import SLAConfig, ServiceQueue, TechnicianProfile

ACTIVE_STATUSES = ('open', 'in_progress', 'on_hold')

_DEFAULT_CONFIG = {
    'max_load': 3,
    'score_overdue': 1000,
    'score_company': 100,
    'score_area': 50,
    'score_individual': 10,
    'score_critical': 40,
    'score_high': 30,
    'score_medium': 20,
    'score_low': 10,
}


def get_config(department):
    config = SLAConfig.objects.filter(department=department).first()
    if config is None:
        config = SLAConfig.objects.filter(department__isnull=True).first()
    return config


def _config_value(config, key):
    if config is not None:
        return getattr(config, key)
    return _DEFAULT_CONFIG[key]


def compute_urgency_score(hd, config=None):
    if config is None:
        config = get_config(hd.service.category.department)

    score = 0
    if hd.due_date and timezone.now() > hd.due_date:
        score += _config_value(config, 'score_overdue')

    impact_map = {
        'company': 'score_company',
        'area': 'score_area',
        'individual': 'score_individual',
    }
    score += _config_value(config, impact_map.get(hd.impact, 'score_individual'))

    priority_map = {
        'critical': 'score_critical',
        'high': 'score_high',
        'medium': 'score_medium',
        'low': 'score_low',
    }
    score += _config_value(config, priority_map.get(hd.priority, 'score_low'))

    return score


def _get_technician_hours(user_id):
    result = (
        HelpDesk.objects
        .filter(assignee_id=user_id, status__in=ACTIVE_STATUSES)
        .aggregate(total=Sum('estimated_hours'))
    )
    return result['total'] or 0


def try_assign(hd):
    if not is_business_hours():
        return False

    department = hd.service.category.department
    config = get_config(department)
    max_load = _config_value(config, 'max_load')

    technicians = TechnicianProfile.objects.filter(department=department, active=True)

    available = []
    for tech in technicians:
        active_count = HelpDesk.objects.filter(
            assignee_id=tech.user_id, status__in=ACTIVE_STATUSES
        ).count()
        if active_count < max_load:
            hours = _get_technician_hours(tech.user_id)
            available.append((hours, tech.user_id))

    if not available:
        return False

    available.sort(key=lambda x: x[0])
    chosen_user_id = available[0][1]

    now = timezone.now()
    hd.assignee_id = chosen_user_id
    hd.assigned_at = now
    if not hd.due_date:
        hd.due_date = add_business_hours(now, hd.estimated_hours)
    hd.save(update_fields=['assignee_id', 'assigned_at', 'due_date', 'updated_at'])
    return True


def enqueue(hd):
    department = hd.service.category.department
    config = get_config(department)
    score = compute_urgency_score(hd, config)
    ServiceQueue.objects.update_or_create(
        help_desk=hd,
        defaults={'urgency_score': score},
    )


def process_queue(department_id):
    from apps.catalog.models import Department
    try:
        department = Department.objects.get(pk=department_id)
    except Department.DoesNotExist:
        return

    queued = (
        ServiceQueue.objects
        .filter(help_desk__service__category__department=department)
        .select_related('help_desk__service__category__department')
        .order_by('-urgency_score', 'queued_at')
    )

    if not queued.exists():
        return

    config = get_config(department)

    # Recalculate scores before picking (some may now be overdue)
    for entry in queued:
        new_score = compute_urgency_score(entry.help_desk, config)
        if new_score != entry.urgency_score:
            entry.urgency_score = new_score
            entry.save(update_fields=['urgency_score'])

    # Re-fetch ordered after score update
    queued = (
        ServiceQueue.objects
        .filter(help_desk__service__category__department=department)
        .select_related('help_desk__service__category__department')
        .order_by('-urgency_score', 'queued_at')
    )

    for entry in queued:
        assigned = try_assign(entry.help_desk)
        if assigned:
            entry.delete()
        else:
            break  # All technicians saturated, no point continuing
