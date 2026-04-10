from django.db import models
from shared.models import BaseModel, AuditModel


class HelpDeskTicket(AuditModel):
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PENDING_USER = 'pending_user'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    STATUS_ESCALATED = 'escalated'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_PENDING_USER, 'Pending User'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_ESCALATED, 'Escalated'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False)
    subject = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    category = models.CharField(max_length=100, blank=True)

    # Asignación manual
    assigned_to = models.UUIDField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)

    # Fechas de ciclo de vida
    sla_deadline = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Datos del clasificador — base para ML en Fase 2
    suggested_category = models.CharField(max_length=100, null=True, blank=True)
    suggested_priority = models.CharField(max_length=10, null=True, blank=True)
    classifier_confidence = models.FloatField(null=True, blank=True)
    suggestion_accepted = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'help_desk_ticket'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.folio}] {self.subject}'


class HelpDeskHistory(BaseModel):
    ticket = models.ForeignKey(
        HelpDeskTicket, on_delete=models.CASCADE, related_name='history'
    )
    field_changed = models.CharField(max_length=50)
    old_value = models.CharField(max_length=200, blank=True)
    new_value = models.CharField(max_length=200, blank=True)
    changed_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'help_desk_history'
        ordering = ['created_at']


class Comment(BaseModel):
    ticket = models.ForeignKey(
        HelpDeskTicket, on_delete=models.CASCADE, related_name='comments'
    )
    author_id = models.UUIDField()
    body = models.TextField()

    class Meta:
        db_table = 'help_desk_comment'
        ordering = ['created_at']


class Attachment(BaseModel):
    ticket = models.ForeignKey(
        HelpDeskTicket, on_delete=models.CASCADE, related_name='attachments'
    )
    uploaded_by = models.UUIDField()
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'help_desk_attachment'
