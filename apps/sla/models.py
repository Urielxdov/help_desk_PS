from django.db import models
from django.utils import timezone

from apps.catalog.models import Department
from apps.helpdesks.models import HelpDesk


class TechnicianProfile(models.Model):
    user_id = models.IntegerField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='technicians')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sla_technicianprofile'
        ordering = ['user_id']

    def __str__(self):
        return f'Technician #{self.user_id} — {self.department.name}'


class SLAConfig(models.Model):
    department = models.OneToOneField(
        Department, on_delete=models.CASCADE,
        null=True, blank=True, related_name='sla_config',
    )
    max_load = models.PositiveIntegerField(default=3)

    # Urgency score weights
    score_overdue = models.IntegerField(default=1000)
    score_company = models.IntegerField(default=100)
    score_area = models.IntegerField(default=50)
    score_individual = models.IntegerField(default=10)
    score_critical = models.IntegerField(default=40)
    score_high = models.IntegerField(default=30)
    score_medium = models.IntegerField(default=20)
    score_low = models.IntegerField(default=10)

    class Meta:
        db_table = 'sla_slaconfig'

    def __str__(self):
        return f'SLAConfig — {self.department.name if self.department else "Global"}'


class ServiceQueue(models.Model):
    help_desk = models.OneToOneField(HelpDesk, on_delete=models.CASCADE, related_name='queue_entry')
    queued_at = models.DateTimeField(auto_now_add=True)
    urgency_score = models.IntegerField(default=0)

    class Meta:
        db_table = 'sla_servicequeue'
        ordering = ['-urgency_score', 'queued_at']

    def __str__(self):
        return f'Queue: {self.help_desk.folio} (score={self.urgency_score})'
