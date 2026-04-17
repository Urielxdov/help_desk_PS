from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.helpdesks.models import HelpDesk
from .models import TechnicianProfile


@receiver(post_save, sender=HelpDesk)
def on_helpdesk_save(sender, instance, created, **kwargs):
    from .tasks import auto_assign_helpdesk, process_department_queue

    if created:
        auto_assign_helpdesk.delay(instance.pk)
        return

    # When a HD is resolved or closed, try to dequeue the next one
    if instance.status in ('resolved', 'closed'):
        dept_id = instance.service.category.department_id
        process_department_queue.delay(dept_id)


@receiver(post_save, sender=TechnicianProfile)
def on_technician_profile_save(sender, instance, **kwargs):
    from .tasks import process_department_queue

    if instance.active:
        process_department_queue.delay(instance.department_id)
