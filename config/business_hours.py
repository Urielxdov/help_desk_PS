from datetime import time, timedelta

from django.utils import timezone

BUSINESS_START = time(8, 30)
BUSINESS_END = time(18, 0)


def _local_naive(dt):
    if timezone.is_aware(dt):
        return timezone.localtime(dt).replace(tzinfo=None)
    return dt


def is_business_hours(dt=None):
    if dt is None:
        dt = timezone.now()
    local = _local_naive(dt)
    return local.weekday() < 5 and BUSINESS_START <= local.time() < BUSINESS_END


def next_business_start(dt):
    """Returns next valid business datetime (08:30) from dt."""
    local = _local_naive(dt)

    if local.weekday() < 5 and local.time() < BUSINESS_START:
        candidate = local.replace(hour=8, minute=30, second=0, microsecond=0)
    else:
        candidate = (local + timedelta(days=1)).replace(hour=8, minute=30, second=0, microsecond=0)

    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)

    return timezone.make_aware(candidate, timezone.get_current_timezone())


def add_business_hours(start, hours):
    """
    Adds `hours` business hours to `start` (Mon-Fri 08:30-18:00).
    If start is outside business hours, advances to next business start first.
    Returns a timezone-aware datetime.
    """
    local = _local_naive(start)

    if not is_business_hours(start):
        local = _local_naive(next_business_start(start))

    remaining = float(hours)

    while remaining > 0:
        end_of_day = local.replace(hour=18, minute=0, second=0, microsecond=0)
        hours_left = (end_of_day - local).total_seconds() / 3600

        if remaining <= hours_left:
            local += timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= hours_left
            local = _local_naive(next_business_start(end_of_day))

    return timezone.make_aware(local, timezone.get_current_timezone())
