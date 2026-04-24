from django.db import models
from django.utils import timezone

from apps.catalog.models import Department
from apps.helpdesks.models import HelpDesk


class TechnicianProfile(models.Model):
    """
    Vincula técnicos del sistema externo con el departamento donde trabajan.

    Representa la identidad de un técnico dentro del contexto SLA. El user_id
    viene del sistema externo de usuarios (OAuth/LDAP), no de Django.
    Los técnicos activos son elegibles para recibir asignaciones automáticas
    de tickets; los inactivos se excluyen del pool de asignación.
    """
    user_id = models.IntegerField(
        unique=True,
        help_text="ID del técnico en el sistema externo de autenticación"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='technicians',
        help_text="Departamento donde el técnico proporciona soporte"
    )
    active = models.BooleanField(
        default=True,
        help_text="Si es True, el técnico recibe asignaciones automáticas. Si es False, queda excluido"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp de creación del perfil"
    )

    class Meta:
        db_table = 'sla_technicianprofile'
        ordering = ['user_id']

    def __str__(self):
        return f'Technician #{self.user_id} — {self.department.name}'


class SLAConfig(models.Model):
    """
    Define políticas de asignación y ponderación de urgencia por departamento.

    La configuración SLA controla:
    1. Carga máxima (max_load): cuántos tickets activos puede atender un técnico
    2. Pesos de urgencia: cómo se calcula la prioridad de un ticket en la cola

    Si un departamento tiene SLAConfig propia, se usa esa. Si no, se usa la
    config global (department=null). Si tampoco existe config global, se
    aplican valores hardcodeados por defecto.

    La urgencia se calcula como: base + puntajes_de_impacto + puntajes_de_prioridad.
    Ejemplo: ticket vencido (1000) de impacto empresa (100) con prioridad alta (30)
    = 1130 puntos.
    """
    department = models.OneToOneField(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sla_config',
        help_text="Departamento (null = config global para todos los departamentos)"
    )
    max_load = models.PositiveIntegerField(
        default=3,
        help_text="Máximo de tickets simultáneos (estado open/in_progress/on_hold) que un técnico puede llevar"
    )

    RESOLUTION_UNIT_CHOICES = [
        ('business_hours', 'Horas hábiles'),
        ('calendar_hours', 'Horas calendario'),
        ('calendar_days', 'Días calendario'),
    ]
    resolution_time = models.PositiveIntegerField(
        default=72,
        help_text="Tiempo máximo para resolver un ticket según la unidad configurada"
    )
    resolution_unit = models.CharField(
        max_length=20,
        choices=RESOLUTION_UNIT_CHOICES,
        default='business_hours',
        help_text="Unidad en que se expresa resolution_time"
    )

    # Urgency score weights — Puntajes base
    score_overdue = models.IntegerField(
        default=1000,
        help_text="Puntaje base si el ticket está vencido (due_date < ahora). Siempre domina la cola"
    )

    # Impact scores — Clasificación del impacto del ticket
    score_company = models.IntegerField(
        default=100,
        help_text="Puntaje adicional si impact='company' (afecta a la empresa entera)"
    )
    score_area = models.IntegerField(
        default=50,
        help_text="Puntaje adicional si impact='area' (afecta un área o grupo)"
    )
    score_individual = models.IntegerField(
        default=10,
        help_text="Puntaje adicional si impact='individual' (afecta a una persona, valor por defecto)"
    )

    # Priority scores — Nivel de urgencia
    score_critical = models.IntegerField(
        default=40,
        help_text="Puntaje adicional si priority='critical' (problema grave, sistema caído)"
    )
    score_high = models.IntegerField(
        default=30,
        help_text="Puntaje adicional si priority='high' (problema importante)"
    )
    score_medium = models.IntegerField(
        default=20,
        help_text="Puntaje adicional si priority='medium' (problema normal)"
    )
    score_low = models.IntegerField(
        default=10,
        help_text="Puntaje adicional si priority='low' (solicitud, mejora, no urgente)"
    )
    incident_threshold = models.PositiveIntegerField(
        default=5,
        help_text=(
            "Cantidad mínima de tickets activos del mismo servicio para considerarlo "
            "candidato a incidente en la vista de monitoreo. "
            "0 = usar el default global de settings."
        )
    )

    class Meta:
        db_table = 'sla_slaconfig'

    def __str__(self):
        return f'SLAConfig — {self.department.name if self.department else "Global"}'


class ServiceQueue(models.Model):
    """
    Cola de tickets en espera de asignación a técnico disponible.

    Un ticket entra a la cola cuando se crea pero todos los técnicos del
    departamento están en max_load (saturados). La cola se ordena por:
    1. urgency_score descend (más urgente primero)
    2. queued_at asc (FIFO como desempate)

    El urgency_score se recalcula periódicamente (cada 15 min) para que
    tickets que se vencen durante la espera suban de prioridad automáticamente.

    Cuando un técnico se libera (resuelve/cierra un ticket), el sistema
    intenta asignar el primer ticket de la cola. Si se asigna, la entrada
    de ServiceQueue se elimina.
    """
    help_desk = models.OneToOneField(
        HelpDesk,
        on_delete=models.CASCADE,
        related_name='queue_entry',
        help_text="El ticket en la cola (sin asignee aún)"
    )
    queued_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Momento en que el ticket entró a la cola"
    )
    urgency_score = models.IntegerField(
        default=0,
        help_text="Puntaje de urgencia calculado (sum de overdue + impact + priority). Recalculado cada 15 min"
    )

    class Meta:
        db_table = 'sla_servicequeue'
        ordering = ['-urgency_score', 'queued_at']

    def __str__(self):
        return f'Queue: {self.help_desk.folio} (score={self.urgency_score})'
