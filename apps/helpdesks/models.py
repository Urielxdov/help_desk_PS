"""
Modelos del dominio de Help Desk.

A HelpDesk represents a support ticket initiated by a user of the external system.
It traverses a controlled lifecycle (see VALID_TRANSITIONS) and can carry
attachments and comments.

Internal dependencies: apps.catalog (Service)
"""
from django.db import models
from apps.catalog.models import Service

ORIGIN_CHOICES = [
    ('error', 'Error'),
    ('request', 'Request'),
    ('inquiry', 'Inquiry'),
    ('maintenance', 'Maintenance'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

STATUS_CHOICES = [
    ('open', 'Open'),
    ('in_progress', 'In Progress'),
    ('on_hold', 'On Hold'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]

# Ticket lifecycle state machine.
# Normal flow: open → in_progress → resolved → closed.
# on_hold allows pausing a ticket (e.g. waiting for user response)
# and resuming it without losing progress history.
# closed is a terminal state — a closed ticket cannot be reopened.
# Transitions are validated in the view (not the model) to keep
# business logic centralized and testable in one place.
VALID_TRANSITIONS = {
    'open':        ['in_progress'],
    'in_progress': ['on_hold', 'resolved'],
    'on_hold':     ['in_progress', 'resolved'],
    'resolved':    ['closed'],
    'closed':      [],
}

IMPACT_CHOICES = [
    ('individual', 'Individual'),
    ('area', 'Area'),
    ('company', 'Company'),
]

ATTACHMENT_TYPE_CHOICES = [
    ('file', 'File'),
    ('url', 'URL'),
]


class HelpDesk(models.Model):
    """
    Support ticket. Central entity of the system.

    The folio (e.g. HD-000001) is the visible identifier for the end user.
    Used in emails, reports and phone follow-up — incremental and readable,
    not a UUID. See save().

    requester_id and assignee_id are IDs from the external user system.
    No FK to a local table because identity management is the external
    system's responsibility; this service only stores the numeric reference.

    estimated_hours is inherited from service.estimated_hours at ticket
    creation if the requester does not specify one. See HelpDeskCreateSerializer.
    """
    folio = models.CharField(max_length=20, unique=True, blank=True)
    requester_id = models.IntegerField(null=True, blank=True, db_index=True)
    assignee_id = models.IntegerField(null=True, blank=True, db_index=True)
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name='helpdesks')
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='open', db_index=True)
    problem_description = models.TextField()
    solution_description = models.TextField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    impact = models.CharField(max_length=10, choices=IMPACT_CHOICES, default='individual')
    estimated_hours = models.PositiveIntegerField(help_text='Hours')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'helpdesks_helpdesk'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # The folio depends on the PK, which only exists after the first INSERT.
        # Two writes are required: the first generates the PK,
        # the second persists the folio derived from that PK.
        super().save(*args, **kwargs)
        if not self.folio:
            self.folio = f'HD-{self.pk:06d}'
            super().save(update_fields=['folio'])

    def __str__(self):
        return self.folio


class HDAttachment(models.Model):
    """
    Attachment linked to a ticket. Supports two storage modes:
    - type='file': the file is physically persisted via FileStorage;
      value stores the internal path returned by storage.save().
    - type='url': reference to an external resource; value stores the URL.

    Physical storage is decoupled from the model in storage.py,
    allowing migration from local storage to S3 or Azure without
    modifying this model or the views.
    """
    help_desk = models.ForeignKey(HelpDesk, on_delete=models.CASCADE, related_name='attachments')
    type = models.CharField(max_length=10, choices=ATTACHMENT_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    value = models.TextField(help_text='File path or URL')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'helpdesks_hdattachment'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.help_desk.folio} — {self.name}'


class HDComment(models.Model):
    """
    Comment on a ticket. Can be public or internal to the IT team.

    Comments with is_internal=True are internal notes from the technical team
    that should not be shown to users with the 'user' role. Filtering is applied
    in HDCommentViewSet.get_queryset() (view layer), not here, so the model
    does not assume the authentication context.

    author_id is the external system ID; can be None if the comment was
    created by an automated process or anonymous user.
    """
    help_desk = models.ForeignKey(HelpDesk, on_delete=models.CASCADE, related_name='comments')
    author_id = models.IntegerField(null=True, blank=True)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Only visible to IT')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'helpdesks_hdcomment'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.help_desk.folio} — comment {self.pk}'
