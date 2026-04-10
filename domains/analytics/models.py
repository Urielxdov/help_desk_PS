from django.db import models
from shared.models import BaseModel


class HelpDeskSnapshot(BaseModel):
    """
    Foto del estado de un ticket en cada evento relevante.
    Solo escribe — nunca modifica datos operativos.
    Es la fuente de verdad para análisis y entrenamiento en Fase 2.
    """
    EVENT_CHOICES = [
        ('created', 'Created'),
        ('status_changed', 'Status Changed'),
        ('deadline_set', 'Deadline Set'),
        ('closed', 'Closed'),
    ]

    ticket_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)

    # Estado en el momento del evento
    status = models.CharField(max_length=20)
    priority = models.CharField(max_length=10)
    category = models.CharField(max_length=100, blank=True)
    assigned_to = models.UUIDField(null=True, blank=True)
    comment_count = models.PositiveIntegerField(default=0)
    was_escalated = models.BooleanField(default=False)

    # Tiempos
    time_in_state = models.DurationField(null=True, blank=True)
    resolution_time = models.DurationField(null=True, blank=True)

    # Datos del clasificador — clave para entrenamiento
    suggested_category = models.CharField(max_length=100, null=True, blank=True)
    suggested_priority = models.CharField(max_length=10, null=True, blank=True)
    accepted_category = models.CharField(max_length=100, null=True, blank=True)
    accepted_priority = models.CharField(max_length=10, null=True, blank=True)
    suggestion_accepted = models.BooleanField(null=True, blank=True)
    classifier_confidence = models.FloatField(null=True, blank=True)

    # Estado completo serializado — para consultas ad-hoc y re-entrenamiento
    snapshot_data = models.JSONField(default=dict)

    class Meta:
        db_table = 'analytics_help_desk_snapshot'
        ordering = ['-created_at']

    def __str__(self):
        return f'Snapshot({self.ticket_id} | {self.event_type})'
